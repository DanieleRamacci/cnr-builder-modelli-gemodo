"""Catalog routes exposed to GEBAN."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.catalog.schemas import (
    CampiRichiestiResponse,
    LinguaModello,
    ModalitaCatalogo,
    ModelloSearchResponse,
)
from app.catalog.service import CatalogService, get_catalog_service
from app.common.security import PrincipalGEMODO, require_documenti_viewer

router = APIRouter(prefix="/api/v1/catalogo", tags=["catalogo"])


def _dimensioni_da_query(request: Request) -> dict[str, str]:
    dimensioni: dict[str, str] = {}
    for chiave, valore in request.query_params.multi_items():
        if not (chiave.startswith("dimensione[") and chiave.endswith("]")):
            continue
        nome = chiave[len("dimensione["):-1].strip()
        valore = valore.strip()
        if not nome or not valore:
            raise HTTPException(status_code=422, detail="Nome e valore della dimensione sono obbligatori")
        precedente = dimensioni.get(nome)
        if precedente is not None and precedente != valore:
            raise HTTPException(status_code=422, detail=f"Valori in conflitto per la dimensione '{nome}'")
        dimensioni[nome] = valore
    return dimensioni


@router.get("/modelli", response_model=ModelloSearchResponse)
def search_modelli(
    request: Request,
    tipo_documento: str,
    profilo: str | None = None,
    codice_tipologia: str | None = None,
    lingua: LinguaModello | None = None,
    livello_professionale: str | None = None,
    modalita: ModalitaCatalogo = ModalitaCatalogo.OPERATIVA,
    data_riferimento: date | None = None,
    pubblicato_da: date | None = None,
    pubblicato_a: date | None = None,
    categoria: str | None = Query(default=None, include_in_schema=False),
    principal: PrincipalGEMODO = Depends(require_documenti_viewer),
    service: CatalogService = Depends(get_catalog_service),
) -> ModelloSearchResponse:
    dimensioni = _dimensioni_da_query(request)
    return service.search_modelli(
        principal=principal,
        tipo_documento=tipo_documento,
        categoria=profilo or categoria,
        codice_tipologia=codice_tipologia,
        lingua=lingua,
        livello_professionale=livello_professionale,
        dimensioni=dimensioni,
        modalita=modalita,
        data_riferimento=data_riferimento,
        pubblicato_da=pubblicato_da,
        pubblicato_a=pubblicato_a,
    )


@router.get("/modelli/{modelloVersioneId}/campi-richiesti", response_model=CampiRichiestiResponse)
def get_campi_richiesti(
    modelloVersioneId: int,
    principal: PrincipalGEMODO = Depends(require_documenti_viewer),
    service: CatalogService = Depends(get_catalog_service),
) -> CampiRichiestiResponse:
    return service.get_campi_richiesti(modelloVersioneId, principal)
