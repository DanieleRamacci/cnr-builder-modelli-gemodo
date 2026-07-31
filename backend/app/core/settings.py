"""Application settings for GEMODO runtime features."""

from __future__ import annotations

from dataclasses import dataclass
import os


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _tuple_env(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str
    keycloak_issuer_url: str
    keycloak_audience: str
    keycloak_frontend_client_id: str
    gemodo_allowed_interactive_clients: tuple[str, ...]
    keycloak_jwks_url: str | None
    keycloak_jwks_cache_ttl_seconds: int
    gemodo_use_mock_principal: bool
    gemodo_mock_subject: str
    gemodo_mock_client_id: str
    gemodo_mock_roles: tuple[str, ...]

    @property
    def jwks_url(self) -> str:
        if self.keycloak_jwks_url:
            return self.keycloak_jwks_url
        return f"{self.keycloak_issuer_url.rstrip('/')}/protocol/openid-connect/certs"


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://gemodo:gemodo@localhost:5432/gemodo"),
        keycloak_issuer_url=os.getenv("KEYCLOAK_ISSUER_URL", "https://sso.test.si.cnr.it/auth/realms/cnr"),
        keycloak_audience=os.getenv("KEYCLOAK_AUDIENCE", "gemodo-backend"),
        keycloak_frontend_client_id=os.getenv("KEYCLOAK_FRONTEND_CLIENT_ID", "gemodo-frontend"),
        gemodo_allowed_interactive_clients=_tuple_env("GEMODO_ALLOWED_INTERACTIVE_CLIENTS", "gemodo-frontend"),
        keycloak_jwks_url=os.getenv("KEYCLOAK_JWKS_URL"),
        keycloak_jwks_cache_ttl_seconds=_int_env("KEYCLOAK_JWKS_CACHE_TTL_SECONDS", 300),
        gemodo_use_mock_principal=_bool_env("GEMODO_USE_MOCK_PRINCIPAL", False),
        gemodo_mock_subject=os.getenv("GEMODO_MOCK_SUBJECT", "mock-geban-backend"),
        gemodo_mock_client_id=os.getenv("GEMODO_MOCK_CLIENT_ID", "geban-backend"),
        gemodo_mock_roles=tuple(
            role.strip()
            for role in os.getenv("GEMODO_MOCK_ROLES", "DOCUMENTI_VIEWER,DOCUMENTI_GENERATORE").split(",")
            if role.strip()
        ),
    )
