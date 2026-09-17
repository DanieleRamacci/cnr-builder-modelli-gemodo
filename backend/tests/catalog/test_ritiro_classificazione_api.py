import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize("path", [
    "/api/v1/catalogo/tipi-documento",
    "/api/v1/catalogo/tipi-documento/BANDO_CONCORSO/profili",
    "/api/v1/catalogo/tipi-documento/BANDO_CONCORSO/categorie",
    "/api/v1/catalogo/tipi-documento/BANDO_CONCORSO/classificazione",
])
def test_old_classification_routes_are_removed(path):
    with TestClient(app) as client:
        assert client.get(path).status_code == 404
    assert not any(p.startswith("/api/v1/catalogo/tipi-documento") for p in app.openapi()["paths"])
