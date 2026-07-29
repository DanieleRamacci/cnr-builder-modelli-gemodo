"""E2E tests: payload non valido, retry idempotente, conflitto idempotente,
generazione fallita e accesso non autorizzato (E2E-002..E2E-006).

Same approach as test_mock_geban_valid_flow.py: drives the real scenario runner and
manifests through a ``FakeGemodoClient`` standing in for the not-yet-implemented real
GEMODO backend (specs 001/004/005/006 have no ``tasks.md`` yet). Authorization comes
from the real ``app.quality.integration_profile`` logic.
"""

from __future__ import annotations

import copy
import json

import pytest
from scenario_runner import esegui_scenario, load_scenario_manifest, parse_scenarios

from app.quality.manifest_loader import load_manifest
from app.quality.mock_contract_guard import OperazionePubblica
from tests.support.fake_gemodo_client import FakeGemodoClient, GemodoErroreFunzionale
from tests.support.integration_profiles import (
    GEBAN_PROFILE_CODE,
    sistema_geban_attivo,
    sistema_geban_profilo_bozza,
)

pytestmark = pytest.mark.e2e


@pytest.fixture()
def scenari(repo_root):
    manifest_path = repo_root / "mock-geban" / "scenarios" / "minimum-e2e.yaml"
    manifest = load_scenario_manifest(manifest_path)
    return {s.id: s for s in parse_scenarios(manifest)}


@pytest.fixture()
def payload_valido(repo_root):
    path = repo_root / "mock-geban" / "payloads" / "bando-concorso-valid.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def payload_invalido(repo_root):
    path = repo_root / "mock-geban" / "payloads" / "bando-concorso-invalid.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def expected_outcomes(repo_root):
    path = repo_root / "mock-geban" / "scenarios" / "expected-outcomes.yaml"
    return load_manifest(path)


def _outcome_for(expected_outcomes, scenario_id):
    return next(o for o in expected_outcomes["scenario_outcomes"] if o["scenario_id"] == scenario_id)


def _authorized_client():
    return FakeGemodoClient(sistema=sistema_geban_attivo(), profilo_codice=GEBAN_PROFILE_CODE)


# ---------------------------------------------------------------------------
# E2E-002: payload non valido
# ---------------------------------------------------------------------------


def test_e2e_002_invalid_payload_is_rejected_with_the_expected_error_codes(
    scenari, payload_invalido, expected_outcomes
):
    risultato = esegui_scenario(scenari["E2E-002"], payload=payload_invalido, client=_authorized_client())

    assert risultato.piano_eseguito is True
    esito_validazione = risultato.passi[-1].esito
    assert esito_validazione["valido"] is False

    codici_prodotti = {e["codice"] for e in esito_validazione["errori"]}
    attesi = set(_outcome_for(expected_outcomes, "E2E-002")["errori_attesi"])
    assert codici_prodotti == attesi


def test_e2e_002_does_not_reach_generation(scenari):
    assert "generazione documento" not in scenari["E2E-002"].contratti_coinvolti


# ---------------------------------------------------------------------------
# E2E-003: retry idempotente
# ---------------------------------------------------------------------------


def test_e2e_003_identical_retry_returns_the_existing_generation_not_a_duplicate(scenari, payload_valido):
    client = _authorized_client()

    primo = esegui_scenario(scenari["E2E-003"], payload=payload_valido, client=client)
    secondo = esegui_scenario(scenari["E2E-003"], payload=payload_valido, client=client)

    esito_primo = next(p.esito for p in primo.passi if p.esito is not None and "riutilizzato" in p.esito)
    esito_secondo = next(p.esito for p in secondo.passi if p.esito is not None and "riutilizzato" in p.esito)

    assert esito_primo["riutilizzato"] is False
    assert esito_secondo["riutilizzato"] is True
    assert esito_primo["output"] == esito_secondo["output"]
    assert len(client._generazioni) == 1


# ---------------------------------------------------------------------------
# E2E-004: conflitto idempotente
# ---------------------------------------------------------------------------


def test_e2e_004_same_key_with_divergent_data_raises_conflict(scenari, payload_valido, expected_outcomes):
    client = _authorized_client()
    payload_divergente = copy.deepcopy(payload_valido)
    payload_divergente["dati"]["numero_posti"] = 999

    esegui_scenario(scenari["E2E-004"], payload=payload_valido, client=client)

    with pytest.raises(GemodoErroreFunzionale) as exc_info:
        esegui_scenario(scenari["E2E-004"], payload=payload_divergente, client=client)

    attesi = set(_outcome_for(expected_outcomes, "E2E-004")["errori_attesi"])
    assert exc_info.value.codice in attesi
    assert exc_info.value.codice == "GENERAZIONE_CONFLITTO_IDEMPOTENTE"


# ---------------------------------------------------------------------------
# E2E-005: generazione fallita
# ---------------------------------------------------------------------------


def test_e2e_005_failed_generation_is_reported_and_status_stays_queryable(scenari, payload_valido, expected_outcomes):
    client = FakeGemodoClient(
        sistema=sistema_geban_attivo(), profilo_codice=GEBAN_PROFILE_CODE, forza_fallimento=True
    )

    with pytest.raises(GemodoErroreFunzionale) as exc_info:
        esegui_scenario(scenari["E2E-005"], payload=payload_valido, client=client)

    attesi = set(_outcome_for(expected_outcomes, "E2E-005")["errori_attesi"])
    assert exc_info.value.codice in attesi

    # Lo stato deve restare consultabile anche dopo il fallimento (FR-020).
    esito_stato = client.esegui(OperazionePubblica.STATO_GENERAZIONE, payload_valido)
    assert esito_stato["stato"] == "FALLITA"


# ---------------------------------------------------------------------------
# E2E-006: accesso non autorizzato
# ---------------------------------------------------------------------------


def test_e2e_006_unauthorized_profile_is_denied_no_status_or_download_exposed(
    scenari, payload_valido, expected_outcomes
):
    client = FakeGemodoClient(sistema=sistema_geban_profilo_bozza(), profilo_codice=GEBAN_PROFILE_CODE)

    with pytest.raises(GemodoErroreFunzionale) as exc_info:
        esegui_scenario(scenari["E2E-006"], payload=payload_valido, client=client)

    attesi = set(_outcome_for(expected_outcomes, "E2E-006")["errori_attesi"])
    assert exc_info.value.codice in attesi
    assert exc_info.value.codice == "PROFILO_INTEGRAZIONE_NON_ABILITATO"


def test_e2e_006_covers_both_status_and_download_operations(scenari):
    assert scenari["E2E-006"].contratti_coinvolti == ["stato generazione", "download documento"]
