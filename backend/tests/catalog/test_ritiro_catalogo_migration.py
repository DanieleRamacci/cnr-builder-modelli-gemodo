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
            prima = {
                t: db.execute(sa.text(f"SELECT * FROM {t} ORDER BY id")).mappings().all()
                for t in tabelle
            }
            modelli_prima = db.execute(sa.text("SELECT * FROM modello_documento ORDER BY id")).mappings().all()
        command.upgrade(config, "head")
        with engine.connect() as db:
            dopo = {
                t: db.execute(sa.text(f"SELECT * FROM {t} ORDER BY id")).mappings().all()
                for t in tabelle
            }
            modelli_dopo = db.execute(sa.text("SELECT * FROM modello_documento ORDER BY id")).mappings().all()
        # Si confrontano le **colonne di prima**, non le tuple intere: una
        # migration che aggiunge una colonna nuova (0022) lascia i dati
        # esistenti intatti, ed e' quello che questo test deve provare. Con il
        # confronto posizionale bastava una colonna in piu', vuota su tutte le
        # righe, per farlo fallire senza che nulla fosse andato perduto.
        for tabella, righe_prima in prima.items():
            righe_dopo = dopo[tabella]
            assert len(righe_prima) == len(righe_dopo), tabella
            for vecchia, nuova in zip(righe_prima, righe_dopo, strict=True):
                for colonna, valore in vecchia.items():
                    assert nuova[colonna] == valore, f"{tabella}.{colonna}"
        assert len(modelli_prima) == len(modelli_dopo)
        # `variante` e `nota` sono escluse dal confronto perche' la 0023 le
        # cambia **di proposito**: il modello inserito sopra duplica la
        # categorizzazione di un altro, e da 002 FR-019 due modelli sullo stesso
        # slot non possono restare entrambi `STANDARD` - il secondo archivierebbe
        # il primo alla pubblicazione. La migration li numera invece di fallire,
        # e qui sotto si verifica che abbia toccato solo il duplicato.
        for old, new in zip(modelli_prima, modelli_dopo, strict=True):
            for key, value in old.items():
                if key not in {"categoria_documento_id", "tipologia_bando_sol_id",
                               "variante", "nota"}:
                    assert new[key] == value

        # Si verifica la proprieta', non un elenco di codici: dopo la migration
        # nessuno slot ha piu' due modelli, e ogni riga rinumerata porta scritto
        # che l'ha rinumerata la migrazione - chi la legge in interfaccia deve
        # sapere che va rivista, non scambiarla per una scelta del gestore.
        rinumerati = [m for m in modelli_dopo if m["variante"] != "STANDARD"]
        assert rinumerati, "nessun duplicato rinumerato: il caso non e' stato esercitato"
        assert all(m["variante"].startswith("VARIANTE_") for m in rinumerati)
        assert all("migrazione 0023" in (m["nota"] or "") for m in rinumerati)
        with engine.connect() as db:
            residui = db.execute(sa.text("""
                SELECT count(*) FROM (
                    SELECT 1 FROM modello_documento
                     WHERE stato <> 'ELIMINATO'
                     GROUP BY tipo_documento_id, percorso_categorizzazione, dimensioni, variante
                    HAVING count(*) > 1
                ) AS duplicati
            """)).scalar()
        assert residui == 0
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
