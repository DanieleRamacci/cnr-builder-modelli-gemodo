from __future__ import annotations

from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.catalog.schemas import ModalitaCatalogo
from app.catalog.service import CatalogService
from app.common.security import PrincipalGEMODO
from tests.support.postgres import postgres_database_url

PRINCIPAL = PrincipalGEMODO(
    "viewer-test", "geban-backend", ("gemodo-backend",), ("DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE"),
    "https://sso.example.test",
)


@pytest.mark.integration
def test_catalog_service_reads_seeded_catalog(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)

            modelli = service.search_modelli(
                principal=PRINCIPAL,
                tipo_documento="BANDO_CONCORSO",
                categoria="COLLABORATORE_TECNICO_ER",
                codice_tipologia="TD",
                modalita=ModalitaCatalogo.OPERATIVA,
            )
            modelli_cp = service.search_modelli(
                principal=PRINCIPAL,
                tipo_documento="BANDO_CONCORSO",
                categoria="COLLABORATORE_TECNICO_ER",
                codice_tipologia="CP",
                modalita=ModalitaCatalogo.OPERATIVA,
            )
    finally:
        engine.dispose()

    assert len(modelli.modelli) == 1
    assert modelli.modelli[0].modello_versione_id == 1
    assert modelli.modelli[0].stato == "PUBBLICATO"
    assert len(modelli_cp.modelli) == 1
    assert modelli_cp.modelli[0].modello_versione_id == 3


@pytest.mark.integration
def test_catalog_service_filters_without_local_typology_allowlist(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)
            response = service.search_modelli(principal=PRINCIPAL, tipo_documento="BANDO_CONCORSO", codice_tipologia="NON_CONFIGURATA")
    finally:
        engine.dispose()

    assert response.modelli == []


@pytest.mark.integration
def test_catalog_service_returns_empty_list_when_no_model_matches_context(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)
            response = service.search_modelli(principal=PRINCIPAL, tipo_documento="BANDO_CONCORSO", categoria="NON_CONFIGURATA")
    finally:
        engine.dispose()

    assert response.tipo_documento == "BANDO_CONCORSO"
    assert response.profilo == "NON_CONFIGURATA"
    assert response.modelli == []


@pytest.mark.integration
def test_catalog_service_filters_historical_models_by_publication_dates(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)
            matching = service.search_modelli(
                principal=PRINCIPAL,
                tipo_documento="BANDO_CONCORSO",
                categoria="COLLABORATORE_TECNICO_ER",
                codice_tipologia="TD",
                modalita=ModalitaCatalogo.STORICO,
                pubblicato_da=date.fromisoformat("2026-07-01"),
                pubblicato_a=date.fromisoformat("2026-07-31"),
            )
            not_matching = service.search_modelli(
                principal=PRINCIPAL,
                tipo_documento="BANDO_CONCORSO",
                categoria="COLLABORATORE_TECNICO_ER",
                codice_tipologia="TD",
                modalita=ModalitaCatalogo.STORICO,
                pubblicato_da=date.fromisoformat("2026-08-01"),
            )
    finally:
        engine.dispose()

    assert [item.modello_versione_id for item in matching.modelli] == [1]
    assert not_matching.modelli == []


@pytest.mark.integration
def test_catalog_service_returns_required_fields_contract(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)
            response = service.get_campi_richiesti(1, PRINCIPAL)
    finally:
        engine.dispose()

    assert response.modello_versione_id == 1
    assert response.tipo_documento == "BANDO_CONCORSO"
    assert [field.codice for field in response.campi] == [
        "codice_bando",
        "titolo_it",
        "descrizione_ridotta_it",
        "sede_prescelta_it",
        "numero_posti",
        "titolo_en",
    ]
    assert response.campi[-1].lingua == "EN"
    assert response.schema_["additionalProperties"] is False
    assert "titolo_en" not in response.schema_["required"]
