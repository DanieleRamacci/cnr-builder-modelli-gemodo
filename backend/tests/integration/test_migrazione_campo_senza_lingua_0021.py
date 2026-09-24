from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from tests.support.postgres import postgres_database_url


def _versione_con_modello(connection):
    """Tipo documento, modello e versione allo schema corrente (post 0020)."""
    suffisso = uuid.uuid4().hex[:12]
    tipo_id, modello_id, versione_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    connection.execute(sa.text("""
        INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto)
        VALUES (:id, :codice, :nome, 'ATTIVA', 'specs/011-dimensioni-generiche-modello', 'migrazione')
    """), {"id": tipo_id, "codice": f"MIG0021_{suffisso}", "nome": f"Tipo {suffisso}"})
    connection.execute(sa.text("""
        INSERT INTO modello_documento
            (id, tipo_documento_id, codice_categoria, codice_tipologia,
             percorso_categorizzazione, codice, nome, variante, stato, dimensioni)
        VALUES (:id, :tipo_id, 'PROFILO_TEST', 'TIPOLOGIA_TEST',
                '["TIPOLOGIA_TEST", "PROFILO_TEST"]'::jsonb, :codice, :nome,
                'STANDARD', 'ATTIVA', '{}'::jsonb)
    """), {"id": modello_id, "tipo_id": tipo_id,
           "codice": f"migrazione-0021-{suffisso}", "nome": f"Modello {suffisso}"})
    connection.execute(sa.text("""
        INSERT INTO modello_versione
            (id, modello_documento_id, versione, stato, formato_documentale,
             struttura_documentale, pubblicato_il, pubblicato_at)
        VALUES (:id, :modello_id, 1, 'PUBBLICATO', 'GEMODO_DOCUMENT_V1',
                '{}'::jsonb, now(), now())
    """), {"id": versione_id, "modello_id": modello_id})
    return versione_id


def _campo(connection, versione_id, codice, lingua):
    campo_id = uuid.uuid4()
    connection.execute(sa.text("""
        INSERT INTO campo_modello
            (id, modello_versione_id, codice, etichetta, tipo_dato, obbligatorio, lingua, ordine)
        VALUES (:id, :versione_id, :codice, :codice, 'string', true, :lingua, 1)
    """), {"id": campo_id, "versione_id": versione_id, "codice": codice, "lingua": lingua})
    return campo_id


@pytest.mark.integration
def test_upgrade_e_downgrade_0021_sulla_lingua_del_campo(postgres_database_url, monkeypatch):
    """0021 toglie la lingua implicita dal campo, e il downgrade la rimette."""
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        versione_id = _versione_con_modello(connection)

    try:
        with engine.begin() as connection:
            senza = _campo(connection, versione_id, "campo_senza_lingua", None)
            con = _campo(connection, versione_id, "campo_inglese", "EN")


        with engine.connect() as connection:
            assert connection.scalar(sa.text(
                "SELECT lingua FROM campo_modello WHERE id = :id"), {"id": senza}) is None
            assert connection.scalar(sa.text(
                "SELECT lingua FROM campo_modello WHERE id = :id"), {"id": con}) == "EN"

        # NULLS NOT DISTINCT: il duplicato resta impedito anche senza lingua.
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                _campo(connection, versione_id, "campo_senza_lingua", None)

        command.downgrade(config, "0020")
        with engine.connect() as connection:
            # Il downgrade inventa 'IT' dove la lingua non c'era: e' documentato
            # nella migration, ed e' il dato falso che 0021 elimina.
            assert connection.scalar(sa.text(
                "SELECT lingua FROM campo_modello WHERE id = :id"), {"id": senza}) == "IT"
            assert connection.scalar(sa.text(
                "SELECT lingua FROM campo_modello WHERE id = :id"), {"id": con}) == "EN"
            assert connection.scalar(sa.text(
                "SELECT stato FROM modello_versione WHERE id = :id"
            ), {"id": versione_id}) == "PUBBLICATO"

        command.upgrade(config, "0021")
    finally:
        with engine.begin() as connection:
            connection.execute(sa.text(
                "DELETE FROM campo_modello WHERE modello_versione_id = :id"
            ), {"id": versione_id})
        command.upgrade(config, "head")
        engine.dispose()
