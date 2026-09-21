import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.common.security import PrincipalGEMODO
from app.configurazione.schemas import (
    IntegrazioneAdmin,
    IntegrazioneCreate,
    IntegrazioneUpdate,
    SchemaResponse,
    StrutturaInput,
    TipoDocumentoCreate,
    TipoDocumentoDashboard,
    VerificaRequest,
)
from app.configurazione.security import require_configurazione_admin
from app.configurazione.service import ConfigurazioneService, IntegrazioniService, get_configurazione_service, get_integrazioni_service

router = APIRouter(prefix="/api/v1/configurazione/tipi-documento", tags=["ConfigurazioneCataloghi"])
router_integrazioni = APIRouter(prefix="/api/v1/configurazione/integrazioni", tags=["ConfigurazioneIntegrazioni"])
Admin = Annotated[PrincipalGEMODO, Depends(require_configurazione_admin)]
Service = Annotated[ConfigurazioneService, Depends(get_configurazione_service)]
ServiceIntegrazioni = Annotated[IntegrazioniService, Depends(get_integrazioni_service)]


@router.get("", response_model=list[TipoDocumentoDashboard])
def dashboard(principal: Admin, service: Service):
    return service.dashboard()


@router.delete("/id/{tipo_id}", status_code=204)
def disattiva(tipo_id: uuid.UUID, principal: Admin, service: Service):
    service.disattiva_per_id(tipo_id, principal)


@router.post("", response_model=TipoDocumentoDashboard, status_code=201)
def crea(request: TipoDocumentoCreate, principal: Admin, service: Service):
    return service.crea(request, principal)


@router.get("/{codice}/struttura", response_model=StrutturaInput)
def leggi_struttura(codice: str, principal: Admin, service: Service):
    return service.struttura_corrente(codice)


@router.put("/{codice}/struttura", response_model=TipoDocumentoDashboard)
def aggiorna(codice: str, request: StrutturaInput, principal: Admin, service: Service):
    return service.aggiorna(codice, request, principal)


@router.post("/{codice}/schema-discovery", response_model=SchemaResponse, status_code=201)
def genera(codice: str, principal: Admin, service: Service):
    return service.genera(codice, principal)


@router.get("/{codice}/schema-discovery/{versione}", response_model=SchemaResponse)
def esporta(codice: str, versione: Annotated[int, Path(ge=1)], principal: Admin, service: Service):
    return service.esporta(codice, versione, principal)


@router_integrazioni.get("", response_model=list[IntegrazioneAdmin])
def lista_integrazioni(principal: Admin, service: ServiceIntegrazioni):
    return service.lista(principal)


@router_integrazioni.post("", response_model=IntegrazioneAdmin, status_code=201)
def crea_integrazione(request: IntegrazioneCreate, principal: Admin, service: ServiceIntegrazioni):
    return service.crea(request, principal)


@router_integrazioni.get("/{integrazione_id}", response_model=IntegrazioneAdmin)
def ottieni_integrazione(integrazione_id: uuid.UUID, principal: Admin, service: ServiceIntegrazioni):
    return service.ottieni(integrazione_id, principal)


@router_integrazioni.put("/{integrazione_id}", response_model=IntegrazioneAdmin)
def configura_integrazione(integrazione_id: uuid.UUID, request: IntegrazioneUpdate, principal: Admin, service: ServiceIntegrazioni):
    return service.configura(integrazione_id, request, principal)


@router_integrazioni.post("/{integrazione_id}/verifica", response_model=IntegrazioneAdmin)
def verifica_integrazione(integrazione_id: uuid.UUID, request: VerificaRequest, principal: Admin, service: ServiceIntegrazioni):
    return service.verifica(integrazione_id, request.revisione_attesa, principal)
