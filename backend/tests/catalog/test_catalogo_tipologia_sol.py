from __future__ import annotations

from fastapi.testclient import TestClient

from app.catalog.service import get_catalog_service
from app.catalog.schemas import ModelloSearchResponse
from app.main import app


class FakeCatalogService:
    def search_modelli(self, **kwargs):
        return ModelloSearchResponse(tipo_documento=kwargs["tipo_documento"],
                                    codice_tipologia=kwargs["codice_tipologia"], modelli=[])


def test_search_modelli_returns_empty_for_unmatched_external_code(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalogService()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/catalogo/modelli",
                params={"tipo_documento": "BANDO_CONCORSO", "codice_tipologia": "NON_CONFIGURATA"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["modelli"] == []
