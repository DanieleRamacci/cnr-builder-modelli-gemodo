from __future__ import annotations

from datetime import timedelta
from dataclasses import replace

import pytest
import yaml
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import app.common.security as security_module
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
        keycloak_jwt_leeway_seconds=60,
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


def _capture_security_warnings(monkeypatch) -> list[str]:
    warnings: list[str] = []

    def _warning(message: str, *args: object, **_: object) -> None:
        warnings.append(message % args if args else message)

    monkeypatch.setattr(security_module.logger, "warning", _warning)
    return warnings


def test_decode_valid_token_with_required_claims():
    keys = JwtTestKeys()
    token = signed_token(keys, roles=(ROLE_DOCUMENTI_GENERATORE,))

    principal = decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)

    assert principal.subject == "test-subject"
    assert principal.client_id == "geban-backend"
    assert ROLE_DOCUMENTI_GENERATORE in principal.ruoli


def test_decode_ignora_l_audience_del_token():
    """`aud` non si verifica (decisione del product owner, 2026-09-25).

    Chi chiama da GEBAN - e dai servizi futuri - non porta `aud`: l'unico
    segnale di destinazione e' il contesto nel token piu' l'allowlist dei
    client. Verificarlo "solo se presente" rifiutava un chiamante legittimo per
    come e' configurato il mapper del suo client, non per cio' che chiedeva.
    """
    keys = JwtTestKeys()
    token = signed_token(keys, audience="oauth2-resource")

    principal = decode_principal_from_token(
        token, settings=_settings(), signing_key=keys.public_pem,
    )

    assert principal.client_id == "geban-backend"
    # Il token resta valutato per cio' che dichiara: l'audience diversa non
    # aggiunge ne' toglie permessi.
    assert ROLE_DOCUMENTI_GENERATORE in principal.ruoli


def test_decode_rejects_expired_token(monkeypatch):
    warnings = _capture_security_warnings(monkeypatch)
    keys = JwtTestKeys()
    token = signed_token(keys, expires_delta=timedelta(minutes=-1))

    with pytest.raises(AuthenticationError):
        decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)

    assert "Authentication rejected: jwt_validation=ExpiredSignatureError" in warnings
    assert all(token not in warning for warning in warnings)


def test_decode_accepts_small_clock_skew_for_issued_at_and_not_before():
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        issued_at_delta=timedelta(seconds=30),
        not_before_delta=timedelta(seconds=30),
    )

    principal = decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)

    assert principal.subject == "test-subject"
    assert ROLE_DOCUMENTI_GENERATORE in principal.ruoli


def test_decode_rejects_token_too_far_in_future(monkeypatch):
    warnings = _capture_security_warnings(monkeypatch)
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        issued_at_delta=timedelta(seconds=120),
        not_before_delta=timedelta(seconds=120),
    )

    with pytest.raises(AuthenticationError):
        decode_principal_from_token(token, settings=_settings(), signing_key=keys.public_pem)

    assert "Authentication rejected: jwt_validation=ImmatureSignatureError" in warnings
    assert all(token not in warning for warning in warnings)


def test_invalid_issuer_is_diagnosed_without_logging_token(monkeypatch):
    warnings = _capture_security_warnings(monkeypatch)
    keys = JwtTestKeys()
    token = signed_token(keys)
    settings = _settings()
    with pytest.raises(AuthenticationError):
        decode_principal_from_token(token, settings=replace(settings, keycloak_issuer_url="https://other.example/realms/test"), signing_key=keys.public_pem)
    assert "Authentication rejected: jwt_validation=InvalidIssuerError" in warnings
    assert all(token not in warning for warning in warnings)


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
    """Riflette il token ACE reale (2026-09-16): nessun claim `aud` - ACE non lo
    valorizza, solo `contexts.<nome>.roles`. Il segnale di destinazione e' il
    contesto riconosciuto (`geban`), non l'audience."""
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        audience=None,
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


