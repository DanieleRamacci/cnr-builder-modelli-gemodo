"""Real document generation route, superseding 001's retired simulated placeholder."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.security import PrincipalGEMODO, require_documenti_generatore
from app.generazione.schemas import EsitoGenerazione
from app.generazione.service import GenerazioneDocumentiService, get_generazione_documenti_service
from app.validation.schemas import ValidazioneRequest

router = APIRouter(prefix="/api/v1", tags=["generazione"])
Generatore = Annotated[PrincipalGEMODO, Depends(require_documenti_generatore)]
Service = Annotated[GenerazioneDocumentiService, Depends(get_generazione_documenti_service)]


@router.post("/documenti/genera", response_model=EsitoGenerazione)
def genera_documento(request: ValidazioneRequest, principal: Generatore, service: Service) -> EsitoGenerazione:
    return service.genera(request, principal)
