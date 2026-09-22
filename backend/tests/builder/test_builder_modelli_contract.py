"""Contract test for the 007 T006 rewrite of builder-modelli-api.openapi.yaml.

Same pattern as tests/configurazione/test_integration_contract.py: structural
validity (including the external $ref into geban-discovery-endpoint.openapi.yaml)
plus success/error examples that actually match their own schemas - the old 0.2.0
contract had neither (see the commit message for what was wrong with it).
"""

from pathlib import Path

import pytest
import yaml
from openapi_schema_validator import OAS30Validator
from openapi_spec_validator import validate


CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml"
)


@pytest.fixture
def contract():
    return yaml.safe_load(CONTRACT.read_text())


def test_builder_modelli_openapi_is_valid_including_external_references(contract):
    validate(contract, base_uri=CONTRACT.as_uri())


def test_contract_only_documents_routes_that_really_exist(contract):
    # The 0.2.0 contract described a tipi-documento/categorie CRUD and
    # archivia/sospendi/bozza-derivata transitions that were never implemented
    # this way (backend/app/builder/api.py has none of them) - this is the
    # concrete regression guard against drifting back to that.
    assert set(contract["paths"]) == {
        "/contesti",
        "/tipi-documento/{codiceTipoDocumento}/struttura-disponibile",
        "/tipi-documento/{codiceTipoDocumento}/policy-dimensioni",
        "/modelli",
        "/modelli/{modelloId}/versioni",
            "/modelli/{modelloId}",
            "/modelli/{modelloId}/edizioni-derivate",
        "/modelli/{modelloId}/versioni/{versioneId}/invia-revisione",
        "/modelli/{modelloId}/versioni/{versioneId}/approva",
        "/modelli/{modelloId}/versioni/{versioneId}/pubblica",
    }
    assert contract["security"] == [{"KeycloakBearer": []}]


def test_success_and_error_examples_match_their_schemas(contract):
    schemas = contract["components"]["schemas"]
    for path_item in contract["paths"].values():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "delete"}:
                continue
            for response in operation["responses"].values():
                if "$ref" in response or "content" not in response:
                    continue
                media = response["content"]["application/json"]
                schema = media["schema"]
                if "$ref" not in schema and "example" in media:
                    OAS30Validator(schema).validate(media["example"])
    error_validator = OAS30Validator(schemas["Errore"])
    for response in contract["components"]["responses"].values():
        media = response["content"]["application/json"]
        if "example" in media:
            error_validator.validate(media["example"])
        else:
            assert media["examples"]
            for example in media["examples"].values():
                error_validator.validate(example["value"])
