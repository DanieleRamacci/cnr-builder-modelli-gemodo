import copy
import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.common.security import PrincipalGEMODO, require_principal
from app.db.session import get_db
from app.main import app
from tests.discovery.conftest import discovery_server  # noqa: F401
from tests.support.postgres import postgres_database_url


STRUTTURA = {
    "tipologie": [{"codice": "TD", "descrizione": "Tempo determinato"}],
    "profili": [{"codice": "RIC", "descrizione": "Ricercatore", "attributi": [
        {"nome": "livello", "valori_ammessi": ["I", "II"], "valore_default": "II"},
    ]}],
    "combinazioni": [{"codice_tipologia": "TD", "codice_profilo": "RIC"}],
    "lingue_possibili": ["IT", "EN"],
    "campi": [{"codice": "livello", "etichetta": "Livello", "tipo": "string",
               "lingua": "IT", "obbligatorio": True, "ordine": 1,
               "dipende_da_attributo_profilo": "livello"}],
}


@pytest.fixture
def admin_client(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = sa.create_engine(postgres_database_url)

    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "admin-test", "gemodo-frontend", ("gemodo-backend",), ("GEMODO_ADMIN",),
        "https://sso.example.test", ruoli_diretti=("GEMODO_ADMIN",),
    )
    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def crea(client, struttura=None):
    code = "DEMO_" + uuid.uuid4().hex[:16]
    payload = {"codice": code, "nome": "Documento demo", "codice_contesto": "demo"}
    if struttura is not None:
        payload["struttura"] = struttura
    response = client.post("/api/v1/configurazione/tipi-documento", json=payload)
    assert response.status_code == 201, response.text
    return code, response.json()


@pytest.mark.integration
def test_admin_configures_policy_for_a_type_discovered_live(admin_client, discovery_server):
    client, engine = admin_client
    url, responses, _ = discovery_server
    responses["/discovery"] = (200, {
        "BANDO_CONCORSO": {
            "validita": "2026-09-22T10:00:00Z",
            "nodi": [{
                "codice": "TD", "descrizione": "Tempo determinato", "tipo_livello": "tipologia",
                "figli": [{
                    "codice": "RIC", "descrizione": "Ricercatore", "tipo_livello": "profilo",
                    "lingue_possibili": ["IT", "EN"], "livelli_possibili": ["I", "II"],
                    "canale": ["PEC", "Portale"],
                    "campi": [{
                        "codice": "titolo", "etichetta": "Titolo", "tipo": "string",
                        "lingua": "IT", "obbligatorio": True, "ordine": 1,
                    }],
                }],
            }],
        },
        "VERBALE": {
            "validita": "2026-09-22T10:00:00Z",
            "nodi": [{
                "codice": "SEDUTA", "descrizione": "Seduta", "lingue_possibili": ["IT"],
                "campi": [{
                    "codice": "data", "etichetta": "Data", "tipo": "date",
                    "lingua": "IT", "obbligatorio": True, "ordine": 1,
                }],
            }],
        },
    })
    with engine.begin() as db:
        integration_id = db.execute(sa.text("""
            INSERT INTO integrazione (id, codice, nome, codice_contesto)
            VALUES (gen_random_uuid(), :codice, 'GEBAN live', 'geban') RETURNING id
        """), {"codice": "LIVE_" + uuid.uuid4().hex[:12]}).scalar_one()
        db.execute(sa.text("""
            INSERT INTO endpoint_integrazione (
                id, integrazione_id, url, timeout_ms, stato, revisione_verificata,
                versione_contratto_verificata, data_ultimo_test, esito_ultimo_test
            ) VALUES (
                gen_random_uuid(), :integration_id, :url, 5000, 'CONNESSO', 1,
                '0.5.0', :now, CAST(:outcome AS jsonb)
            )
        """), {
            "integration_id": integration_id,
            "url": url + "/discovery",
            "now": datetime.now(timezone.utc),
            "outcome": '{"esito":"CONFORME","errori":[]}',
        })

    base = f"/api/v1/configurazione/integrazioni/{integration_id}/tipi-documento"
    listed = client.get(base)
    assert listed.status_code == 200, listed.text
    assert listed.json() == ["BANDO_CONCORSO", "VERBALE"]

    policies = client.get(base + "/BANDO_CONCORSO/policy-dimensioni")
    assert policies.status_code == 200, policies.text
    assert {item["nome_dimensione"] for item in policies.json()["policy"]} == {
        "lingua", "livello",
    }
    assert {item["nome_dimensione"] for item in policies.json()["dimensioni_non_configurate"]} == {
        "canale",
    }

    saved = client.put(base + "/BANDO_CONCORSO/policy-dimensioni", json={
        "nome_dimensione": "lingua", "consente_valore_generico": False,
    })
    assert saved.status_code == 200, saved.text
    with engine.connect() as db:
        row = db.execute(sa.text("""
            SELECT td.integrazione_id, pd.nome_dimensione, pd.consente_valore_generico
                FROM tipo_documento td
                JOIN policy_dimensione pd ON pd.tipo_documento_id = td.id
                WHERE td.codice = 'BANDO_CONCORSO' AND td.integrazione_id = :integration_id
                  AND pd.nome_dimensione = 'lingua'
            """), {"integration_id": integration_id}).one()
        assert row == (integration_id, "lingua", False)


