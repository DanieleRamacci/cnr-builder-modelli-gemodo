from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.common.errors import AuthenticationError, AuthorizationError, install_error_handlers
from app.common.security import (
    ROLE_DOCUMENTI_GENERATORE,
    ROLE_DOCUMENTI_VIEWER,
    decode_principal_from_token,
    require_documenti_generatore,
)
from app.core.settings import Settings
from tests.support.security import JwtTestKeys, signed_token


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        keycloak_issuer_url="https://sso.test.si.cnr.it/auth/realms/cnr",
        keycloak_audience="gemodo-backend",
        keycloak_jwks_url=None,
        keycloak_jwks_cache_ttl_seconds=300,
        gemodo_use_mock_principal=False,
        gemodo_mock_subject="mock",
        gemodo_mock_client_id="geban-backend",
        gemodo_mock_roles=(ROLE_DOCUMENTI_VIEWER,),
    )


def test_decode_valid_token_with_required_claims():
    keys = JwtTestKeys()
    token = signed_token(keys, roles=(ROLE_DOCUMENTI_GENERATORE,))

    principal = decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)

    assert principal.subject == "test-subject"
    assert principal.client_id == "geban-backend"
    assert ROLE_DOCUMENTI_GENERATORE in principal.ruoli


def test_decode_rejects_invalid_audience():
    keys = JwtTestKeys()
    token = signed_token(keys, audience="wrong-audience")

    with pytest.raises(AuthenticationError):
        decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)


def test_decode_rejects_expired_token():
    keys = JwtTestKeys()
    token = signed_token(keys, expires_delta=timedelta(minutes=-1))

    with pytest.raises(AuthenticationError):
        decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)


def test_decode_rejects_wrong_client():
    keys = JwtTestKeys()
    token = signed_token(keys, client_id="altro-client")

    with pytest.raises(AuthorizationError):
        decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)


def test_missing_role_is_forbidden():
    keys = JwtTestKeys()
    token = signed_token(keys, roles=(ROLE_DOCUMENTI_VIEWER,))
    principal = decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)

    with pytest.raises(AuthorizationError):
        require_documenti_generatore(principal)


def test_missing_token_returns_401_error_envelope():
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/protected")
    def protected(_: object = Depends(require_documenti_generatore)) -> dict[str, str]:
        return {"ok": "true"}

    response = TestClient(app).get("/protected")

    assert response.status_code == 401
    assert response.json()["codice"] == "ACCESSO_NON_AUTENTICATO"
