"""Migrazione 0025: la cornice di pagina sul tipo documento (012 T043).

Su PostgreSQL reale: i tipi documento esistenti restano senza cornice, una
cornice scritta si rilegge nel formato, e il `downgrade` toglie la colonna.
"""

from __future__ import annotations

import json

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.documentale.schemas import CornicePagina
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

CORNICE = {
    "logo_ref": "logo-ente",
    "intestazione": [{"testo": "Consiglio Nazionale delle Ricerche", "grassetto": True}],
    "pie_pagina": [{"testo": "Piazzale Aldo Moro 7 - Roma"}],
    "numerazione_pagine": True,
}


def _colonne(engine) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns("tipo_documento")}


@pytest.mark.integration
def test_upgrade_e_downgrade_0025_cornice(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0024")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        assert "cornice_pagina" not in _colonne(engine)
        command.upgrade(config, "0025")
        assert "cornice_pagina" in _colonne(engine)
        with engine.begin() as connection:
            esistenti = connection.execute(sa.text("SELECT cornice_pagina FROM tipo_documento")).scalars().all()
            # Nessun tipo documento riceve una cornice che nessuno ha configurato.
            assert all(cornice is None for cornice in esistenti)
            if esistenti:
                connection.execute(
                    sa.text("UPDATE tipo_documento SET cornice_pagina = CAST(:c AS jsonb)"),
                    {"c": json.dumps(CORNICE)},
                )
                letta = connection.scalar(sa.text("SELECT cornice_pagina FROM tipo_documento LIMIT 1"))
                assert CornicePagina.model_validate(letta).logo_ref == "logo-ente"

        command.downgrade(config, "0024")
        assert "cornice_pagina" not in _colonne(engine)
    finally:
        command.upgrade(config, "head")
        engine.dispose()
