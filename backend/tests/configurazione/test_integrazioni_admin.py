import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import sqlalchemy as sa
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.common.security import PrincipalGEMODO, require_principal
from app.db.session import get_db
from app.main import app
from tests.discovery.conftest import discovery_server  # noqa: F401 (fixture reuse)
from tests.discovery.test_pagination import fragment
from tests.support.postgres import postgres_database_url


@pytest.fixture
def slow_discovery_server():
    """A discovery server whose /discovery response blocks until the test releases it -
    real HTTP, not a mock, so a genuine concurrent request can race the in-flight verify
    (T084), not just a simulated interleaving via direct SQL beforehand."""
    arrived = Event()
    respond = Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            arrived.set()
            respond.wait(timeout=5)
            raw = json.dumps(fragment()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", arrived, respond
    finally:
        respond.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture
def admin_client(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = sa.create_engine(postgres_database_url)

    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "admin-test", "gemodo-frontend", ("gemodo-backend",), ("GEMODO_ADMIN",),
        "https://sso.example.test", ruoli_diretti=("GEMODO_ADMIN",),
    )
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def crea(client, codice=None):
    codice = codice or ("SOFTWARE_" + uuid.uuid4().hex[:16])
    response = client.post("/api/v1/configurazione/integrazioni", json={
        "codice": codice, "nome": "Software Demo", "codice_contesto": "demo",
    })
    assert response.status_code == 201, response.text
    return codice, response.json()


def allowlist(monkeypatch, origine, *, privato=True):
    monkeypatch.setenv("GEMODO_INTEGRAZIONI_ALLOWLIST", origine)
    if privato:
        monkeypatch.setenv("GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO", origine)


@pytest.mark.integration
def test_create_starts_disconnected_and_rejects_duplicate_code(admin_client):
    client, _ = admin_client
    codice, created = crea(client)
    assert created["stato"] == "DEFINITO"
    assert created["revisione"] == 1
    assert created["url"] is None
    assert created["ultima_verifica"] is None
    assert created["modalita"] == "SINGOLO_ENDPOINT"
    duplicate = client.post("/api/v1/configurazione/integrazioni", json={
        "codice": codice, "nome": "Altro", "codice_contesto": "demo",
    })
    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["codice"] == "INTEGRAZIONE_DUPLICATA"


@pytest.mark.integration
def test_list_and_get_roundtrip_and_missing_id_is_404(admin_client):
    client, _ = admin_client
    codice, created = crea(client)
    listing = client.get("/api/v1/configurazione/integrazioni")
    assert listing.status_code == 200
    assert any(item["id"] == created["id"] for item in listing.json())
    fetched = client.get(f"/api/v1/configurazione/integrazioni/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created
    missing = client.get(f"/api/v1/configurazione/integrazioni/{uuid.uuid4()}")
    assert missing.status_code == 404


@pytest.mark.integration
def test_configure_enforces_optimistic_revision_and_egress_allowlist(admin_client, monkeypatch):
    client, _ = admin_client
    codice, created = crea(client)
    base = f"/api/v1/configurazione/integrazioni/{created['id']}"
    stale = client.put(base, json={
        "revisione_attesa": 99, "nome": "Software Demo", "url": None, "timeout_ms": 5000,
    })
    assert stale.status_code == 409, stale.text
    assert stale.json()["codice"] == "REVISIONE_SUPERATA"
    not_allowed = client.put(base, json={
        "revisione_attesa": 1, "nome": "Software Demo",
        "url": "https://not-allowlisted.example.test/discovery", "timeout_ms": 5000,
    })
    assert not_allowed.status_code == 422, not_allowed.text
    assert not_allowed.json()["codice"] == "DESTINAZIONE_NON_APPROVATA"
    allowlist(monkeypatch, "https://software.example.test")
    configured = client.put(base, json={
        "revisione_attesa": 1, "nome": "Software Demo",
        "url": "https://software.example.test/discovery", "timeout_ms": 4000,
    })
    assert configured.status_code == 200, configured.text
    body = configured.json()
    assert body["revisione"] == 2
    assert body["url"] == "https://software.example.test/discovery"
    assert body["stato"] == "DEFINITO"


@pytest.mark.integration
def test_public_https_origin_with_a_private_ip_is_rejected(admin_client, monkeypatch):
    client, _ = admin_client
    _, created = crea(client)
    # "localhost" resolves to a loopback IP without needing real DNS; not listed as
    # "privato", so the allowlist alone must not be enough to approve it.
    monkeypatch.setenv("GEMODO_INTEGRAZIONI_ALLOWLIST", "https://localhost")
    response = client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo",
        "url": "https://localhost/discovery", "timeout_ms": 5000,
    })
    assert response.status_code == 422, response.text
    assert response.json()["codice"] == "DESTINAZIONE_NON_APPROVATA"


