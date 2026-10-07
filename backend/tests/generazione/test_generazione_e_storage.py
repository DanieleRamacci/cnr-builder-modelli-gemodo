"""Generazione reale e registro delle generazioni (004, 013).

GEMODO genera e consegna senza conservare il PDF; ogni chiamata lascia una riga
nel registro, e la stessa chiave si ripete quante volte serve. Le fixture creano
tipo/modello/versione propri, cosi' i conteggi per chiave sono isolati.
"""

from __future__ import annotations

import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.common.security import PrincipalGEMODO, require_principal
from app.db.session import get_db
from app.main import app
from app.storage.service import hash_dati
from tests.support.postgres import postgres_database_url
from tests.support.pdf import estrai_testo


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
        "generatore-test", "gemodo-frontend", ("gemodo-backend",), ("DOCUMENTI_GENERATORE", "GEMODO_ADMIN"),
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


def _righe(db_engine, ctx: str) -> list[dict]:
    with Session(db_engine) as db:
        return [dict(riga) for riga in db.execute(sa.text(
            "SELECT riferimento, stato, hash_dati, hash_file, dimensione_byte, percorso_file, creato_da, "
            "client_id, ruoli, errore_messaggio FROM documento_generato "
            "WHERE external_context_id = :ctx ORDER BY created_at"
        ), {"ctx": ctx}).mappings()]


@pytest.mark.integration
def test_generazione_consegna_il_pdf_e_lo_registra_senza_conservarlo(db_engine, client):
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"], dati={"titolo": "Bando reale", "note": "Prima nota"})

    esito = client.post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 200, esito.text
    assert esito.headers["content-type"] == "application/pdf"
    assert esito.content.startswith(b"%PDF")
    assert "Bando reale" in estrai_testo(esito.content)
    assert "Prima nota" in estrai_testo(esito.content)
    riferimento = esito.headers["x-riferimento-documentale"]
    metadati = PdfReader(BytesIO(esito.content)).metadata
    assert metadati.subject == f"Riferimento documentale: {riferimento}"
    assert f"riferimento_documentale={riferimento}" in (metadati.get("/Keywords") or "")

    [riga] = _righe(db_engine, payload["external_context_id"])
    assert riga["riferimento"] == riferimento
    assert riga["stato"] == "COMPLETATO"
    # L'impronta e' quella del PDF consegnato: basta a verificarlo; il file no.
    assert riga["hash_file"] == hashlib.sha256(esito.content).hexdigest()
    assert riga["dimensione_byte"] == len(esito.content)
    assert riga["percorso_file"] is None
    assert riga["hash_dati"] == hash_dati(payload["dati"])
    assert (riga["creato_da"], riga["client_id"]) == ("generatore-test", "gemodo-frontend")
    assert "DOCUMENTI_GENERATORE" in riga["ruoli"]

    stato = client.get(f"/api/v1/documenti/{riferimento}")
    assert stato.status_code == 200, stato.text
    assert stato.json()["stato"] == "COMPLETATO"
    assert stato.json()["external_context_id"] == payload["external_context_id"]
    # Il download non c'e' piu': GEMODO non conserva il PDF.
    assert client.get(f"/api/v1/documenti/{riferimento}/download").status_code == 404


@pytest.mark.integration
def test_stessa_chiave_dati_diversi_genera_ogni_volta(db_engine, client):
    # 013: GEBAN usa la chiave del bando e lo rigenera a ogni correzione.
    versione = _crea_versione(db_engine)
    ctx = "ctx-" + uuid.uuid4().hex[:12]
    risposte = [
        client.post("/api/v1/documenti/genera",
                    json=_payload(versione["public_id"], dati={"titolo": titolo}, external_context_id=ctx))
        for titolo in ("Prima stesura", "Seconda stesura", "Definitivo")
    ]
    assert [r.status_code for r in risposte] == [200, 200, 200]
    assert all(r.headers["content-type"] == "application/pdf" for r in risposte)
    assert "Definitivo" in estrai_testo(risposte[-1].content)

    righe = _righe(db_engine, ctx)
    assert [riga["stato"] for riga in righe] == ["COMPLETATO"] * 3
    assert len({riga["riferimento"] for riga in righe}) == 3
    assert [riga["riferimento"] for riga in righe] == [r.headers["x-riferimento-documentale"] for r in risposte]


