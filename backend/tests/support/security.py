"""JWT helpers for security tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class JwtTestKeys:
    def __init__(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    @property
    def private_pem(self) -> bytes:
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    @property
    def public_pem(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )


def signed_token(
    keys: JwtTestKeys,
    *,
    issuer: str = "https://sso.test.si.cnr.it/auth/realms/cnr",
    audience: str | list[str] | None = "gemodo-backend",
    client_id: str = "geban-backend",
    roles: Iterable[str] | None = ("DOCUMENTI_GENERATORE",),
    contexts: dict[str, Iterable[str]] | None = None,
    expires_delta: timedelta = timedelta(minutes=5),
    issued_at_delta: timedelta = timedelta(),
    not_before_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    issued_at = now + issued_at_delta
    payload: dict[str, Any] = {
        "iss": issuer,
        "sub": "test-subject",
        "azp": client_id,
        "iat": int(issued_at.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if not_before_delta is not None:
        payload["nbf"] = int((now + not_before_delta).timestamp())
    if audience is not None:
        payload["aud"] = audience
    if roles is not None:
        resource_audience = audience if isinstance(audience, str) else "gemodo-backend"
        payload["resource_access"] = {
            resource_audience: {
                "roles": list(roles),
            }
        }
    if contexts is not None:
        payload["contexts"] = {
            context_name: {"roles": list(context_roles)}
            for context_name, context_roles in contexts.items()
        }
    return jwt.encode(payload, keys.private_pem, algorithm="RS256")