@pytest.mark.integration
def test_verify_end_to_end_connects_against_a_real_server(admin_client, monkeypatch, discovery_server):
    client, engine = admin_client
    base_url, responses, requests = discovery_server
    responses["/discovery"] = (200, fragment())
    codice, created = crea(client)
    allowlist(monkeypatch, base_url)
    configured = client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo",
        "url": base_url + "/discovery", "timeout_ms": 5000,
    }).json()
    assert configured["revisione"] == 2
    verified = client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
                           json={"revisione_attesa": 2})
    assert verified.status_code == 200, verified.text
    body = verified.json()
    assert body["stato"] == "CONNESSO"
    assert body["ultima_verifica"]["esito"] == "CONFORME"
    assert body["ultima_verifica"]["errori"] == []
    assert body["ultima_verifica"]["revisione"] == 2
    assert body["ultima_verifica"]["versione_contratto"] == "0.4.0"
    assert requests == ["/discovery"]
    with engine.connect() as db:
        assert db.execute(sa.text(
            "SELECT tentativo_id FROM endpoint_integrazione WHERE integrazione_id = :id"
        ), {"id": created["id"]}).scalar() is None


@pytest.mark.integration
def test_verify_with_stale_revision_does_not_connect(admin_client, monkeypatch, discovery_server):
    client, _ = admin_client
    base_url, responses, _ = discovery_server
    responses["/discovery"] = (200, fragment())
    _, created = crea(client)
    allowlist(monkeypatch, base_url)
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo", "url": base_url + "/discovery", "timeout_ms": 5000,
    })
    response = client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
                           json={"revisione_attesa": 1})
    assert response.status_code == 409, response.text
    assert response.json()["codice"] == "REVISIONE_SUPERATA"
    refreshed = client.get(f"/api/v1/configurazione/integrazioni/{created['id']}").json()
    assert refreshed["stato"] == "DEFINITO"


@pytest.mark.integration
def test_verify_maps_unreachable_and_non_conformant_responses(admin_client, monkeypatch, discovery_server):
    client, _ = admin_client
    base_url, responses, _ = discovery_server
    _, created = crea(client)
    allowlist(monkeypatch, base_url)
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo", "url": base_url + "/unreachable", "timeout_ms": 1000,
    })
    unreachable = client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
                              json={"revisione_attesa": 2})
    assert unreachable.status_code == 200, unreachable.text
    body = unreachable.json()
    assert body["stato"] == "ERRORE"
    assert body["ultima_verifica"]["esito"] == "NON_RAGGIUNGIBILE"

    responses["/malformato"] = (200, {"BANDO_CONCORSO": {"validita": "invalid", "nodi": "not-a-list"}})
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 2, "nome": "Software Demo", "url": base_url + "/malformato", "timeout_ms": 1000,
    })
    non_conforme = client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
                               json={"revisione_attesa": 3})
    assert non_conforme.status_code == 200, non_conforme.text
    body = non_conforme.json()
    assert body["stato"] == "ERRORE"
    assert body["ultima_verifica"]["esito"] == "NON_CONFORME"


@pytest.mark.integration
def test_renaming_preserves_connection_but_changing_url_requires_reverification(admin_client, monkeypatch, discovery_server):
    client, _ = admin_client
    base_url, responses, _ = discovery_server
    responses["/discovery"] = (200, fragment())
    _, created = crea(client)
    allowlist(monkeypatch, base_url)
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo", "url": base_url + "/discovery", "timeout_ms": 5000,
    })
    client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica", json={"revisione_attesa": 2})

    renamed = client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 2, "nome": "Nome aggiornato", "url": base_url + "/discovery", "timeout_ms": 5000,
    })
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["revisione"] == 3
    assert renamed.json()["stato"] == "CONNESSO"
    assert renamed.json()["ultima_verifica"] is not None

    responses["/altro"] = (200, fragment())
    rewired = client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 3, "nome": "Nome aggiornato", "url": base_url + "/altro", "timeout_ms": 5000,
    })
    assert rewired.status_code == 200, rewired.text
    assert rewired.json()["stato"] == "DEFINITO"
    assert rewired.json()["ultima_verifica"] is None


@pytest.mark.integration
def test_removing_the_url_deletes_the_endpoint_row(admin_client, monkeypatch, discovery_server):
    client, engine = admin_client
    base_url, responses, _ = discovery_server
    responses["/discovery"] = (200, fragment())
    _, created = crea(client)
    allowlist(monkeypatch, base_url)
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo", "url": base_url + "/discovery", "timeout_ms": 5000,
    })
    removed = client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 2, "nome": "Software Demo", "url": None, "timeout_ms": 5000,
    })
    assert removed.status_code == 200, removed.text
    assert removed.json()["url"] is None
    assert removed.json()["stato"] == "DEFINITO"
    with engine.connect() as db:
        assert db.execute(sa.text(
            "SELECT count(*) FROM endpoint_integrazione WHERE integrazione_id = :id"
        ), {"id": created["id"]}).scalar() == 0


