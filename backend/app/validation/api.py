"""Payload validation routes exposed to GEBAN."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.common.security import PrincipalGEMODO, require_documenti_generatore
from app.validation.schemas import ValidazioneRequest, ValidazioneResponse
from app.validation.service import PayloadValidationService, get_payload_validation_service

router = APIRouter(prefix="/api/v1", tags=["validazione"])


@router.post("/documenti/valida", response_model=ValidazioneResponse)
def valida_payload(
    request: ValidazioneRequest,
    _: PrincipalGEMODO = Depends(require_documenti_generatore),
    service: PayloadValidationService = Depends(get_payload_validation_service),
) -> ValidazioneResponse:
    return service.validate_payload(request)
