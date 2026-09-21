"""Real generation + storage tests (004/005, MVP FR-019/020 slice).

Fixtures insert their own isolated tipo/modello/versione rows directly (not the
shared demo seed) so idempotent-key collisions across tests are impossible.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.common.security import PrincipalGEMODO, require_principal
from app.db.session import get_db
from app.main import app
from tests.support.postgres import postgres_database_url


@pytest.fixture()
def db_engine(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def _crea_versione(db_engine, *, stato="PUBBLICATO"):
    suffix = uuid.uuid4().hex[:12]
    public_id = uuid.uuid4().int % 900_000_000 + 100_000_000
    with Session(db_engine) as db:
        tipo = TipoDocumento(codice="GEN_" + suffix, nome="Tipo generazione test", stato="BOZZA",
                             spec_owner="specs/004-generazione-documenti-pdf", codice_contesto="geban")
        db.add(tipo)
        db.flush()
        modello = ModelloDocumento(tipo_documento_id=tipo.id, codice_categoria="DEMO",
                                   percorso_categorizzazione=["DEMO"], codice="MOD_" + suffix,
                                   nome="Modello generazione test", stato="PUBBLICATO")
        db.add(modello)
        db.flush()
        versione = ModelloDocumentoVersione(modello_documento_id=modello.id, versione=1, stato=stato,
                                            struttura_documentale={}, public_id=public_id)
        db.add(versione)
        db.flush()
        db.add(ModelloCampoRichiesto(modello_versione_id=versione.id, codice="titolo", etichetta="Titolo",
                                     tipo_dato="string", obbligatorio=True, lingua="IT", ordine=1))
        db.add(ModelloCampoRichiesto(modello_versione_id=versione.id, codice="note", etichetta="Note",
                                     tipo_dato="string", obbligatorio=False, lingua="IT", ordine=2))
        db.commit()
        return {"versione_id": versione.id, "public_id": public_id}


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
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "generatore-test", "gemodo-frontend", ("gemodo-backend",), ("DOCUMENTI_GENERATORE",),
        "https://sso.example.test",
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _payload(public_id: int, *, dati=None, external_context_id=None):
    return {
        "sistema_richiedente": "GEBAN",
        "external_context_id": external_context_id or ("ctx-" + uuid.uuid4().hex[:12]),
        "modello_versione_id": public_id,
        "dati": dati if dati is not None else {"titolo": "Prova"},
    }


@pytest.mark.integration
def test_generazione_reale_produce_pdf_scaricabile(db_engine, client):
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"], dati={"titolo": "Bando reale", "note": "Prima nota"})

    esito = client.post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 200, esito.text
    assert esito.headers["content-type"] == "application/pdf"
    assert esito.content.startswith(b"%PDF")
    assert b"Bando reale" in esito.content
    assert b"Prima nota" in esito.content
    riferimento = esito.headers["x-riferimento-documentale"]
    assert riferimento

    stato = client.get(f"/api/v1/documenti/{riferimento}")
    assert stato.status_code == 200, stato.text
    assert stato.json()["stato"] == "COMPLETATO"
    assert stato.json()["hash_file"]
    assert stato.json()["dimensione_byte"] > 0

    # il riferimento resta consultabile/riscaricabile anche dopo la prima risposta diretta
    download = client.get(f"/api/v1/documenti/{riferimento}/download")
    assert download.status_code == 200
    assert download.content == esito.content


@pytest.mark.integration
def test_dati_non_validi_non_persiste_nulla(db_engine, client):
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"], dati={})  # "titolo" obbligatorio mancante

    esito = client.post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 200, esito.text
    body = esito.json()
    assert body["stato"] == "DATI_NON_VALIDI"
    assert body["riferimento_documentale"] is None
    assert body["validazione"]["valido"] is False

    with Session(db_engine) as db:
        count = db.execute(sa.text(
            "SELECT count(*) FROM documento_generato WHERE external_context_id = :ctx"
        ), {"ctx": payload["external_context_id"]}).scalar()
        assert count == 0


@pytest.mark.integration
def test_versione_non_pubblicata_e_rifiutata(db_engine, client):
    versione = _crea_versione(db_engine, stato="BOZZA")
    payload = _payload(versione["public_id"])

    esito = client.post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 409, esito.text
    assert esito.json()["codice"] == "MODELLO_VERSIONE_NON_PUBBLICATO"


@pytest.mark.integration
def test_stessa_chiave_stessi_dati_replica_lo_stesso_documento(db_engine, client):
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"], dati={"titolo": "Idempotenza"})

    primo = client.post("/api/v1/documenti/genera", json=payload)
    secondo = client.post("/api/v1/documenti/genera", json=payload)
    assert primo.headers["x-riferimento-documentale"] == secondo.headers["x-riferimento-documentale"]
    assert primo.content == secondo.content

    with Session(db_engine) as db:
        count = db.execute(sa.text(
            "SELECT count(*) FROM documento_generato WHERE external_context_id = :ctx"
        ), {"ctx": payload["external_context_id"]}).scalar()
        assert count == 1


@pytest.mark.integration
def test_stessa_chiave_dati_diversi_e_conflitto(db_engine, client):
    versione = _crea_versione(db_engine)
    ctx = "ctx-" + uuid.uuid4().hex[:12]
    primo = client.post("/api/v1/documenti/genera", json=_payload(versione["public_id"], dati={"titolo": "A"}, external_context_id=ctx))
    assert primo.status_code == 200

    conflitto = client.post("/api/v1/documenti/genera", json=_payload(versione["public_id"], dati={"titolo": "B"}, external_context_id=ctx))
    assert conflitto.status_code == 409, conflitto.text
    assert conflitto.json()["codice"] == "RICHIESTA_IDEMPOTENTE_IN_CONFLITTO"


@pytest.mark.integration
def test_rendering_failure_produces_fallito_without_download(db_engine, client, monkeypatch):
    def _rompi(*args, **kwargs):
        raise RuntimeError("errore renderer simulato")

    monkeypatch.setattr("app.generazione.service.render_pdf", _rompi)
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"])

    esito = client.post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 200, esito.text
    body = esito.json()
    assert body["stato"] == "FALLITO"
    riferimento = body["riferimento_documentale"]
    assert riferimento
    assert "errore" not in body["messaggio"].lower() or "runtime" not in body["messaggio"].lower()

    stato = client.get(f"/api/v1/documenti/{riferimento}")
    assert stato.status_code == 200
    assert stato.json()["stato"] == "FALLITO"
    assert "RuntimeError" not in stato.json()["errore_messaggio"]

    download = client.get(f"/api/v1/documenti/{riferimento}/download")
    assert download.status_code == 409
    assert download.json()["codice"] == "DOCUMENTO_NON_DISPONIBILE"


@pytest.mark.integration
def test_riferimento_inesistente_e_404(client):
    assert client.get(f"/api/v1/documenti/{uuid.uuid4().hex}").status_code == 404
    assert client.get(f"/api/v1/documenti/{uuid.uuid4().hex}/download").status_code == 404


@pytest.mark.integration
def test_concorrenza_sulla_stessa_chiave_produce_un_solo_documento(db_engine):
    versione = _crea_versione(db_engine)
    ctx = "ctx-" + uuid.uuid4().hex[:12]
    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "generatore-test", "gemodo-frontend", ("gemodo-backend",), ("DOCUMENTI_GENERATORE",),
        "https://sso.example.test",
    )
    try:
        with TestClient(app) as test_client:
            payload = _payload(versione["public_id"], dati={"titolo": "Concorrenza"}, external_context_id=ctx)

            def _chiama(_):
                return test_client.post("/api/v1/documenti/genera", json=payload)

            with ThreadPoolExecutor(max_workers=4) as executor:
                risposte = list(executor.map(_chiama, range(4)))
    finally:
        app.dependency_overrides.clear()

    assert all(r.status_code == 200 for r in risposte)
    riferimenti = {r.headers["x-riferimento-documentale"] for r in risposte}
    assert len(riferimenti) == 1
    with Session(db_engine) as db:
        count = db.execute(sa.text(
            "SELECT count(*) FROM documento_generato WHERE external_context_id = :ctx"
        ), {"ctx": ctx}).scalar()
        assert count == 1
