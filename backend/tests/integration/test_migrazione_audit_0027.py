"""Migrazione 0027: l'audit sopravvive alla cancellazione (010 T106).

Su PostgreSQL reale: prima della 0027 un'integrazione con il suo evento di
creazione e il suo endpoint non si cancella; dopo, si cancella, l'endpoint la
segue e l'evento resta con il suo identificativo. Il `downgrade` rifiuta di
procedere finche' esiste un evento di una riga cancellata, invece di perderlo.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def _integrazione(connection) -> uuid.UUID:
    integrazione_id = uuid.uuid4()
    connection.execute(sa.text("""
        INSERT INTO integrazione (id, codice, nome, codice_contesto)
        VALUES (:id, :codice, 'Migrazione 0027', 'mig0027')
    """), {"id": integrazione_id, "codice": f"MIG0027_{integrazione_id.hex[:8]}"})
    connection.execute(sa.text("""
        INSERT INTO audit_evento_integrazione (id, integrazione_id, tipo_evento, soggetto_id, client_id, payload_minimo)
        VALUES (gen_random_uuid(), :id, 'INTEGRAZIONE_CREATA', 'test', 'test', '{}'::jsonb)
    """), {"id": integrazione_id})
    connection.execute(sa.text("""
        INSERT INTO endpoint_integrazione (id, integrazione_id, url)
        VALUES (gen_random_uuid(), :id, 'https://esempio.test/discovery')
    """), {"id": integrazione_id})
    return integrazione_id


def _cancella(engine, integrazione_id: uuid.UUID) -> None:
    with engine.begin() as connection:
        connection.execute(sa.text("DELETE FROM integrazione WHERE id = :id"), {"id": integrazione_id})


def _conta(engine, tabella: str, integrazione_id: uuid.UUID) -> int:
    with engine.connect() as connection:
        return connection.scalar(
            sa.text(f"SELECT count(*) FROM {tabella} WHERE integrazione_id = :id"), {"id": integrazione_id}
        )


@pytest.mark.integration
def test_upgrade_e_downgrade_0027_audit(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0026")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            bloccata = _integrazione(connection)
        with pytest.raises(sa.exc.IntegrityError):
            _cancella(engine, bloccata)

        command.upgrade(config, "0027")
        _cancella(engine, bloccata)
        assert _conta(engine, "endpoint_integrazione", bloccata) == 0, "l'endpoint segue l'integrazione"
        assert _conta(engine, "audit_evento_integrazione", bloccata) == 1, "l'evento resta, con il suo id"

        with pytest.raises(RuntimeError, match="audit"):
            command.downgrade(config, "0026")

        with engine.begin() as connection:
            connection.execute(
                sa.text("DELETE FROM audit_evento_integrazione WHERE integrazione_id = :id"), {"id": bloccata}
            )
        command.downgrade(config, "0026")
        with engine.begin() as connection:
            di_nuovo = _integrazione(connection)
        with pytest.raises(sa.exc.IntegrityError):
            _cancella(engine, di_nuovo)
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(sa.text(
                "DELETE FROM audit_evento_integrazione WHERE integrazione_id IN "
                "(SELECT id FROM integrazione WHERE codice LIKE 'MIG0027_%')"
            ))
            connection.execute(sa.text("DELETE FROM integrazione WHERE codice LIKE 'MIG0027_%'"))
        engine.dispose()
