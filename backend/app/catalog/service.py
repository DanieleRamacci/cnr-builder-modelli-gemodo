"""Catalog query service for GEBAN-facing APIs."""

from __future__ import annotations

from datetime import date

from fastapi import Depends
from sqlalchemy.orm import Session

from app.catalog import repository
from app.catalog.models import ModelloDocumentoVersione
from app.catalog.schemas import (
    CampiRichiestiResponse,
    CampoRichiestoSchema,
    LinguaCampo,
    LinguaModello,
    ModalitaCatalogo,
    ModelloCatalogoSchema,
    ModelloSearchResponse,
    TipoCampo,
)
from app.builder import repository as builder_repository
from app.catalog.repository import NOME_LIVELLO
from app.common.errors import AuthorizationError, CatalogError, ErrorCode
from app.common.security import PrincipalGEMODO, ROLE_DOCUMENTI_VIEWER, verifica_permesso_contesto
from app.db.session import get_db


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search_modelli(
        self,
        *,
        principal: PrincipalGEMODO,
        tipo_documento: str,
        categoria: str | None = None,
        codice_tipologia: str | None = None,
        lingua: LinguaModello | None = None,
        livello_professionale: str | None = None,
        dimensioni: dict[str, str] | None = None,
        modalita: ModalitaCatalogo = ModalitaCatalogo.OPERATIVA,
        data_riferimento: date | None = None,
        pubblicato_da: date | None = None,
        pubblicato_a: date | None = None,
    ) -> ModelloSearchResponse:
        tipi = repository.list_tipi_documento_attivi_by_codice(self.db, tipo_documento)
        if not tipi:
            raise CatalogError(
                ErrorCode.CONTESTO_NON_VALIDO,
                "Tipo documento non configurato o non attivo",
                status_code=400,
            )
        tipi_autorizzati = [
            tipo for tipo in tipi
            if verifica_permesso_contesto(principal, tipo.codice_contesto, ROLE_DOCUMENTI_VIEWER)
        ]
        if not tipi_autorizzati:
            # Explicit filter on a forbidden perimeter -> sanitized 403 (FR-037),
            # not the same 400 as a nonexistent/inactive tipo documento.
            raise AuthorizationError()

        dimensioni_query = dict(dimensioni or {})
        lingua_richiesta = lingua.value if lingua else None
        for nome, valore_legacy in (
            ("lingua", lingua_richiesta),
            (NOME_LIVELLO, livello_professionale),
        ):
            valore_dimensione = dimensioni_query.pop(nome, None)
            if valore_dimensione is not None and valore_legacy is not None and valore_dimensione != valore_legacy:
                raise CatalogError(
                    "RICHIESTA_NON_VALIDA",
                    f"Valori in conflitto per la dimensione '{nome}'",
                    status_code=400,
                )
            if valore_legacy is None and valore_dimensione is not None:
                if nome == "lingua":
                    lingua_richiesta = valore_dimensione
                else:
                    livello_professionale = valore_dimensione

        query = dict(
            codice_tipo_documento=tipo_documento,
            tipo_documento_ids=[tipo.id for tipo in tipi_autorizzati],
            codice_categoria=categoria,
            codice_tipologia=codice_tipologia,
            lingua=lingua_richiesta,
            livello_professionale=livello_professionale,
            dimensioni=dimensioni_query,
            historical=modalita == ModalitaCatalogo.STORICO,
            data_riferimento=data_riferimento,
            pubblicato_da=pubblicato_da,
            pubblicato_a=pubblicato_a,
        )
        versions = repository.list_published_model_versions(self.db, **query)
        dimensioni_rilassate = self._fallback_per_policy(query, versions, tipi_autorizzati)
        if dimensioni_rilassate:
            versions = repository.list_published_model_versions(self.db, **query)
        fallback_applicato = bool(dimensioni_rilassate)
        return ModelloSearchResponse(
            tipo_documento=tipo_documento,
            profilo=categoria,
            codice_tipologia=codice_tipologia,
            modalita=modalita,
            fallback_applicato=fallback_applicato,
            dimensioni_rilassate=dimensioni_rilassate,
            livello_richiesto=livello_professionale,
            livello_risolto=(
                None if fallback_applicato or not versions else livello_professionale
            ),
            modelli=_raggruppa_edizioni(versions),
        )

    def _fallback_per_policy(self, query: dict, versions: list, tipi) -> list[str]:
        """Rilassa le dimensioni che la policy dichiara generiche (011 FR-010).

        Generalizza DEC-007-FALLBACK-LIVELLO-CATALOGO, che resta valida nel
        merito per il livello ma smette di essere un nome nel codice: il
        fallback scatta dove `consente_valore_generico` e' vero, e non scatta
        altrove. La protezione della lingua - «tornare un'edizione diversa da
        quella esplicitamente richiesta sarebbe scorretto, non solo una
        scorciatoia» - diventa automatica, perche' la sua policy la dichiara
        obbligatoria.

        Rilassa **una dimensione alla volta, in ordine alfabetico**, e si ferma
        al primo risultato non vuoto: l'ordine dev'essere deterministico e non
        dipendere da come l'integrazione elenca le dimensioni.
        """
        if versions:
            return []
        richieste = {
            nome: valore
            for nome, valore in {
                "lingua": query.get("lingua"),
                NOME_LIVELLO: query.get("livello_professionale"),
                **(query.get("dimensioni") or {}),
            }.items()
            if valore is not None
        }
        if not richieste:
            return []
        generiche = {
            p.nome_dimensione
            for tipo in tipi
            for p in builder_repository.policy_dimensioni(self.db, tipo.id)
            if p.consente_valore_generico
        }
        # 011 FR-010 (rivisto, DEC-011-POLICY-NON-INVALIDA-IL-PUBBLICATO): la
        # policy governa cosa si puo' *creare*, non la reperibilita' di cio'
        # che e' gia' pubblicato. Un modello senza quella dimensione e' stato
        # pubblicato quando il generico era ammesso, e dichiara di valere per
        # tutti i valori: chiudere la policy dopo lo rendeva irreperibile per
        # ogni valore, cioe' lo stesso danno che FR-009 vieta quando la causa
        # e' l'albero che cambia. Non indebolisce la protezione originale
        # ("tornare un'edizione diversa da quella richiesta sarebbe
        # scorretto"): un modello generico non e' un'edizione diversa.
        generiche |= {
            nome
            for nome in richieste
            if nome not in generiche
            and any(
                builder_repository.modelli_pubblicati_senza_dimensione(self.db, tipo.id, nome)
                for tipo in tipi
            )
        }
        rilassate: list[str] = []
        for nome in sorted(richieste):
            if nome not in generiche:
                continue
            tentativo = dict(query)
            if nome == "lingua":
                tentativo["lingua"] = None
                tentativo["dimensioni_generiche"] = [
                    *(tentativo.get("dimensioni_generiche") or ()),
                    nome,
                ]
            elif nome == NOME_LIVELLO:
                tentativo["livello_professionale"] = None
                tentativo["solo_livello_generico"] = True
            else:
                tentativo["dimensioni"] = {
                    k: v for k, v in (tentativo.get("dimensioni") or {}).items() if k != nome
                }
                tentativo["dimensioni_generiche"] = [*(tentativo.get("dimensioni_generiche") or ()), nome]
            if repository.list_published_model_versions(self.db, **tentativo):
                query.clear()
                query.update(tentativo)
                rilassate.append(nome)
                break
        return rilassate

    def get_campi_richiesti(self, modello_versione_id: int, principal: PrincipalGEMODO) -> CampiRichiestiResponse:
        version = repository.get_model_version_by_public_id(self.db, modello_versione_id)
        if version is None or not verifica_permesso_contesto(
            principal, version.modello.tipo_documento.codice_contesto, ROLE_DOCUMENTI_VIEWER,
        ):
            # Direct-ID access: nonexistent and out-of-context are the same public
            # response (FR-037) - never reveal that a forbidden version exists.
            raise CatalogError(
                ErrorCode.MODELLO_VERSIONE_NON_TROVATO,
                "Versione modello non trovata",
                status_code=404,
            )
        if version.stato != repository.STATO_PUBBLICATO:
            raise CatalogError(
                ErrorCode.MODELLO_VERSIONE_NON_PUBBLICATO,
                "Versione modello non pubblicata",
                status_code=409,
            )

        fields = repository.list_required_fields(self.db, version.id)
        field_schemas = [_campo_richiesto_schema(field) for field in fields]
        return CampiRichiestiResponse(
            modello_versione_id=modello_versione_id,
            tipo_documento=version.modello.tipo_documento.codice,
            profilo=version.modello.codice_categoria,
            campi=field_schemas,
            schema_=_json_schema_for_fields(field_schemas),
        )


