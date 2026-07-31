from __future__ import annotations

from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.catalog.schemas import ModalitaCatalogo
from app.catalog.service import CatalogService
from app.common.errors import ApiError
from tests.support.postgres import postgres_database_url


@pytest.mark.integration
def test_catalog_service_reads_seeded_catalog(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)

            tipi = service.list_tipi_documento()
            categorie = service.list_categorie("BANDO_CONCORSO")
            modelli = service.search_modelli(
                tipo_documento="BANDO_CONCORSO",
                categoria="DEMO",
                modalita=ModalitaCatalogo.OPERATIVA,
            )
    finally:
        engine.dispose()

    assert [item.codice for item in tipi.items] == ["BANDO_CONCORSO"]
    assert [item.codice for item in categorie.categorie] == ["DEMO"]
    assert len(modelli.modelli) == 1
    assert modelli.modelli[0].modello_versione_id == 1
    assert modelli.modelli[0].stato == "PUBBLICATO"


@pytest.mark.integration
def test_catalog_service_rejects_unconfigured_tipologia_sol(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)
            with pytest.raises(ApiError) as exc_info:
                service.search_modelli(tipo_documento="BANDO_CONCORSO", codice_tipologia="NON_CONFIGURATA")
    finally:
        engine.dispose()

    assert exc_info.value.codice == "TIPOLOGIA_SOL_NON_VALIDA"


@pytest.mark.integration
def test_catalog_service_returns_empty_list_when_no_model_matches_context(postgres_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(postgres_database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = CatalogService(session)
            response = service.search_modelli(tipo_documento="BANDO_CONCORSO", categoria="NON_CONFIGURATA")
    finally:
        engine.dispose()

    assert response.tipo_documento == "BANDO_CONCORSO"
    assert response.categoria == "NON_CONFIGURATA"
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
                tipo_documento="BANDO_CONCORSO",
                modalita=ModalitaCatalogo.STORICO,
                pubblicato_da=date.fromisoformat("2026-07-01"),
                pubblicato_a=date.fromisoformat("2026-07-31"),
            )
            not_matching = service.search_modelli(
                tipo_documento="BANDO_CONCORSO",
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
            response = service.get_campi_richiesti(1)
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
