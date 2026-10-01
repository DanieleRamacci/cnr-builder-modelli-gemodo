"""Migrazione 0026: cornice a maschere e logo caricato (012 T065, T066).

Su PostgreSQL reale: una cornice salvata nella forma della 0025 diventa
intestazione e pie' di pagina indipendenti, leggibili dal formato; il
`downgrade` la riporta indietro e toglie la colonna del logo.
"""

from __future__ import annotations

import json

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.documentale.schemas import CornicePagina
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

VECCHIA = {
    "logo_ref": "logo-ente",
    "intestazione": [{"testo": "Consiglio Nazionale delle Ricerche", "grassetto": True}],
    "pie_pagina": [{"testo": "Roma"}],
    "numerazione_pagine": True,
}
SOLO_NUMERO = {"logo_ref": None, "intestazione": [], "pie_pagina": [], "numerazione_pagine": True}


def _tipo(connection, codice: str, cornice: dict) -> None:
    connection.execute(sa.text("""
        INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto, cornice_pagina)
        VALUES (gen_random_uuid(), :codice, :codice, 'ATTIVA', '012', 'migrazione', CAST(:c AS jsonb))
    """), {"codice": codice, "c": json.dumps(cornice)})


def _cornice(engine, codice: str):
    with engine.connect() as connection:
        return connection.scalar(sa.text("SELECT cornice_pagina FROM tipo_documento WHERE codice = :c"),
                                 {"c": codice})


@pytest.mark.integration
def test_upgrade_e_downgrade_0026_maschere(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0025")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            _tipo(connection, "MIG0026_COMPLETA", VECCHIA)
            _tipo(connection, "MIG0026_NUMERO", SOLO_NUMERO)

        command.upgrade(config, "0026")
        completa = _cornice(engine, "MIG0026_COMPLETA")
        assert completa["intestazione"] == {
            "maschera": "LOGO_CENTRO_TESTO_SOTTO", "con_logo": True,
            "testo": [{"testo": "Consiglio Nazionale delle Ricerche", "grassetto": True}],
        }
        assert completa["pie_pagina"]["numerazione_pagine"] is True
        CornicePagina.model_validate(completa)
        solo_numero = _cornice(engine, "MIG0026_NUMERO")
        assert solo_numero["intestazione"] is None, "senza testo ne' logo non c'e' intestazione"
        assert solo_numero["pie_pagina"]["testo"] == []
        assert "logo_cornice" in {c["name"] for c in sa.inspect(engine).get_columns("tipo_documento")}

        command.downgrade(config, "0025")
        assert _cornice(engine, "MIG0026_COMPLETA") == VECCHIA
        assert "logo_cornice" not in {c["name"] for c in sa.inspect(engine).get_columns("tipo_documento")}
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM tipo_documento WHERE codice LIKE 'MIG0026_%'"))
        engine.dispose()
