"""Security helpers for Keycloak-protected APIs."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import jwt
import logging
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient

from app.common.errors import AuthenticationError, AuthorizationError
from app.core.settings import Settings, get_settings
from app.quality.integration_profile import (
    client_ids_attivi,
    load_sistemi_richiedenti,
    permessi_da_ruoli_esterni,
)


KEYCLOAK_AUDIENCE = "gemodo-backend"
GEBAN_BACKEND_CLIENT_ID = "geban-backend"
ROLE_DOCUMENTI_VIEWER = "DOCUMENTI_VIEWER"
ROLE_DOCUMENTI_GENERATORE = "DOCUMENTI_GENERATORE"
ROLE_GEMODO_MODELLI_GESTORE = "GEMODO_MODELLI_GESTORE"
ALLOWED_ALGORITHMS = ["RS256"]

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrincipalGEMODO:
    subject: str
    client_id: str
    audience: tuple[str, ...]
    ruoli: tuple[str, ...]
    issuer: str
    ruoli_diretti: tuple[str, ...] = ()
    ruoli_contesto: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def has_any_role(self, required_roles: Iterable[str]) -> bool:
        available = set(self.ruoli)
        return any(role in available for role in required_roles)


def ensure_roles(principal: PrincipalGEMODO, required_roles: Iterable[str]) -> PrincipalGEMODO:
    if not principal.has_any_role(required_roles):
        raise AuthorizationError()
    return principal


def _audience_tuple(audience: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if audience is None:
        return ()
    if isinstance(audience, str):
        return (audience,)
    return tuple(audience)


def _extract_roles(payload: dict[str, Any], audience: str) -> tuple[str, ...]:
    resource_access = payload.get("resource_access") or {}
    client_access = resource_access.get(audience) or {}
    roles = client_access.get("roles") or []
    return tuple(str(role) for role in roles)


def _extract_context_roles(payload: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    contexts = payload.get("contexts") or {}
    if not isinstance(contexts, dict):
        return {}
    extracted: dict[str, tuple[str, ...]] = {}
    for context_name, context_value in contexts.items():
        if not isinstance(context_value, dict):
            continue
        roles = context_value.get("roles") or []
        if isinstance(roles, list):
            extracted[str(context_name)] = tuple(str(role) for role in roles)
    return extracted


@lru_cache(maxsize=16)
def _load_sistemi_richiedenti_cached(path: str):
    return tuple(load_sistemi_richiedenti(Path(path)))


def _configured_sistemi(settings: Settings):
    if settings.integration_profiles_path is None:
        return ()
    path = Path(settings.integration_profiles_path)
    if not path.exists():
        return ()
    return _load_sistemi_richiedenti_cached(str(path))


def _principal_from_payload(payload: dict[str, Any], settings: Settings) -> PrincipalGEMODO:
    client_id = payload.get("azp") or payload.get("client_id")
    sistemi = list(_configured_sistemi(settings))
    allowed_clients = {
        GEBAN_BACKEND_CLIENT_ID,
        *settings.gemodo_allowed_interactive_clients,
        *client_ids_attivi(sistemi),
    }
    if client_id not in allowed_clients:
        raise AuthorizationError("Client non autorizzato per le API GEMODO")
    direct_roles = _extract_roles(payload, settings.keycloak_audience)
    context_roles = _extract_context_roles(payload)
    external_permissions = permessi_da_ruoli_esterni(
        sistemi,
        client_id=str(client_id),
        context_roles=context_roles,
    )
    normalized_roles = tuple(dict.fromkeys([*direct_roles, *sorted(external_permissions)]))
    return PrincipalGEMODO(
        subject=str(payload.get("sub") or ""),
        client_id=str(client_id),
        audience=_audience_tuple(payload.get("aud")),
        ruoli=normalized_roles,
        issuer=str(payload.get("iss") or ""),
        ruoli_diretti=direct_roles,
        ruoli_contesto=tuple(sorted(context_roles.items())),
    )


def decode_principal_from_token(
    token: str,
    *,
    settings: Settings | None = None,
    signing_key: str | bytes | None = None,
) -> PrincipalGEMODO:
    settings = settings or get_settings()
    try:
        key = signing_key
        if key is None:
            key = PyJWKClient(settings.jwks_url).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            key=key,
            algorithms=ALLOWED_ALGORITHMS,
            issuer=settings.keycloak_issuer_url,
            # PyJWT rifiuta un token con `aud` presente se non gli passiamo
            # `audience=`, ma ACE non valorizza affatto `aud` - l'unico modo per
            # accettare entrambi i casi e' disabilitare il controllo integrato e
            # farlo noi stessi, condizionalmente, in _ensure_audience_if_declared.
            options={"verify_aud": False},
        )
    except InvalidTokenError as exc:
        logger.warning("Authentication rejected: jwt_validation=%s", type(exc).__name__)
        raise AuthenticationError() from exc
    _ensure_audience_if_declared(payload, settings)
    return _principal_from_payload(payload, settings)


def _ensure_audience_if_declared(payload: dict[str, Any], settings: Settings) -> None:
    """Verify ``aud`` only when the token declares one.

    ACE (2026-09-16, confirmed by the product owner against real tokens) does
    not set ``aud`` at all - the ACE mapper only adds ``contexts.<nome>.roles``.
    A token without ``aud`` is authenticated on issuer/signature/expiry alone;
    the destination signal is the recognized context, checked later in
    ``_principal_from_payload`` (client allow-list + configured
    ``role_mappings``). Direct GEMODO clients (``gemodo-frontend``,
    ``geban-backend``) still set ``aud``, so when it IS present it MUST still
    contain ``keycloak_audience`` - this branch is not relaxed.
    """

    aud = payload.get("aud")
    if aud is None:
        return
    if settings.keycloak_audience not in _audience_tuple(aud):
        logger.warning("Authentication rejected: audience_mismatch")
        raise AuthenticationError()


def mock_principal(settings: Settings) -> PrincipalGEMODO:
    ruoli_contesto: tuple[tuple[str, tuple[str, ...]], ...] = ()
    if settings.gemodo_mock_context is not None:
        ruoli_contesto = ((settings.gemodo_mock_context, settings.gemodo_mock_context_roles),)
    return PrincipalGEMODO(
        subject=settings.gemodo_mock_subject,
        client_id=settings.gemodo_mock_client_id,
        audience=(settings.keycloak_audience,),
        ruoli=settings.gemodo_mock_roles,
        issuer=settings.keycloak_issuer_url,
        ruoli_diretti=settings.gemodo_mock_roles,
        ruoli_contesto=ruoli_contesto,
    )


def require_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> PrincipalGEMODO:
    if settings.gemodo_use_mock_principal:
        return mock_principal(settings)
    if credentials is None or credentials.scheme.lower() != "bearer":
        logger.warning("Authentication rejected: bearer_missing_or_wrong_scheme")
        raise AuthenticationError()
    return decode_principal_from_token(credentials.credentials, settings=settings)


def require_documenti_viewer(principal: PrincipalGEMODO = Depends(require_principal)) -> PrincipalGEMODO:
    return ensure_roles(principal, (ROLE_DOCUMENTI_VIEWER, ROLE_DOCUMENTI_GENERATORE))


def require_documenti_generatore(principal: PrincipalGEMODO = Depends(require_principal)) -> PrincipalGEMODO:
    return ensure_roles(principal, (ROLE_DOCUMENTI_GENERATORE,))


def require_modelli_gestore(principal: PrincipalGEMODO = Depends(require_principal)) -> PrincipalGEMODO:
    return ensure_roles(principal, (ROLE_GEMODO_MODELLI_GESTORE,))


def _permessi_nel_contesto(principal: PrincipalGEMODO, codice_contesto: str, settings: Settings) -> set[str]:
    """Permissions granted by ``codice_contesto`` alone, never mixed with any other context.

    DEC-001-CONTESTO-SOSTITUISCE-UFFICIO: a role granting a permission in one context
    MUST NOT authorize an action scoped to a different context - so this always calls
    ``permessi_da_ruoli_esterni`` with a single-context dict, never
    ``principal.ruoli`` (already flattened across every context the token carries).
    """
    ruoli_nel_contesto = dict(principal.ruoli_contesto).get(codice_contesto, ())
    if not ruoli_nel_contesto:
        return set()
    sistemi = list(_configured_sistemi(settings))
    return permessi_da_ruoli_esterni(
        sistemi,
        client_id=principal.client_id,
        context_roles={codice_contesto: ruoli_nel_contesto},
    )


def verify_scrittura_su_contesto(
    principal: PrincipalGEMODO,
    codice_contesto: str,
    settings: Settings | None = None,
) -> None:
    """Authorize a write for a tipo documento owned by ``codice_contesto``."""
    settings = settings or get_settings()
    if ROLE_GEMODO_MODELLI_GESTORE not in _permessi_nel_contesto(principal, codice_contesto, settings):
        raise AuthorizationError()


def verifica_permesso_contesto(
    principal: PrincipalGEMODO,
    codice_contesto: str,
    permesso: str,
    settings: Settings | None = None,
) -> bool:
    """Whether ``permesso`` is granted by ``codice_contesto`` alone (001 FR-034..038, 006 FR-014..017).

    Gated behind ``GEMODO_ENFORCE_CONTESTO_CONSUMATORE`` (default off) for a staged
    rollout: while off, every caller with the coarse role keeps today's behavior
    (this returns True unconditionally) so existing callers/tests are unaffected;
    once on, a caller must additionally hold ``permesso`` in the resource's own
    context - no fallback to the aggregated/global role list (FR-036). Callers
    decide the exact denial response themselves (404 sanitized for direct-ID
    access per FR-037, 403 for an explicitly filtered search) since that varies
    per route; this only answers the yes/no question.
    """
    settings = settings or get_settings()
    if not settings.gemodo_enforce_contesto_consumatore:
        return True
    return permesso in _permessi_nel_contesto(principal, codice_contesto, settings)


def contesti_con_permesso(
    principal: PrincipalGEMODO,
    permesso: str,
    codici_contesto: Iterable[str],
    settings: Settings | None = None,
) -> set[str]:
    """Subset of ``codici_contesto`` that grant ``permesso`` on their own (T083).

    Each candidate context is evaluated in isolation via ``_permessi_nel_contesto``,
    so a manager authorized to read/write in context A never gains visibility into an
    integration owned by context B just because both appear in the same token.
    """
    settings = settings or get_settings()
    return {
        codice for codice in set(codici_contesto)
        if permesso in _permessi_nel_contesto(principal, codice, settings)
    }
