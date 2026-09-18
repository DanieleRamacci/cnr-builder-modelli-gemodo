"""T083: manager reads over registered integrations (contract T078).

Real Postgres + a real local HTTP server for the "connected" integration; no mock of
the authorization or discovery logic under test.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common.security import PrincipalGEMODO, require_principal
from app.configurazione.models import EndpointIntegrazione, Integrazione
from app.db.session import get_db
from app.main import app
from tests.discovery.conftest import discovery_server  # noqa: F401 (fixture reuse)
from tests.discovery.test_pagination import fragment
from tests.support.postgres import postgres_database_url


@pytest.fixture()
def db_engine(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def manager_client(db_engine, monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "geri-angular-public")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "geban")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_MANAGER#geban")

    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _crea_integrazione(db_engine, *, codice_contesto: str, url: str | None, stato: str = "CONNESSO"):
    with Session(db_engine) as db:
        source = Integrazione(codice="MGR_" + uuid.uuid4().hex[:16], nome="Software di test", codice_contesto=codice_contesto)
        db.add(source)
        db.flush()
        if url is not None:
            db.add(EndpointIntegrazione(
                integrazione_id=source.id, url=url, timeout_ms=5000, stato=stato,
                revisione_verificata=1, versione_contratto_verificata="0.4.0",
                data_ultimo_test=datetime.now(timezone.utc), esito_ultimo_test={"esito": "CONFORME", "errori": []},
            ))
        db.commit()
        return source.id


def _rimuovi_integrazione(db_engine, integrazione_id):
    with Session(db_engine) as db:
        db.execute(sa.delete(EndpointIntegrazione).where(EndpointIntegrazione.integrazione_id == integrazione_id))
        db.execute(sa.delete(Integrazione).where(Integrazione.id == integrazione_id))
        db.commit()


@pytest.mark.integration
@pytest.mark.parametrize("client_id", ["geri-angular-public", "gemodo-frontend"])
def test_manager_sees_only_connected_integrations_authorized_in_their_context(manager_client, db_engine, discovery_server, monkeypatch, client_id):
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", client_id)
    url, responses, _ = discovery_server
    responses["/discovery"] = (200, fragment())
    autorizzata = _crea_integrazione(db_engine, codice_contesto="geban", url=url + "/discovery")
    non_autorizzata = _crea_integrazione(db_engine, codice_contesto="altro-contesto-senza-ruoli", url="https://unreachable.example.test/discovery")
    try:
        response = manager_client.get("/api/v1/builder/integrazioni")
        assert response.status_code == 200, response.text
        ids = {item["id"] for item in response.json()}
        assert str(autorizzata) in ids
        assert str(non_autorizzata) not in ids
        visibile = next(item for item in response.json() if item["id"] == str(autorizzata))
        assert set(visibile) == {"id", "codice", "nome", "codice_contesto"}
    finally:
        _rimuovi_integrazione(db_engine, autorizzata)
        _rimuovi_integrazione(db_engine, non_autorizzata)


@pytest.mark.integration
def test_multicontext_token_does_not_leak_permission_across_contexts(manager_client, db_engine, discovery_server):
    """T084: a token can legitimately carry more than one context (e.g. a user active in
    both 'geban' and a future context). A role held in one context MUST NOT authorize an
    integration owned by another, even when the token also carries *some* role for that
    other context (unlike the single-context manager_client fixture, which never claims
    the second context at all)."""
    url, responses, _ = discovery_server
    responses["/discovery"] = (200, fragment())
    propria = _crea_integrazione(db_engine, codice_contesto="geban", url=url + "/discovery")
    altrui = _crea_integrazione(db_engine, codice_contesto="altro-contesto-senza-ruoli", url="https://unreachable.example.test/discovery")
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "manager-multicontesto", "geri-angular-public", ("gemodo-backend",), (),
        "https://sso.example.test",
        ruoli_contesto=(
            ("geban", ("ROLE_MANAGER#geban",)),
            ("altro-contesto-senza-ruoli", ("ROLE_SCONOSCIUTO#altro",)),
        ),
    )
    try:
        lista = manager_client.get("/api/v1/builder/integrazioni")
        assert lista.status_code == 200, lista.text
        ids = {item["id"] for item in lista.json()}
        assert str(propria) in ids
        assert str(altrui) not in ids

        negato = manager_client.get(f"/api/v1/builder/integrazioni/{altrui}/tipi-documento")
        assert negato.status_code == 404, negato.text
        assert negato.json()["codice"] == "RISORSA_NON_TROVATA"
    finally:
        _rimuovi_integrazione(db_engine, propria)
        _rimuovi_integrazione(db_engine, altrui)


@pytest.mark.integration
def test_not_yet_connected_integration_is_excluded_from_the_list(manager_client, db_engine):
    definita = _crea_integrazione(db_engine, codice_contesto="geban", url="https://software.example.test/discovery", stato="DEFINITO")
    try:
        response = manager_client.get("/api/v1/builder/integrazioni")
        assert response.status_code == 200
        assert str(definita) not in {item["id"] for item in response.json()}
    finally:
        _rimuovi_integrazione(db_engine, definita)


@pytest.mark.integration
def test_unauthorized_context_gets_404_without_ever_calling_the_endpoint(manager_client, db_engine, discovery_server):
    url, responses, requests = discovery_server
    responses["/discovery"] = (200, fragment())
    non_autorizzata = _crea_integrazione(db_engine, codice_contesto="altro-contesto-senza-ruoli", url=url + "/discovery")
    try:
        response = manager_client.get(f"/api/v1/builder/integrazioni/{non_autorizzata}/tipi-documento")
        assert response.status_code == 404, response.text
        assert response.json()["codice"] == "RISORSA_NON_TROVATA"
        assert requests == []
    finally:
        _rimuovi_integrazione(db_engine, non_autorizzata)


@pytest.mark.integration
def test_unknown_integration_id_is_404(manager_client):
    response = manager_client.get(f"/api/v1/builder/integrazioni/{uuid.uuid4()}/tipi-documento")
    assert response.status_code == 404
    assert response.json()["codice"] == "RISORSA_NON_TROVATA"


@pytest.mark.integration
def test_not_connected_integration_returns_409(manager_client, db_engine):
    definita = _crea_integrazione(db_engine, codice_contesto="geban", url="https://software.example.test/discovery", stato="ERRORE")
    try:
        response = manager_client.get(f"/api/v1/builder/integrazioni/{definita}/tipi-documento")
        assert response.status_code == 409, response.text
        assert response.json()["codice"] == "INTEGRAZIONE_NON_CONNESSA"
    finally:
        _rimuovi_integrazione(db_engine, definita)


@pytest.mark.integration
def test_tipi_documento_and_struttura_reflect_the_live_multi_type_map(manager_client, db_engine, discovery_server):
    url, responses, requests = discovery_server
    body = fragment()
    body["VERBALE"] = {"validita": "2026-09-17T00:00:00Z", "nodi": [
        {"codice": "SEDUTA", "descrizione": "Seduta", "campi": [
            {"codice": "data_seduta", "etichetta": "Data", "tipo": "date", "lingua": "IT", "ordine": 1, "obbligatorio": True},
        ]},
    ]}
    responses["/discovery"] = (200, body)
    connessa = _crea_integrazione(db_engine, codice_contesto="geban", url=url + "/discovery")
    try:
        tipi = manager_client.get(f"/api/v1/builder/integrazioni/{connessa}/tipi-documento")
        assert tipi.status_code == 200, tipi.text
        assert tipi.json() == ["BANDO_CONCORSO", "VERBALE"]

        struttura = manager_client.get(f"/api/v1/builder/integrazioni/{connessa}/tipi-documento/VERBALE/struttura")
        assert struttura.status_code == 200, struttura.text
        assert struttura.json()["nodi"][0]["codice"] == "SEDUTA"

        missing = manager_client.get(f"/api/v1/builder/integrazioni/{connessa}/tipi-documento/INESISTENTE/struttura")
        assert missing.status_code == 404
        assert missing.json()["codice"] == "RISORSA_NON_TROVATA"
        assert requests == ["/discovery", "/discovery", "/discovery"]
    finally:
        _rimuovi_integrazione(db_engine, connessa)


@pytest.mark.integration
def test_transport_failure_maps_to_502_not_503(manager_client, db_engine, discovery_server):
    url, responses, _ = discovery_server
    responses["/discovery"] = (500, {"messaggio": "Errore esterno"})
    connessa = _crea_integrazione(db_engine, codice_contesto="geban", url=url + "/discovery")
    try:
        response = manager_client.get(f"/api/v1/builder/integrazioni/{connessa}/tipi-documento")
        assert response.status_code == 502, response.text
        assert response.json()["codice"] == "DISCOVERY_NON_DISPONIBILE"
    finally:
        _rimuovi_integrazione(db_engine, connessa)


@pytest.mark.integration
def test_non_conformant_shape_maps_to_502(manager_client, db_engine, discovery_server):
    url, responses, _ = discovery_server
    responses["/discovery"] = (200, {"BANDO_CONCORSO": {"validita": "invalid", "nodi": "not-a-list"}})
    connessa = _crea_integrazione(db_engine, codice_contesto="geban", url=url + "/discovery")
    try:
        response = manager_client.get(f"/api/v1/builder/integrazioni/{connessa}/tipi-documento")
        assert response.status_code == 502, response.text
        assert response.json()["codice"] == "DISCOVERY_NON_CONFORME"
    finally:
        _rimuovi_integrazione(db_engine, connessa)


@pytest.mark.integration
def test_manager_routes_require_authentication(db_engine):
    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/builder/integrazioni").status_code == 401
    finally:
        app.dependency_overrides.clear()
