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
    ModalitaCatalogo,
    ModelloCatalogoSchema,
    ModelloSearchResponse,
    TipoCampo,
)
from app.common.errors import CatalogError, ErrorCode
from app.db.session import get_db


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search_modelli(
        self,
        *,
        tipo_documento: str,
        categoria: str | None = None,
        codice_tipologia: str | None = None,
        modalita: ModalitaCatalogo = ModalitaCatalogo.OPERATIVA,
        data_riferimento: date | None = None,
        pubblicato_da: date | None = None,
        pubblicato_a: date | None = None,
    ) -> ModelloSearchResponse:
        tipo = repository.get_tipo_documento_by_codice(self.db, tipo_documento)
        if tipo is None or tipo.stato != repository.STATO_ATTIVO:
            raise CatalogError(
                ErrorCode.CONTESTO_NON_VALIDO,
                "Tipo documento non configurato o non attivo",
                status_code=400,
            )

        versions = repository.list_published_model_versions(
            self.db,
            codice_tipo_documento=tipo_documento,
            tipo_documento_id=tipo.id,
            codice_categoria=categoria,
            codice_tipologia=codice_tipologia,
            historical=modalita == ModalitaCatalogo.STORICO,
            data_riferimento=data_riferimento,
            pubblicato_da=pubblicato_da,
            pubblicato_a=pubblicato_a,
        )
        return ModelloSearchResponse(
            tipo_documento=tipo_documento,
            profilo=categoria,
            codice_tipologia=codice_tipologia,
            modalita=modalita,
            modelli=[_modello_catalogo_schema(version) for version in versions],
        )

    def get_campi_richiesti(self, modello_versione_id: int) -> CampiRichiestiResponse:
        version = repository.get_model_version_by_public_id(self.db, modello_versione_id)
        if version is None:
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
        versione=version.versione,
        stato=version.stato,
        data_inizio_validita=_date_only(version.data_inizio_validita),
        data_fine_validita=_date_only(version.data_fine_validita),
        pubblicato_at=version.pubblicato_at or version.pubblicato_il,
    )


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
