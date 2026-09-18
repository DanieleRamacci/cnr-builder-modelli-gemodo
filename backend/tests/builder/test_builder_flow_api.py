"""Real end-to-end test of the builder write API against a real Postgres DB.

Covers the flow the product owner asked for on 2026-09-15: an authorized
gestore reads the available structure over HTTP, creates
a model + version choosing fields from the external selected leaf,
pushes it through the full BOZZA->IN_REVISIONE->APPROVATO->PUBBLICATO chain
(with auto-archive of the previous current version), and the already-existing
/documenti/valida and /documenti/genera then succeed against it for real -
this is the concrete proof that "GEBAN puo' generare un documento" end to end.

Also proves the DEC-001-CONTESTO-SOSTITUISCE-UFFICIO security property: a
role granting GEMODO_MODELLI_GESTORE in one token context MUST NOT authorize
a write on a tipo documento owned by a different context.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
import yaml
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import TipoDocumento
from app.configurazione.models import EndpointIntegrazione, Integrazione
from app.db.session import get_db
from app.main import app
from tests.support.postgres import postgres_database_url
from tests.discovery.conftest import discovery_server


@pytest.fixture()
def catalogo_esterno(discovery_server):
    url, responses, requests = discovery_server
    campi = [
        {"codice": codice, "etichetta": codice, "tipo": tipo, "lingua": lingua,
         "obbligatorio": obbligatorio, "ordine": ordine}
        for ordine, (codice, tipo, lingua, obbligatorio) in enumerate([
            ("codice_bando", "string", "IT", True),
            ("titolo_it", "string", "IT", True),
            ("sede_prescelta_it", "string", "IT", True),
            ("numero_posti", "number", "IT", True),
            ("titolo_en", "string", "EN", True),
            ("livello", "string", "IT", False),
        ], start=1)
    ]
    responses["/discovery"] = (200, {"BANDO_CONCORSO": {
        "validita": "2026-09-17T00:00:00Z", "nodi": [
            {"codice": "TD", "descrizione": "Tempo determinato", "tipo_livello": "tipologia", "figli": [
                {"codice": "RICERCATORE", "descrizione": "Ricercatore", "tipo_livello": "profilo", "campi": campi}
            ]}
        ]}})
    return url, responses, requests


@pytest.fixture()
def db_engine(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def integrazione_connessa(db_engine, catalogo_esterno, monkeypatch):
    """Registers a CONNESSO Integrazione/EndpointIntegrazione for BANDO_CONCORSO (T082).

    The builder resolves discovery through the registry, never through an env var
    bypass; this fixture sets up the registry state a real admin verify (T081) would
    have produced, without re-running the HTTP round trip (that flow is covered by
    ``tests/configurazione/test_integrazioni_admin.py``). A real verify would only ever
    reach CONNESSO for a URL that passed ``valida_destinazione_approvata`` in the first
    place (T081), and T084 made every live read re-check that same allowlist on each
    resolution (``discovery_per_tipo``) - so this fixture must allowlist the test
    server's origin too, or every builder call would now 422 with
    DESTINAZIONE_NON_APPROVATA regardless of the DB row.
    """
    url, _, _ = catalogo_esterno
    monkeypatch.setenv("GEMODO_INTEGRAZIONI_ALLOWLIST", url)
    monkeypatch.setenv("GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO", url)
    with Session(db_engine) as db:
        tipo = db.execute(sa.select(TipoDocumento).where(TipoDocumento.codice == "BANDO_CONCORSO")).scalar_one()
        integrazione_precedente = tipo.integrazione_id
        source = Integrazione(codice="TEST_" + uuid.uuid4().hex[:16], nome="Software di test",
                              codice_contesto=tipo.codice_contesto)
        db.add(source)
        db.flush()
        db.add(EndpointIntegrazione(
            integrazione_id=source.id, url=url + "/discovery", timeout_ms=5000, stato="CONNESSO",
            revisione_verificata=1, versione_contratto_verificata="0.4.0",
            data_ultimo_test=datetime.now(timezone.utc), esito_ultimo_test={"esito": "CONFORME", "errori": []},
        ))
        tipo.integrazione_id = source.id
        db.commit()
        source_id = source.id
    try:
        yield source_id
    finally:
        with Session(db_engine) as db:
            db.execute(sa.text("UPDATE tipo_documento SET integrazione_id = :precedente WHERE codice = 'BANDO_CONCORSO'"),
                      {"precedente": integrazione_precedente})
            db.execute(sa.delete(EndpointIntegrazione).where(EndpointIntegrazione.integrazione_id == source_id))
            db.execute(sa.delete(Integrazione).where(Integrazione.id == source_id))
            db.commit()


@pytest.fixture()
def builder_client(db_engine, monkeypatch, integrazione_connessa):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "geri-angular-public")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "geban")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_MANAGER#geban")

    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


CAMPI_BASE = [
    {"codice": "codice_bando", "lingua": "IT"},
    {"codice": "titolo_it", "lingua": "IT"},
    {"codice": "sede_prescelta_it", "lingua": "IT"},
    {"codice": "numero_posti", "lingua": "IT"},
    {"codice": "titolo_en", "lingua": "EN"},
    {"codice": "livello", "lingua": "IT"},
]


@pytest.mark.integration
def test_selected_integration_creates_scoped_type_and_versions_despite_legacy_duplicate(
    builder_client, db_engine, catalogo_esterno, integrazione_connessa,
):
    code = "TEST_SCOPED"
    catalogo_esterno[1]["/discovery"][1][code] = deepcopy(
        catalogo_esterno[1]["/discovery"][1]["BANDO_CONCORSO"]
    )
    legacy_id = uuid.uuid4()
    with Session(db_engine) as db:
        db.add(TipoDocumento(id=legacy_id, codice=code, nome=code,
                             codice_contesto="geban", spec_owner="specs/002-builder-modelli"))
        db.commit()
    try:
        response = builder_client.post("/api/v1/builder/modelli", json={
            "codice": "scoped-" + uuid.uuid4().hex, "nome": "Modello scoped",
            "codice_tipo_documento": code, "integrazione_id": str(integrazione_connessa),
            "percorso_categorizzazione": ["TD", "RICERCATORE"],
        })
        assert response.status_code == 201, response.text
        model = response.json()
        version = _crea_versione(builder_client, model["id"])
        assert version["stato"] == "BOZZA"
        with Session(db_engine) as db:
            assert db.get(TipoDocumento, legacy_id).integrazione_id is None
            assert db.scalar(sa.text(
                "SELECT t.integrazione_id FROM tipo_documento t JOIN modello_documento m "
                "ON m.tipo_documento_id = t.id WHERE m.id = :id"
            ), {"id": model["id"]}) == integrazione_connessa
    finally:
        with Session(db_engine) as db:
            db.execute(sa.delete(TipoDocumento).where(TipoDocumento.codice == code))
            db.commit()


@pytest.mark.integration
def test_selected_integration_requires_context_permission_before_creating_type(builder_client, db_engine):
    source_id = uuid.uuid4()
    with Session(db_engine) as db:
        db.add(Integrazione(id=source_id, codice="DENIED_" + uuid.uuid4().hex[:16],
                            nome="Non autorizzata", codice_contesto="altro"))
        db.commit()
    try:
        response = builder_client.post("/api/v1/builder/modelli", json={
            "codice": "denied-scoped", "nome": "Negato", "codice_tipo_documento": "ASSENTE",
            "integrazione_id": str(source_id), "percorso_categorizzazione": ["FOGLIA"],
        })
        assert response.status_code == 403, response.text
        with Session(db_engine) as db:
            assert db.scalar(sa.select(TipoDocumento.id).where(TipoDocumento.integrazione_id == source_id)) is None
    finally:
        with Session(db_engine) as db:
            db.execute(sa.delete(Integrazione).where(Integrazione.id == source_id))
            db.commit()


def _crea_modello(client: TestClient, *, codice: str, variante: str = "STANDARD") -> dict:
    response = client.post(
        "/api/v1/builder/modelli",
        json={
            "codice": codice,
            "nome": f"Modello {codice}",
            "codice_tipo_documento": "BANDO_CONCORSO",
            "codice_categoria": "RICERCATORE",
            "codice_tipologia": "TD",
            "variante": variante,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _crea_versione(client: TestClient, modello_id: str, campi: list[dict] = CAMPI_BASE) -> dict:
    response = client.post(f"/api/v1/builder/modelli/{modello_id}/versioni", json={"campi": campi})
    assert response.status_code == 201, response.text
    return response.json()


def _pubblica_fino_in_fondo(client: TestClient, modello_id: str, versione_id: str) -> dict:
    for azione in ("invia-revisione", "approva", "pubblica"):
        response = client.post(f"/api/v1/builder/modelli/{modello_id}/versioni/{versione_id}/{azione}")
        assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.integration
def test_struttura_disponibile_riflette_solo_la_discovery_http(builder_client, catalogo_esterno):
    response = builder_client.get("/api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile")

    assert response.status_code == 200
    body = response.json()
    codici_tipologie = {t["codice"] for t in body["nodi"]}
    assert "TD" in codici_tipologie
    campi = body["nodi"][0]["figli"][0]["campi"]
    codici_campi = {c["codice"] for c in campi}
    assert codici_campi == {
        "codice_bando",
        "titolo_it",
        "sede_prescelta_it",
        "numero_posti",
        "titolo_en",
        "livello",
    }
    assert "tipologie" not in body and "campi" not in body
    assert catalogo_esterno[2] == ["/discovery"]


def _richiesta_percorso(codice, percorso):
    return {"codice": codice, "nome": codice, "codice_tipo_documento": "BANDO_CONCORSO",
            "percorso_categorizzazione": percorso}


@pytest.mark.integration
def test_new_three_level_external_branch_needs_no_local_catalog(builder_client, catalogo_esterno, db_engine):
    _, responses, _ = catalogo_esterno
    nuovo_campo = {"codice": "nuovo_dato", "etichetta": "Nuovo dato", "tipo": "string",
                   "lingua": "IT", "obbligatorio": True, "ordine": 1,
                   "descrizione": "Definizione esterna corrente"}
    responses["/discovery"][1]["BANDO_CONCORSO"]["nodi"].append({
        "codice": "AREA_NUOVA", "descrizione": "Area nuova", "figli": [{
            "codice": "GRUPPO_NUOVO", "descrizione": "Gruppo nuovo", "figli": [{
                "codice": "FOGLIA_NUOVA", "descrizione": "Foglia nuova", "campi": [nuovo_campo]
            }]
        }]
    })
    percorso = ["AREA_NUOVA", "GRUPPO_NUOVO", "FOGLIA_NUOVA"]
    response = builder_client.post("/api/v1/builder/modelli", json=_richiesta_percorso("nuovo-ramo-esterno", percorso))
    assert response.status_code == 201, response.text
    modello = response.json()
    assert modello["percorso_categorizzazione"] == percorso
    assert modello["codice_categoria"] == "FOGLIA_NUOVA"
    assert modello["codice_tipologia"] is None
    versione = _crea_versione(builder_client, modello["id"], [{"codice": "nuovo_dato", "lingua": "IT"}])
    wrong = builder_client.post(f"/api/v1/builder/modelli/{modello['id']}/versioni", json={"campi": CAMPI_BASE})
    assert wrong.status_code == 404
    with Session(db_engine) as db:
        saved = db.execute(sa.text("SELECT descrizione FROM campo_modello WHERE modello_versione_id = :id"),
                           {"id": versione["id"]}).scalar_one()
        assert saved == nuovo_campo["descrizione"]
    assert "categoria_documento" not in sa.inspect(db_engine).get_table_names()


@pytest.mark.integration
def test_scalar_selection_ambiguous_requires_full_path(builder_client, catalogo_esterno):
    nodi = catalogo_esterno[1]["/discovery"][1]["BANDO_CONCORSO"]["nodi"]
    altro = deepcopy(nodi[0])
    altro["codice"] = "TI"
    nodi.append(altro)
    request = _richiesta_percorso("selezione-ambigua", ["TD", "RICERCATORE"])
    request.pop("percorso_categorizzazione")
    request["codice_categoria"] = "RICERCATORE"
    assert builder_client.post("/api/v1/builder/modelli", json=request).status_code == 400
    request["percorso_categorizzazione"] = ["TI", "RICERCATORE"]
    result = builder_client.post("/api/v1/builder/modelli", json=request)
    assert result.status_code == 201
    assert result.json()["codice_tipologia"] == "TI"


@pytest.mark.integration
@pytest.mark.parametrize("percorso", [["TD"], ["TD", "ASSENTE"]])
def test_selection_must_resolve_to_an_existing_leaf(builder_client, percorso):
    response = builder_client.post("/api/v1/builder/modelli", json=_richiesta_percorso("percorso-errato", percorso))
    assert response.status_code == 404


@pytest.mark.integration
def test_explicit_codes_cannot_contradict_selected_path(builder_client):
    request = _richiesta_percorso("codici-incoerenti", ["TD", "RICERCATORE"])
    request["codice_tipologia"] = "TI"
    assert builder_client.post("/api/v1/builder/modelli", json=request).status_code == 400


@pytest.mark.integration
def test_versions_use_fresh_external_fields_without_rewriting_old_contract(builder_client, catalogo_esterno, db_engine):
    modello = _crea_modello(builder_client, codice="contratto-aggiornato")
    versione1 = _crea_versione(builder_client, modello["id"], [CAMPI_BASE[0]])
    campo = catalogo_esterno[1]["/discovery"][1]["BANDO_CONCORSO"]["nodi"][0]["figli"][0]["campi"][0]
    campo["tipo"] = "number"
    versione2 = _crea_versione(builder_client, modello["id"], [CAMPI_BASE[0]])
    with Session(db_engine) as db:
        for versione, expected in [(versione1, "string"), (versione2, "number")]:
            assert db.execute(sa.text("SELECT tipo_dato FROM campo_modello WHERE modello_versione_id = :id"),
                              {"id": versione["id"]}).scalar_one() == expected
    assert len(catalogo_esterno[2]) == 3


@pytest.mark.integration
def test_removed_branch_and_duplicate_fields_do_not_create_versions(builder_client, catalogo_esterno, db_engine):
    modello = _crea_modello(builder_client, codice="ramo-scomparso")
    duplicate = builder_client.post(f"/api/v1/builder/modelli/{modello['id']}/versioni",
                                    json={"campi": [CAMPI_BASE[0], CAMPI_BASE[0]]})
    assert duplicate.status_code == 400
    catalogo_esterno[1]["/discovery"][1]["BANDO_CONCORSO"]["nodi"] = []
    removed = builder_client.post(f"/api/v1/builder/modelli/{modello['id']}/versioni", json={"campi": CAMPI_BASE})
    assert removed.status_code == 404
    with Session(db_engine) as db:
        assert db.execute(sa.text("SELECT count(*) FROM modello_versione WHERE modello_documento_id = :id"),
                          {"id": modello["id"]}).scalar_one() == 0


@pytest.mark.integration
def test_unconfigured_tipo_documento_does_not_fall_back_to_seed(builder_client, db_engine):
    with Session(db_engine) as db:
        db.execute(sa.text("UPDATE tipo_documento SET integrazione_id = NULL WHERE codice = 'BANDO_CONCORSO'"))
        db.commit()
    response = builder_client.get("/api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile")
    assert response.status_code == 503
    assert response.json()["codice"] == "DISCOVERY_NON_CONFIGURATA"


@pytest.mark.integration
@pytest.mark.parametrize("stato", ["DEFINITO", "ERRORE"])
def test_not_connected_integration_does_not_fall_back_to_seed(builder_client, db_engine, integrazione_connessa, stato):
    with Session(db_engine) as db:
        db.execute(sa.text("UPDATE endpoint_integrazione SET stato = :stato WHERE integrazione_id = :id"),
                  {"stato": stato, "id": integrazione_connessa})
        db.commit()
    response = builder_client.get("/api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile")
    assert response.status_code == 409
    assert response.json()["codice"] == "INTEGRAZIONE_NON_CONNESSA"


@pytest.mark.integration
def test_connected_integration_falling_out_of_the_allowlist_is_denied_on_next_read(builder_client, monkeypatch):
    """T084: CONNESSO never expires on its own, so a URL approved once must be
    re-checked on every live read, not just at configure/verify time - otherwise
    narrowing GEMODO_INTEGRAZIONI_ALLOWLIST after the fact would have no effect on an
    already-connected integration."""
    monkeypatch.delenv("GEMODO_INTEGRAZIONI_ALLOWLIST", raising=False)
    monkeypatch.delenv("GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO", raising=False)
    response = builder_client.get("/api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile")
    assert response.status_code == 422, response.text
    assert response.json()["codice"] == "DESTINAZIONE_NON_APPROVATA"


@pytest.mark.integration
def test_unavailable_external_service_never_returns_seed_or_creates_model(builder_client, catalogo_esterno, db_engine):
    catalogo_esterno[1]["/discovery"] = (500, {"messaggio": "Errore esterno"})
    response = builder_client.post("/api/v1/builder/modelli",
                                   json=_richiesta_percorso("nessun-fallback", ["TD", "RICERCATORE"]))
    assert response.status_code == 503
    assert response.json()["codice"] == "DISCOVERY_NON_DISPONIBILE"
    with Session(db_engine) as db:
        assert db.execute(sa.text("SELECT count(*) FROM modello_documento WHERE codice = 'nessun-fallback'" )).scalar_one() == 0


@pytest.mark.integration
def test_crea_modello_e_versione_con_campo_non_ammesso_viene_rifiutato(builder_client):
    modello = _crea_modello(builder_client, codice="pytest-modello-campo-invalido")

    response = builder_client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni",
        json={"campi": [{"codice": "campo_inventato", "lingua": "IT"}]},
    )

    assert response.status_code == 404
    assert response.json()["codice"] == "CAMPO_NON_AMMESSO"


@pytest.mark.integration
def test_flusso_completo_creazione_pubblicazione_e_generazione_documento(builder_client):
    modello = _crea_modello(builder_client, codice="pytest-modello-e2e", variante="PYTEST")
    versione = _crea_versione(builder_client, modello["id"])
    assert versione["stato"] == "BOZZA"

    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])
    assert pubblicata["stato"] == "PUBBLICATO"
    modello_versione_id = pubblicata["public_id"]
    assert modello_versione_id is not None

    payload = {
        "sistema_richiedente": "GEBAN",
        "external_context_id": "pytest-context",
        "modello_versione_id": modello_versione_id,
        "dati": {
            "codice_bando": "BANDO-PYTEST-1",
            "titolo_it": "Bando pytest",
            "sede_prescelta_it": "Roma",
            "numero_posti": 3,
            "titolo_en": "Pytest call",
            "livello": "III",
        },
    }

    validazione = builder_client.post("/api/v1/documenti/valida", json=payload)
    assert validazione.status_code == 200, validazione.text
    assert validazione.json() == {"valido": True, "errori": []}

    generazione = builder_client.post("/api/v1/documenti/genera", json=payload)
    assert generazione.status_code == 200, generazione.text
    esito = generazione.json()
    assert esito["stato"] == "COMPLETATO"
    riferimento = esito["riferimento_documentale"]
    assert riferimento

    stato = builder_client.get(f"/api/v1/documenti/{riferimento}")
    assert stato.status_code == 200, stato.text
    assert stato.json()["stato"] == "COMPLETATO"
    assert stato.json()["modello_versione_id"] == modello_versione_id

    download = builder_client.get(f"/api/v1/documenti/{riferimento}/download")
    assert download.status_code == 200, download.text
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF")
    assert b"Bando pytest" in download.content

    replay = builder_client.post("/api/v1/documenti/genera", json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["riferimento_documentale"] == riferimento

    payload_diverso = {**payload, "dati": {**payload["dati"], "numero_posti": 99}}
    conflitto = builder_client.post("/api/v1/documenti/genera", json=payload_diverso)
    assert conflitto.status_code == 409, conflitto.text
    assert conflitto.json()["codice"] == "RICHIESTA_IDEMPOTENTE_IN_CONFLITTO"
    assert builder_client.delete(f"/api/v1/builder/modelli/{modello['id']}").status_code == 204
    retained = builder_client.get(f"/api/v1/documenti/{riferimento}/download")
    assert retained.status_code == 200
    assert retained.content == download.content


@pytest.mark.integration
def test_pubblicazione_archivia_automaticamente_la_versione_corrente_precedente(builder_client, db_engine):
    modello = _crea_modello(builder_client, codice="pytest-modello-auto-archivio", variante="PYTEST-ARCHIVIO")

    versione_1 = _crea_versione(builder_client, modello["id"])
    _pubblica_fino_in_fondo(builder_client, modello["id"], versione_1["id"])

    versione_2 = _crea_versione(builder_client, modello["id"])
    pubblicata_2 = _pubblica_fino_in_fondo(builder_client, modello["id"], versione_2["id"])
    assert pubblicata_2["stato"] == "PUBBLICATO"

    with Session(db_engine) as verifica:
        stato_versione_1 = verifica.execute(
            sa.text("SELECT stato FROM modello_versione WHERE id = :id"),
            {"id": versione_1["id"]},
        ).scalar_one()
    assert stato_versione_1 == "ARCHIVIATO"


@pytest.mark.integration
def test_transizione_non_valida_e_rifiutata(builder_client):
    modello = _crea_modello(builder_client, codice="pytest-modello-transizione-invalida")
    versione = _crea_versione(builder_client, modello["id"])

    response = builder_client.post(f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/approva")

    assert response.status_code == 409
    assert response.json()["codice"] == "TRANSIZIONE_STATO_NON_VALIDA"


@pytest.mark.integration
def test_context_list_and_model_list_include_drafts_and_publication_states(builder_client):
    assert "geban" in builder_client.get("/api/v1/builder/contesti").json()
    model = _crea_modello(builder_client, codice="lista-" + uuid.uuid4().hex)
    version = _crea_versione(builder_client, model["id"])
    response = builder_client.get("/api/v1/builder/modelli", params={"codice_contesto": "geban", "limit": 100})
    assert response.status_code == 200, response.text
    item = next(m for m in response.json() if m["id"] == model["id"])
    assert item["codice_contesto"] == "geban"
    assert item["versioni"][0]["stato"] == "BOZZA"
    assert "url" not in item
    published = _pubblica_fino_in_fondo(builder_client, model["id"], version["id"])
    response = builder_client.get("/api/v1/builder/modelli", params={"codice_contesto": "geban", "limit": 100})
    item = next(m for m in response.json() if m["id"] == model["id"])
    assert item["versioni"][0]["stato"] == "PUBBLICATO"
    assert item["versioni"][0]["public_id"] == published["public_id"]
    assert builder_client.get("/api/v1/builder/modelli", params={"codice_contesto": "altro"}).status_code == 403
    assert builder_client.get("/api/v1/builder/modelli", params={"codice_contesto": "geban", "limit": 101}).status_code == 400


@pytest.mark.integration
def test_delete_hides_model_preserves_versions_and_prevents_republication(builder_client, db_engine):
    model = _crea_modello(builder_client, codice="delete-test")
    version = _crea_versione(builder_client, model["id"])
    _pubblica_fino_in_fondo(builder_client, model["id"], version["id"])
    assert builder_client.delete(f"/api/v1/builder/modelli/{model['id']}").status_code == 204
    listing = builder_client.get("/api/v1/builder/modelli", params={"codice_contesto": "geban"}).json()
    assert all(item["id"] != model["id"] for item in listing)
    assert builder_client.post(f"/api/v1/builder/modelli/{model['id']}/versioni/{version['id']}/pubblica").status_code == 404
    with Session(db_engine) as db:
        assert db.scalar(sa.text("SELECT stato FROM modello_versione WHERE id = :id"), {"id": version["id"]}) == "ARCHIVIATO"
        assert db.scalar(sa.text("SELECT count(*) FROM audit_evento_modello WHERE modello_documento_id = :id AND tipo_evento = 'MODELLO_ELIMINATO'"), {"id": model["id"]}) == 1


def test_delete_requires_permission_in_target_context(builder_client, monkeypatch):
    model = _crea_modello(builder_client, codice="delete-denied")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "altro")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_MANAGER#altro")
    assert builder_client.delete(f"/api/v1/builder/modelli/{model['id']}").status_code == 403


def test_new_installation_without_demo_opt_in_is_empty(postgres_database_url, monkeypatch):
    engine = create_engine(postgres_database_url)
    schema = "demo_clean_" + uuid.uuid4().hex
    with engine.begin() as db:
        db.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    isolated = create_engine(postgres_database_url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        monkeypatch.setenv("DATABASE_URL", postgres_database_url)
        monkeypatch.setenv("PGOPTIONS", f"-csearch_path={schema}")
        monkeypatch.delenv("GEMODO_KEEP_DEMO_MODELS", raising=False)
        command.upgrade(Config("alembic.ini"), "head")
        with isolated.connect() as db:
            assert db.scalar(sa.text("SELECT count(*) FROM modello_documento")) == 0
    finally:
        isolated.dispose()
        with engine.begin() as db:
            db.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_transition_rejects_version_under_wrong_parent_model(builder_client):
    first = _crea_modello(builder_client, codice="parent-a-" + uuid.uuid4().hex)
    second = _crea_modello(builder_client, codice="parent-b-" + uuid.uuid4().hex)
    version = _crea_versione(builder_client, first["id"])
    response = builder_client.post(f"/api/v1/builder/modelli/{second['id']}/versioni/{version['id']}/invia-revisione")
    assert response.status_code == 404, response.text


@pytest.mark.integration
def test_gestore_senza_il_contesto_del_tipo_documento_e_rifiutato(db_engine, monkeypatch):
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "geri-angular-public")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "altro-contesto-senza-ruoli")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_MANAGER#geban")

    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/builder/modelli",
                json={
                    "codice": "pytest-modello-non-autorizzato",
                    "nome": "Non autorizzato",
                    "codice_tipo_documento": "BANDO_CONCORSO",
                    "codice_categoria": "RICERCATORE",
                    "codice_tipologia": "TD",
                    "variante": "STANDARD",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["codice"] == "ACCESSO_NON_AUTORIZZATO"


@pytest.mark.integration
def test_gestore_di_un_contesto_non_puo_scrivere_su_un_tipo_documento_di_un_altro_contesto(
    db_engine, monkeypatch, tmp_path
):
    """DEC-001-CONTESTO-SOSTITUISCE-UFFICIO: nessun permission bleed fra contesti.

    Un token con contexts.geban.roles=ROLE_MANAGER#geban (gestore per BANDO_CONCORSO,
    contesto "geban") NON deve autorizzare la scrittura su un tipo documento il cui
    codice_contesto e' "contratti", anche se lo stesso token porta ANCHE il contesto
    "contratti" con un ruolo che in quel contesto vale solo per consultazione.
    """
    manifest = {
        "sistemi_richiedenti": [
            {
                "codice": "GEBAN",
                "nome": "GEBAN",
                "stato": "ATTIVO",
                "spec_owner": "specs/001-catalogo-contratto-geban",
                "client_applicativi": [
                    {
                        "client_id": "geri-angular-public",
                        "audience_attesa": "gemodo-backend",
                        "token_contexts": ["geban"],
                        "sistemi_abilitati": ["GEBAN"],
                        "stato": "ATTIVO",
                        "gestisce_credenziali": False,
                    }
                ],
                "profili_integrazione": [
                    {
                        "codice": "GEBAN_V1",
                        "sistema_richiedente": "GEBAN",
                        "versione": "1",
                        "stato": "ATTIVO",
                        "client_ammessi": ["geri-angular-public"],
                        "tipi_documento_ammessi": ["BANDO_CONCORSO"],
                        "categorie_ammessi": ["RICERCATORE"],
                        "tipologie_ammessi": ["TD"],
                        "modelli_versioni_ammessi": [],
                        "contratti_dati_ammessi": [],
                        "permessi_operativi": ["catalogo"],
                        "role_mappings": [
                            {
                                "token_context": "geban",
                                "external_role": "ROLE_MANAGER#geban",
                                "internal_permissions": ["GEMODO_MODELLI_GESTORE", "DOCUMENTI_VIEWER"],
                                "scope": ["builder"],
                            }
                        ],
                    }
                ],
            },
            {
                "codice": "CONTRATTI",
                "nome": "Ufficio contratti (test)",
                "stato": "ATTIVO",
                "spec_owner": "specs/001-catalogo-contratto-geban",
                "client_applicativi": [
                    {
                        "client_id": "geri-angular-public",
                        "audience_attesa": "gemodo-backend",
                        "token_contexts": ["contratti"],
                        "sistemi_abilitati": ["CONTRATTI"],
                        "stato": "ATTIVO",
                        "gestisce_credenziali": False,
                    }
                ],
                "profili_integrazione": [
                    {
                        "codice": "CONTRATTI_V1",
                        "sistema_richiedente": "CONTRATTI",
                        "versione": "1",
                        "stato": "ATTIVO",
                        "client_ammessi": ["geri-angular-public"],
                        "tipi_documento_ammessi": ["CONTRATTO"],
                        "categorie_ammessi": [],
                        "tipologie_ammessi": [],
                        "modelli_versioni_ammessi": [],
                        "contratti_dati_ammessi": [],
                        "permessi_operativi": ["catalogo"],
                        "role_mappings": [
                            {
                                "token_context": "contratti",
                                "external_role": "ROLE_VIEWER#contratti",
                                "internal_permissions": ["DOCUMENTI_VIEWER"],
                                "scope": ["consultazione"],
                            }
                        ],
                    }
                ],
            },
        ]
    }
    manifest_path = tmp_path / "integration-profiles.test.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "geri-angular-public")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "contratti")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_VIEWER#contratti")
    monkeypatch.setenv("GEMODO_INTEGRATION_PROFILES_PATH", str(manifest_path))

    session_factory = sessionmaker(bind=db_engine)
    tipo_contratto_id = uuid.uuid4()
    with Session(db_engine) as setup_session:
        setup_session.add(
            TipoDocumento(
                id=tipo_contratto_id,
                codice="CONTRATTO",
                nome="Contratto (test)",
                stato="ATTIVA",
                spec_owner="specs/002-builder-modelli",
                codice_contesto="contratti",
            )
        )
        setup_session.commit()

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/builder/tipi-documento/CONTRATTO/struttura-disponibile")
    finally:
        app.dependency_overrides.clear()
        # Il database e' condiviso fra i test di questa run (DATABASE_URL fissato per
        # l'intera sessione pytest): questo tipo documento sintetico non deve restare
        # visibile ad altri test (es. quelli che asseriscono l'elenco esatto dei tipi
        # documento reali).
        with Session(db_engine) as cleanup_session:
            cleanup_session.execute(sa.text("DELETE FROM tipo_documento WHERE id = :id"), {"id": tipo_contratto_id})
            cleanup_session.commit()

    # Il token ha contexts.contratti.roles=ROLE_VIEWER#contratti (solo DOCUMENTI_VIEWER
    # nel contesto "contratti", nessun GEMODO_MODELLI_GESTORE li') - anche avendo in
    # astratto un ruolo di gestore per il contesto "geban" nello stesso profilo GEBAN
    # sopra, quel ruolo non deve mai autorizzare una scrittura sul contesto "contratti".
    assert response.status_code == 403
    assert response.json()["codice"] == "ACCESSO_NON_AUTORIZZATO"
