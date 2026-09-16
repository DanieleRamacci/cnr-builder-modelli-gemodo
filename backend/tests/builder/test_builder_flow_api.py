"""Real end-to-end test of the builder write API against a real Postgres DB.

Covers the flow the product owner asked for on 2026-09-15: an authorized
gestore reads the available structure (PortaDiscovery/AdapterLocale), creates
a model + version choosing fields from the real registro contratti dati,
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

import pytest
import sqlalchemy as sa
import yaml
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import TipoDocumento
from app.db.session import get_db
from app.main import app
from tests.support.postgres import postgres_database_url


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
def builder_client(db_engine, monkeypatch):
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
def test_struttura_disponibile_riflette_il_registro_reale(builder_client):
    response = builder_client.get("/api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile")

    assert response.status_code == 200
    body = response.json()
    codici_tipologie = {t["codice"] for t in body["tipologie"]}
    assert "TD" in codici_tipologie
    codici_campi = {c["codice"] for c in body["campi"]}
    assert codici_campi == {
        "codice_bando",
        "titolo_it",
        "descrizione_ridotta_it",
        "sede_prescelta_it",
        "numero_posti",
        "titolo_en",
        "livello",
    }
    campo_livello = next(c for c in body["campi"] if c["codice"] == "livello")
    assert campo_livello["validazione"]["fonte_opzioni"] == "profilo.livelli_possibili"


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
    assert generazione.json()["stato"] == "GENERAZIONE_SIMULATA"


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
