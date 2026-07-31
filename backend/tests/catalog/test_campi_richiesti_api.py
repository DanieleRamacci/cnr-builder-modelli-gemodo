from __future__ import annotations

from fastapi.testclient import TestClient

from app.catalog.schemas import CampiRichiestiResponse, CampoRichiestoSchema
from app.catalog.service import get_catalog_service
from app.common.errors import ApiError, ErrorCode
from app.main import app


class FakeCatalogService:
    def get_campi_richiesti(self, modello_versione_id: int) -> CampiRichiestiResponse:
        return CampiRichiestiResponse(
            modello_versione_id=modello_versione_id,
            tipo_documento="BANDO_CONCORSO",
            categoria="DEMO",
            campi=[
                CampoRichiestoSchema(
                    codice="codice_bando",
                    etichetta="Codice bando",
                    tipo="string",
                    lingua="IT",
                    obbligatorio=True,
                    ordine=1,
                    validazione={"minLength": 1},
                ),
                CampoRichiestoSchema(
                    codice="titolo_en",
                    etichetta="Title",
                    tipo="string",
                    lingua="EN",
                    obbligatorio=True,
                    ordine=2,
                ),
            ],
            schema_={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "codice_bando": {"type": "string", "minLength": 1},
                    "titolo_en": {"type": "string"},
                },
                "required": ["codice_bando"],
            },
        )


def test_get_campi_richiesti_returns_contract_response_with_lingua(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/modelli/11/campi-richiesti")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["modello_versione_id"] == 11
    assert body["tipo_documento"] == "BANDO_CONCORSO"
    assert [campo["lingua"] for campo in body["campi"]] == ["IT", "EN"]
    assert body["schema"]["additionalProperties"] is False


def test_get_campi_richiesti_rejects_non_published_version(monkeypatch):
    class NonPublishedCatalogService:
        def get_campi_richiesti(self, modello_versione_id: int):
            raise ApiError(
                ErrorCode.MODELLO_VERSIONE_NON_PUBBLICATO,
                "Versione modello non pubblicata",
                status_code=409,
            )

    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    app.dependency_overrides[get_catalog_service] = lambda: NonPublishedCatalogService()
    try:
        response = TestClient(app).get("/api/v1/catalogo/modelli/12/campi-richiesti")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["codice"] == "MODELLO_VERSIONE_NON_PUBBLICATO"
