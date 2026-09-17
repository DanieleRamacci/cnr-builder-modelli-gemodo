from pathlib import Path
from urllib.parse import urljoin

import yaml
from fastapi.testclient import TestClient

from app.main import app


def test_builder_docs_share_versioned_contract_and_resolve_external_ref():
    path = Path(__file__).resolve().parents[3] / "specs/010-configurazione-cataloghi-integrazioni/contracts/builder-discovery-api.openapi.yaml"
    with TestClient(app) as client:
        source = client.get("/openapi/builder-discovery.yaml")
        assert source.status_code == 200
        assert source.text == path.read_text()
        contract = yaml.safe_load(source.text)
        for page in ["/docs/builder-discovery", "/redoc/builder-discovery"]:
            response = client.get(page)
            assert response.status_code == 200
            assert "/openapi/builder-discovery.yaml" in response.text
        operation = contract["paths"]["/api/v1/builder/tipi-documento/{codiceTipoDocumento}/struttura-disponibile"]["get"]
        ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["properties"]["nodi"]["items"]["$ref"]
        external = client.get(urljoin("/openapi/builder-discovery.yaml", ref.split("#")[0]))
        assert external.status_code == 200
        assert "NodoCategorizzazione" in yaml.safe_load(external.text)["components"]["schemas"]
