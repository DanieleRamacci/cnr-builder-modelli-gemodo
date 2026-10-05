"""Payload validation routes exposed to GEBAN."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.attivita.registro import registra_attivita
from app.common.security import PrincipalGEMODO, require_documenti_generatore
from app.db.session import get_db
from app.validation.schemas import ValidazioneRequest, ValidazioneResponse
from app.validation.service import PayloadValidationService, get_payload_validation_service

router = APIRouter(prefix="/api/v1", tags=["validazione"])


@router.post("/documenti/valida", response_model=ValidazioneResponse)
def valida_payload(
    request: ValidazioneRequest,
    principal: PrincipalGEMODO = Depends(require_documenti_generatore),
    service: PayloadValidationService = Depends(get_payload_validation_service),
    db: Session = Depends(get_db),
) -> ValidazioneResponse:
    esito = service.validate_payload(request, principal)
    # 013: chi usa le API e con che esito; non ferma mai la risposta.
    registra_attivita(
        db.get_bind(), categoria="VALIDAZIONE", azione="VALIDAZIONE",
        esito="VALIDO" if esito.valido else "DATI_NON_VALIDI", principal=principal,
        oggetto_tipo="modello_versione", oggetto_id=str(request.modello_versione_id),
        dettaglio={
            "sistema_richiedente": request.sistema_richiedente,
            "external_context_id": request.external_context_id,
            "campi_non_validi": sorted({e.campo or e.codice for e in esito.errori}),
        },
    )
    return esito
