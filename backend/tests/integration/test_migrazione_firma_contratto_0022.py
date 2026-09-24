from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from tests.support.postgres import postgres_database_url


def _versione(connection):
    suffisso = uuid.uuid4().hex[:12]
    tipo_id, modello_id, versione_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    connection.execute(sa.text("""
        INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto)
        VALUES (:id, :codice, :nome, 'ATTIVA', 'specs/010-configurazione-cataloghi-integrazioni', 'migrazione')
    """), {"id": tipo_id, "codice": f"MIG0022_{suffisso}", "nome": f"Tipo {suffisso}"})
    connection.execute(sa.text("""
        INSERT INTO modello_documento
            (id, tipo_documento_id, codice_categoria, codice_tipologia,
             percorso_categorizzazione, codice, nome, variante, stato, dimensioni)
        VALUES (:id, :tipo_id, 'PROFILO_TEST', 'TIPOLOGIA_TEST',
                '["TIPOLOGIA_TEST", "PROFILO_TEST"]'::jsonb, :codice, :nome,
                'STANDARD', 'ATTIVA', '{}'::jsonb)
    """), {"id": modello_id, "tipo_id": tipo_id,
           "codice": f"migrazione-0022-{suffisso}", "nome": f"Modello {suffisso}"})
    connection.execute(sa.text("""
        INSERT INTO modello_versione
            (id, modello_documento_id, versione, stato, formato_documentale,
             struttura_documentale, pubblicato_il, pubblicato_at)
        VALUES (:id, :modello_id, 1, 'PUBBLICATO', 'GEMODO_DOCUMENT_V1',
                '{}'::jsonb, now(), now())
    """), {"id": versione_id, "modello_id": modello_id})
    return versione_id


@pytest.mark.integration
def test_upgrade_e_downgrade_0022_firma_e_esito(postgres_database_url, monkeypatch):
    """La firma vive sulla versione, l'esito in tabella propria (FR-014, T055)."""
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        versione_id = _versione(connection)

    try:
        # Una versione anteriore alla migration resta senza firma: non se ne
        # puo' inventare una, perche' l'albero di allora non e' osservabile.
        with engine.connect() as connection:
            riga = connection.execute(sa.text(
                "SELECT firma_algoritmo, firma_contratto, contratto_firmato"
                " FROM modello_versione WHERE id = :id"
            ), {"id": versione_id}).one()
            assert riga == (None, None, None)

        # Firma e algoritmo vanno insieme: una senza l'altro non e' confrontabile.
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(sa.text(
                    "UPDATE modello_versione SET firma_contratto = :f WHERE id = :id"
                ), {"f": "a" * 64, "id": versione_id})

        with engine.begin() as connection:
            connection.execute(sa.text("""
                UPDATE modello_versione
                SET firma_algoritmo = 'sha256-v1', firma_contratto = :firma,
                    contratto_firmato = :contratto
                WHERE id = :id
            """), {"firma": "b" * 64, "id": versione_id,
                   "contratto": '{"campi_obbligatori_ramo": ["codice_bando"]}'})

        esito_id = uuid.uuid4()
        with engine.begin() as connection:
            connection.execute(sa.text("""
                INSERT INTO esito_compatibilita_versione
                    (id, modello_versione_id, esito, verificato_at, differenze, firma_osservata)
                VALUES (:id, :versione_id, 'DA_AGGIORNARE', :quando,
                        '[{"tipo": "NUOVO_CAMPO_OBBLIGATORIO", "campo": "sede"}]'::jsonb, :firma)
            """), {"id": esito_id, "versione_id": versione_id,
                   "quando": datetime.now(timezone.utc), "firma": "c" * 64})

        # Un esito fuori dai quattro previsti non entra.
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(sa.text("""
                    INSERT INTO esito_compatibilita_versione
                        (id, modello_versione_id, esito, verificato_at)
                    VALUES (:id, :versione_id, 'FORSE', :quando)
                """), {"id": uuid.uuid4(), "versione_id": uuid.uuid4(),
                       "quando": datetime.now(timezone.utc)})

        # Una riga sola per versione: e' l'ultimo esito, non uno storico.
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(sa.text("""
                    INSERT INTO esito_compatibilita_versione
                        (id, modello_versione_id, esito, verificato_at)
                    VALUES (:id, :versione_id, 'ALLINEATO', :quando)
                """), {"id": uuid.uuid4(), "versione_id": versione_id,
                       "quando": datetime.now(timezone.utc)})

        command.downgrade(config, "0021")
        with engine.connect() as connection:
            assert connection.scalar(sa.text(
                "SELECT to_regclass('esito_compatibilita_versione')"
            )) is None, "il downgrade rimuove la tabella degli esiti"
            # La versione sopravvive: il downgrade toglie i metadati di
            # confronto, non cio' che era stato pubblicato.
            assert connection.scalar(sa.text(
                "SELECT stato FROM modello_versione WHERE id = :id"
            ), {"id": versione_id}) == "PUBBLICATO"

        command.upgrade(config, "0022")
        with engine.connect() as connection:
            assert connection.scalar(sa.text(
                "SELECT firma_contratto FROM modello_versione WHERE id = :id"
            ), {"id": versione_id}) is None, "il giro completo non reinventa la firma persa"
    finally:
        command.upgrade(config, "head")
        engine.dispose()
