"""E2E test: mock GEBAN valid flow, catalogo -> campi -> validazione -> generazione -> stato.

Drives the real ``mock-geban/scenario_runner.py`` against the real scenario manifest
and the real ``bando-concorso-valid.json`` demo payload. Since specs 001/004/005/006
have not implemented the real GEMODO HTTP API yet (no ``tasks.md``), a
``FakeGemodoClient`` (backend/tests/support/fake_gemodo_client.py) stands in for that
not-yet-built backend; authorization is delegated to the real
``app.quality.integration_profile`` logic, not reimplemented in the fake. What is
verified here is real: scenario resolution and step ordering, the guard against
internal shortcuts, and that the demo artifacts (payload, scenario, expected outcomes)
are mutually consistent.
"""

from __future__ import annotations

import json

import pytest
from scenario_runner import esegui_scenario, load_scenario_manifest, parse_scenarios

from app.quality.mock_contract_guard import OperazionePubblica
from tests.support.fake_gemodo_client import FakeGemodoClient, GemodoErroreFunzionale
from tests.support.integration_profiles import (
    GEBAN_PROFILE_CODE,
    sistema_geban_attivo,
    sistema_geban_profilo_bozza,
)

pytestmark = pytest.mark.e2e


@pytest.fixture()
def scenario_e2e_001(repo_root):
    manifest_path = repo_root / "mock-geban" / "scenarios" / "minimum-e2e.yaml"
    manifest = load_scenario_manifest(manifest_path)
    scenari = {s.id: s for s in parse_scenarios(manifest)}
    return scenari["E2E-001"]


@pytest.fixture()
def payload_valido(repo_root):
    path = repo_root / "mock-geban" / "payloads" / "bando-concorso-valid.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def expected_outcomes(repo_root):
    from app.quality.manifest_loader import load_manifest

    path = repo_root / "mock-geban" / "scenarios" / "expected-outcomes.yaml"
    return load_manifest(path)


def test_valid_payload_has_no_expected_errors(payload_valido):
    assert payload_valido.get("atteso_errori", []) == []
    assert payload_valido["bando_inglese"] is True


def test_e2e_001_step_order_is_catalog_fields_validation_generation_status(scenario_e2e_001):
    piano = scenario_e2e_001.contratti_coinvolti

    assert piano == [
        "catalogo modelli pubblicati",
        "campi richiesti/schema",
        "validazione payload",
        "generazione documento",
        "stato generazione",
    ]


def test_e2e_001_runs_end_to_end_against_an_authorized_fake_client(scenario_e2e_001, payload_valido):
    client = FakeGemodoClient(sistema=sistema_geban_attivo(), profilo_codice=GEBAN_PROFILE_CODE)

    risultato = esegui_scenario(scenario_e2e_001, payload=payload_valido, client=client)

    assert risultato.piano_eseguito is True
    assert [p.passo.operazione for p in risultato.passi] == [
        OperazionePubblica.CATALOGO_MODELLI,
        OperazionePubblica.CAMPI_RICHIESTI,
        OperazionePubblica.VALIDA_PAYLOAD,
        OperazionePubblica.GENERA_DOCUMENTO,
        OperazionePubblica.STATO_GENERAZIONE,
    ]

    esito_generazione = next(
        p.esito for p in risultato.passi if p.passo.operazione is OperazionePubblica.GENERA_DOCUMENTO
    )
    assert esito_generazione["stato"] == "COMPLETATA"

    esito_stato = next(
        p.esito for p in risultato.passi if p.passo.operazione is OperazionePubblica.STATO_GENERAZIONE
    )
    assert esito_stato["stato"] == "COMPLETATA"


def test_e2e_001_english_flag_produces_two_outputs_it_and_en(scenario_e2e_001, payload_valido, expected_outcomes):
    client = FakeGemodoClient(sistema=sistema_geban_attivo(), profilo_codice=GEBAN_PROFILE_CODE)

    risultato = esegui_scenario(scenario_e2e_001, payload=payload_valido, client=client)

    esito_generazione = next(
        p.esito for p in risultato.passi if p.passo.operazione is OperazionePubblica.GENERA_DOCUMENTO
    )
    lingue_prodotte = {o["lingua"] for o in esito_generazione["output"]}
    assert lingue_prodotte == {"IT", "EN"}

    attese = next(o for o in expected_outcomes["scenario_outcomes"] if o["scenario_id"] == "E2E-001")
    lingue_attese = {o["lingua"] for o in attese["output_attesi"]}
    assert lingue_prodotte == lingue_attese


def test_e2e_001_is_rejected_for_a_client_without_an_active_integration_profile(scenario_e2e_001, payload_valido):
    client = FakeGemodoClient(sistema=sistema_geban_profilo_bozza(), profilo_codice=GEBAN_PROFILE_CODE)

    with pytest.raises(GemodoErroreFunzionale) as exc_info:
        esegui_scenario(scenario_e2e_001, payload=payload_valido, client=client)

    assert exc_info.value.codice == "PROFILO_INTEGRAZIONE_NON_ABILITATO"
