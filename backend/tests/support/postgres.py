"""PostgreSQL test support for integration tests.

Tests that need a real database can use ``postgres_database_url``. In CI or local
developer environments set ``DATABASE_URL`` to reuse an existing PostgreSQL instance.
When it is absent, the fixture tries Testcontainers and skips cleanly if Docker is not
available.
"""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import socket

import pytest


def _docker_socket_path() -> Path:
    docker_host = os.getenv("DOCKER_HOST", "")
    if docker_host.startswith("unix://"):
        return Path(docker_host.removeprefix("unix://")).expanduser()
    user_socket = Path.home() / ".docker" / "run" / "docker.sock"
    if user_socket.exists():
        return user_socket
    return Path("/var/run/docker.sock")


def _docker_is_reachable() -> bool:
    sock_path = _docker_socket_path()
    if not sock_path.exists():
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            sock.connect(str(sock_path))
    except OSError:
        return False
    return True


@pytest.fixture(scope="session")
def postgres_database_url() -> Iterator[str]:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        yield configured_url
        return

    if not _docker_is_reachable():
        pytest.skip("Docker/Testcontainers PostgreSQL non disponibile: socket Docker non raggiungibile")

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
