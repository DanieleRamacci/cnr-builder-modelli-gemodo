"""Catalog routes exposed to GEBAN."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from app.catalog.schemas import (
    CampiRichiestiResponse,
    CategoriaDocumentoListResponse,
    ClassificazioneCatalogoResponse,
    ModalitaCatalogo,
    ModelloSearchResponse,
    TipoDocumentoListResponse,
)
from app.catalog.service import CatalogService, get_catalog_service
from app.common.security import PrincipalGEMODO, require_documenti_viewer

router = APIRouter(prefix="/api/v1/catalogo", tags=["catalogo"])


@router.get("/tipi-documento", response_model=TipoDocumentoListResponse)
def list_tipi_documento(
    _: PrincipalGEMODO = Depends(require_documenti_viewer),
    service: CatalogService = Depends(get_catalog_service),
) -> TipoDocumentoListResponse:
    return service.list_tipi_documento()


@router.get("/tipi-documento/{codiceTipoDocumento}/categorie", response_model=CategoriaDocumentoListResponse)
def list_categorie_documento(
    codiceTipoDocumento: str,
    _: PrincipalGEMODO = Depends(require_documenti_viewer),
    service: CatalogService = Depends(get_catalog_service),
) -> CategoriaDocumentoListResponse:
    return service.list_categorie(codiceTipoDocumento)


@router.get("/tipi-documento/{codiceTipoDocumento}/classificazione", response_model=ClassificazioneCatalogoResponse)
def get_classificazione_documento(
    codiceTipoDocumento: str,
    _: PrincipalGEMODO = Depends(require_documenti_viewer),
    service: CatalogService = Depends(get_catalog_service),
) -> ClassificazioneCatalogoResponse:
    return service.get_classificazione(codiceTipoDocumento)


@router.get("/modelli", response_model=ModelloSearchResponse)
def search_modelli(
    tipo_documento: str,
    categoria: str | None = None,
    codice_tipologia: str | None = None,
    modalita: ModalitaCatalogo = ModalitaCatalogo.OPERATIVA,
    data_riferimento: date | None = None,
    pubblicato_da: date | None = None,
    pubblicato_a: date | None = None,
    _: PrincipalGEMODO = Depends(require_documenti_viewer),
    service: CatalogService = Depends(get_catalog_service),
) -> ModelloSearchResponse:
    return service.search_modelli(
        tipo_documento=tipo_documento,
        categoria=categoria,
        codice_tipologia=codice_tipologia,
        modalita=modalita,
        data_riferimento=data_riferimento,
        pubblicato_da=pubblicato_da,
        pubblicato_a=pubblicato_a,
    )


@router.get("/modelli/{modelloVersioneId}/campi-richiesti", response_model=CampiRichiestiResponse)
def get_campi_richiesti(
    modelloVersioneId: int,
    _: PrincipalGEMODO = Depends(require_documenti_viewer),
    service: CatalogService = Depends(get_catalog_service),
) -> CampiRichiestiResponse:
    return service.get_campi_richiesti(modelloVersioneId)
