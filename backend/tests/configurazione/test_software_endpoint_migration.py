import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.catalog.models import TipoDocumento
from app.catalog.repository import get_tipo_documento_by_codice
from app.common.errors import AuthorizationError, DomainError
from app.common.security import PrincipalGEMODO
from app.configurazione import repository
from app.configurazione.models import EndpointIntegrazione, Integrazione
from app.configurazione.models import AuditEventoIntegrazione
from app.configurazione.service import ConfigurazioneService
from tests.support.postgres import postgres_database_url


@pytest.mark.integration
def test_endpoint_history_is_inert_and_codes_are_scoped(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.downgrade(config, "0012")
    engine = sa.create_engine(postgres_database_url)
    tipo_id, schema_id, endpoint_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    code = "SCOPED_" + uuid.uuid4().hex[:16]
    with engine.begin() as db:
        db.execute(sa.text("""
            INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto)
            VALUES (:id, :code, 'Demo', 'BOZZA', '010', 'demo')
        """), {"id": tipo_id, "code": code})
        db.execute(sa.text("""
            INSERT INTO schema_discovery_generato (id, tipo_documento_id, versione, contenuto, generato_da)
            VALUES (:id, :tipo, 1, '{}'::jsonb, 'test')
        """), {"id": schema_id, "tipo": tipo_id})
        db.execute(sa.text("""
            INSERT INTO endpoint_integrazione
                (id, tipo_documento_id, url, stato, schema_discovery_generato_id_verificato, data_ultimo_test)
            VALUES (:id, :tipo, 'https://software.example.test/discovery', 'CONNESSO', :schema, now())
        """), {"id": endpoint_id, "tipo": tipo_id, "schema": schema_id})
        old = db.execute(sa.text("SELECT to_jsonb(t) FROM endpoint_integrazione t WHERE id = :id"), {"id": endpoint_id}).scalar()
    try:
        command.upgrade(config, "head")
        with engine.connect() as db:
            assert db.execute(sa.text("SELECT to_jsonb(t) FROM endpoint_integrazione_storico t WHERE id = :id"), {"id": endpoint_id}).scalar() == old
            assert db.execute(sa.text("SELECT count(*) FROM endpoint_integrazione")).scalar() == 0
        with Session(engine) as db:
            sources = [Integrazione(codice=f"SOURCE_{uuid.uuid4().hex}", nome="Demo", codice_contesto="demo") for _ in range(2)]
            db.add_all(sources)
            db.flush()
            principal = PrincipalGEMODO("admin", "gemodo-frontend", ("gemodo-backend",),
                                        ("GEMODO_ADMIN",), "https://sso.example.test")
            types = [TipoDocumento(codice=code, nome="Demo", stato="ATTIVA", spec_owner="010",
                                   codice_contesto="demo", integrazione_id=source.id) for source in sources]
            db.add_all(types)
            db.flush()
            for duplicate in [
                TipoDocumento(codice=code, nome="Demo", stato="BOZZA", spec_owner="010", codice_contesto="demo"),
                TipoDocumento(codice=code, nome="Demo", stato="BOZZA", spec_owner="010",
                              codice_contesto="demo", integrazione_id=sources[0].id),
            ]:
                with pytest.raises(IntegrityError):
                    with db.begin_nested():
                        db.add(duplicate)
                        db.flush()
            for lookup in [get_tipo_documento_by_codice, repository.tipo_documento]:
                with pytest.raises(DomainError) as error:
                    lookup(db, code)
                assert error.value.codice == "SORGENTE_AMBIGUA"
                assert error.value.status_code == 409
            source_ids, type_ids = [s.id for s in sources], [t.id for t in types]
            with pytest.raises(DomainError) as error:
                ConfigurazioneService(db).associa_tipo(tipo_id, sources[0].id, principal)
            assert error.value.status_code == 409
            assert db.get(TipoDocumento, tipo_id).integrazione_id is None
            # The failed association rolls back its audit and the pending fixtures.
            db.add_all(sources)
            db.flush()
            for tipo in types:
                db.add(tipo)
            db.flush()
            endpoint = EndpointIntegrazione(integrazione_id=sources[0].id, url="https://software.example.test/discovery",
                                           stato="CONNESSO", revisione_verificata=1, versione_contratto_verificata="1",
                                           data_ultimo_test=datetime.now(timezone.utc), esito_ultimo_test={"esito": "CONFORME"})
            db.add(endpoint)
            db.commit()
        with pytest.raises(DBAPIError, match="endpoint software o codici duplicati"):
            command.downgrade(config, "0012")
        with engine.begin() as db:
            db.execute(sa.text("DELETE FROM endpoint_integrazione WHERE integrazione_id = ANY(:ids)"), {"ids": source_ids})
            db.execute(sa.text("DELETE FROM tipo_documento WHERE id = ANY(:ids)"), {"ids": type_ids})
            db.execute(sa.text("DELETE FROM integrazione WHERE id = ANY(:ids)"), {"ids": source_ids})
        command.downgrade(config, "0012")
        with engine.connect() as db:
            assert db.execute(sa.text("SELECT to_jsonb(t) FROM endpoint_integrazione t WHERE id = :id"), {"id": endpoint_id}).scalar() == old
        command.upgrade(config, "head")
    finally:
        with engine.begin() as db:
            db.execute(sa.text("DELETE FROM tipo_documento WHERE id = :id"), {"id": tipo_id})
        engine.dispose()


@pytest.mark.integration
def test_legacy_association_is_explicit_authorized_and_audited(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = sa.create_engine(postgres_database_url)
    prefix = uuid.uuid4().hex
    principal = PrincipalGEMODO("admin", "gemodo-frontend", ("gemodo-backend",),
                                ("GEMODO_ADMIN",), "https://sso.example.test")
    manager = PrincipalGEMODO("manager", "gemodo-frontend", ("gemodo-backend",),
                              ("GEMODO_MODELLI_GESTORE",), "https://sso.example.test")
    with Session(engine) as db:
        source = Integrazione(codice="ASSOC_" + prefix, nome="Demo", codice_contesto="demo")
        other = Integrazione(codice="OTHER_" + prefix, nome="Demo", codice_contesto="demo")
        tipo = TipoDocumento(codice="ASSOC_" + prefix, nome="Demo", codice_contesto="demo", spec_owner="010", stato="BOZZA")
        different = TipoDocumento(codice="DIFF_" + prefix, nome="Demo", codice_contesto="altro", spec_owner="010", stato="BOZZA")
        db.add_all([source, other, tipo, different])
        db.commit()
        source_id, other_id, tipo_id, different_id = source.id, other.id, tipo.id, different.id
        try:
            service = ConfigurazioneService(db)
            with pytest.raises(AuthorizationError) as error:
                service.associa_tipo(tipo_id, source_id, manager)
            assert error.value.status_code == 403
            with pytest.raises(DomainError) as error:
                service.associa_tipo(different_id, source_id, principal)
            assert error.value.codice == "CONTESTO_NON_VALIDO"
            with Session(engine) as observer:
                observed = observer.get(TipoDocumento, tipo_id)
                assert observed.integrazione_id is None
                result = service.associa_tipo(tipo_id, source_id, principal)
                assert result.id == tipo_id
                assert result.integrazione_id == source_id
                with pytest.raises(DomainError) as error:
                    ConfigurazioneService(observer).associa_tipo(tipo_id, other_id, principal)
                assert error.value.codice == "OWNERSHIP_GIA_ASSOCIATA"
                observer.rollback()
            event = db.scalar(sa.select(AuditEventoIntegrazione).where(AuditEventoIntegrazione.integrazione_id == source_id))
            assert event.payload_minimo == {"tipo_documento_id": str(tipo_id)}
            assert event.soggetto_id == "admin"
            with pytest.raises(DomainError) as error:
                service.associa_tipo(tipo_id, other_id, principal)
            assert error.value.codice == "OWNERSHIP_GIA_ASSOCIATA"
            assert db.scalar(sa.select(sa.func.count()).select_from(EndpointIntegrazione)
                             .where(EndpointIntegrazione.integrazione_id == source_id)) == 0
        finally:
            db.rollback()
            db.execute(sa.delete(AuditEventoIntegrazione).where(AuditEventoIntegrazione.integrazione_id.in_([source_id, other_id])))
            db.execute(sa.delete(TipoDocumento).where(TipoDocumento.id.in_([tipo_id, different_id])))
            db.execute(sa.delete(Integrazione).where(Integrazione.id.in_([source_id, other_id])))
            db.commit()
    engine.dispose()