def test_decode_accepts_ace_token_with_multiple_contexts_only_geban_configured(tmp_path):
    """Caso reale segnalato dal product owner: lo stesso token ACE puo' portare
    piu' contesti (es. "geri" oltre a "geban"). GEMODO deve derivare permessi
    solo dal contesto che conosce (`geban`), ignorare "geri" senza errore, e
    continuare a non richiedere `aud`."""
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        audience=None,
        client_id="geri-angular-public",
        roles=None,
        contexts={"geri": ["ROLE_ADMIN#geri"], "geban": ["ROLE_COORDINATOR#geban"]},
    )

    principal = decode_principal_from_token(
        token,
        settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
        signing_key=keys.public_pem,
    )

    assert ROLE_DOCUMENTI_GENERATORE in principal.ruoli
    assert ROLE_DOCUMENTI_VIEWER in principal.ruoli
    assert dict(principal.ruoli_contesto)["geri"] == ("ROLE_ADMIN#geri",)


def test_un_token_ace_con_audience_diversa_resta_valido_per_il_suo_contesto(tmp_path):
    """Il caso concreto per cui il controllo e' stato tolto.

    Un client del realm cnr configurato con un audience mapper qualunque
    (`oauth2-resource` e' quello di serie) veniva respinto pur portando un
    contesto valido e i ruoli giusti. Ora conta cio' che il token dichiara -
    client ammesso e ruoli di contesto mappati - non a chi era intestato.
    """
    keys = JwtTestKeys()
    token = signed_token(
        keys,
        audience="oauth2-resource",
        client_id="geri-angular-public",
        roles=None,
        contexts={"geban": ["ROLE_COORDINATOR#geban"]},
    )

    principal = decode_principal_from_token(
        token,
        settings=_settings(integration_profiles_path=_write_integration_profiles(tmp_path)),
        signing_key=keys.public_pem,
    )

    assert dict(principal.ruoli_contesto) == {"geban": ("ROLE_COORDINATOR#geban",)}
    assert principal.ruoli_diretti == ()


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


@pytest.mark.parametrize("role,manager", [("ROLE_MANAGER#geban", True), ("ROLE_USER#geban", False), ("ROLE_UNKNOWN#geban", False)])
def test_interactive_ace_permissions_are_scoped_without_profile_client_registration(tmp_path, role, manager):
    keys = JwtTestKeys()
    settings = _settings(integration_profiles_path=_write_integration_profiles(tmp_path))
    token = signed_token(keys, client_id="gemodo-frontend", roles=None,
                         contexts={"geban": [role], "other": ["ROLE_MANAGER#other"]})
    principal = decode_principal_from_token(token, settings=settings, signing_key=keys.public_pem)
    assert principal.ruoli_diretti == ()
    assert (ROLE_GEMODO_MODELLI_GESTORE in principal.ruoli) is manager
    assert security_module.contesti_con_permesso(
        principal, ROLE_GEMODO_MODELLI_GESTORE, ("geban", "other"), settings=settings
    ) == ({"geban"} if manager else set())


def test_technical_client_does_not_gain_interactive_context_permissions(tmp_path):
    keys = JwtTestKeys()
    settings = _settings(integration_profiles_path=_write_integration_profiles(tmp_path))
    token = signed_token(keys, client_id="geban-backend", roles=None,
                         contexts={"geban": ["ROLE_MANAGER#geban"]})
    principal = decode_principal_from_token(token, settings=settings, signing_key=keys.public_pem)
    assert principal.ruoli == ()


@pytest.mark.parametrize("target", ["system", "profile"])
def test_interactive_context_permissions_require_active_configuration(tmp_path, target):
    from pathlib import Path
    path = Path(_write_integration_profiles(tmp_path))
    manifest = yaml.safe_load(path.read_text())
    system = manifest["sistemi_richiedenti"][0]
    entity = system if target == "system" else system["profili_integrazione"][0]
    entity["stato"] = "SOSPESO"
    path.write_text(yaml.safe_dump(manifest))
    keys = JwtTestKeys()
    token = signed_token(keys, client_id="gemodo-frontend", roles=None,
                         contexts={"geban": ["ROLE_MANAGER#geban"]})
    principal = decode_principal_from_token(token, settings=_settings(integration_profiles_path=str(path)), signing_key=keys.public_pem)
    assert principal.ruoli == ()


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
