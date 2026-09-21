"""Per-context authorization for consumer APIs (001 FR-034..038, 006 FR-014..017).

Gated behind GEMODO_ENFORCE_CONTESTO_CONSUMATORE (default off, see
backend/app/common/security.py:verifica_permesso_contesto). These tests turn it on
explicitly and use the REAL default manifest (infra/local/integration-profiles.local.yaml)
with the exact JWT shape ACE issues (contexts.<nome>.roles), not a mocked permission
check - "ROLE_COORDINATOR#geban" is a real external role from that manifest.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.common.security import PrincipalGEMODO, require_principal
from app.core.settings import get_settings
from app.db.session import get_db
from app.main import app
from app.quality.integration_profile import load_sistemi_richiedenti, permessi_da_ruoli_esterni
from tests.support.postgres import postgres_database_url

CLIENT_ID = "geban-backend"


@pytest.fixture()
def db_engine(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    monkeypatch.setenv("GEMODO_ENFORCE_CONTESTO_CONSUMATORE", "true")
    command.upgrade(Config("alembic.ini"), "head")
    engine = sa.create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


def _crea_versione(db_engine, *, codice_contesto: str, stato="PUBBLICATO"):
    suffix = uuid.uuid4().hex[:12]
    public_id = uuid.uuid4().int % 900_000_000 + 100_000_000
    modello_public_id = uuid.uuid4().int % 900_000_000 + 100_000_000
    with Session(db_engine) as db:
        tipo = TipoDocumento(codice="CTX_" + suffix, nome="Tipo per test contesto", stato="ATTIVA",
                             spec_owner="specs/001-catalogo-contratto-geban", codice_contesto=codice_contesto)
        db.add(tipo)
        db.flush()
        modello = ModelloDocumento(tipo_documento_id=tipo.id, codice_categoria="DEMO",
                                   percorso_categorizzazione=["DEMO"], codice="MOD_" + suffix,
                                   nome="Modello per test contesto", stato="PUBBLICATO",
                                   public_id=modello_public_id)
        db.add(modello)
        db.flush()
        versione = ModelloDocumentoVersione(modello_documento_id=modello.id, versione=1, stato=stato,
                                            struttura_documentale={}, public_id=public_id)
        db.add(versione)
        db.flush()
        db.add(ModelloCampoRichiesto(modello_versione_id=versione.id, codice="titolo", etichetta="Titolo",
                                     tipo_dato="string", obbligatorio=True, lingua="IT", ordine=1))
        db.commit()
        return {"codice_tipo": tipo.codice, "versione_id": versione.id, "public_id": public_id}


@pytest.fixture()
def client(db_engine):
    session_factory = sessionmaker(bind=db_engine)

    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _principal(*ruoli_contesto: tuple[str, tuple[str, ...]]) -> PrincipalGEMODO:
    """Build a principal the way ``_principal_from_payload`` would for a real ACE token:

    ``ruoli`` is the aggregate of ``ruoli_contesto`` resolved against the real default
    manifest (same client the route-level ``require_documenti_viewer``/``_generatore``
    dependency checks), kept separate from the per-context breakdown that
    ``verifica_permesso_contesto`` uses. Passing an empty ``ruoli`` here would make every
    request 403 at the coarse dependency, before ever reaching the per-context check
    these tests exist to exercise.
    """
    settings = get_settings()
    sistemi = list(load_sistemi_richiedenti(Path(settings.integration_profiles_path)))
    ruoli = tuple(sorted(permessi_da_ruoli_esterni(
        sistemi, client_id=CLIENT_ID, context_roles=dict(ruoli_contesto),
    )))
    return PrincipalGEMODO(
        "coordinatore-test", CLIENT_ID, ("gemodo-backend",), ruoli, "https://sso.example.test",
        ruoli_contesto=ruoli_contesto,
    )


def _as(client, principal):
    app.dependency_overrides[require_principal] = lambda: principal
    return client


def _payload(public_id: int, contesto_suffix: str):
    return {
        "sistema_richiedente": "GEBAN", "external_context_id": f"ctx-{contesto_suffix}-{uuid.uuid4().hex[:8]}",
        "modello_versione_id": public_id, "dati": {"titolo": "Prova"},
    }


@pytest.mark.integration
def test_catalog_search_allows_own_context_denies_other(db_engine, client):
    geban = _crea_versione(db_engine, codice_contesto="geban")
    altro = _crea_versione(db_engine, codice_contesto="altro-contesto-senza-ruoli")
    principal = _principal(("geban", ("ROLE_COORDINATOR#geban",)))

    consentito = _as(client, principal).get(f"/api/v1/catalogo/modelli?tipo_documento={geban['codice_tipo']}")
    assert consentito.status_code == 200, consentito.text
    assert len(consentito.json()["modelli"]) == 1

    vietato = _as(client, principal).get(f"/api/v1/catalogo/modelli?tipo_documento={altro['codice_tipo']}")
    assert vietato.status_code == 403, vietato.text
    assert vietato.json()["codice"] == "ACCESSO_NON_AUTORIZZATO"


@pytest.mark.integration
def test_campi_richiesti_out_of_context_is_indistinguishable_from_not_found(db_engine, client):
    altro = _crea_versione(db_engine, codice_contesto="altro-contesto-senza-ruoli")
    principal = _principal(("geban", ("ROLE_COORDINATOR#geban",)))

    fuori_contesto = _as(client, principal).get(f"/api/v1/catalogo/modelli/{altro['public_id']}/campi-richiesti")
    inesistente = _as(client, principal).get("/api/v1/catalogo/modelli/999999999/campi-richiesti")
    assert fuori_contesto.status_code == inesistente.status_code == 404
    assert fuori_contesto.json() == inesistente.json()
    assert fuori_contesto.json()["codice"] == "MODELLO_VERSIONE_NON_TROVATO"


@pytest.mark.integration
def test_valida_e_genera_negano_accesso_fuori_contesto(db_engine, client):
    altro = _crea_versione(db_engine, codice_contesto="altro-contesto-senza-ruoli")
    principal = _principal(("geban", ("ROLE_COORDINATOR#geban",)))
    payload = _payload(altro["public_id"], "fuori")

    valida = _as(client, principal).post("/api/v1/documenti/valida", json=payload)
    assert valida.status_code == 404, valida.text
    assert valida.json()["codice"] == "MODELLO_VERSIONE_NON_TROVATO"

    genera = _as(client, principal).post("/api/v1/documenti/genera", json=payload)
    assert genera.status_code == 404, genera.text
    assert genera.json()["codice"] == "MODELLO_VERSIONE_NON_TROVATO"


@pytest.mark.integration
def test_genera_e_download_funzionano_nel_proprio_contesto(db_engine, client):
    geban = _crea_versione(db_engine, codice_contesto="geban")
    principal = _principal(("geban", ("ROLE_COORDINATOR#geban",)))
    payload = _payload(geban["public_id"], "geban")

    esito = _as(client, principal).post("/api/v1/documenti/genera", json=payload)
    assert esito.status_code == 200, esito.text
    assert esito.headers["content-type"] == "application/pdf"
    riferimento = esito.headers["x-riferimento-documentale"]
    assert riferimento

    stato = _as(client, principal).get(f"/api/v1/documenti/{riferimento}")
    assert stato.status_code == 200, stato.text
    download = _as(client, principal).get(f"/api/v1/documenti/{riferimento}/download")
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")

    # A caller who genuinely holds DOCUMENTI_VIEWER/GENERATORE (so the coarse route
    # dependency lets them through, unlike test_ruoli_diretti_senza_contesto_sono_negati)
    # but no role at all in "geban" - the manifest only maps roles for "geban", so this
    # must be built directly rather than via _principal(), which would zero out `ruoli`
    # for any context/role combo the manifest doesn't resolve.
    estraneo = PrincipalGEMODO(
        "estraneo-test", CLIENT_ID, ("gemodo-backend",), ("DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE"),
        "https://sso.example.test", ruoli_diretti=("DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE"),
        ruoli_contesto=(("altro-contesto-senza-ruoli", ("ROLE_COORDINATOR#geban",)),),
    )
    stato_negato = _as(client, estraneo).get(f"/api/v1/documenti/{riferimento}")
    download_negato = _as(client, estraneo).get(f"/api/v1/documenti/{riferimento}/download")
    assert stato_negato.status_code == 404
    assert download_negato.status_code == 404
    assert stato_negato.json()["codice"] == "DOCUMENTO_NON_TROVATO"


@pytest.mark.integration
def test_token_multicontesto_non_bleeda_permessi_tra_contesti(db_engine, client):
    """Un ruolo valido in 'geban' non deve autorizzare un modello di un contesto diverso,
    anche se lo stesso token porta ANCHE quel secondo contesto (con un ruolo che li' non
    e' mappato a nulla di utile) - DEC-001-CONTESTO-SOSTITUISCE-UFFICIO applicato ai
    consumatori, non solo al builder."""
    geban = _crea_versione(db_engine, codice_contesto="geban")
    altro = _crea_versione(db_engine, codice_contesto="altro-contesto-senza-ruoli")
    principal = _principal(
        ("geban", ("ROLE_COORDINATOR#geban",)),
        ("altro-contesto-senza-ruoli", ("ROLE_SCONOSCIUTO#altro",)),
    )

    ok = _as(client, principal).get(f"/api/v1/catalogo/modelli/{geban['public_id']}/campi-richiesti")
    assert ok.status_code == 200, ok.text

    negato = _as(client, principal).get(f"/api/v1/catalogo/modelli/{altro['public_id']}/campi-richiesti")
    assert negato.status_code == 404


@pytest.mark.integration
def test_ruoli_diretti_senza_contesto_sono_negati(db_engine, client):
    """FR-036: contesto assente MUST negare, senza fallback ai permessi aggregati -
    un principal senza alcun ruoli_contesto (solo ruoli diretti sul client) non supera
    il controllo anche se possiede DOCUMENTI_VIEWER/GENERATORE a livello di token."""
    geban = _crea_versione(db_engine, codice_contesto="geban")
    principal = PrincipalGEMODO(
        "diretto-test", CLIENT_ID, ("gemodo-backend",), ("DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE"),
        "https://sso.example.test", ruoli_diretti=("DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE"),
    )

    response = _as(client, principal).get(f"/api/v1/catalogo/modelli/{geban['public_id']}/campi-richiesti")
    assert response.status_code == 404, response.text


@pytest.mark.integration
def test_flag_disattivato_preserva_il_comportamento_odierno(db_engine, client, monkeypatch):
    monkeypatch.setenv("GEMODO_ENFORCE_CONTESTO_CONSUMATORE", "false")
    altro = _crea_versione(db_engine, codice_contesto="altro-contesto-senza-ruoli")
    principal = _principal(("geban", ("ROLE_COORDINATOR#geban",)))

    response = _as(client, principal).get(f"/api/v1/catalogo/modelli/{altro['public_id']}/campi-richiesti")
    assert response.status_code == 200, response.text
