from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.common.errors import AuthenticationError, install_error_handlers
from app.core.settings import Settings, get_settings
from app.main import configure_cors


def _app(settings: Settings) -> FastAPI:
    app = FastAPI()
    configure_cors(app, settings)
    install_error_handlers(app)

    @app.get("/protected")
    def protected() -> dict[str, str]:
        raise AuthenticationError()

    return app


def test_cors_allowed_origins_are_normalized(monkeypatch):
    monkeypatch.setenv(
        "GEMODO_CORS_ALLOWED_ORIGINS",
        " http://localhost:4200 , https://geban.test.si.cnr.it/ ",
    )

    settings = get_settings()

    assert settings.gemodo_cors_allowed_origins == (
        "http://localhost:4200",
        "https://geban.test.si.cnr.it",
    )


def test_cors_preflight_from_geban_origin_is_accepted(monkeypatch):
    monkeypatch.setenv(
        "GEMODO_CORS_ALLOWED_ORIGINS",
        "http://localhost:4200,https://geban.test.si.cnr.it/",
    )
    settings = get_settings()

    with TestClient(_app(settings)) as client:
        response = client.options(
            "/protected",
            headers={
                "Origin": "https://geban.test.si.cnr.it",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://geban.test.si.cnr.it"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_cors_headers_are_present_on_unauthenticated_response(monkeypatch):
    monkeypatch.setenv("GEMODO_CORS_ALLOWED_ORIGINS", "http://localhost:4200")
    settings = get_settings()

    with TestClient(_app(settings)) as client:
        response = client.get("/protected", headers={"Origin": "http://localhost:4200"})

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert response.json()["codice"] == "ACCESSO_NON_AUTENTICATO"


def test_cors_preflight_from_unapproved_origin_is_rejected(monkeypatch):
    monkeypatch.setenv("GEMODO_CORS_ALLOWED_ORIGINS", "https://geban.test.si.cnr.it")
    settings = get_settings()

    with TestClient(_app(settings)) as client:
        response = client.options(
            "/protected",
            headers={
                "Origin": "https://non-approvato.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
