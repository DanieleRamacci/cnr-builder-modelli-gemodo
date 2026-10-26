from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from tests.support.postgres import postgres_database_url


def _tipo(connection) -> uuid.UUID:
    suffisso = uuid.uuid4().hex[:12]
    tipo_id = uuid.uuid4()
    connection.execute(sa.text("""
        INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto)
        VALUES (:id, :codice, :nome, 'ATTIVA', 'specs/014-articolazioni-bando', 'migrazione')
    """), {"id": tipo_id, "codice": f"MIG0031_{suffisso}", "nome": f"Tipo {suffisso}"})
    return tipo_id


def _modello(connection, tipo_id: uuid.UUID, *, multiplo: bool | None = None) -> uuid.UUID:
    modello_id = uuid.uuid4()
    colonna, valore = (", multiplo", ", :multiplo") if multiplo is not None else ("", "")
    connection.execute(sa.text(f"""
        INSERT INTO modello_documento
            (id, tipo_documento_id, codice_categoria, codice_tipologia,
             percorso_categorizzazione, codice, nome, variante, stato, dimensioni{colonna})
        VALUES (:id, :tipo_id, 'COLLABORATORE_TECNICO_ER', 'TD',
                '["TD", "COLLABORATORE_TECNICO_ER"]'::jsonb, :codice, 'Modello',
                'STANDARD', 'ATTIVA', '{{"lingua": "IT"}}'::jsonb{valore})
    """), {"id": modello_id, "tipo_id": tipo_id, "codice": f"mig-0031-{modello_id.hex[:12]}",
           "multiplo": multiplo})
    return modello_id


@pytest.mark.integration
def test_upgrade_e_downgrade_0031_multiplo_nello_slot(postgres_database_url, monkeypatch):
    """Singolo e multiplo della stessa categorizzazione coesistono (014 FR-009f, T007)."""
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            tipo_id = _tipo(connection)
            # Un modello inserito senza dire nulla e' singolo: e' cio' che sono
            # tutti i modelli esistenti al momento della migrazione.
            singolo = _modello(connection, tipo_id)
            assert connection.scalar(sa.text(
                "SELECT multiplo FROM modello_documento WHERE id = :id"
            ), {"id": singolo}) is False
            multiplo = _modello(connection, tipo_id, multiplo=True)

        # Un secondo multiplo STANDARD sullo stesso slot no: e' la regola delle
        # varianti, che vale anche fra multipli.
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                _modello(connection, tipo_id, multiplo=True)

        # I sotto-campi sono una lista o niente.
        versione_id = uuid.uuid4()
        with engine.begin() as connection:
            connection.execute(sa.text("""
                INSERT INTO modello_versione
                    (id, modello_documento_id, versione, stato, formato_documentale, struttura_documentale)
                VALUES (:id, :modello_id, 1, 'BOZZA', 'GEMODO_DOCUMENT_V1', '{}'::jsonb)
            """), {"id": versione_id, "modello_id": multiplo})
            connection.execute(sa.text("""
                INSERT INTO campo_modello (id, modello_versione_id, codice, etichetta, tipo_dato, obbligatorio, ordine, sotto_campi)
                VALUES (:id, :versione_id, 'articolazioni', 'Tematiche', 'array', true, 14,
                        '[{"codice": "numero_posti", "etichetta": "Posti", "tipo": "number", "obbligatorio": true, "ordine": 1}]'::jsonb)
            """), {"id": uuid.uuid4(), "versione_id": versione_id})
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(sa.text("""
                    INSERT INTO campo_modello (id, modello_versione_id, codice, etichetta, tipo_dato, obbligatorio, ordine, sotto_campi)
                    VALUES (:id, :versione_id, 'altro', 'Altro', 'array', false, 15, '{"codice": "x"}'::jsonb)
                """), {"id": uuid.uuid4(), "versione_id": versione_id})

        # Con un multiplo vivo il downgrade si ferma prima di toccare gli
        # indici, invece di fallire a meta' strada.
        with pytest.raises(RuntimeError, match="modelli multipli non eliminati"):
            command.downgrade(config, "0030")
        with engine.connect() as connection:
            assert connection.scalar(sa.text(
                "SELECT count(*) FROM information_schema.columns"
                " WHERE table_name = 'modello_documento' AND column_name = 'multiplo'"
            )) == 1

        with engine.begin() as connection:
            connection.execute(sa.text(
                "UPDATE modello_documento SET stato = 'ELIMINATO' WHERE multiplo"
            ))
        command.downgrade(config, "0030")
        with engine.connect() as connection:
            assert connection.scalar(sa.text(
                "SELECT count(*) FROM information_schema.columns"
                " WHERE table_name = 'modello_documento' AND column_name = 'multiplo'"
            )) == 0
            assert connection.scalar(sa.text(
                "SELECT stato FROM modello_documento WHERE id = :id"
            ), {"id": singolo}) == "ATTIVA", "il downgrade toglie la colonna, non i modelli"
    finally:
        command.upgrade(config, "head")
        engine.dispose()
