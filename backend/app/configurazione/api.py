from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.common.security import PrincipalGEMODO
from app.configurazione.schemas import SchemaResponse, StrutturaInput, TipoDocumentoCreate, TipoDocumentoDashboard
from app.configurazione.security import require_configurazione_admin
from app.configurazione.service import ConfigurazioneService, get_configurazione_service

router = APIRouter(prefix="/api/v1/configurazione/tipi-documento", tags=["ConfigurazioneCataloghi"])
Admin = Annotated[PrincipalGEMODO, Depends(require_configurazione_admin)]
Service = Annotated[ConfigurazioneService, Depends(get_configurazione_service)]


@router.get("", response_model=list[TipoDocumentoDashboard])
def dashboard(principal: Admin, service: Service):
    return service.dashboard()


@router.post("", response_model=TipoDocumentoDashboard, status_code=201)
def crea(request: TipoDocumentoCreate, principal: Admin, service: Service):
    return service.crea(request, principal)


@router.put("/{codice}/struttura", response_model=TipoDocumentoDashboard)
def aggiorna(codice: str, request: StrutturaInput, principal: Admin, service: Service):
    return service.aggiorna(codice, request, principal)


@router.post("/{codice}/schema-discovery", response_model=SchemaResponse, status_code=201)
def genera(codice: str, principal: Admin, service: Service):
    return service.genera(codice, principal)


@router.get("/{codice}/schema-discovery/{versione}", response_model=SchemaResponse)
def esporta(codice: str, versione: Annotated[int, Path(ge=1)], principal: Admin, service: Service):
    return service.esporta(codice, versione, principal)
