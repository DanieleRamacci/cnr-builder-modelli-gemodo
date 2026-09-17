from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.catalog.models import TipoDocumento
from app.common.errors import DomainError
from app.common.security import PrincipalGEMODO, ensure_roles
from app.configurazione import repository
from app.configurazione.models import AttributoProfilo, AuditEventoConfigurazione, AuditEventoIntegrazione, DefinizioneStruttura, Integrazione, SchemaDiscoveryGenerato
from app.configurazione.schemas import SchemaResponse, StrutturaInput, TipoDocumentoCreate, TipoDocumentoDashboard
from app.db.session import get_db
from app.discovery.schemas import CatalogoDiscovery


def documentazione(codice: str, struttura: StrutturaInput, validita: datetime) -> dict:
    profili = {p.codice: p for p in struttura.profili}
    nodi = []
    for tipo in struttura.tipologie:
        figli = []
        for combo in struttura.combinazioni:
            if combo.codice_tipologia != tipo.codice:
                continue
            profilo = profili[combo.codice_profilo]
            attributi = {a.nome: a for a in profilo.attributi}
            campi = []
            for campo in struttura.campi:
                item = campo.model_dump(exclude_none=True, exclude={"dipende_da_attributo_profilo"})
                if campo.dipende_da_attributo_profilo is not None:
                    attr = attributi[campo.dipende_da_attributo_profilo]
                    item["validazione"] = {**(campo.validazione or {}), "enum": attr.valori_ammessi}
                    if attr.valore_default is not None:
                        item["validazione"]["default"] = attr.valore_default
                campi.append(item)
            figli.append({"codice": profilo.codice, "descrizione": profilo.descrizione,
                          "tipo_livello": "profilo", "campi": campi,
                          "attributi": {a.nome: {"valori_ammessi": a.valori_ammessi,
                                               "valore_default": a.valore_default} for a in profilo.attributi}})
        nodi.append({"codice": tipo.codice, "descrizione": tipo.descrizione,
                     "tipo_livello": "tipologia", "figli": figli})
    body = {"validita": validita.isoformat(), "nodi": nodi}
    # Validate the generated example with the same DTOs used by the HTTP adapter.
    CatalogoDiscovery(codice_tipo_documento=codice, **body)
    return {codice: body}


def dashboard_response(tipo, definizione, schema, endpoint) -> TipoDocumentoDashboard:
    completa = definizione is not None and not StrutturaInput.model_validate(definizione.contenuto).mancanze()
    corrente = schema if definizione is not None and schema is not None and schema.definizione_struttura_id == definizione.id else None
    stato = "DEFINITO" if completa else "INCOMPLETO"
    if endpoint is not None:
        stato = endpoint.stato
    return TipoDocumentoDashboard(
        codice=tipo.codice, nome=tipo.nome, codice_contesto=tipo.codice_contesto,
        stato_integrazione=stato, versione_schema_corrente=corrente.versione if corrente else None,
        versione_definizione=definizione.versione if definizione else None,
        esito_ultimo_test=endpoint.esito_ultimo_test if endpoint else None,
        data_ultimo_test=endpoint.data_ultimo_test if endpoint else None,
    )


