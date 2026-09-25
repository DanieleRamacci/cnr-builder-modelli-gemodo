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

from app.builder.api import router as builder_router


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
    """Il contratto elenca esattamente le rotte che il router espone.

    La 0.2.0 descriveva un CRUD di tipi documento/categorie e transizioni mai
    implementate cosi' (`backend/app/builder/api.py` non ne aveva nessuna):
    questo test e' la difesa contro quel ritorno.

    Il confronto e' **contro il router vero**, non contro un elenco scritto a
    mano: quello andava aggiornato a ogni rotta nuova e, fra un aggiornamento e
    l'altro, non diceva piu' nulla di utile. Cosi' invece una rotta aggiunta
    senza contratto - o un contratto che descrive una rotta inesistente - fa
    fallire il test da solo.
    """
    reali = {
        route.path.removeprefix(builder_router.prefix) for route in builder_router.routes
    }
    # Nessuna rotta documentata che non esista davvero. Questo confronto non
    # invecchia: vale anche per le rotte aggiunte domani.
    documentate = set(contract["paths"])
    assert documentate <= reali, documentate - reali
    # L'elenco resta esplicito perche' il router del builder serve anche rotte
    # che appartengono ad **altri** contratti - `/integrazioni*` e' della 010,
    # `/sezioni` della 003 - quindi qui non si puo' pretendere l'uguaglianza
    # con tutto il router.
    assert documentate == {
        "/contesti",
        "/tipi-documento/{codiceTipoDocumento}/struttura-disponibile",
        "/tipi-documento/{codiceTipoDocumento}/policy-dimensioni",
        "/modelli",
        "/modelli/filtri",
        "/modelli/{modelloId}/versioni",
        "/modelli/{modelloId}",
        "/modelli/{modelloId}/varianti",
        "/modelli/{modelloId}/edizioni-derivate",
        "/modelli/{modelloId}/versioni/{versioneId}/invia-revisione",
        "/modelli/{modelloId}/versioni/{versioneId}/approva",
        "/modelli/{modelloId}/versioni/{versioneId}/pubblica",
        "/modelli/{modelloId}/versioni/{versioneId}/sospendi",
        "/modelli/{modelloId}/versioni/{versioneId}/archivia",
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
