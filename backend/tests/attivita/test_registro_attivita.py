"""Registro attivita' per gli amministratori (013 US4), su PostgreSQL vero.

Il principal nasce dalla richiesta (GEMODO_USE_MOCK_PRINCIPAL), come in
produzione nasce dal token: e' cosi' che un accesso negato sa chi era.
"""

from __future__ import annotations

import csv
import io
import logging
import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import (
    AuditEventoModello,
    ModelloCampoRichiesto,
    ModelloDocumento,
    ModelloDocumentoVersione,
    TipoDocumento,
)
from app.db.session import get_db
from app.main import app
from tests.support.postgres import postgres_database_url  # noqa: F401 - fixture


@pytest.fixture()
def db_engine(postgres_database_url, monkeypatch):  # noqa: F811
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def come(db_engine, monkeypatch):
    """Un client che chiama come l'utente indicato, coi ruoli indicati."""
    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "gemodo-frontend")
    client = TestClient(app)

    def _come(utente: str, *ruoli: str) -> TestClient:
        monkeypatch.setenv("GEMODO_MOCK_SUBJECT", utente)
        monkeypatch.setenv("GEMODO_MOCK_ROLES", ",".join(ruoli))
        return client

    try:
        yield _come
    finally:
        app.dependency_overrides.clear()


def _crea_versione(db_engine) -> dict:
    suffix = uuid.uuid4().hex[:12]
    public_id = uuid.uuid4().int % 900_000_000 + 100_000_000
    with Session(db_engine) as db:
        tipo = TipoDocumento(codice="ATT_" + suffix, nome="Tipo attivita", stato="BOZZA",
                             spec_owner="specs/013-generazione-registro-verifica", codice_contesto="geban")
        db.add(tipo)
        db.flush()
        modello = ModelloDocumento(tipo_documento_id=tipo.id, codice_categoria="DEMO",
                                   percorso_categorizzazione=["DEMO"], codice="MOD_" + suffix,
                                   nome="Bando attivita " + suffix, stato="PUBBLICATO")
        db.add(modello)
        db.flush()
        versione = ModelloDocumentoVersione(modello_documento_id=modello.id, versione=1, stato="PUBBLICATO",
                                            struttura_documentale={}, public_id=public_id)
        db.add(versione)
        db.flush()
        db.add(ModelloCampoRichiesto(modello_versione_id=versione.id, codice="titolo", etichetta="Titolo",
                                     tipo_dato="string", obbligatorio=True, lingua="IT", ordine=1))
        db.commit()
        return {"public_id": public_id, "modello_id": modello.id, "nome": modello.nome}


def _payload(public_id: int, ctx: str, dati: dict) -> dict:
    return {"sistema_richiedente": "GEBAN", "external_context_id": ctx, "modello_versione_id": public_id, "dati": dati}


def _registro(client: TestClient, **filtri) -> list[dict]:
    risposta = client.get("/api/v1/admin/attivita", params={"limite": 200, **filtri})
    assert risposta.status_code == 200, risposta.text
    return risposta.json()["eventi"]


@pytest.mark.integration
def test_il_registro_mostra_insieme_generazioni_validazioni_modelli_e_accessi_negati(db_engine, come):
    versione = _crea_versione(db_engine)
    ctx = "att-" + uuid.uuid4().hex[:10]
    utente = "geban-" + uuid.uuid4().hex[:6]

    geban = come(utente, "DOCUMENTI_GENERATORE")
    assert geban.post("/api/v1/documenti/valida", json=_payload(versione["public_id"], ctx, {})).status_code == 200
    assert geban.post("/api/v1/documenti/genera", json=_payload(
        versione["public_id"], ctx, {"titolo": "Bando"})).headers["content-type"] == "application/pdf"
    # Un utente che genera non legge il registro: 403, e l'accesso negato si registra.
    assert geban.get("/api/v1/admin/attivita").status_code == 403
    # Un evento del builder scritto prima della 013, senza username.
    with Session(db_engine) as db:
        db.add(AuditEventoModello(
            id=uuid.uuid4(), tipo_evento="MODELLO_CREATO", soggetto_id=utente, client_id="gemodo-frontend",
            ruoli=["GEMODO_MODELLI_GESTORE"], modello_documento_id=versione["modello_id"],
            payload_minimo={"nome": versione["nome"]},
        ))
        db.commit()

    eventi = _registro(come("admin-test", "GEMODO_ADMIN"), utente=utente)
    per_categoria = {evento["categoria"]: evento for evento in eventi}
    assert set(per_categoria) == {"GENERAZIONE", "VALIDAZIONE", "ACCESSO", "MODELLO"}

    generazione = per_categoria["GENERAZIONE"]
    assert generazione["esito"] == "COMPLETATO"
    assert generazione["contesto"] == "geban"
    assert generazione["oggetto_nome"] == versione["nome"]
    assert generazione["dettaglio"]["external_context_id"] == ctx
    assert generazione["dettaglio"]["hash_file"]

    assert per_categoria["VALIDAZIONE"]["esito"] == "DATI_NON_VALIDI"
    assert per_categoria["VALIDAZIONE"]["dettaglio"]["campi_non_validi"] == ["titolo"]

    negato = per_categoria["ACCESSO"]
    assert (negato["azione"], negato["esito"]) == ("ACCESSO_NEGATO", "403")
    assert negato["oggetto_id"] == "GET /api/v1/admin/attivita"

    # Lo username manca solo all'evento vecchio, e lo prende dallo stesso soggetto.
    assert {evento["username"] for evento in eventi} == {utente}
    # In ordine di tempo, dal piu' recente.
    assert [evento["quando"] for evento in eventi] == sorted((e["quando"] for e in eventi), reverse=True)


