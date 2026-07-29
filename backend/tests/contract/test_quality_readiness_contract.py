"""Contract test: the quality-readiness manifest satisfies its required sections.

Exercises the real, versioned contract
(specs/009-fondamenta-mock-test-qualita/contracts/quality-readiness-contract.yaml) and
the real local manifest (infra/local/quality-readiness.local.yaml), plus the generic
validation engine itself against synthetic fixtures that must fail for concrete,
specific reasons. No part of the validation is mocked: a broken manifest or a broken
contract fails this suite for real.
"""

from __future__ import annotations

import copy

import pytest

from app.quality.errors import ContrattoNonValidoError
from app.quality.manifest_loader import (
    load_contract,
    load_manifest,
    validate_manifest_against_contract,
)

pytestmark = pytest.mark.contract


def test_contract_declares_all_nine_required_sections(quality_readiness_contract):
    expected_sections = {
        "environment",
        "seed_demo",
        "contracts",
        "api_documentation",
        "open_source_reuse",
        "integration_profiles",
        "document_models",
        "coverage",
        "open_decisions",
    }
    assert set(quality_readiness_contract["required_sections"]) == expected_sections


def test_real_local_manifest_satisfies_the_real_contract(
    local_quality_readiness_manifest, quality_readiness_contract
):
    result = validate_manifest_against_contract(
        local_quality_readiness_manifest, quality_readiness_contract
    )

    assert result.violations == []
    assert result.is_valid is True


def test_real_local_manifest_passes_every_mechanically_checked_boolean_rule(
    local_quality_readiness_manifest, quality_readiness_contract
):
    result = validate_manifest_against_contract(
        local_quality_readiness_manifest, quality_readiness_contract
    )
    checked = result.checked_rules()

    # These specific "must be false/true" invariants are the ones the constitution and
    # FR-010/FR-036/FR-045 treat as non-negotiable; assert they were actually evaluated
    # (not silently skipped) and that every one of them passed.
    checked_rule_texts = {r.rule for r in checked}
    assert "contains_real_or_sensitive_data must be false" in checked_rule_texts
    assert "contains_free_html must be false" in checked_rule_texts
    assert "contains_secrets must be false" in checked_rule_texts
    assert "manages_credentials must be false" in checked_rule_texts
    assert all(r.passed for r in checked)


def test_missing_required_section_is_reported(
    local_quality_readiness_manifest, quality_readiness_contract
):
    broken = copy.deepcopy(local_quality_readiness_manifest)
    del broken["integration_profiles"]

    result = validate_manifest_against_contract(broken, quality_readiness_contract)

    assert result.is_valid is False
    assert any("sezione mancante: integration_profiles" in v for v in result.violations)


def test_missing_required_field_on_a_section_item_is_reported(
    local_quality_readiness_manifest, quality_readiness_contract
):
    broken = copy.deepcopy(local_quality_readiness_manifest)
    del broken["seed_demo"][0]["contains_real_or_sensitive_data"]

    result = validate_manifest_against_contract(broken, quality_readiness_contract)

    assert result.is_valid is False
    assert any(
        "campi mancanti" in v and "contains_real_or_sensitive_data" in v for v in result.violations
    )


def test_sensitive_seed_data_violates_the_must_be_false_rule(
    local_quality_readiness_manifest, quality_readiness_contract
):
    broken = copy.deepcopy(local_quality_readiness_manifest)
    broken["seed_demo"][0]["contains_real_or_sensitive_data"] = True

    result = validate_manifest_against_contract(broken, quality_readiness_contract)

    assert result.is_valid is False
    assert any("contains_real_or_sensitive_data must be false" in v for v in result.violations)


def test_raise_if_invalid_raises_contratto_non_valido_error(
    local_quality_readiness_manifest, quality_readiness_contract
):
    broken = copy.deepcopy(local_quality_readiness_manifest)
    broken["open_source_reuse"]["contains_secrets"] = True

    result = validate_manifest_against_contract(broken, quality_readiness_contract)

    with pytest.raises(ContrattoNonValidoError):
        result.raise_if_invalid("quality-readiness")


def test_validate_against_a_contract_without_required_sections_is_rejected(
    mock_geban_scenarios_contract,
):
    with pytest.raises(ContrattoNonValidoError):
        validate_manifest_against_contract({}, mock_geban_scenarios_contract)


def test_load_contract_rejects_a_file_missing_contract_and_version_keys(tmp_path):
    bad_contract = tmp_path / "not-a-contract.yaml"
    bad_contract.write_text("just: a-random-yaml-file\n", encoding="utf-8")

    with pytest.raises(ContrattoNonValidoError):
        load_contract(bad_contract)


def test_load_manifest_rejects_a_non_mapping_yaml_document(tmp_path):
    bad_manifest = tmp_path / "not-a-manifest.yaml"
    bad_manifest.write_text("- just\n- a\n- list\n", encoding="utf-8")

    with pytest.raises(ContrattoNonValidoError):
        load_manifest(bad_manifest)
