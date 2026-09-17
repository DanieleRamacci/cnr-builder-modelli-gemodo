from pathlib import Path

import yaml

from app.common.errors import ErrorCode
from app.discovery.schemas import CampoDiscovery


CONTRACT = Path(__file__).resolve().parents[3] / "specs/010-configurazione-cataloghi-integrazioni/contracts/configurazione-cataloghi-api.openapi.yaml"


def test_admin_contract_uses_existing_security_and_error_envelope():
    contract = yaml.safe_load(CONTRACT.read_text())
    assert contract["security"] == [{"KeycloakBearer": []}]
    for path in contract["paths"].values():
        for operation in path.values():
            assert operation["x-required-role"] == "GEMODO_ADMIN"
            assert {"401", "403"} <= operation["responses"].keys()
    responses = contract["components"]["responses"]
    for name, code in [("Unauthorized", ErrorCode.ACCESSO_NON_AUTENTICATO),
                       ("Forbidden", ErrorCode.ACCESSO_NON_AUTORIZZATO),
                       ("DiscoveryNonConforme", ErrorCode.DISCOVERY_NON_CONFORME),
                       ("DiscoveryNonDisponibile", ErrorCode.DISCOVERY_NON_DISPONIBILE)]:
        example = responses[name]["content"]["application/json"]["example"]
        assert example["codice"] == code
        assert "messaggio" in example
    error = contract["components"]["schemas"]["ErrorResponse"]
    assert error["required"] == ["codice", "messaggio"]
    assert error["properties"]["dettagli"]["type"] == "array"


def test_admin_documentation_example_obeys_common_field_shape():
    contract = yaml.safe_load(CONTRACT.read_text())
    schemas = contract["components"]["schemas"]
    example = schemas["SchemaDiscoveryGenerato"]["example"]["schema"]
    field = example["DOCUMENTO_DEMO"]["nodi"][0]["campi"][0]
    assert CampoDiscovery.model_validate(field).codice == "titolo"
    types = schemas["CampoContrattoDatiInput"]["properties"]["tipo"]["enum"]
    assert set(types) == {"string", "number", "boolean", "date", "object", "array"}