@pytest.mark.integration
def test_definition_export_revisions_and_audit(admin_client):
    client, engine = admin_client
    code, created = crea(client, STRUTTURA)
    assert created["stato_integrazione"] == "DEFINITO"
    assert created["versione_definizione"] == 1
    base = f"/api/v1/configurazione/tipi-documento/{code}"
    response = client.post(base + "/schema-discovery")
    assert response.status_code == 201, response.text
    original = response.json()
    assert original["versione"] == 1
    leaf = original["schema"][code]["nodi"][0]["figli"][0]
    assert leaf["campi"][0]["validazione"] == {"enum": ["I", "II"], "default": "II"}
    exported = client.get(base + "/schema-discovery/1")
    assert exported.status_code == 200
    assert exported.json() == original
    letta = client.get(base + "/struttura")
    assert letta.status_code == 200, letta.text
    assert letta.json()["campi"][0]["etichetta"] == "Livello"
    assert letta.json()["campi"][0]["obbligatorio"] is True
    assert letta.json()["tipologie"][0]["codice"] == "TD"
    modified = copy.deepcopy(STRUTTURA)
    modified["campi"][0]["etichetta"] = "Livello aggiornato"
    response = client.put(base + "/struttura", json=modified)
    assert response.status_code == 200, response.text
    assert response.json()["versione_definizione"] == 2
    assert client.get(base + "/struttura").json()["campi"][0]["etichetta"] == "Livello aggiornato"
    assert response.json()["versione_schema_corrente"] is None
    second = client.post(base + "/schema-discovery").json()
    assert second["versione"] == 2
    assert client.get(base + "/schema-discovery/1").json() == original
    with engine.connect() as db:
        events = db.execute(sa.text("""
            SELECT tipo_evento FROM audit_evento_configurazione
            WHERE tipo_documento_id = (SELECT id FROM tipo_documento WHERE codice = :code)
        """), {"code": code}).scalars().all()
        assert events.count("STRUTTURA_MODIFICATA") == 1
        assert events.count("SCHEMA_GENERATO") == 2
        assert events.count("SCHEMA_ESPORTATO") == 2


