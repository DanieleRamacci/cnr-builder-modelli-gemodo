import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from tests.support.postgres import postgres_database_url


@pytest.mark.integration
def test_registry_is_empty_and_ownership_is_scoped(postgres_database_url, monkeypatch):
    from app.catalog.models import TipoDocumento
    from app.configurazione.models import AuditEventoIntegrazione, Integrazione

    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "0011")
    engine = sa.create_engine(postgres_database_url)
    code = "REGISTRY_" + uuid.uuid4().hex[:16]
    legacy_id = uuid.uuid4()
    model_id, version_id = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as db:
        db.execute(sa.text("""
            INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto)
            VALUES (:id, :code, 'Legacy', 'BOZZA', '010', 'geban')
        """), {"id": legacy_id, "code": code})
        db.execute(sa.text("""
            INSERT INTO modello_documento
                (id, tipo_documento_id, codice_categoria, percorso_categorizzazione,
                 codice, nome, variante, stato, public_id)
            VALUES (:id, :tipo, 'DEMO', '["DEMO"]'::jsonb,
                    'DEMO', 'Demo', 'STANDARD', 'BOZZA', 9100001)
        """), {"id": model_id, "tipo": legacy_id})
        db.execute(sa.text("""
            INSERT INTO modello_versione
                (id, modello_documento_id, versione, stato, formato_documentale,
                 struttura_documentale, public_id)
            VALUES (:id, :modello, 1, 'BOZZA', 'GEMODO_DOCUMENT_V1', '{}'::jsonb, 9100002)
        """), {"id": version_id, "modello": model_id})
        before = {
            table: db.execute(sa.text(f"SELECT to_jsonb(t) FROM {table} t WHERE id = :id"), {"id": ident}).scalar()
            for table, ident in [("modello_documento", model_id), ("modello_versione", version_id)]
        }
    try:
        command.upgrade(config, "0012")
        with Session(engine) as db:
            assert db.scalar(sa.select(sa.func.count()).select_from(Integrazione)) == 0
            legacy = db.get(TipoDocumento, legacy_id)
            assert legacy.codice == code
            assert legacy.integrazione_id is None
            source = Integrazione(codice="SOFTWARE_DEMO", nome="Demo", codice_contesto="geban")
            db.add(source)
            db.flush()
            assert source.revisione == 1
            assert source.modalita == "SINGOLO_ENDPOINT"
            invalid = [
                Integrazione(codice="SOFTWARE_DEMO", nome="Duplicato", codice_contesto="altro"),
                Integrazione(codice=" ", nome="Demo", codice_contesto="geban"),
                Integrazione(codice="BAD_REV", nome="Demo", codice_contesto="geban", revisione=0),
                Integrazione(codice="BAD_MODE", nome="Demo", codice_contesto="geban", modalita="PER_NODI"),
                TipoDocumento(codice="BAD_CTX", nome="Demo", stato="BOZZA", spec_owner="010",
                              codice_contesto="altro", integrazione_id=source.id),
                AuditEventoIntegrazione(integrazione_id=uuid.uuid4(), tipo_evento="CREATA",
                                        soggetto_id="admin", client_id="demo", payload_minimo={}),
                AuditEventoIntegrazione(integrazione_id=source.id, tipo_evento="CREATA",
                                        soggetto_id="admin", client_id="demo", payload_minimo=[]),
            ]
            for row in invalid:
                with pytest.raises(IntegrityError):
                    with db.begin_nested():
                        db.add(row)
                        db.flush()
            legacy.integrazione_id = source.id
            db.add(AuditEventoIntegrazione(integrazione_id=source.id, tipo_evento="ASSOCIATA",
                                          soggetto_id="admin", client_id="demo", payload_minimo={"tipo_id": str(legacy.id)}))
            db.commit()
            source_id = source.id

        with pytest.raises(DBAPIError, match="registro integrazioni non vuoto"):
            command.downgrade(config, "0011")
        with engine.begin() as db:
            assert db.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == "0012"
            assert db.execute(sa.text("SELECT id FROM tipo_documento WHERE id = :id"), {"id": legacy_id}).scalar() == legacy_id
            for table, ident in [("modello_documento", model_id), ("modello_versione", version_id)]:
                assert db.execute(sa.text(f"SELECT to_jsonb(t) FROM {table} t WHERE id = :id"), {"id": ident}).scalar() == before[table]
            db.execute(sa.text("UPDATE tipo_documento SET integrazione_id = NULL WHERE id = :id"), {"id": legacy_id})
            db.execute(sa.text("DELETE FROM audit_evento_integrazione WHERE integrazione_id = :id"), {"id": source_id})
            db.execute(sa.text("DELETE FROM integrazione WHERE id = :id"), {"id": source_id})
        command.downgrade(config, "0011")
        assert "integrazione" not in sa.inspect(engine).get_table_names()
        with engine.connect() as db:
            assert db.execute(sa.text("SELECT id FROM tipo_documento WHERE id = :id"), {"id": legacy_id}).scalar() == legacy_id
        command.upgrade(config, "head")
    finally:
        with engine.begin() as db:
            db.execute(sa.text("DELETE FROM tipo_documento WHERE id = :id"), {"id": legacy_id})
        engine.dispose()
