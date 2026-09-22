"""L'indice della documentazione API deve elencare ogni contratto pubblicato.

Senza questo test l'indice diventa una lista scritta a mano che si scorda un
contratto appena ne viene aggiunto uno: il punto della pagina e' proprio essere
l'unico posto da cui partire.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quality.openapi_docs import PUBLISHED_CONTRACTS

pytestmark = pytest.mark.contract


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_index_lists_every_published_contract(client):
    risposta = client.get("/docs")
    assert risposta.status_code == 200, risposta.text
    corpo = risposta.text
    for spec_id in PUBLISHED_CONTRACTS:
        if spec_id.endswith(".openapi"):
            continue  # alias di compatibilita' per i riferimenti relativi
        assert f"/docs/{spec_id}" in corpo, f"contratto '{spec_id}' assente dall'indice"
        assert f"/redoc/{spec_id}" in corpo
        assert f"/openapi/{spec_id}.yaml" in corpo


def test_index_points_to_the_geban_integration_guide(client):
    corpo = client.get("/docs").text
    assert "geban" in corpo.lower()
    # I quattro endpoint che GEMODO espone a GEBAN piu' i due di consultazione.
    for rotta in (
        "/api/v1/catalogo/modelli",
        "/api/v1/documenti/valida",
        "/api/v1/documenti/genera",
        "/api/v1/documenti/{riferimento}",
    ):
        assert rotta in corpo, f"{rotta} non citata nell'indice"


def test_runtime_explorer_is_still_reachable(client):
    """Lo Swagger dell'app viva resta disponibile, spostato sotto /docs/runtime."""
    assert client.get("/docs/runtime").status_code == 200
