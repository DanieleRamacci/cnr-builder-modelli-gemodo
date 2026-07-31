from __future__ import annotations

from fastapi.testclient import TestClient

from app.catalog.schemas import (
    ClassificazioneCatalogoResponse,
    ProfiloDocumentoListResponse,
    ProfiloDocumentoSchema,
    TipologiaCatalogoSchema,
)
from app.catalog.service import get_catalog_service
from app.common.errors import ApiError, ErrorCode
from app.main import app


class FakeCatalogService:
    def list_profili(self, codice_tipo_documento: str) -> ProfiloDocumentoListResponse:
        return ProfiloDocumentoListResponse(
            tipo_documento=codice_tipo_documento,
            profili=[ProfiloDocumentoSchema(codice="CTER", descrizione="Collaboratore Tecnico Enti di Ricerca")],
        )

    def get_classificazione(self, codice_tipo_documento: str) -> ClassificazioneCatalogoResponse:
        return ClassificazioneCatalogoResponse(
            tipo_documento=codice_tipo_documento,
            tipologie=[
                TipologiaCatalogoSchema(
                    codice="TD",
                    descrizione="Tempo determinato",
                    profili=[
                        ProfiloDocumentoSchema(codice="CTER", descrizione="Collaboratore Tecnico Enti di Ricerca")
                    ],
                )
            ],
        )


def test_list_profili_documento_returns_contract_response(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/tipi-documento/BANDO_CONCORSO/profili")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "tipo_documento": "BANDO_CONCORSO",
        "profili": [{"codice": "CTER", "descrizione": "Collaboratore Tecnico Enti di Ricerca"}],
    }


def test_list_profili_documento_returns_error_envelope_when_tipo_is_unknown(monkeypatch):
    class NotFoundCatalogService:
        def list_profili(self, codice_tipo_documento: str):
            raise ApiError(ErrorCode.CONTESTO_NON_VALIDO, "Tipo documento non configurato o non attivo", status_code=404)

    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: NotFoundCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/tipi-documento/NON_CONFIGURATO/profili")
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
                "profili": [{"codice": "CTER", "descrizione": "Collaboratore Tecnico Enti di Ricerca"}],
            }
        ],
    }
