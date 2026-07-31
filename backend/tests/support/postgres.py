"""PostgreSQL test support for integration tests.

Tests that need a real database can use ``postgres_database_url``. In CI or local
developer environments set ``DATABASE_URL`` to reuse an existing PostgreSQL instance.
When it is absent, the fixture tries Testcontainers and skips cleanly if Docker is not
available.
"""

from __future__ import annotations

from collections.abc import Iterator
import os

import pytest


@pytest.fixture(scope="session")
def postgres_database_url() -> Iterator[str]:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        yield configured_url
        return

    try:
        from testcontainers.community.postgres import PostgresContainer
    except Exception as exc:  # pragma: no cover - depends on optional local tooling.
        try:
            from testcontainers.postgres import PostgresContainer
        except Exception:
            pytest.skip(f"Testcontainers PostgreSQL non disponibile: {exc}")

    try:
        with PostgresContainer("postgres:15") as postgres:
            yield postgres.get_connection_url(driver="psycopg")
    except Exception as exc:  # pragma: no cover - depends on Docker availability.
        pytest.skip(f"Docker/Testcontainers PostgreSQL non disponibile: {exc}")
