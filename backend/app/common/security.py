"""Security helpers for Keycloak-protected APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient

from app.common.errors import AuthenticationError, AuthorizationError
from app.core.settings import Settings, get_settings


KEYCLOAK_AUDIENCE = "gemodo-backend"
GEBAN_BACKEND_CLIENT_ID = "geban-backend"
ROLE_DOCUMENTI_VIEWER = "DOCUMENTI_VIEWER"
ROLE_DOCUMENTI_GENERATORE = "DOCUMENTI_GENERATORE"
ALLOWED_ALGORITHMS = ["RS256"]

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class PrincipalGEMODO:
    subject: str
    client_id: str
    audience: tuple[str, ...]
    ruoli: tuple[str, ...]
    issuer: str

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


def _principal_from_payload(payload: dict[str, Any], settings: Settings) -> PrincipalGEMODO:
    client_id = payload.get("azp") or payload.get("client_id")
    if client_id != GEBAN_BACKEND_CLIENT_ID:
        raise AuthorizationError("Client non autorizzato per le API GEBAN")
    return PrincipalGEMODO(
        subject=str(payload.get("sub") or ""),
        client_id=str(client_id),
        audience=_audience_tuple(payload.get("aud")),
        ruoli=_extract_roles(payload, settings.keycloak_audience),
        issuer=str(payload.get("iss") or ""),
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
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer_url,
        )
    except InvalidTokenError as exc:
        raise AuthenticationError() from exc
    return _principal_from_payload(payload, settings)


def mock_principal(settings: Settings) -> PrincipalGEMODO:
    return PrincipalGEMODO(
        subject=settings.gemodo_mock_subject,
        client_id=settings.gemodo_mock_client_id,
        audience=(settings.keycloak_audience,),
        ruoli=settings.gemodo_mock_roles,
        issuer=settings.keycloak_issuer_url,
    )


def require_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> PrincipalGEMODO:
    if settings.gemodo_use_mock_principal:
        return mock_principal(settings)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    return decode_principal_from_token(credentials.credentials, settings=settings)


def require_documenti_viewer(principal: PrincipalGEMODO = Depends(require_principal)) -> PrincipalGEMODO:
    return ensure_roles(principal, (ROLE_DOCUMENTI_VIEWER, ROLE_DOCUMENTI_GENERATORE))


def require_documenti_generatore(principal: PrincipalGEMODO = Depends(require_principal)) -> PrincipalGEMODO:
    return ensure_roles(principal, (ROLE_DOCUMENTI_GENERATORE,))
