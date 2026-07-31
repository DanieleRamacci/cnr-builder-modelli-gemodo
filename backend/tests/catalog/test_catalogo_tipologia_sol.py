from __future__ import annotations

from fastapi.testclient import TestClient

from app.catalog.service import get_catalog_service
from app.common.errors import ApiError, ErrorCode
from app.main import app


class FakeCatalogService:
    def search_modelli(self, **kwargs):
        raise ApiError(
            ErrorCode.TIPOLOGIA_SOL_NON_VALIDA,
            "Tipologia GEBAN/SOL non configurata",
            status_code=400,
        )


def test_search_modelli_rejects_unconfigured_tipologia_sol(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalogService()
    try:
        response = TestClient(app).get(
            "/api/v1/catalogo/modelli",
            params={"tipo_documento": "BANDO_CONCORSO", "codice_tipologia": "NON_CONFIGURATA"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["codice"] == "TIPOLOGIA_SOL_NON_VALIDA"
