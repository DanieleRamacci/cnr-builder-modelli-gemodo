"""Contract test: mock-geban/scenarios/minimum-e2e.yaml mirrors the versioned contract.

Exercises the real local scenario manifest against the real
specs/009-fondamenta-mock-test-qualita/contracts/mock-geban-scenarios.yaml contract, and
the real per-scenario/minimum-coverage validation in ``app.quality.scenario``. No part
of the comparison logic is mocked.
"""

from __future__ import annotations

import copy

import pytest

from app.quality.errors import ContrattoNonValidoError
from app.quality.scenario import (
    compare_manifest_to_contract,
    parse_scenarios,
    validate_minimum_coverage,
    validate_scenario,
)
from app.quality.schemas import TipoScenario

pytestmark = pytest.mark.contract


def test_local_scenario_manifest_does_not_drift_from_the_contract(
    local_mock_scenarios_manifest, mock_geban_scenarios_contract
):
    violazioni = compare_manifest_to_contract(local_mock_scenarios_manifest, mock_geban_scenarios_contract)

    assert violazioni == []


def test_contract_defines_exactly_the_six_minimum_scenarios(mock_geban_scenarios_contract):
    ids = {s["id"] for s in mock_geban_scenarios_contract["scenarios"]}

    assert ids == {"E2E-001", "E2E-002", "E2E-003", "E2E-004", "E2E-005", "E2E-006"}


def test_every_local_scenario_is_individually_valid(local_mock_scenarios_manifest):
    scenari = parse_scenarios(local_mock_scenarios_manifest)

    assert len(scenari) == 6
    for scenario in scenari:
        validate_scenario(scenario)  # must not raise


def test_local_manifest_covers_the_six_minimum_scenario_types(local_mock_scenarios_manifest):
    scenari = parse_scenarios(local_mock_scenarios_manifest)

    validate_minimum_coverage(scenari)  # must not raise
    assert {s.tipo for s in scenari} == set(TipoScenario)


def test_unauthorized_and_failure_scenarios_are_present_not_optional(local_mock_scenarios_manifest):
    scenari = {s.id: s for s in parse_scenarios(local_mock_scenarios_manifest)}

    assert scenari["E2E-005"].tipo == TipoScenario.FALLIMENTO
    assert scenari["E2E-006"].tipo == TipoScenario.AUTORIZZAZIONE


def test_drift_in_required_contracts_is_detected(local_mock_scenarios_manifest, mock_geban_scenarios_contract):
    tampered = copy.deepcopy(local_mock_scenarios_manifest)
    tampered["scenarios"][0]["required_contracts"] = ["accesso diretto al database"]

    violazioni = compare_manifest_to_contract(tampered, mock_geban_scenarios_contract)

    assert any("required_contracts" in v for v in violazioni)


def test_missing_scenario_in_manifest_is_detected(local_mock_scenarios_manifest, mock_geban_scenarios_contract):
    tampered = copy.deepcopy(local_mock_scenarios_manifest)
    tampered["scenarios"] = [s for s in tampered["scenarios"] if s["id"] != "E2E-006"]

    violazioni = compare_manifest_to_contract(tampered, mock_geban_scenarios_contract)

    assert any("E2E-006" in v and "assente dal manifest" in v for v in violazioni)


def test_scenario_without_a_public_contract_reference_is_rejected(local_mock_scenarios_manifest):
    scenari = parse_scenarios(local_mock_scenarios_manifest)
    scenario_senza_contratti = scenari[0].model_copy(update={"contratti_coinvolti": []})

    with pytest.raises(ContrattoNonValidoError):
        validate_scenario(scenario_senza_contratti)
