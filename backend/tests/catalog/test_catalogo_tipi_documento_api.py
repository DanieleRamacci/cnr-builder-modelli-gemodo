from __future__ import annotations

from fastapi.testclient import TestClient

from app.catalog.schemas import TipoDocumentoListResponse, TipoDocumentoSchema
from app.catalog.service import get_catalog_service
from app.main import app


class FakeCatalogService:
    def list_tipi_documento(self) -> TipoDocumentoListResponse:
        return TipoDocumentoListResponse(
            items=[TipoDocumentoSchema(codice="BANDO_CONCORSO", descrizione="Bando di concorso")]
        )


def test_list_tipi_documento_returns_contract_response(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/tipi-documento")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"items": [{"codice": "BANDO_CONCORSO", "descrizione": "Bando di concorso"}]}
