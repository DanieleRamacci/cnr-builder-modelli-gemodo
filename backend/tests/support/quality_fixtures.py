"""Shared pytest fixtures for loading quality manifests and mock scenarios.

These fixtures load the real, versioned files under ``specs/009-.../contracts`` and
``infra/local`` / ``mock-geban`` - tests using them exercise the actual repository
artifacts, not synthetic stand-ins, so a broken manifest fails the test suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.quality.manifest_loader import load_contract, load_manifest

# backend/tests/support/quality_fixtures.py -> repo root is three levels up.
REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = REPO_ROOT / "specs" / "009-fondamenta-mock-test-qualita"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def quality_readiness_contract_path() -> Path:
    return SPEC_DIR / "contracts" / "quality-readiness-contract.yaml"


@pytest.fixture(scope="session")
def quality_readiness_contract(quality_readiness_contract_path: Path) -> dict:
    return load_contract(quality_readiness_contract_path)


@pytest.fixture(scope="session")
def local_quality_readiness_manifest_path() -> Path:
    return REPO_ROOT / "infra" / "local" / "quality-readiness.local.yaml"


@pytest.fixture(scope="session")
def local_quality_readiness_manifest(local_quality_readiness_manifest_path: Path) -> dict:
    return load_manifest(local_quality_readiness_manifest_path)


@pytest.fixture(scope="session")
def mock_geban_scenarios_contract_path() -> Path:
    return SPEC_DIR / "contracts" / "mock-geban-scenarios.yaml"


@pytest.fixture(scope="session")
def mock_geban_scenarios_contract(mock_geban_scenarios_contract_path: Path) -> dict:
    return load_contract(mock_geban_scenarios_contract_path)


@pytest.fixture(scope="session")
def local_mock_scenarios_manifest_path() -> Path:
    return REPO_ROOT / "mock-geban" / "scenarios" / "minimum-e2e.yaml"


@pytest.fixture(scope="session")
def local_mock_scenarios_manifest(local_mock_scenarios_manifest_path: Path) -> dict:
    return load_manifest(local_mock_scenarios_manifest_path)