@pytest.mark.integration
def test_incomplete_duplicate_and_invalid_references(admin_client):
    client, engine = admin_client
    code, created = crea(client)
    assert created["stato_integrazione"] == "INCOMPLETO"
    base = f"/api/v1/configurazione/tipi-documento/{code}"
    assert client.post(base + "/schema-discovery").status_code == 400
    bad = copy.deepcopy(STRUTTURA)
    bad["combinazioni"][0]["codice_profilo"] = "inesistente"
    assert client.put(base + "/struttura", json=bad).status_code == 400
    bad = copy.deepcopy(STRUTTURA)
    bad["tipologie"].append(bad["tipologie"][0])
    assert client.put(base + "/struttura", json=bad).status_code == 400
    bad = copy.deepcopy(STRUTTURA)
    bad["campi"][0]["dipende_da_attributo_profilo"] = "inesistente"
    assert client.put(base + "/struttura", json=bad).status_code == 400
    assert client.post("/api/v1/configurazione/tipi-documento", json={
        "codice": code, "nome": "Duplicato", "codice_contesto": "demo",
    }).status_code == 409
    with engine.connect() as db:
        assert db.execute(sa.text("""
            SELECT count(*) FROM definizione_struttura
            WHERE tipo_documento_id = (SELECT id FROM tipo_documento WHERE codice = :code)
        """), {"code": code}).scalar() == 1


@pytest.mark.integration
def test_admin_cannot_create_active_duplicate_of_integration_owned_type(admin_client):
    """FR-024: l'indice parziale copre solo i tipi senza integrazione; il servizio copre il resto."""
    client, engine = admin_client
    code = "DUP_" + uuid.uuid4().hex[:16]
    with engine.begin() as db:
        integrazione_id = db.execute(sa.text("""
            INSERT INTO integrazione (id, codice, nome, codice_contesto)
            VALUES (gen_random_uuid(), :codice, 'Software proprietario', 'demo') RETURNING id
        """), {"codice": "SOFTWARE_" + code}).scalar()
        db.execute(sa.text("""
            INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto, integrazione_id)
            VALUES (gen_random_uuid(), :code, 'Del software', 'ATTIVA', 'test', 'demo', :integrazione_id)
        """), {"code": code, "integrazione_id": integrazione_id})
    response = client.post("/api/v1/configurazione/tipi-documento", json={
        "codice": code, "nome": "Duplicato admin", "codice_contesto": "demo",
    })
    assert response.status_code == 409, response.text
    assert response.json()["codice"] == "TIPO_DOCUMENTO_ALREADY_EXISTS"
    with engine.connect() as db:
        assert db.execute(sa.text("SELECT count(*) FROM tipo_documento WHERE codice = :c"), {"c": code}).scalar() == 1


@pytest.mark.integration
def test_disattivazione_per_id_risolve_il_codice_duplicato(admin_client):
    client, engine = admin_client
    code, first = crea(client, STRUTTURA)
    with engine.begin() as db:
        # Riproduce lo scenario reale (SORGENTE_AMBIGUA): la riga "attiva" del
        # builder ha sempre un integrazione_id reale, quindi il duplicato deve
        # averne uno diverso - due righe con integrazione_id NULL violerebbero
        # l'indice unico parziale su codice (uq_tipo_documento_legacy_codice).
        integrazione_id = db.execute(sa.text("""
            INSERT INTO integrazione (id, codice, nome, codice_contesto)
            VALUES (gen_random_uuid(), :codice, 'Software duplicato', 'demo')
            RETURNING id
        """), {"codice": "SOFTWARE_" + code}).scalar()
        duplicate_id = db.execute(sa.text("""
            INSERT INTO tipo_documento (id, codice, nome, stato, spec_owner, codice_contesto, integrazione_id)
            VALUES (gen_random_uuid(), :code, 'Duplicato incompleto', 'BOZZA', '010', 'demo', :integrazione_id)
            RETURNING id
        """), {"code": code, "integrazione_id": integrazione_id}).scalar()

    dashboard = client.get("/api/v1/configurazione/tipi-documento").json()
    codes = [row["codice"] for row in dashboard]
    assert codes.count(code) == 2

    # con due righe attive, anche leggere/scrivere la struttura per codice
    # (non solo il catalogo GEBAN) deve rifiutarsi con la stessa ambiguita'
    base = f"/api/v1/configurazione/tipi-documento/{code}"
    assert client.get(base + "/struttura").status_code == 409
    assert client.put(base + "/struttura", json=STRUTTURA).status_code == 409

    delete = client.delete(f"/api/v1/configurazione/tipi-documento/id/{duplicate_id}")
    assert delete.status_code == 204, delete.text

    dashboard_dopo = client.get("/api/v1/configurazione/tipi-documento").json()
    matching = [row for row in dashboard_dopo if row["codice"] == code]
    assert len(matching) == 1
    assert matching[0]["id"] == first["id"]

    # disattivata la riga duplicata, leggere/scrivere per codice torna a funzionare
    assert client.get(base + "/struttura").status_code == 200
    assert client.put(base + "/struttura", json=STRUTTURA).status_code == 200

    # idempotente: ridisattivare la stessa riga non e' un errore
    assert client.delete(f"/api/v1/configurazione/tipi-documento/id/{duplicate_id}").status_code == 204

    inesistente = client.delete(f"/api/v1/configurazione/tipi-documento/id/{uuid.uuid4()}")
    assert inesistente.status_code == 404


