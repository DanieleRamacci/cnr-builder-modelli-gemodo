"""Migrazione 0028: il profilo di accesso nel database (001 T088).

Su PostgreSQL reale: un'integrazione di contesto `geban` gia' registrata
riceve la mappatura che aveva dal file, un'integrazione di un altro contesto
non riceve nulla, e il `downgrade` toglie le due tabelle.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def _integrazione(connection, contesto: str) -> uuid.UUID:
    integrazione_id = uuid.uuid4()
    connection.execute(sa.text("""
        INSERT INTO integrazione (id, codice, nome, codice_contesto)
        VALUES (:id, :codice, 'Migrazione 0028', :contesto)
    """), {"id": integrazione_id, "codice": f"MIG0028_{integrazione_id.hex[:8]}", "contesto": contesto})
    return integrazione_id


@pytest.mark.integration
def test_upgrade_e_downgrade_0028_accessi(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0027")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            geban = _integrazione(connection, "geban")
            altra = _integrazione(connection, "mig0028")

        command.upgrade(config, "0028")
        with engine.connect() as connection:
            ruoli = dict(connection.execute(sa.text(
                "SELECT ruolo, permessi FROM ruolo_integrazione WHERE integrazione_id = :id"
            ), {"id": geban}).all())
            client = set(connection.scalars(sa.text(
                "SELECT client_id FROM client_integrazione WHERE integrazione_id = :id"
            ), {"id": geban}))
            dell_altra = connection.scalar(sa.text(
                "SELECT count(*) FROM ruolo_integrazione WHERE integrazione_id = :id"
            ), {"id": altra})
        assert set(ruoli) == {"ROLE_GESTORE", "ROLE_MANAGER", "ROLE_COORDINATOR", "ROLE_USER"}
        assert "GEMODO_MODELLI_GESTORE" in ruoli["ROLE_MANAGER"]
        assert "GEMODO_MODELLI_GESTORE" not in ruoli["ROLE_USER"]
        assert client == {"geban-backend", "geri-angular-public"}
        assert dell_altra == 0, "un contesto diverso da geban nasce senza ruoli"

        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(sa.text("""
                    INSERT INTO ruolo_integrazione (id, integrazione_id, ruolo, permessi)
                    VALUES (gen_random_uuid(), :id, 'ROLE_X', '["GEMODO_ADMIN"]'::jsonb)
                """), {"id": altra})

        command.downgrade(config, "0027")
        tabelle = set(sa.inspect(engine).get_table_names())
        assert "ruolo_integrazione" not in tabelle and "client_integrazione" not in tabelle
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM integrazione WHERE codice LIKE 'MIG0028_%'"))
        engine.dispose()
