from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.common.errors import AuthenticationError, AuthorizationError, install_error_handlers
from app.common.security import (
    ROLE_GEMODO_MODELLI_GESTORE,
    ROLE_DOCUMENTI_GENERATORE,
    ROLE_DOCUMENTI_VIEWER,
    decode_principal_from_token,
    require_documenti_generatore,
    require_modelli_gestore,
)
from app.core.settings import Settings
from tests.support.security import JwtTestKeys, signed_token


def _settings(*, integration_profiles_path: str | None = None) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://test:test@localhost:5432/test",
        keycloak_issuer_url="https://sso.test.si.cnr.it/auth/realms/cnr",
        keycloak_audience="gemodo-backend",
        keycloak_frontend_client_id="gemodo-frontend",
        gemodo_allowed_interactive_clients=("gemodo-frontend",),
        keycloak_jwks_url=None,
        keycloak_jwks_cache_ttl_seconds=300,
        gemodo_use_mock_principal=False,
        gemodo_mock_subject="mock",
        gemodo_mock_client_id="geban-backend",
        gemodo_mock_roles=(ROLE_DOCUMENTI_VIEWER,),
        integration_profiles_path=integration_profiles_path,
    )


def _write_integration_profiles(tmp_path) -> str:
    manifest = tmp_path / "integration-profiles.local.yaml"
    manifest.write_text(
        """
sistemi_richiedenti:
  - codice: GEBAN
    nome: GEBAN
    stato: ATTIVO
    spec_owner: specs/006-sicurezza-autorizzazioni-audit
    client_applicativi:
      - client_id: geri-angular-public
        audience_attesa: gemodo-backend
        token_contexts:
          - geban
        sistemi_abilitati:
          - GEBAN
        stato: ATTIVO
        gestisce_credenziali: false
    profili_integrazione:
      - codice: GEBAN_RECLUTAMENTO_V1
        sistema_richiedente: GEBAN
        versione: "1"
        stato: ATTIVO
        client_ammessi:
          - geri-angular-public
        permessi_operativi:
          - catalogo
          - generazione_bozza
        role_mappings:
          - token_context: geban
            external_role: ROLE_USER#geban
            internal_permissions:
              - DOCUMENTI_GENERATORE
              - DOCUMENTI_VIEWER
          - token_context: geban
            external_role: ROLE_COORDINATOR#geban
            internal_permissions:
              - DOCUMENTI_GENERATORE
              - DOCUMENTI_VIEWER
          - token_context: geban
            external_role: ROLE_MANAGER#geban
            internal_permissions:
              - DOCUMENTI_GENERATORE
              - DOCUMENTI_VIEWER
              - GEMODO_MODELLI_GESTORE
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return str(manifest)


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


def test_decode_accepts_configured_interactive_client():
    keys = JwtTestKeys()
    token = signed_token(keys, client_id="gemodo-frontend", roles=(ROLE_DOCUMENTI_VIEWER,))

    principal = decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)

    assert principal.client_id == "gemodo-frontend"
    assert ROLE_DOCUMENTI_VIEWER in principal.ruoli


def test_decode_accepts_configured_ace_client_with_context_role(tmp_path):
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        client_id="geri-angular-public",
        roles=None,
        contexts={"geban": ["ROLE_COORDINATOR#geban"]},
    )

    principal = decode_principal_from_token(
        token,
        settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
        signing_key=keys.public_pem,
    )

    assert principal.client_id == "geri-angular-public"
    assert ROLE_DOCUMENTI_GENERATORE in principal.ruoli
    assert ROLE_DOCUMENTI_VIEWER in principal.ruoli
    assert principal.ruoli_diretti == ()
    assert principal.ruoli_contesto == (("geban", ("ROLE_COORDINATOR#geban",)),)


def test_decode_rejects_ace_token_without_gemodo_audience(tmp_path):
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        audience="oauth2-resource",
        client_id="geri-angular-public",
        roles=None,
        contexts={"geban": ["ROLE_COORDINATOR#geban"]},
    )

    with pytest.raises(AuthenticationError):
        decode_principal_from_token(
            token,
            settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
            signing_key=keys.public_pem,
        )


def test_decode_rejects_unconfigured_ace_client_with_context_role(tmp_path):
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        client_id="ace-non-censito",
        roles=None,
        contexts={"geban": ["ROLE_COORDINATOR#geban"]},
    )

    with pytest.raises(AuthorizationError):
        decode_principal_from_token(
            token,
            settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
            signing_key=keys.public_pem,
        )


def test_ace_user_role_can_generate_but_cannot_manage_models(tmp_path):
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        client_id="geri-angular-public",
        roles=None,
        contexts={"geban": ["ROLE_USER#geban"]},
    )
    principal = decode_principal_from_token(
        token,
        settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
        signing_key=keys.public_pem,
    )

    require_documenti_generatore(principal)
    with pytest.raises(AuthorizationError):
        require_modelli_gestore(principal)


def test_ace_manager_role_can_manage_models(tmp_path):
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        client_id="geri-angular-public",
        roles=None,
        contexts={"geban": ["ROLE_MANAGER#geban"]},
    )
    principal = decode_principal_from_token(
        token,
        settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
        signing_key=keys.public_pem,
    )

    assert ROLE_GEMODO_MODELLI_GESTORE in principal.ruoli
    require_modelli_gestore(principal)


def test_unknown_ace_role_does_not_derive_permissions(tmp_path):
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        client_id="geri-angular-public",
        roles=None,
        contexts={"geban": ["ROLE_UNKNOWN#geban"]},
    )
    principal = decode_principal_from_token(
        token,
        settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
        signing_key=keys.public_pem,
    )

    assert principal.ruoli == ()
    with pytest.raises(AuthorizationError):
        require_documenti_generatore(principal)


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

    with TestClient(app) as client:
        response = client.get("/protected")

    assert response.status_code == 401
    assert response.json()["codice"] == "ACCESSO_NON_AUTENTICATO"


def test_authorization_error_does_not_expose_bearer_token(tmp_path):
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        client_id="ace-non-censito",
        roles=None,
        contexts={"geban": ["ROLE_COORDINATOR#geban"]},
    )
    app = FastAPI()
    install_error_handlers(app)
    settings = _settings(integration_profiles_path=_write_integration_profiles(tmp_path))

    @app.get("/protected")
    def protected(
        _: object = Depends(lambda: decode_principal_from_token(token, settings=settings, signing_key=keys.public_pem))
    ) -> dict[str, str]:
        return {"ok": "true"}

    with TestClient(app) as client:
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["codice"] == "ACCESSO_NON_AUTORIZZATO"
    assert token not in response.text
