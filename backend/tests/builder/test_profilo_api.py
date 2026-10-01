"""Profilo dell'utente calcolato dal backend (007 FR-034, T114, T115).

Il punto e' che l'interfaccia smetta di indovinare: cio' che questa rotta
dichiara deve coincidere con cio' che le altre rotte autorizzano.
"""

from __future__ import annotations

import pytest

from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def _per_contesto(profilo: dict) -> dict[str, list[str]]:
    return {c["codice"]: [p["codice"] for p in c["permessi"]] for c in profilo["contesti"]}


@pytest.mark.integration
def test_un_gestore_vede_i_permessi_che_il_suo_ruolo_gli_concede_davvero(builder_client):
    profilo = builder_client.get("/api/v1/builder/profilo").json()

    contesti = _per_contesto(profilo)
    assert contesti["geban"] == ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER", "GEMODO_MODELLI_GESTORE"]
    assert profilo["contesti"][0]["ruoli"] == ["ROLE_MANAGER#geban"]
    assert "GEMODO_MODELLI_GESTORE" in profilo["permessi"]
    # Ogni permesso dice cosa consente, con il testo del backend.
    gestore = next(p for p in profilo["contesti"][0]["permessi"] if p["codice"] == "GEMODO_MODELLI_GESTORE")
    assert "pubblica" in gestore["descrizione"]


@pytest.mark.integration
def test_un_contesto_non_mappato_compare_senza_permessi(builder_client, monkeypatch):
    """Il caso che l'interfaccia sbagliava: ROLE_MANAGER#altro sembrava un gestore."""
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "altro")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_MANAGER#altro")
    monkeypatch.setenv("GEMODO_MOCK_ROLES", "")

    profilo = builder_client.get("/api/v1/builder/profilo").json()

    assert _per_contesto(profilo) == {"altro": []}
    assert "GEMODO_MODELLI_GESTORE" not in profilo["permessi"]
    # E il backend lo tratta coerentemente: niente scrittura di modelli.
    assert builder_client.get("/api/v1/builder/contesti").json() == []


@pytest.mark.integration
def test_l_amministratore_e_un_permesso_diretto_non_di_contesto(builder_client):
    profilo = builder_client.get("/api/v1/builder/profilo").json()
    diretti = [p["codice"] for p in profilo["permessi_diretti"]]
    assert "GEMODO_ADMIN" in diretti
    assert "GEMODO_ADMIN" in profilo["permessi"]
