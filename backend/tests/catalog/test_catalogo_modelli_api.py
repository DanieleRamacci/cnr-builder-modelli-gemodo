from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from app.catalog.schemas import ModalitaCatalogo, ModelloCatalogoSchema, ModelloSearchResponse
from app.catalog.service import get_catalog_service
from app.main import app


class FakeCatalogService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search_modelli(self, **kwargs) -> ModelloSearchResponse:
        self.calls.append(kwargs)
        return ModelloSearchResponse(
            tipo_documento=kwargs["tipo_documento"],
            categoria=kwargs.get("categoria"),
            codice_tipologia=kwargs.get("codice_tipologia"),
            modalita=kwargs.get("modalita", ModalitaCatalogo.OPERATIVA),
            modelli=[
                ModelloCatalogoSchema(
                    modello_id=10,
                    modello_versione_id=11,
                    codice="demo-bando-concorso-standard-v1",
                    descrizione="Bando concorso standard",
                    variante="STANDARD",
                    versione=1,
                    stato="PUBBLICATO",
                    pubblicato_at=datetime.fromisoformat("2026-07-31T10:00:00+00:00"),
                )
            ],
        )


def test_search_modelli_operative_returns_published_versions(monkeypatch):
    fake_service = FakeCatalogService()
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: fake_service
    try:
        response = TestClient(app).get(
            "/api/v1/catalogo/modelli",
            params={"tipo_documento": "BANDO_CONCORSO", "categoria": "TECNOLOGO", "codice_tipologia": "TD"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["modalita"] == "OPERATIVA"
    assert body["tipo_documento"] == "BANDO_CONCORSO"
    assert body["categoria"] == "TECNOLOGO"
    assert body["codice_tipologia"] == "TD"
    assert body["modelli"][0]["modello_versione_id"] == 11
    assert body["modelli"][0]["stato"] == "PUBBLICATO"
    assert fake_service.calls[0]["modalita"] == ModalitaCatalogo.OPERATIVA


def test_search_modelli_historical_passes_date_filters(monkeypatch):
    fake_service = FakeCatalogService()
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: fake_service
    try:
        response = TestClient(app).get(
            "/api/v1/catalogo/modelli",
            params={
                "tipo_documento": "BANDO_CONCORSO",
                "modalita": "STORICO",
                "pubblicato_da": "2026-01-01",
                "pubblicato_a": "2026-12-31",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["modalita"] == "STORICO"
    assert fake_service.calls[0]["modalita"] == ModalitaCatalogo.STORICO
    assert fake_service.calls[0]["pubblicato_da"].isoformat() == "2026-01-01"
    assert fake_service.calls[0]["pubblicato_a"].isoformat() == "2026-12-31"


def test_search_modelli_invalid_context_returns_error_envelope(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")

    response = TestClient(app).get(
        "/api/v1/catalogo/modelli",
        params={"tipo_documento": "BANDO_CONCORSO", "modalita": "NON_VALIDA"},
    )

    assert response.status_code == 400
    assert response.json()["codice"] == "CONTESTO_NON_VALIDO"
