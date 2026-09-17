import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.errors import install_error_handlers
from app.common.security import PrincipalGEMODO, require_principal
from tests.support.postgres import postgres_database_url


@pytest.mark.parametrize("roles,status", [
    (("GEMODO_ADMIN",), 200),
    (("GEMODO_MODELLI_GESTORE",), 403),
    (("DOCUMENTI_GENERATORE",), 403),
    ((), 403),
])
def test_configuration_requires_admin(roles, status):
    from app.configurazione.security import require_configurazione_admin

    app = FastAPI()
    install_error_handlers(app)
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        subject="test", client_id="gemodo-frontend", audience=("gemodo-backend",),
        ruoli=roles, issuer="https://sso.example.test", ruoli_diretti=roles,
    )

    @app.get("/admin-test")
    def protected(_=Depends(require_configurazione_admin)):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/admin-test")
    assert response.status_code == status
    if status == 403:
        assert response.json()["codice"] == "ACCESSO_NON_AUTORIZZATO"


def test_configuration_requires_authentication(monkeypatch):
    from app.configurazione.security import require_configurazione_admin

    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "false")
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/admin-test")
    def protected(_=Depends(require_configurazione_admin)):
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/admin-test")
    assert response.status_code == 401
    assert response.json()["codice"] == "ACCESSO_NON_AUTENTICATO"


@pytest.mark.integration
def test_configuration_migration_and_constraints(postgres_database_url, monkeypatch):
    from app.catalog.models import TipoDocumento
    from app.configurazione.models import (
        AttributoProfilo, EndpointIntegrazione, Integrazione, SchemaDiscoveryGenerato,
    )

    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(postgres_database_url)
    try:
        with Session(engine) as db:
            source = Integrazione(codice="FOUNDATION_DEMO", nome="Demo", codice_contesto="demo")
            other_source = Integrazione(codice="FOUNDATION_ALTRO", nome="Altro", codice_contesto="demo")
            db.add_all([source, other_source])
            db.flush()
            tipo = TipoDocumento(codice=f"TEST_{uuid.uuid4().hex[:16]}", nome="Demo",
                                 stato="BOZZA", spec_owner="010", codice_contesto="demo")
            altro = TipoDocumento(codice=f"TEST_{uuid.uuid4().hex[:16]}", nome="Altro",
                                  stato="BOZZA", spec_owner="010", codice_contesto="demo")
            db.add_all([tipo, altro])
            db.flush()
            schema = SchemaDiscoveryGenerato(tipo_documento_id=tipo.id, versione=1,
                                            contenuto={"esempio": True}, generato_da="test")
            db.add(schema)
            db.flush()
            endpoint = EndpointIntegrazione(integrazione_id=source.id,
                                           url="https://software.example.test/discovery")
            attributo = AttributoProfilo(tipo_documento_id=tipo.id, percorso_profilo=["A", "B"],
                                       codice="livello", valori_ammessi=["I", "II"], valore_default="II")
            db.add_all([endpoint, attributo])
            db.flush()
            assert endpoint.stato == "DEFINITO"
            assert endpoint.timeout_ms == 5000
            assert endpoint.revisione_verificata is None

            invalid = [
                AttributoProfilo(tipo_documento_id=tipo.id, percorso_profilo=["A", "B"],
                                codice="livello", valori_ammessi=["I"]),
                AttributoProfilo(tipo_documento_id=tipo.id, percorso_profilo=[],
                                codice="vuoto", valori_ammessi=["I"]),
                AttributoProfilo(tipo_documento_id=tipo.id, percorso_profilo=["A"],
                                codice="default", valori_ammessi=["I"], valore_default="III"),
                SchemaDiscoveryGenerato(tipo_documento_id=tipo.id, versione=1,
                                       contenuto={}, generato_da="test"),
                SchemaDiscoveryGenerato(tipo_documento_id=tipo.id, versione=0,
                                       contenuto={}, generato_da="test"),
                EndpointIntegrazione(integrazione_id=source.id, url="https://altro.example.test"),
                EndpointIntegrazione(integrazione_id=other_source.id, url="https://altro.example.test",
                                     stato="CONNESSO"),
                EndpointIntegrazione(integrazione_id=other_source.id, url="https://altro.example.test",
                                     stato="CONNESSO", data_ultimo_test=datetime.now(timezone.utc)),
                EndpointIntegrazione(integrazione_id=other_source.id, url="https://altro.example.test",
                                     timeout_ms=0),
            ]
            for row in invalid:
                with pytest.raises(IntegrityError):
                    with db.begin_nested():
                        db.add(row)
                        db.flush()
            endpoint.stato = "CONNESSO"
            endpoint.revisione_verificata = 1
            endpoint.versione_contratto_verificata = "1"
            endpoint.esito_ultimo_test = {"esito": "CONFORME"}
            endpoint.data_ultimo_test = datetime.now(timezone.utc)
            db.flush()
            db.expire_all()
            assert db.get(EndpointIntegrazione, endpoint.id).stato == "CONNESSO"
            db.rollback()

        tables = set(sa.inspect(engine).get_table_names())
        assert {"attributo_profilo", "endpoint_integrazione", "schema_discovery_generato"} <= tables
        assert not tables.intersection({"categoria_documento", "tipologia_bando_sol", "registro_contratti_dati"})
        command.downgrade(config, "0009")
        assert not {"attributo_profilo", "endpoint_integrazione", "schema_discovery_generato"}.intersection(
            sa.inspect(engine).get_table_names()
        )
        command.upgrade(config, "head")
    finally:
        engine.dispose()
