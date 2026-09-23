from __future__ import annotations

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from tests.support.migrazione_dimensioni import crea_stato_migrazione_dimensioni
from tests.support.postgres import postgres_database_url


@pytest.mark.integration
def test_upgrade_e_downgrade_0020_conservano_modello_versione_e_documento(
    postgres_database_url, monkeypatch,
):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0019")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)

    with engine.begin() as connection:
        stato = crea_stato_migrazione_dimensioni(connection)

    try:
        command.upgrade(config, "0020")
        with engine.connect() as connection:
            modello = connection.execute(sa.text("""
                SELECT codice, nome, dimensioni
                FROM modello_documento WHERE id = :id
            """), {"id": stato.modello_id}).mappings().one()
            assert modello["codice"] == stato.codice
            assert modello["nome"] == stato.nome
            assert modello["dimensioni"] == {"lingua": "IT"}
            assert connection.scalar(sa.text(
                "SELECT stato FROM modello_versione WHERE id = :id"
            ), {"id": stato.versione_id}) == "PUBBLICATO"
            assert connection.scalar(sa.text(
                "SELECT modello_versione_id FROM documento_generato WHERE id = :id"
            ), {"id": stato.documento_id}) == stato.versione_id

        command.downgrade(config, "0019")
        with engine.connect() as connection:
            modello = connection.execute(sa.text("""
                SELECT codice, nome, lingua, livello_professionale
                FROM modello_documento WHERE id = :id
            """), {"id": stato.modello_id}).mappings().one()
            assert dict(modello) == {
                "codice": stato.codice,
                "nome": stato.nome,
                "lingua": "IT",
                "livello_professionale": None,
            }
            assert connection.scalar(sa.text(
                "SELECT stato FROM modello_versione WHERE id = :id"
            ), {"id": stato.versione_id}) == "PUBBLICATO"
            assert connection.scalar(sa.text(
                "SELECT modello_versione_id FROM documento_generato WHERE id = :id"
            ), {"id": stato.documento_id}) == stato.versione_id
    finally:
        command.downgrade(config, "0019")
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM documento_generato WHERE id = :id"), {"id": stato.documento_id})
            connection.execute(sa.text("DELETE FROM modello_versione WHERE id = :id"), {"id": stato.versione_id})
            connection.execute(sa.text("DELETE FROM modello_documento WHERE id = :id"), {"id": stato.modello_id})
            connection.execute(sa.text("DELETE FROM tipo_documento WHERE id = :id"), {"id": stato.tipo_id})
        command.upgrade(config, "head")
        engine.dispose()