@pytest.mark.integration
def test_disattivazione_bloccata_se_esistono_modelli(admin_client):
    client, engine = admin_client
    code, created = crea(client, STRUTTURA)
    with engine.begin() as db:
        db.execute(sa.text("""
            INSERT INTO modello_documento
                (id, tipo_documento_id, codice_categoria, codice_tipologia, percorso_categorizzazione, codice, nome, stato, lingua)
            VALUES (gen_random_uuid(), :tipo_id, 'RIC', 'TD', '["TD","RIC"]'::jsonb, :mod_code, 'Modello test', 'BOZZA', 'IT')
        """), {"tipo_id": created["id"], "mod_code": "MOD_" + code})

    blocked = client.delete(f"/api/v1/configurazione/tipi-documento/id/{created['id']}")
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["codice"] == "TIPO_DOCUMENTO_HA_MODELLI"


@pytest.mark.integration
def test_routes_require_admin_and_export_is_scoped(admin_client):
    client, _ = admin_client
    code, created = crea(client, STRUTTURA)
    other, _ = crea(client, STRUTTURA)
    base = f"/api/v1/configurazione/tipi-documento/{code}"
    assert client.post(base + "/schema-discovery").status_code == 201
    assert client.get(f"/api/v1/configurazione/tipi-documento/{other}/schema-discovery/1").status_code == 404
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "manager", "gemodo-frontend", ("gemodo-backend",), ("GEMODO_MODELLI_GESTORE",),
        "https://sso.example.test",
    )
    for method, path, body in [
        ("get", "/api/v1/configurazione/tipi-documento", None),
        ("post", "/api/v1/configurazione/tipi-documento", {}),
        ("get", base + "/struttura", None),
        ("put", base + "/struttura", STRUTTURA),
        ("post", base + "/schema-discovery", None),
        ("get", base + "/schema-discovery/1", None),
        ("delete", f"/api/v1/configurazione/tipi-documento/id/{created['id']}", None),
    ]:
        assert client.request(method, path, json=body).status_code == 403