def get_catalog_service(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


def _date_only(value):
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date()
    return value


def _modello_catalogo_schema(version: ModelloDocumentoVersione) -> ModelloCatalogoSchema:
    modello = version.modello
    if modello.public_id is None or version.public_id is None:
        raise CatalogError(ErrorCode.MODELLO_NON_TROVATO, "Modello pubblicato privo di identificativo pubblico", status_code=500)
    return ModelloCatalogoSchema(
        modello_id=modello.public_id,
        modello_versione_id=version.public_id,
        codice=modello.codice,
        descrizione=modello.nome,
        variante=modello.variante,
        lingua=LinguaModello(modello.dimensioni["lingua"]) if modello.dimensioni.get("lingua") else None,
        livello_professionale=modello.dimensioni.get(NOME_LIVELLO),
        dimensioni=dict(modello.dimensioni),
        versione=version.versione,
        stato=version.stato,
        data_inizio_validita=_date_only(version.data_inizio_validita),
        data_fine_validita=_date_only(version.data_fine_validita),
        pubblicato_at=version.pubblicato_at or version.pubblicato_il,
    )


def _raggruppa_edizioni(versions: list[ModelloDocumentoVersione]) -> list[ModelloCatalogoSchema]:
    schemi = {version.modello.id: _modello_catalogo_schema(version) for version in versions}
    radici: list[ModelloCatalogoSchema] = []
    for version in versions:
        schema = schemi[version.modello.id]
        origine_id = version.modello.derivato_da_modello_id
        if origine_id is not None and origine_id in schemi:
            schemi[origine_id].edizioni_derivate.append(schema)
        else:
            radici.append(schema)
    return radici


def _campo_richiesto_schema(field) -> CampoRichiestoSchema:
    return CampoRichiestoSchema(
        codice=field.codice,
        etichetta=field.etichetta,
        tipo=TipoCampo(field.tipo_dato),
        lingua=LinguaCampo(field.lingua or LinguaCampo.IT),
        obbligatorio=field.obbligatorio,
        ordine=field.ordine,
        descrizione=field.descrizione,
        validazione=field.validazione,
    )


def _json_schema_for_fields(fields: list[CampoRichiestoSchema]) -> dict[str, object]:
    required: list[str] = []
    properties: dict[str, dict[str, object]] = {}
    for field in fields:
        field_schema = _json_schema_for_field(field)
        properties[field.codice] = field_schema
        if field.obbligatorio and field.lingua == LinguaCampo.IT:
            required.append(field.codice)
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


def _json_schema_for_field(field: CampoRichiestoSchema) -> dict[str, object]:
    if field.tipo == TipoCampo.DATE:
        schema: dict[str, object] = {"type": "string", "format": "date"}
    else:
        schema = {"type": field.tipo.value}
    if field.descrizione:
        schema["description"] = field.descrizione
    schema["x-gemodo-lingua"] = field.lingua.value
    schema["x-gemodo-obbligatorio"] = field.obbligatorio
    if field.validazione:
        schema.update(field.validazione)
    return schema