@pytest.mark.integration
def test_i_filtri_e_la_paginazione(db_engine, come):
    versione = _crea_versione(db_engine)
    utente = "filtro-" + uuid.uuid4().hex[:6]
    geban = come(utente, "DOCUMENTI_GENERATORE")
    for numero in range(3):
        geban.post("/api/v1/documenti/genera", json=_payload(versione["public_id"], f"pag-{numero}", {"titolo": "x"}))
    geban.post("/api/v1/documenti/genera", json=_payload(versione["public_id"], "pag-invalido", {}))

    admin = come("admin-test", "GEMODO_ADMIN")
    assert len(_registro(admin, utente=utente, categoria="GENERAZIONE")) == 4
    assert len(_registro(admin, utente=utente, esito="DATI_NON_VALIDI")) == 1
    assert len(_registro(admin, utente=utente, testo="pag-invalido")) == 1
    pagina = admin.get("/api/v1/admin/attivita", params={"utente": utente, "limite": 3}).json()
    assert (len(pagina["eventi"]), pagina["altri"]) == (3, True)
    seguito = admin.get("/api/v1/admin/attivita", params={"utente": utente, "limite": 3, "salto": 3}).json()
    assert (len(seguito["eventi"]), seguito["altri"]) == (1, False)


@pytest.mark.integration
def test_esportazione_csv_senza_formule(db_engine, come):
    versione = _crea_versione(db_engine)
    utente = "csv-" + uuid.uuid4().hex[:6]
    come(utente, "DOCUMENTI_GENERATORE").post(
        "/api/v1/documenti/genera", json=_payload(versione["public_id"], "=CMD()", {"titolo": "x"}))

    risposta = come("admin-test", "GEMODO_ADMIN").get("/api/v1/admin/attivita.csv", params={"utente": utente})
    assert risposta.status_code == 200
    assert risposta.headers["content-type"].startswith("text/csv")
    righe = list(csv.reader(io.StringIO(risposta.text.lstrip("﻿")), delimiter=";"))
    assert righe[0][:4] == ["quando", "categoria", "azione", "esito"]
    assert len(righe) == 2
    # Il dettaglio contiene la chiave esterna scritta da altri: non diventa formula.
    assert not any(cella.startswith("=") for cella in righe[1])


@pytest.mark.integration
def test_se_il_registro_non_scrive_l_azione_riesce_lo_stesso(db_engine, come, monkeypatch, caplog):
    # 013 FR-013: validazioni e accessi negati sono informazioni, non condizioni.
    class SessioneRotta:
        def __init__(self, *args, **kwargs):
            raise sa.exc.OperationalError("INSERT", {}, Exception("registro non disponibile"))

    monkeypatch.setattr("app.attivita.registro.Session", SessioneRotta)
    # La migrazione del fixture configura il logging di alembic nello stesso
    # processo, che spegne i logger gia' creati; in produzione alembic gira in
    # un processo a parte (Dockerfile), quindi li' il logger resta acceso.
    monkeypatch.setattr(logging.getLogger("gemodo.attivita"), "disabled", False)
    versione = _crea_versione(db_engine)
    geban = come("rotto-" + uuid.uuid4().hex[:6], "DOCUMENTI_GENERATORE")

    risposta = geban.post("/api/v1/documenti/valida", json=_payload(versione["public_id"], "r", {"titolo": "x"}))
    assert risposta.status_code == 200
    assert risposta.json()["valido"] is True
    assert geban.get("/api/v1/admin/attivita").status_code == 403
    assert "non registrato" in caplog.text


@pytest.mark.integration
def test_solo_gli_amministratori(db_engine, come):
    gestore = come("gestore-test", "GEMODO_MODELLI_GESTORE", "DOCUMENTI_VIEWER")
    assert gestore.get("/api/v1/admin/attivita").status_code == 403
    assert gestore.get("/api/v1/admin/attivita.csv").status_code == 403
