from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app
from app.validation.service import PayloadValidationService, get_payload_validation_service
from tests.support.postgres import postgres_database_url


@pytest.fixture()
def validation_client(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    session = Session(engine)
    app.dependency_overrides[get_payload_validation_service] = lambda: PayloadValidationService(session)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def _request_payload(dati: dict[str, object], *, bando_inglese: bool = False, modello_versione_id: int = 1):
    return {
        "sistema_richiedente": "GEBAN",
        "external_context_id": "test-context-001",
        "modello_versione_id": modello_versione_id,
        "bando_inglese": bando_inglese,
        "dati": dati,
    }


def _valid_dati() -> dict[str, object]:
    return {
        "codice_bando": "BANDO-001",
        "titolo_it": "Bando demo",
        "sede_prescelta_it": "Roma",
        "numero_posti": 2,
    }


@pytest.mark.integration
def test_validazione_payload_success(validation_client):
    response = validation_client.post("/api/v1/documenti/valida", json=_request_payload(_valid_dati()))

    assert response.status_code == 200
    assert response.json() == {"valido": True, "errori": []}


@pytest.mark.integration
def test_validazione_payload_reports_missing_required_field(validation_client):
    dati = _valid_dati()
    del dati["titolo_it"]

    response = validation_client.post("/api/v1/documenti/valida", json=_request_payload(dati))

    assert response.status_code == 200
    body = response.json()
    assert body["valido"] is False
    assert body["errori"][0]["campo"] == "titolo_it"
    assert body["errori"][0]["codice"] == "CAMPO_OBBLIGATORIO"


@pytest.mark.integration
def test_validazione_payload_reports_wrong_type(validation_client):
    dati = _valid_dati()
    dati["numero_posti"] = "due"

    response = validation_client.post("/api/v1/documenti/valida", json=_request_payload(dati))

    assert response.status_code == 200
    body = response.json()
    assert body["valido"] is False
    assert body["errori"][0]["campo"] == "numero_posti"
    assert body["errori"][0]["codice"] == "TIPO_NON_VALIDO"


@pytest.mark.integration
def test_validazione_payload_rejects_extra_field(validation_client):
    dati = _valid_dati()
    dati["campo_extra"] = "non ammesso"

    response = validation_client.post("/api/v1/documenti/valida", json=_request_payload(dati))

    assert response.status_code == 200
    body = response.json()
    assert body["valido"] is False
    assert body["errori"][0]["campo"] == "campo_extra"
    assert body["errori"][0]["codice"] == "CAMPO_NON_AMMESSO"


@pytest.mark.integration
def test_validazione_payload_rejects_non_published_version(validation_client):
    response = validation_client.post(
        "/api/v1/documenti/valida",
        json=_request_payload(_valid_dati(), modello_versione_id=2),
    )

    assert response.status_code == 409
    assert response.json()["codice"] == "MODELLO_VERSIONE_NON_PUBBLICATO"


@pytest.mark.integration
def test_validazione_payload_requires_english_field_when_bando_inglese_true(validation_client):
    response = validation_client.post(
        "/api/v1/documenti/valida",
        json=_request_payload(_valid_dati(), bando_inglese=True),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valido"] is False
    assert body["errori"][0]["campo"] == "titolo_en"
    assert body["errori"][0]["codice"] == "CAMPO_INGLESE_MANCANTE"


@pytest.mark.integration
def test_validazione_payload_accepts_missing_english_field_when_bando_inglese_false(validation_client):
    response = validation_client.post(
        "/api/v1/documenti/valida",
        json=_request_payload(_valid_dati(), bando_inglese=False),
    )

    assert response.status_code == 200
    assert response.json() == {"valido": True, "errori": []}
