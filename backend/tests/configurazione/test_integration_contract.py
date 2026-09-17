from pathlib import Path

import pytest
import yaml
from openapi_schema_validator import OAS30Validator
from openapi_spec_validator import validate


CONTRACT = (
    Path(__file__).resolve().parents[3]
    / "specs/010-configurazione-cataloghi-integrazioni/contracts/integrazioni-api.openapi.yaml"
)


@pytest.fixture
def contract():
    return yaml.safe_load(CONTRACT.read_text())


def test_integration_openapi_is_valid_including_external_references(contract):
    validate(contract, base_uri=CONTRACT.as_uri())


def test_integration_contract_does_not_claim_runtime_or_seed(contract):
    assert contract["x-implementation-status"] == "planned"
    assert contract["security"] == [{"KeycloakBearer": []}]
    assert contract["components"]["schemas"]["IntegrazioneAdmin"]["properties"]["modalita"]["enum"] == ["SINGOLO_ENDPOINT"]
    assert "codice_contesto" not in contract["components"]["schemas"]["IntegrazioneUpdate"]["properties"]


def test_manager_representation_cannot_expose_admin_metadata(contract):
    visible = contract["components"]["schemas"]["IntegrazioneVisibile"]
    assert visible["additionalProperties"] is False
    assert set(visible["properties"]) == {"id", "codice", "nome", "codice_contesto"}
    for path, item in contract["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "post", "put"}:
                continue
            assert "401" in operation["responses"]
            if path.startswith("/configurazione/"):
                assert operation["x-required-role"] == "GEMODO_ADMIN"
                assert "403" in operation["responses"]
            if path.startswith("/builder/") and "{" in path:
                assert "404" in operation["responses"]
                assert {"502", "504"} <= operation["responses"].keys()


def test_success_and_error_examples_match_their_schemas(contract):
    schemas = contract["components"]["schemas"]
    for schema in schemas.values():
        if "example" in schema:
            OAS30Validator(schema).validate(schema["example"])
    error_validator = OAS30Validator(schemas["Errore"])
    for response in contract["components"]["responses"].values():
        media = response["content"]["application/json"]
        if "example" in media:
            error_validator.validate(media["example"])
        else:
            assert media["examples"]
            for example in media["examples"].values():
                error_validator.validate(example["value"])
