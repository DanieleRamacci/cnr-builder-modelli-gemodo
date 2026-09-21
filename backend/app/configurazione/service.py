from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.catalog.models import TipoDocumento
from app.common.errors import DomainError
from app.common.security import PrincipalGEMODO, ensure_roles
from app.configurazione import repository
from app.configurazione.models import AttributoProfilo, AuditEventoConfigurazione, AuditEventoIntegrazione, DefinizioneStruttura, EndpointIntegrazione, Integrazione, SchemaDiscoveryGenerato
from app.configurazione.schemas import (
    ErroreVerifica,
    IntegrazioneAdmin,
    IntegrazioneCreate,
    IntegrazioneUpdate,
    SchemaResponse,
    StrutturaInput,
    TipoDocumentoCreate,
    TipoDocumentoDashboard,
    UltimaVerifica,
)
from app.configurazione.security import ROLE_GEMODO_ADMIN
from app.core.settings import get_settings
from app.db.session import get_db
from app.discovery.adapter_http import AdapterHTTP
from app.discovery.egress import valida_destinazione_approvata
from app.discovery.errors import DiscoveryError
from app.discovery.schemas import VERSIONE_CONTRATTO_DISCOVERY, CatalogoDiscovery

# Verification runs synchronously inside one request; this margin above the endpoint's
# own HTTP timeout is how long a reserved tentativo blocks a concurrent verify before
# it is treated as abandoned (a crash never leaves a permanent lock).
MARGINE_TENTATIVO_SECONDI = 5


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
            livello = next((a for a in profilo.attributi if a.nome == "livello"), None)
            foglia = {
                "codice": profilo.codice,
                "descrizione": profilo.descrizione,
                "tipo_livello": "profilo",
                "campi": campi,
                "lingue_possibili": struttura.lingue_possibili,
                "attributi": {
                    a.nome: {"valori_ammessi": a.valori_ammessi, "valore_default": a.valore_default}
                    for a in profilo.attributi
                },
            }
            if livello is not None:
                foglia["livelli_possibili"] = livello.valori_ammessi
                foglia["livello_base"] = livello.valore_default
            figli.append(foglia)
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


def _proietta_integrazione(source: Integrazione, endpoint: EndpointIntegrazione | None) -> IntegrazioneAdmin:
    ultima_verifica = None
    if endpoint is not None and endpoint.data_ultimo_test is not None:
        esito = endpoint.esito_ultimo_test or {}
        ultima_verifica = UltimaVerifica(
            data=endpoint.data_ultimo_test,
            revisione=endpoint.revisione_verificata,
            versione_contratto=endpoint.versione_contratto_verificata,
            esito=esito.get("esito", "NON_CONFORME"),
            errori=[ErroreVerifica(**errore) for errore in esito.get("errori", [])],
        )
    return IntegrazioneAdmin(
        id=source.id, codice=source.codice, nome=source.nome, codice_contesto=source.codice_contesto,
        modalita=source.modalita, revisione=source.revisione,
        url=endpoint.url if endpoint else None,
        timeout_ms=endpoint.timeout_ms if endpoint else 5000,
        stato=endpoint.stato if endpoint else "DEFINITO",
        ultima_verifica=ultima_verifica,
    )


