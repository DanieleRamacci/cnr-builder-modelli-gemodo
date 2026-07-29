"""Integration tests: coverage matrix mapping scenarios to requirements and contracts.

Exercises the real docs/quality-coverage-matrix.yaml against the real validation in
app.quality.coverage (spec 009, User Story 3, FR-016).
"""

from __future__ import annotations

import copy

import pytest

from app.quality.coverage import (
    riepilogo_stato,
    validate_copertura_scenari_minimi,
    validate_riga_copertura,
)
from app.quality.errors import ContrattoNonValidoError
from app.quality.manifest_loader import load_yaml
from app.quality.schemas import MatriceCopertura, StatoCopertura

pytestmark = pytest.mark.integration

SCENARI_MINIMI = {"E2E-001", "E2E-002", "E2E-003", "E2E-004", "E2E-005", "E2E-006"}

# FR-027..FR-045, esplicitamente richiesti dal task T056.
REQUISITI_027_045 = [f"FR-{n:03d}" for n in range(27, 46)]


@pytest.fixture()
def coverage_matrix_path(repo_root):
    return repo_root / "docs" / "quality-coverage-matrix.yaml"


@pytest.fixture()
def coverage_matrix_raw(coverage_matrix_path):
    return load_yaml(coverage_matrix_path)


@pytest.fixture()
def coverage_rows(coverage_matrix_raw):
    return [MatriceCopertura.model_validate(item) for item in coverage_matrix_raw["coverage"]]


def test_every_real_row_passes_validation(coverage_rows):
    for riga in coverage_rows:
        validate_riga_copertura(riga)  # must not raise


def test_real_matrix_covers_all_six_minimum_e2e_scenarios(coverage_rows):
    validate_copertura_scenari_minimi(coverage_rows, SCENARI_MINIMI)  # must not raise

    scenari_presenti = {r.scenario_id for r in coverage_rows}
    assert SCENARI_MINIMI <= scenari_presenti


@pytest.mark.parametrize("requirement_id", REQUISITI_027_045)
def test_every_requirement_from_fr027_to_fr045_is_covered(coverage_rows, requirement_id):
    requisiti_presenti = {r.requirement_id for r in coverage_rows}
    assert requirement_id in requisiti_presenti


def test_every_row_has_a_recognized_spec_owner_path(coverage_rows):
    for riga in coverage_rows:
        assert riga.spec_owner.startswith("specs/"), riga.id


def test_riepilogo_stato_counts_match_the_raw_data(coverage_rows):
    riepilogo = riepilogo_stato(coverage_rows)

    assert sum(riepilogo.values()) == len(coverage_rows)
    assert set(riepilogo) <= {s.value for s in StatoCopertura}


def test_missing_scenario_in_the_matrix_is_detected():
    righe_incomplete = [
        MatriceCopertura(
            id="COV-X",
            spec_owner="specs/009-fondamenta-mock-test-qualita",
            requirement_id="FR-013",
            scenario_id="E2E-001",
            contract_ref="mock-geban/scenarios/minimum-e2e.yaml",
            stato=StatoCopertura.COPERTO,
        )
    ]

    with pytest.raises(ContrattoNonValidoError) as exc_info:
        validate_copertura_scenari_minimi(righe_incomplete, SCENARI_MINIMI)

    mancanti = exc_info.value.violazioni[0]
    for scenario_id in SCENARI_MINIMI - {"E2E-001"}:
        assert scenario_id in mancanti


def test_bloccato_row_without_note_is_rejected(coverage_rows):
    riga_bloccata_senza_nota = coverage_rows[0].model_copy(update={"stato": StatoCopertura.BLOCCATO, "note": None})

    with pytest.raises(ContrattoNonValidoError):
        validate_riga_copertura(riga_bloccata_senza_nota)


def test_bloccato_row_with_note_is_accepted(coverage_rows):
    riga_bloccata_con_nota = coverage_rows[0].model_copy(
        update={"stato": StatoCopertura.BLOCCATO, "note": "bloccato da DEC-001-CONFIG-PROFILO-GEBAN"}
    )

    validate_riga_copertura(riga_bloccata_con_nota)  # must not raise


def test_no_duplicate_row_ids(coverage_rows):
    ids = [r.id for r in coverage_rows]
    assert len(ids) == len(set(ids))


def test_tampered_matrix_missing_a_scenario_is_detected(coverage_matrix_raw):
    tampered = copy.deepcopy(coverage_matrix_raw)
    tampered["coverage"] = [row for row in tampered["coverage"] if row["scenario_id"] != "E2E-006"]
    righe = [MatriceCopertura.model_validate(item) for item in tampered["coverage"]]

    with pytest.raises(ContrattoNonValidoError):
        validate_copertura_scenari_minimi(righe, SCENARI_MINIMI)