class ConfigurazioneService:
    def __init__(self, db: Session):
        self.db = db

    def associa_tipo(self, tipo_id, integrazione_id, principal: PrincipalGEMODO):
        ensure_roles(principal, ("GEMODO_ADMIN",))
        source = self.db.scalar(select(Integrazione).where(Integrazione.id == integrazione_id)
                                .with_for_update().execution_options(populate_existing=True))
        tipo = self.db.get(TipoDocumento, tipo_id, with_for_update=True, populate_existing=True)
        if source is None or tipo is None:
            raise DomainError("RISORSA_NON_TROVATA", "Risorsa non disponibile", status_code=404)
        if tipo.codice_contesto != source.codice_contesto:
            raise DomainError("CONTESTO_NON_VALIDO", "Contesti non coerenti", status_code=409)
        if tipo.integrazione_id is not None and tipo.integrazione_id != source.id:
            raise DomainError("OWNERSHIP_GIA_ASSOCIATA", "Tipo gia' associato a un'altra integrazione", status_code=409)
        tipo.integrazione_id = source.id
        self.db.add(AuditEventoIntegrazione(
            integrazione_id=source.id, tipo_evento="TIPO_ASSOCIATO", soggetto_id=principal.subject,
            client_id=principal.client_id, payload_minimo={"tipo_documento_id": str(tipo.id)},
        ))
        try:
            self.db.flush()
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise DomainError("TIPO_DOCUMENTO_ALREADY_EXISTS", "Tipo gia' presente nell'integrazione", status_code=409) from exc
            raise
        return tipo

    def _tipo(self, codice, *, lock=False):
        tipo = repository.tipo_documento(self.db, codice, lock=lock)
        if tipo is None:
            raise DomainError("TIPO_DOCUMENTO_NOT_FOUND", "Tipo documento non trovato", status_code=404)
        return tipo

    def _audit(self, tipo_id, principal: PrincipalGEMODO, evento: str, payload: dict):
        self.db.add(AuditEventoConfigurazione(
            tipo_documento_id=tipo_id, tipo_evento=evento, soggetto_id=principal.subject,
            client_id=principal.client_id, payload_minimo=payload,
        ))

    def _salva(self, tipo, struttura, principal, evento):
        precedente = repository.definizione_corrente(self.db, tipo.id)
        definizione = DefinizioneStruttura(
            tipo_documento_id=tipo.id, versione=precedente.versione + 1 if precedente else 1,
            contenuto=struttura.model_dump(mode="json"),
        )
        self.db.add(definizione)
        self.db.execute(delete(AttributoProfilo).where(AttributoProfilo.tipo_documento_id == tipo.id))
        for profilo in struttura.profili:
            for attributo in profilo.attributi:
                self.db.add(AttributoProfilo(
                    tipo_documento_id=tipo.id, percorso_profilo=[profilo.codice],
                    codice=attributo.nome, valori_ammessi=attributo.valori_ammessi,
                    valore_default=attributo.valore_default,
                ))
        endpoint = repository.endpoint(self.db, tipo.integrazione_id)
        self._audit(tipo.id, principal, evento, {"versione_definizione": definizione.versione})
        self.db.flush()
        response = dashboard_response(tipo, definizione, repository.schema_discovery(self.db, tipo.id), endpoint)
        self.db.commit()
        return response

    def crea(self, request: TipoDocumentoCreate, principal):
        tipo = TipoDocumento(codice=request.codice, nome=request.nome,
                             codice_contesto=request.codice_contesto, stato="BOZZA", spec_owner="010")
        self.db.add(tipo)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise DomainError("TIPO_DOCUMENTO_ALREADY_EXISTS", "Tipo documento gia' configurato", status_code=409) from exc
            raise
        return self._salva(tipo, request.struttura, principal, "TIPO_DOCUMENTO_CREATO")

    def aggiorna(self, codice, struttura, principal):
        return self._salva(self._tipo(codice, lock=True), struttura, principal, "STRUTTURA_MODIFICATA")

    def genera(self, codice, principal):
        tipo = self._tipo(codice, lock=True)
        definizione = repository.definizione_corrente(self.db, tipo.id)
        struttura = StrutturaInput.model_validate(definizione.contenuto) if definizione else StrutturaInput()
        missing = struttura.mancanze()
        if missing:
            raise DomainError("DEFINIZIONE_INCOMPLETA", "Definizione incompleta: " + ", ".join(missing), status_code=400)
        schema = SchemaDiscoveryGenerato(
            tipo_documento_id=tipo.id, definizione_struttura_id=definizione.id,
            versione=repository.prossima_versione_schema(self.db, tipo.id),
            contenuto=documentazione(codice, struttura, datetime.now(timezone.utc)), generato_da=principal.subject,
        )
        self.db.add(schema)
        self.db.flush()
        self._audit(tipo.id, principal, "SCHEMA_GENERATO", {"versione_schema": schema.versione, "versione_definizione": definizione.versione})
        self.db.commit()
        return self._schema_response(codice, schema)

    def esporta(self, codice, versione, principal):
        tipo = self._tipo(codice)
        schema = repository.schema_discovery(self.db, tipo.id, versione)
        if schema is None:
            raise DomainError("SCHEMA_DISCOVERY_NOT_FOUND", "Schema discovery non trovato", status_code=404)
        self._audit(tipo.id, principal, "SCHEMA_ESPORTATO", {"versione_schema": versione})
        self.db.commit()
        return self._schema_response(codice, schema)

    @staticmethod
    def _schema_response(codice, schema):
        return SchemaResponse(codice_tipo_documento=codice, versione=schema.versione,
                              generato_il=schema.generato_il, schema_documentazione=schema.contenuto)

    def dashboard(self):
        return [dashboard_response(*row) for row in repository.dashboard(self.db)]


def get_configurazione_service(db: Session = Depends(get_db)):
    return ConfigurazioneService(db)
