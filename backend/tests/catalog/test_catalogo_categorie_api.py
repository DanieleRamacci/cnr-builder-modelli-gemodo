from __future__ import annotations

from fastapi.testclient import TestClient

from app.catalog.schemas import (
    CategoriaDocumentoListResponse,
    CategoriaDocumentoSchema,
    ClassificazioneCatalogoResponse,
    TipologiaCatalogoSchema,
)
from app.catalog.service import get_catalog_service
from app.common.errors import ApiError, ErrorCode
from app.main import app


class FakeCatalogService:
    def list_categorie(self, codice_tipo_documento: str) -> CategoriaDocumentoListResponse:
        return CategoriaDocumentoListResponse(
            tipo_documento=codice_tipo_documento,
            categorie=[CategoriaDocumentoSchema(codice="TECNOLOGO", descrizione="Tecnologo")],
        )

    def get_classificazione(self, codice_tipo_documento: str) -> ClassificazioneCatalogoResponse:
        return ClassificazioneCatalogoResponse(
            tipo_documento=codice_tipo_documento,
            tipologie=[
                TipologiaCatalogoSchema(
                    codice="TD",
                    descrizione="Tempo determinato",
                    categorie=[CategoriaDocumentoSchema(codice="TECNOLOGO", descrizione="Tecnologo")],
                )
            ],
        )


def test_list_categorie_documento_returns_contract_response(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/tipi-documento/BANDO_CONCORSO/categorie")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "tipo_documento": "BANDO_CONCORSO",
        "categorie": [{"codice": "TECNOLOGO", "descrizione": "Tecnologo"}],
    }


def test_list_categorie_documento_returns_error_envelope_when_tipo_is_unknown(monkeypatch):
    class NotFoundCatalogService:
        def list_categorie(self, codice_tipo_documento: str):
            raise ApiError(ErrorCode.CONTESTO_NON_VALIDO, "Tipo documento non configurato o non attivo", status_code=404)

    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: NotFoundCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/tipi-documento/NON_CONFIGURATO/categorie")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["codice"] == "CONTESTO_NON_VALIDO"


def test_get_classificazione_documento_returns_tree(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/tipi-documento/BANDO_CONCORSO/classificazione")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "tipo_documento": "BANDO_CONCORSO",
        "tipologie": [
            {
                "codice": "TD",
                "descrizione": "Tempo determinato",
                "categorie": [{"codice": "TECNOLOGO", "descrizione": "Tecnologo"}],
            }
        ],
    }
