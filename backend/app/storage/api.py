"""Lettura di una generazione per riferimento (013; il download della 005 non c'e' piu').

GEMODO non conserva i PDF: il documento si riceve solo dalla risposta di
`genera`. Per riferimento si legge la riga del registro, ed e' cosa da
amministratori.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.security import PrincipalGEMODO
from app.configurazione.security import require_configurazione_admin
from app.storage.schemas import StatoDocumento
from app.storage.service import StorageDocumentiService, get_storage_documenti_service

router = APIRouter(prefix="/api/v1/documenti", tags=["storage"])
Admin = Annotated[PrincipalGEMODO, Depends(require_configurazione_admin)]
Service = Annotated[StorageDocumentiService, Depends(get_storage_documenti_service)]


@router.get("/{riferimento}", response_model=StatoDocumento)
def get_stato_documento(riferimento: str, _principal: Admin, service: Service) -> StatoDocumento:
    return service.stato(riferimento)
