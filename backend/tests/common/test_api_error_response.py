from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_request_validation_error_uses_stable_error_envelope(monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")

    response = TestClient(app).post(
        "/api/v1/documenti/valida",
        json={"sistema_richiedente": "GEBAN", "external_context_id": "ctx"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["codice"] == "CONTESTO_NON_VALIDO"
    assert body["messaggio"]
    assert "dettagli" in body


def test_missing_route_uses_stable_error_envelope():
    response = TestClient(app).get("/api/v1/catalogo/non-esiste")

    assert response.status_code == 404
    assert response.json()["codice"] == "CONTESTO_NON_VALIDO"
