"""Migrazione 0024: il testo dei blocchi diventa frammenti (012 T009/T010, FR-016).

Su PostgreSQL reale: righe nella forma vecchia, `upgrade`, righe nella forma
nuova e leggibili dal formato; `downgrade`, righe di nuovo **identiche** a
prima.
"""

from __future__ import annotations

import json
import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.documentale.schemas import BloccoDocumento
from tests.integration.test_migrazione_firma_contratto_0022 import _versione
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

BLOCCHI_VECCHI = [
    {"id": "titolo", "tipo": "TITOLO", "posizionamento": "TOP", "ordine": 0,
     "contenuto": "Bando {{codice_bando}}", "placeholder_usati": ["codice_bando"],
     "stile": "H1", "regole_layout": {}, "asset_ref": None, "colonne": []},
    {"id": "visto", "tipo": "PARAGRAFO", "posizionamento": "BODY", "ordine": 1,
     "contenuto": "VISTO il D.Lgs. 127/2003 “Riordino del CNR” – art. 4",
     "placeholder_usati": [], "stile": None, "regole_layout": {}, "asset_ref": None, "colonne": []},
    {"id": "logo", "tipo": "LOGO", "posizionamento": "TOP", "ordine": 2,
     "contenuto": None, "asset_ref": "logo-cnr"},
    {"id": "vuoto", "tipo": "PARAGRAFO", "posizionamento": "BODY", "ordine": 3, "contenuto": ""},
]


def _sezione(connection, versione_id, blocchi) -> uuid.UUID:
    sezione_id = uuid.uuid4()
    connection.execute(sa.text("""
        INSERT INTO sezione_modello (id, modello_versione_id, codice, ordine, contenuto)
        VALUES (:id, :versione_id, :codice, 10, CAST(:contenuto AS jsonb))
    """), {"id": sezione_id, "versione_id": versione_id, "codice": f"s-{sezione_id.hex[:8]}",
           "contenuto": json.dumps(blocchi)})
    return sezione_id


def _contenuto(engine, sezione_id):
    with engine.connect() as connection:
        return connection.scalar(sa.text("SELECT contenuto FROM sezione_modello WHERE id = :id"),
                                 {"id": sezione_id})


@pytest.mark.integration
def test_upgrade_e_downgrade_0024_frammenti(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0023")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            # Una versione PUBBLICATA: la migrazione tocca anche quelle (FR-016).
            sezione_id = _sezione(connection, _versione(connection), BLOCCHI_VECCHI)

        command.upgrade(config, "0024")
        dopo = _contenuto(engine, sezione_id)

        assert all("contenuto" not in blocco for blocco in dopo)
        assert dopo[0]["frammenti"] == [{"testo": "Bando {{codice_bando}}"}]
        assert dopo[1]["frammenti"] == [{"testo": "VISTO il D.Lgs. 127/2003 “Riordino del CNR” – art. 4"}]
        assert dopo[2]["frammenti"] == [], "contenuto null diventa nessun frammento"
        assert dopo[3]["frammenti"] == [{"testo": ""}], "la stringa vuota resta distinguibile da null"
        # Il resto del blocco non si tocca.
        assert dopo[0]["stile"] == "H1" and dopo[0]["placeholder_usati"] == ["codice_bando"]
        assert dopo[2]["asset_ref"] == "logo-cnr"
        # E il risultato e' il formato nuovo, non qualcosa che gli somiglia.
        for blocco in dopo:
            BloccoDocumento.model_validate(blocco)

        command.downgrade(config, "0023")
        assert _contenuto(engine, sezione_id) == BLOCCHI_VECCHI, "il giro completo restituisce i dati di prima"
    finally:
        command.upgrade(config, "head")
        engine.dispose()


@pytest.mark.integration
def test_downgrade_0024_perde_l_enfasi_e_appiattisce_gli_elenchi(postgres_database_url, monkeypatch):
    """Tornare al formato vecchio significa perdere cio' che non sa rappresentare - e solo quello."""
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            sezione_id = _sezione(connection, _versione(connection), [
                {"id": "v", "tipo": "PARAGRAFO", "posizionamento": "BODY", "allineamento": "GIUSTIFICATO",
                 "frammenti": [{"testo": "VISTO", "grassetto": True}, {"testo": " il decreto"}]},
                {"id": "e", "tipo": "ELENCO", "posizionamento": "BODY", "frammenti": [],
                 "elementi": [{"livello": 0, "frammenti": [{"testo": "Roma"}]},
                              {"livello": 1, "frammenti": [{"testo": "Pisa"}]}]},
            ])

        command.downgrade(config, "0023")
        prima = _contenuto(engine, sezione_id)
        assert prima == [
            {"id": "v", "tipo": "PARAGRAFO", "posizionamento": "BODY", "contenuto": "VISTO il decreto"},
            {"id": "e", "tipo": "PARAGRAFO", "posizionamento": "BODY", "contenuto": "Roma\nPisa"},
        ]
    finally:
        command.upgrade(config, "head")
        engine.dispose()