@pytest.mark.integration
def test_stessa_chiave_stessi_dati_genera_e_registra_ogni_chiamata(db_engine, client):
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"], dati={"titolo": "Ritentativo"})

    primo = client.post("/api/v1/documenti/genera", json=payload)
    secondo = client.post("/api/v1/documenti/genera", json=payload)
    assert primo.status_code == secondo.status_code == 200
    assert estrai_testo(primo.content) == estrai_testo(secondo.content)
    assert primo.headers["x-riferimento-documentale"] != secondo.headers["x-riferimento-documentale"]
    assert len(_righe(db_engine, payload["external_context_id"])) == 2


@pytest.mark.integration
def test_dati_non_validi_si_registrano_senza_pdf(db_engine, client):
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"], dati={})  # "titolo" obbligatorio mancante

    esito = client.post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 200, esito.text
    body = esito.json()
    assert body["stato"] == "DATI_NON_VALIDI"
    assert body["validazione"]["valido"] is False

    [riga] = _righe(db_engine, payload["external_context_id"])
    assert riga["stato"] == "DATI_NON_VALIDI"
    assert riga["riferimento"] == body["riferimento_documentale"]
    assert riga["hash_file"] is None
    assert "titolo" in riga["errore_messaggio"]
    assert riga["hash_dati"] == hash_dati({})


@pytest.mark.integration
def test_versione_non_pubblicata_e_rifiutata(db_engine, client):
    versione = _crea_versione(db_engine, stato="BOZZA")
    payload = _payload(versione["public_id"])

    esito = client.post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 409, esito.text
    assert esito.json()["codice"] == "MODELLO_VERSIONE_NON_PUBBLICATO"


@pytest.mark.integration
def test_errore_del_renderer_si_registra_come_fallito(db_engine, client, monkeypatch):
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

    stato = client.get(f"/api/v1/documenti/{riferimento}")
    assert stato.status_code == 200
    assert stato.json()["stato"] == "FALLITO"
    assert "RuntimeError" not in stato.json()["errore_messaggio"]


@pytest.mark.integration
def test_senza_registro_il_pdf_non_si_consegna(db_engine, client, monkeypatch):
    # 013 FR-006: un PDF consegnato e non registrato non si potrebbe verificare.
    from sqlalchemy.exc import OperationalError

    def _registro_giu(self):
        raise OperationalError("COMMIT", {}, Exception("database non disponibile"))

    versione = _crea_versione(db_engine)
    monkeypatch.setattr(Session, "commit", _registro_giu)
    esito = client.post("/api/v1/documenti/genera", json=_payload(versione["public_id"]))
    monkeypatch.undo()

    assert esito.status_code == 503, esito.text
    assert esito.headers["content-type"].startswith("application/json")
    assert esito.json()["codice"] == "REGISTRO_GENERAZIONI_NON_DISPONIBILE"


@pytest.mark.integration
def test_riferimento_inesistente_e_404(client):
    assert client.get(f"/api/v1/documenti/{uuid.uuid4().hex}").status_code == 404


@pytest.mark.integration
def test_il_registro_e_solo_per_gli_amministratori(db_engine):
    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "generatore-test", "gemodo-frontend", ("gemodo-backend",), ("DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"),
        "https://sso.example.test",
    )
    try:
        with TestClient(app) as test_client:
            assert test_client.get(f"/api/v1/documenti/{uuid.uuid4().hex}").status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_chiamate_concorrenti_sulla_stessa_chiave_generano_tutte(db_engine, client):
    versione = _crea_versione(db_engine)
    payload = _payload(versione["public_id"], dati={"titolo": "Concorrenza"})

    with ThreadPoolExecutor(max_workers=4) as executor:
        risposte = list(executor.map(lambda _: client.post("/api/v1/documenti/genera", json=payload), range(4)))

    assert all(r.status_code == 200 for r in risposte)
    assert len({r.headers["x-riferimento-documentale"] for r in risposte}) == 4
    assert len(_righe(db_engine, payload["external_context_id"])) == 4
