from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from openapi_spec_validator import validate

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERAZIONE = REPO_ROOT / "specs/004-generazione-documenti-pdf/contracts/generazione-documenti-api.openapi.yaml"
STORAGE = REPO_ROOT / "specs/005-storage-idempotenza-consultazione/contracts/storage-documenti-api.openapi.yaml"
CATALOGO = REPO_ROOT / "specs/001-catalogo-contratto-geban/contracts/geban-catalog-api.openapi.yaml"


@pytest.mark.parametrize("path", [GENERAZIONE, STORAGE, CATALOGO])
def test_contracts_are_valid_openapi(path):
    doc = yaml.safe_load(path.read_text())
    validate(doc, base_uri=path.as_uri())


def test_generazione_contract_matches_real_states():
    contract = yaml.safe_load(GENERAZIONE.read_text())
    stato = contract["components"]["schemas"]["EsitoGenerazione"]["properties"]["stato"]
    assert set(stato["enum"]) == {"COMPLETATO", "FALLITO", "DATI_NON_VALIDI"}


def test_storage_contract_matches_real_states():
    contract = yaml.safe_load(STORAGE.read_text())
    stato = contract["components"]["schemas"]["StatoDocumento"]["properties"]["stato"]
    assert set(stato["enum"]) == {"COMPLETATO", "FALLITO"}


def test_old_simulated_generation_endpoint_is_withdrawn():
    contract = yaml.safe_load(CATALOGO.read_text())
    operazione = contract["paths"]["/documenti/genera"]["post"]
    assert operazione["deprecated"] is True
    assert operazione["x-implementation-status"] == "withdrawn"


@pytest.mark.parametrize("spec_id", ["generazione-documenti", "storage-documenti"])
def test_versioned_documentation_available(spec_id):
    with TestClient(app) as client:
        source = client.get(f"/openapi/{spec_id}.yaml")
        assert source.status_code == 200
        for path in (f"/docs/{spec_id}", f"/redoc/{spec_id}"):
            response = client.get(path)
            assert response.status_code == 200
            assert f"/openapi/{spec_id}.yaml" in response.text
