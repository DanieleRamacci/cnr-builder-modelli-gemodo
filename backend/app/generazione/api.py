"""Real document generation route, superseding 001's retired simulated placeholder."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.common.security import PrincipalGEMODO, require_documenti_generatore
from app.generazione.service import GenerazioneDocumentiService, get_generazione_documenti_service
from app.validation.schemas import ValidazioneRequest

router = APIRouter(prefix="/api/v1", tags=["generazione"])
Generatore = Annotated[PrincipalGEMODO, Depends(require_documenti_generatore)]
Service = Annotated[GenerazioneDocumentiService, Depends(get_generazione_documenti_service)]


@router.post("/documenti/genera")
def genera_documento(request: ValidazioneRequest, principal: Generatore, service: Service) -> Response:
    risultato = service.genera(request, principal)
    if risultato.contenuto is None:
        return Response(
            content=risultato.esito.model_dump_json(), media_type="application/json",
        )
    return Response(
        content=risultato.contenuto, media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{risultato.nome_file}"',
            "X-Riferimento-Documentale": risultato.esito.riferimento_documentale or "",
        },
    )