class IntegrazioniService:
    """Admin registry/configuration/verification for T081 (contract T078).

    Registration never connects automatically (ADR 0002): creating an ``Integrazione``
    only reserves its identity; configuring a URL requires a separate verification
    before the dashboard reports it as ``CONNESSO``.
    """

    def __init__(self, db: Session):
        self.db = db

    def _integrazione(self, integrazione_id: uuid.UUID, *, lock: bool = False) -> Integrazione:
        source = repository.integrazione(self.db, integrazione_id, lock=lock)
        if source is None:
            raise DomainError("RISORSA_NON_TROVATA", "Integrazione non trovata", status_code=404)
        return source

    def _audit(self, integrazione_id: uuid.UUID, principal: PrincipalGEMODO, evento: str, payload: dict) -> None:
        self.db.add(AuditEventoIntegrazione(
            integrazione_id=integrazione_id, tipo_evento=evento,
            soggetto_id=principal.subject, client_id=principal.client_id, payload_minimo=payload,
        ))

    def lista(self, principal: PrincipalGEMODO) -> list[IntegrazioneAdmin]:
        ensure_roles(principal, (ROLE_GEMODO_ADMIN,))
        return [_proietta_integrazione(source, repository.endpoint(self.db, source.id))
                for source in repository.integrazioni(self.db)]

    def ottieni(self, integrazione_id: uuid.UUID, principal: PrincipalGEMODO) -> IntegrazioneAdmin:
        ensure_roles(principal, (ROLE_GEMODO_ADMIN,))
        source = self._integrazione(integrazione_id)
        return _proietta_integrazione(source, repository.endpoint(self.db, source.id))

    def crea(self, request: IntegrazioneCreate, principal: PrincipalGEMODO) -> IntegrazioneAdmin:
        ensure_roles(principal, (ROLE_GEMODO_ADMIN,))
        source = Integrazione(codice=request.codice, nome=request.nome, codice_contesto=request.codice_contesto)
        self.db.add(source)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise DomainError("INTEGRAZIONE_DUPLICATA", "Codice integrazione gia' registrato", status_code=409) from exc
            raise
        self._audit(source.id, principal, "INTEGRAZIONE_CREATA", {"codice": source.codice})
        self.db.flush()
        result = _proietta_integrazione(source, None)
        self.db.commit()
        return result

    def configura(self, integrazione_id: uuid.UUID, request: IntegrazioneUpdate, principal: PrincipalGEMODO) -> IntegrazioneAdmin:
        ensure_roles(principal, (ROLE_GEMODO_ADMIN,))
        source = self._integrazione(integrazione_id, lock=True)
        if source.revisione != request.revisione_attesa:
            raise DomainError("REVISIONE_SUPERATA", "Rileggere la configurazione corrente", status_code=409)
        endpoint = repository.endpoint(self.db, source.id, lock=True)
        url_precedente = endpoint.url if endpoint else None
        timeout_precedente = endpoint.timeout_ms if endpoint else None
        richiede_riverifica = request.url != url_precedente or (
            request.url is not None and request.timeout_ms != timeout_precedente
        )
        if request.url is not None:
            valida_destinazione_approvata(request.url, get_settings())
        source.nome = request.nome
        source.revisione += 1
        source.updated_at = datetime.now(timezone.utc)
        if request.url is None:
            if endpoint is not None:
                self.db.delete(endpoint)
                endpoint = None
        elif endpoint is None:
            endpoint = EndpointIntegrazione(integrazione_id=source.id, url=request.url, timeout_ms=request.timeout_ms)
            self.db.add(endpoint)
        else:
            endpoint.url = request.url
            endpoint.timeout_ms = request.timeout_ms
            endpoint.updated_at = datetime.now(timezone.utc)
        if richiede_riverifica and endpoint is not None:
            endpoint.stato = "DEFINITO"
            endpoint.revisione_verificata = None
            endpoint.versione_contratto_verificata = None
            endpoint.esito_ultimo_test = None
            endpoint.data_ultimo_test = None
            endpoint.tentativo_id = None
            endpoint.tentativo_scadenza = None
        self._audit(source.id, principal, "INTEGRAZIONE_CONFIGURATA", {
            "revisione": source.revisione, "riverifica_richiesta": richiede_riverifica,
        })
        self.db.flush()
        result = _proietta_integrazione(source, endpoint)
        self.db.commit()
        return result

    def verifica(self, integrazione_id: uuid.UUID, revisione_attesa: int, principal: PrincipalGEMODO) -> IntegrazioneAdmin:
        ensure_roles(principal, (ROLE_GEMODO_ADMIN,))
        ora = datetime.now(timezone.utc)
        source = self._integrazione(integrazione_id, lock=True)
        if source.revisione != revisione_attesa:
            raise DomainError("REVISIONE_SUPERATA", "Rileggere la configurazione corrente", status_code=409)
        endpoint = repository.endpoint(self.db, source.id, lock=True)
        if endpoint is None or not endpoint.url:
            raise DomainError("CONFIGURAZIONE_NON_VALIDA", "Nessun endpoint configurato per la verifica", status_code=422)
        if endpoint.tentativo_id is not None and endpoint.tentativo_scadenza is not None and endpoint.tentativo_scadenza > ora:
            raise DomainError("VERIFICA_IN_CORSO", "Verifica gia' avviata", status_code=409)
        valida_destinazione_approvata(endpoint.url, get_settings())
        tentativo_id = uuid.uuid4()
        endpoint.tentativo_id = tentativo_id
        endpoint.tentativo_scadenza = ora + timedelta(seconds=endpoint.timeout_ms / 1000 + MARGINE_TENTATIVO_SECONDI)
        endpoint_id, url, timeout_ms = endpoint.id, endpoint.url, endpoint.timeout_ms
        self.db.commit()  # Release the row locks before the HTTP call, which can take up to timeout_ms.

        esito, errori = self._esegui_verifica_http(url, timeout_ms)
        completato_il = datetime.now(timezone.utc)

        source = self._integrazione(integrazione_id, lock=True)
        endpoint = repository.endpoint(self.db, source.id, lock=True)
        if (
            endpoint is None or endpoint.id != endpoint_id
            or endpoint.tentativo_id != tentativo_id or source.revisione != revisione_attesa
        ):
            raise DomainError("REVISIONE_SUPERATA", "La configurazione e' cambiata durante la verifica", status_code=409)
        endpoint.stato = "CONNESSO" if esito == "CONFORME" else "ERRORE"
        endpoint.revisione_verificata = revisione_attesa
        endpoint.versione_contratto_verificata = VERSIONE_CONTRATTO_DISCOVERY
        endpoint.data_ultimo_test = completato_il
        endpoint.esito_ultimo_test = {"esito": esito, "errori": errori}
        endpoint.tentativo_id = None
        endpoint.tentativo_scadenza = None
        self._audit(source.id, principal, "INTEGRAZIONE_VERIFICATA", {"esito": esito, "revisione": revisione_attesa})
        self.db.flush()
        result = _proietta_integrazione(source, endpoint)
        self.db.commit()
        return result

    @staticmethod
    def _esegui_verifica_http(url: str, timeout_ms: int) -> tuple[str, list[dict]]:
        try:
            AdapterHTTP(url, timeout_seconds=timeout_ms / 1000).mappa_discovery(forza_aggiornamento=True)
            return "CONFORME", []
        except DiscoveryError as exc:
            esito = "NON_CONFORME" if exc.codice == "DISCOVERY_NON_CONFORME" else "NON_RAGGIUNGIBILE"
            return esito, [{"codice": exc.codice, "messaggio": exc.messaggio}]


def get_integrazioni_service(db: Session = Depends(get_db)):
    return IntegrazioniService(db)
