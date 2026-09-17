"""Consultation/download routes for generated documents (005, MVP FR-019/020 slice)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.common.security import PrincipalGEMODO, require_documenti_viewer
from app.storage.schemas import StatoDocumento
from app.storage.service import StorageDocumentiService, get_storage_documenti_service

router = APIRouter(prefix="/api/v1/documenti", tags=["storage"])
Viewer = Annotated[PrincipalGEMODO, Depends(require_documenti_viewer)]
Service = Annotated[StorageDocumentiService, Depends(get_storage_documenti_service)]


@router.get("/{riferimento}", response_model=StatoDocumento)
def get_stato_documento(riferimento: str, principal: Viewer, service: Service) -> StatoDocumento:
    return service.stato(riferimento, principal)


@router.get("/{riferimento}/download")
def download_documento(riferimento: str, principal: Viewer, service: Service) -> Response:
    stato, contenuto = service.contenuto_per_download(riferimento, principal)
    return Response(
        content=contenuto, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{stato.nome_file}"'},
    )
