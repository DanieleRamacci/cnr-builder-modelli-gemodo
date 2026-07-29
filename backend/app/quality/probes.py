"""Real healthcheck probes used to wire ``environment_verifier.verifica_ambiente``.

Kept separate from ``environment_verifier`` so the classification logic (PASS/PARTIAL/
FAIL) can be unit-tested with fake, deterministic probes while these functions remain
the only place that actually talks to the network or spawns a process.
"""

from __future__ import annotations

import os
import subprocess
import urllib.error
import urllib.request

from app.quality.environment_verifier import (
    HealthCheck,
    HealthCheckOutcome,
    healthcheck_errore_applicativo,
    healthcheck_prerequisito_mancante,
    healthcheck_up,
)


def http_healthcheck(url: str, *, timeout: float = 2.0) -> HealthCheck:
    """Build a healthcheck that performs a GET request against ``url``."""

    def _check() -> HealthCheckOutcome:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 (local/test infra only)
                status = response.status
        except urllib.error.HTTPError as exc:
            if exc.code >= 500:
                return healthcheck_errore_applicativo(f"HTTP {exc.code} da {url}")
            return healthcheck_up(f"HTTP {exc.code} da {url}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            return healthcheck_prerequisito_mancante(f"{url} non raggiungibile: {exc}")
        if status >= 500:
            return healthcheck_errore_applicativo(f"HTTP {status} da {url}")
        return healthcheck_up(f"HTTP {status} da {url}")

    return _check


def subprocess_healthcheck(command: list[str], *, timeout: float = 5.0) -> HealthCheck:
    """Build a healthcheck that runs a CLI probe (e.g. ``pg_isready``)."""

    def _check() -> HealthCheckOutcome:
        try:
            result = subprocess.run(  # noqa: S603 (fixed, non-shell command list)
                command, capture_output=True, timeout=timeout, check=False, text=True
            )
        except FileNotFoundError as exc:
            return healthcheck_prerequisito_mancante(f"comando non disponibile: {exc}")
        except subprocess.TimeoutExpired:
            return healthcheck_prerequisito_mancante(f"timeout eseguendo: {' '.join(command)}")
        if result.returncode == 0:
            return healthcheck_up((result.stdout or "").strip() or "ok")
        return healthcheck_prerequisito_mancante((result.stderr or result.stdout or "").strip() or f"exit code {result.returncode}")

    return _check


def probes_ambiente_locale() -> dict[str, HealthCheck]:
    """Real probes for the canonical local-dev environment, driven by env vars.

    ``mock-geban`` is intentionally not wired here: its declared healthcheck runs an
    end-to-end scenario, not a liveness probe, and the scenario runner is implemented
    by User Story 2 - see ``mock-geban/scenario_runner.py``.
    """

    backend_url = os.environ.get("GEMODO_API_BASE_URL", "http://localhost:8000")
    frontend_url = os.environ.get("GEMODO_FRONTEND_BASE_URL", "http://localhost:4200")
    documentale_url = os.environ.get("DOCUMENTALE_MOCK_URL", "http://localhost:9000")
    keycloak_issuer = os.environ.get(
        "KEYCLOAK_ISSUER_URL", "https://sso.test.si.cnr.it/auth/realms/cnr"
    )
    postgres_user = os.environ.get("POSTGRES_USER", "gemodo")

    return {
        "backend": http_healthcheck(f"{backend_url}/health"),
        "frontend": http_healthcheck(frontend_url),
        "postgres": subprocess_healthcheck(["pg_isready", "-U", postgres_user]),
        "keycloak": http_healthcheck(f"{keycloak_issuer}/.well-known/openid-configuration"),
        "documentale-mock": http_healthcheck(f"{documentale_url}/health"),
    }