@pytest.mark.integration
def test_verify_without_a_configured_endpoint_is_rejected(admin_client):
    client, _ = admin_client
    _, created = crea(client)
    response = client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
                           json={"revisione_attesa": 1})
    assert response.status_code == 422, response.text
    assert response.json()["codice"] == "CONFIGURAZIONE_NON_VALIDA"


@pytest.mark.integration
def test_concurrent_verify_attempt_is_rejected(admin_client, monkeypatch, discovery_server):
    client, engine = admin_client
    base_url, responses, _ = discovery_server
    responses["/discovery"] = (200, fragment())
    _, created = crea(client)
    allowlist(monkeypatch, base_url)
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo", "url": base_url + "/discovery", "timeout_ms": 5000,
    })
    with engine.begin() as db:
        db.execute(sa.text("""
            UPDATE endpoint_integrazione SET tentativo_id = :tid, tentativo_scadenza = :scadenza
            WHERE integrazione_id = :id
        """), {"tid": uuid.uuid4(), "scadenza": datetime.now(timezone.utc) + timedelta(seconds=30), "id": created["id"]})
    response = client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
                           json={"revisione_attesa": 2})
    assert response.status_code == 409, response.text
    assert response.json()["codice"] == "VERIFICA_IN_CORSO"


@pytest.mark.integration
def test_expired_attempt_does_not_block_a_new_verify(admin_client, monkeypatch, discovery_server):
    client, engine = admin_client
    base_url, responses, _ = discovery_server
    responses["/discovery"] = (200, fragment())
    _, created = crea(client)
    allowlist(monkeypatch, base_url)
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo", "url": base_url + "/discovery", "timeout_ms": 5000,
    })
    with engine.begin() as db:
        db.execute(sa.text("""
            UPDATE endpoint_integrazione SET tentativo_id = :tid, tentativo_scadenza = :scadenza
            WHERE integrazione_id = :id
        """), {"tid": uuid.uuid4(), "scadenza": datetime.now(timezone.utc) - timedelta(seconds=1), "id": created["id"]})
    response = client.post(f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
                           json={"revisione_attesa": 2})
    assert response.status_code == 200, response.text
    assert response.json()["stato"] == "CONNESSO"


@pytest.mark.integration
def test_reconfiguring_url_while_a_verify_is_in_flight_wins_the_race(admin_client, monkeypatch, slow_discovery_server):
    """T084: verifica() releases its row locks before the (potentially slow) HTTP call
    so a concurrent configure isn't blocked for the whole timeout - but that means the
    stale in-flight verify must never overwrite what the concurrent configure produced.
    A real second request races the real HTTP wait, not a pre-seeded UPDATE."""
    client, _ = admin_client
    base_url, arrived, respond = slow_discovery_server
    _, created = crea(client)
    allowlist(monkeypatch, base_url)
    client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
        "revisione_attesa": 1, "nome": "Software Demo", "url": base_url + "/discovery", "timeout_ms": 5000,
    })

    with ThreadPoolExecutor(max_workers=1) as pool:
        verify_future = pool.submit(
            client.post, f"/api/v1/configurazione/integrazioni/{created['id']}/verifica",
            json={"revisione_attesa": 2},
        )
        assert arrived.wait(timeout=5), "la richiesta HTTP di verifica non e' mai arrivata al server"
        rewired = client.put(f"/api/v1/configurazione/integrazioni/{created['id']}", json={
            "revisione_attesa": 2, "nome": "Software Demo", "url": base_url + "/altro", "timeout_ms": 5000,
        })
        assert rewired.status_code == 200, rewired.text
        respond.set()
        verify_response = verify_future.result(timeout=5)

    assert verify_response.status_code == 409, verify_response.text
    assert verify_response.json()["codice"] == "REVISIONE_SUPERATA"
    final = client.get(f"/api/v1/configurazione/integrazioni/{created['id']}").json()
    assert final["url"] == base_url + "/altro"
    assert final["revisione"] == 3
    assert final["stato"] == "DEFINITO"
    assert final["ultima_verifica"] is None


def test_versioned_admin_documentation_available():
    with TestClient(app) as client:
        source = client.get("/openapi/integrazioni.yaml")
        assert source.status_code == 200
        for path in ("/docs/integrazioni", "/redoc/integrazioni"):
            response = client.get(path)
            assert response.status_code == 200
            assert "/openapi/integrazioni.yaml" in response.text


@pytest.mark.integration
def test_admin_routes_reject_non_admin_principals(admin_client):
    client, _ = admin_client
    _, created = crea(client)
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "manager", "gemodo-frontend", ("gemodo-backend",), ("GEMODO_MODELLI_GESTORE",),
        "https://sso.example.test",
    )
    base = f"/api/v1/configurazione/integrazioni/{created['id']}"
    for method, path, body in [
        ("get", "/api/v1/configurazione/integrazioni", None),
        ("post", "/api/v1/configurazione/integrazioni", {}),
        ("get", base, None),
        ("put", base, {}),
        ("post", base + "/verifica", {}),
    ]:
        response = client.request(method, path, json=body)
        assert response.status_code == 403, (path, response.text)
