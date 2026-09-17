import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from app.catalog.models import Base
from tests.support.postgres import postgres_database_url


@pytest.mark.integration
def test_migration_preserves_owned_models_and_contracts(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "0008")
    engine = sa.create_engine(postgres_database_url)
    try:
        with engine.begin() as db:
            db.execute(sa.text("""
                INSERT INTO modello_documento (id, tipo_documento_id,
                    categoria_documento_id, codice, nome, stato)
                SELECT :id, tipo_documento_id, categoria_documento_id,
                    'migrazione-senza-tipologia', 'Senza tipologia', 'BOZZA'
                FROM modello_documento LIMIT 1
            """), {"id": uuid.uuid4()})
            refs = db.execute(sa.text("""
                SELECT m.id, c.codice AS categoria, t.codice AS tipologia
                FROM modello_documento m
                JOIN categoria_documento c ON m.categoria_documento_id = c.id
                LEFT JOIN tipologia_bando_sol t ON m.tipologia_bando_sol_id = t.id
            """)).mappings().all()
            db.execute(sa.text("""
                INSERT INTO audit_evento_modello (id, tipo_evento, soggetto_id,
                    client_id, ruoli, modello_documento_id, payload_minimo)
                VALUES (:id, 'MODELLO_CREATO', 'test', 'test', '[]'::jsonb,
                    :modello, '{}'::jsonb)
            """), {"id": uuid.uuid4(), "modello": refs[0]["id"]})
            tabelle = ["modello_versione", "campo_modello", "audit_evento_modello",
                       "sezione_modello", "generazione_documento"]
            prima = {t: db.execute(sa.text(f"SELECT * FROM {t} ORDER BY id")).all() for t in tabelle}
            modelli_prima = db.execute(sa.text("SELECT * FROM modello_documento ORDER BY id")).mappings().all()
        command.upgrade(config, "head")
        with engine.connect() as db:
            dopo = {t: db.execute(sa.text(f"SELECT * FROM {t} ORDER BY id")).all() for t in tabelle}
            modelli_dopo = db.execute(sa.text("SELECT * FROM modello_documento ORDER BY id")).mappings().all()
        assert prima == dopo
        assert len(modelli_prima) == len(modelli_dopo)
        for old, new in zip(modelli_prima, modelli_dopo, strict=True):
            for key, value in old.items():
                if key not in {"categoria_documento_id", "tipologia_bando_sol_id"}:
                    assert new[key] == value
        by_id = {m["id"]: m for m in modelli_dopo}
        for ref in refs:
            model = by_id[ref["id"]]
            assert model["codice_categoria"] == ref["categoria"]
            assert model["codice_tipologia"] == ref["tipologia"]
            assert model["percorso_categorizzazione"] == (
                [ref["tipologia"], ref["categoria"]] if ref["tipologia"] else [ref["categoria"]]
            )
        retired = {"categoria_documento", "classificazione_catalogo", "tipologia_bando_sol",
                   "tipologia_bando", "registro_contratti_dati"}
        assert retired.isdisjoint(sa.inspect(engine).get_table_names())
        assert retired.isdisjoint(Base.metadata.tables)
    finally:
        engine.dispose()