@pytest.mark.integration
def test_redefinition_preserves_software_connection_and_old_schema(admin_client):
    from datetime import datetime, timezone
    from app.configurazione.models import EndpointIntegrazione, Integrazione

    client, engine = admin_client
    code, _ = crea(client, STRUTTURA)
    base = f"/api/v1/configurazione/tipi-documento/{code}"
    old = client.post(base + "/schema-discovery").json()
    with Session(engine) as db:
        tipo_id = db.execute(sa.text("SELECT id FROM tipo_documento WHERE codice = :code"), {"code": code}).scalar()
        source = Integrazione(codice="SOURCE_" + uuid.uuid4().hex[:16], nome="Demo", codice_contesto="demo")
        db.add(source)
        db.flush()
        db.execute(sa.text("UPDATE tipo_documento SET integrazione_id = :source WHERE id = :id"), {"source": source.id, "id": tipo_id})
        db.add(EndpointIntegrazione(integrazione_id=source.id, url="https://example.test/discovery",
                                   stato="CONNESSO", revisione_verificata=1, versione_contratto_verificata="1",
                                   data_ultimo_test=datetime.now(timezone.utc), esito_ultimo_test={"messaggio": "ok"}))
        source_id = source.id
        db.commit()
    listing = client.get("/api/v1/configurazione/tipi-documento").json()
    assert next(t for t in listing if t["codice"] == code)["stato_integrazione"] == "CONNESSO"
    with Session(engine) as db:
        db.execute(sa.update(EndpointIntegrazione).where(EndpointIntegrazione.integrazione_id == source_id)
                   .values(stato="ERRORE", esito_ultimo_test={"messaggio": "test fallito"}))
        db.commit()
    listing = client.get("/api/v1/configurazione/tipi-documento").json()
    failed = next(t for t in listing if t["codice"] == code)
    assert failed["stato_integrazione"] == "ERRORE"
    assert failed["esito_ultimo_test"] == {"messaggio": "test fallito"}
    assert client.put(base + "/struttura", json=STRUTTURA).json()["stato_integrazione"] == "ERRORE"
    assert client.get(base + "/schema-discovery/1").json() == old
    with engine.connect() as db:
        assert db.execute(sa.text("SELECT stato FROM endpoint_integrazione WHERE integrazione_id = :id"), {"id": source_id}).scalar() == "ERRORE"
    with Session(engine) as db:
        db.execute(sa.text("UPDATE tipo_documento SET integrazione_id = NULL WHERE id = :id"), {"id": tipo_id})
        db.execute(sa.delete(EndpointIntegrazione).where(EndpointIntegrazione.integrazione_id == source_id))
        db.execute(sa.delete(Integrazione).where(Integrazione.id == source_id))
        db.commit()


@pytest.mark.integration
def test_audit_failure_rolls_back_definition(admin_client, monkeypatch):
    from app.configurazione.service import ConfigurazioneService

    client, engine = admin_client
    code = "ROLLBACK_" + uuid.uuid4().hex[:16]

    def fail(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr(ConfigurazioneService, "_audit", fail)
    with pytest.raises(RuntimeError, match="audit failure"):
        client.post("/api/v1/configurazione/tipi-documento", json={
            "codice": code, "nome": "Rollback", "codice_contesto": "demo", "struttura": STRUTTURA,
        })
    with engine.connect() as db:
        assert db.execute(sa.text("SELECT count(*) FROM tipo_documento WHERE codice = :code"), {"code": code}).scalar() == 0


def test_versioned_admin_documentation_available():
    with TestClient(app) as client:
        source = client.get("/openapi/configurazione-cataloghi.yaml")
        assert source.status_code == 200
        for path in ("/docs/configurazione-cataloghi", "/redoc/configurazione-cataloghi"):
            response = client.get(path)
            assert response.status_code == 200
            assert "/openapi/configurazione-cataloghi.yaml" in response.text


@pytest.mark.integration
def test_parallel_revisions_are_serialized_per_document_type(admin_client):
    from concurrent.futures import ThreadPoolExecutor
    from app.configurazione.schemas import StrutturaInput
    from app.configurazione.service import ConfigurazioneService

    client, engine = admin_client
    code, _ = crea(client, STRUTTURA)
    principal = app.dependency_overrides[require_principal]()

    def update(_):
        with Session(engine, expire_on_commit=False) as db:
            return ConfigurazioneService(db).aggiorna(code, StrutturaInput.model_validate(STRUTTURA), principal).versione_definizione

    def generate(_):
        with Session(engine, expire_on_commit=False) as db:
            return ConfigurazioneService(db).genera(code, principal).versione

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert sorted(executor.map(update, range(4))) == [2, 3, 4, 5]
        assert sorted(executor.map(generate, range(4))) == [1, 2, 3, 4]
