"""Isolamento per contesto con il flag acceso e il profilo dal database (001 T114, T115).

Come in un ambiente con `GEMODO_ENFORCE_CONTESTO_CONSUMATORE=true`: il profilo
di accesso sta nelle tabelle dell'integrazione, e il principal nasce da un
token firmato vero decodificato dal codice di produzione. PostgreSQL reale,
API via HTTP.

- T114: lo stesso token porta due contesti; nel primo il ruolo concede la
  generazione, nel secondo solo la consultazione. Il secondo consulta ma non
  genera.
- T115: un client tecnico server-server (client credentials, ruoli diretti,
  nessun contesto nel token) esercita i suoi ruoli di consumo solo nel
  contesto dell'integrazione che lo ammette. Senza questa regola, accendere il
  flag avrebbe chiuso fuori il backend di GEBAN.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.common.errors import AuthorizationError
from app.common.security import decode_principal_from_token, require_principal
from app.configurazione.models import ClientIntegrazione, Integrazione, RuoloIntegrazione
from app.core.settings import get_settings
from app.db.session import get_db
from app.main import app
from tests.common.test_autorizzazione_per_contesto import _crea_versione, _payload
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)
from tests.support.security import JwtTestKeys, signed_token


@pytest.fixture()
def db_engine(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    monkeypatch.setenv("GEMODO_ENFORCE_CONTESTO_CONSUMATORE", "true")
    monkeypatch.delenv("GEMODO_INTEGRATION_PROFILES_PATH", raising=False)
    command.upgrade(Config("alembic.ini"), "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def client(db_engine):
    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _integrazione(engine, contesto: str, ruoli: dict[str, list[str]], client: tuple[str, ...] = ()) -> None:
    with Session(engine) as db:
        integrazione = Integrazione(codice="SW_" + uuid.uuid4().hex[:12], nome="Prova", codice_contesto=contesto)
        db.add(integrazione)
        db.flush()
        db.add_all([RuoloIntegrazione(integrazione_id=integrazione.id, ruolo=r, permessi=p) for r, p in ruoli.items()])
        db.add_all([ClientIntegrazione(integrazione_id=integrazione.id, client_id=c) for c in client])
        db.commit()


def _come(client, engine, token: str, keys: JwtTestKeys):
    """Il principal che produrrebbe `require_principal` con questo token."""
    with Session(engine) as db:
        principal = decode_principal_from_token(token, settings=get_settings(), signing_key=keys.public_pem, db=db)
    app.dependency_overrides[require_principal] = lambda: principal
    return client


def _contesto() -> str:
    return "ctx" + uuid.uuid4().hex[:10]


@pytest.mark.integration
def test_t114_nel_secondo_contesto_si_consulta_ma_non_si_genera(db_engine, client):
    genera, consulta = _contesto(), _contesto()
    _integrazione(db_engine, genera, {"ROLE_COORDINATOR": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"]})
    _integrazione(db_engine, consulta, {"ROLE_USER": ["DOCUMENTI_VIEWER"]})
    nel_primo = _crea_versione(db_engine, codice_contesto=genera)
    nel_secondo = _crea_versione(db_engine, codice_contesto=consulta)
    keys = JwtTestKeys()
    token = signed_token(keys, audience=None, client_id="gemodo-frontend", roles=None, contexts={
        genera: [f"ROLE_COORDINATOR#{genera}"], consulta: [f"ROLE_USER#{consulta}"],
    })
    http = _come(client, db_engine, token, keys)

    assert http.get(f"/api/v1/catalogo/modelli/{nel_secondo['public_id']}/campi-richiesti").status_code == 200
    valida = http.post("/api/v1/documenti/valida", json=_payload(nel_secondo["public_id"], "secondo"))
    assert valida.status_code == 404, valida.text
    assert valida.json()["codice"] == "MODELLO_VERSIONE_NON_TROVATO"
    generato = http.post("/api/v1/documenti/genera", json=_payload(nel_secondo["public_id"], "secondo"))
    assert generato.status_code == 404, generato.text

    ok = http.post("/api/v1/documenti/genera", json=_payload(nel_primo["public_id"], "primo"))
    assert ok.status_code == 200, ok.text
    assert ok.headers["content-type"] == "application/pdf"


@pytest.mark.integration
def test_un_contesto_del_token_senza_integrazione_non_vede_nulla(db_engine, client):
    estraneo = _contesto()
    versione = _crea_versione(db_engine, codice_contesto=estraneo)
    keys = JwtTestKeys()
    token = signed_token(keys, audience=None, client_id="gemodo-frontend", roles=None,
                         contexts={estraneo: [f"ROLE_MANAGER#{estraneo}"]})

    risposta = _come(client, db_engine, token, keys).get(
        f"/api/v1/catalogo/modelli/{versione['public_id']}/campi-richiesti"
    )

    # Nessun permesso in nessun contesto: si ferma gia' al controllo di rotta.
    assert risposta.status_code in (403, 404), risposta.text


@pytest.mark.integration
def test_t115_il_client_tecnico_genera_solo_nel_contesto_che_lo_ammette(db_engine, client):
    suo, altro = _contesto(), _contesto()
    _integrazione(db_engine, suo, {}, client=("backend-tecnico-prova",))
    _integrazione(db_engine, altro, {"ROLE_USER": ["DOCUMENTI_VIEWER"]})
    nel_suo = _crea_versione(db_engine, codice_contesto=suo)
    nell_altro = _crea_versione(db_engine, codice_contesto=altro)
    keys = JwtTestKeys()
    token = signed_token(keys, client_id="backend-tecnico-prova", roles=("DOCUMENTI_GENERATORE",))
    http = _come(client, db_engine, token, keys)

    ok = http.post("/api/v1/documenti/genera", json=_payload(nel_suo["public_id"], "suo"))
    assert ok.status_code == 200, ok.text
    negato = http.post("/api/v1/documenti/genera", json=_payload(nell_altro["public_id"], "altro"))
    assert negato.status_code == 404, negato.text
    assert negato.json()["codice"] == "MODELLO_VERSIONE_NON_TROVATO"


@pytest.mark.integration
def test_t115_il_client_tecnico_non_ottiene_il_builder(db_engine, client):
    """I ruoli diretti valgono per il consumo; il builder e' per le persone."""
    suo = _contesto()
    _integrazione(db_engine, suo, {}, client=("backend-tecnico-prova",))
    keys = JwtTestKeys()
    token = signed_token(keys, client_id="backend-tecnico-prova",
                         roles=("DOCUMENTI_GENERATORE", "GEMODO_MODELLI_GESTORE"))

    with Session(db_engine) as db:
        principal = decode_principal_from_token(token, settings=get_settings(), signing_key=keys.public_pem, db=db)

    assert dict(principal.permessi_contesto)[suo] == ("DOCUMENTI_GENERATORE",)


@pytest.mark.integration
def test_t115_un_client_tecnico_non_registrato_e_rifiutato(db_engine, client):
    keys = JwtTestKeys()
    token = signed_token(keys, client_id="backend-mai-registrato", roles=("DOCUMENTI_GENERATORE",))

    with Session(db_engine) as db, pytest.raises(AuthorizationError):
        decode_principal_from_token(token, settings=get_settings(), signing_key=keys.public_pem, db=db)
