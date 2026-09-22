"""Eliminazione logica e riuso: 010 FR-029 e 002 FR-018.

Entrambi i difetti coperti qui sono stati trovati il 2026-09-22 rispondendo a una
domanda operativa - "se creo dati di prova, posso poi ripulire e ripartire?" - e
riprodotti end-to-end prima di essere corretti:

- l'eliminazione di un modello e' logica, ma il conteggio che protegge la
  disattivazione di un tipo documento includeva anche le righe ``ELIMINATO``:
  dopo il primo modello un tipo non era piu' disattivabile, mai;
- il vincolo unico ``uq_modello_derivato_padre_lingua`` non escludeva gli
  eliminati mentre il codice applicativo si', quindi ricreare un'edizione
  derivata dopo averla eliminata restituiva HTTP 500 invece di riuscire.

I test girano su PostgreSQL reale e passano dalle API HTTP.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.catalog.models import ModelloDocumento, TipoDocumento
from app.common.security import PrincipalGEMODO, require_principal
from app.configurazione import repository as configurazione_repository
from app.main import app

from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    CAMPI_BASE,
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def _disattiva_tipo(client, tipo_id: str):
    """Disattiva un tipo documento impersonando un GEMODO_ADMIN.

    Il ``builder_client`` porta ROLE_MANAGER nel contesto: autorizza la gestione
    dei modelli, non l'amministrazione. Serve quindi il ruolo amministrativo solo
    per questa chiamata, e va rimesso a posto subito dopo: un override permanente
    toglierebbe al builder il proprio contesto e i suoi POST diventerebbero 403.
    """
    precedente = app.dependency_overrides.get(require_principal)
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "admin-pulizia", "gemodo-frontend", ("gemodo-backend",), ("GEMODO_ADMIN",),
        "https://sso.example.test", ruoli_diretti=("GEMODO_ADMIN",),
    )
    try:
        return client.delete(f"/api/v1/configurazione/tipi-documento/id/{tipo_id}")
    finally:
        if precedente is None:
            app.dependency_overrides.pop(require_principal, None)
        else:
            app.dependency_overrides[require_principal] = precedente


def _crea_modello(client, *, lingua: str = "IT", livello: str | None = None) -> dict:
    response = client.post(
        "/api/v1/builder/modelli",
        json={
            "codice_tipo_documento": "BANDO_CONCORSO",
            "codice_categoria": "RICERCATORE",
            "codice_tipologia": "TD",
            "lingua": lingua,
            "livello_professionale": livello,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _pubblica(client, modello_id: str) -> str:
    versione = client.post(
        f"/api/v1/builder/modelli/{modello_id}/versioni", json={"campi": CAMPI_BASE}
    )
    assert versione.status_code == 201, versione.text
    versione_id = versione.json()["id"]
    for azione in ("invia-revisione", "approva", "pubblica"):
        esito = client.post(
            f"/api/v1/builder/modelli/{modello_id}/versioni/{versione_id}/{azione}"
        )
        assert esito.status_code == 200, esito.text
    return versione_id


def _tipo_id(db_engine) -> str:
    with Session(db_engine) as db:
        return str(db.scalar(sa.select(TipoDocumento.id).where(TipoDocumento.codice == "BANDO_CONCORSO")))


@pytest.fixture()
def tipo_isolato(db_engine):
    """Un tipo documento senza i modelli demo seedati dalle migration.

    Il database di test contiene modelli demo con id deterministici, attivi e
    legati a BANDO_CONCORSO: usarlo qui renderebbe il 409 finale legittimo e
    nasconderebbe proprio il comportamento da osservare.
    """
    tipo_id = uuid.uuid4()
    with Session(db_engine) as db:
        db.execute(sa.insert(TipoDocumento).values(
            id=tipo_id, codice=f"TIPO_PULIZIA_{tipo_id.hex[:8]}", nome="Tipo per pulizia",
            codice_contesto="geban", stato="ATTIVA", spec_owner="specs/010-configurazione-cataloghi-integrazioni",
        ))
        db.commit()
    yield tipo_id
    with Session(db_engine) as db:
        # L'audit della disattivazione referenzia il tipo e la sua FK non e' in
        # CASCADE: va rimosso prima. E' lo stesso ostacolo che incontrera' il
        # reset previsto da 010 T104.
        db.execute(
            sa.text("DELETE FROM audit_evento_configurazione WHERE tipo_documento_id = :id"),
            {"id": tipo_id},
        )
        db.execute(sa.delete(ModelloDocumento).where(ModelloDocumento.tipo_documento_id == tipo_id))
        db.execute(sa.delete(TipoDocumento).where(TipoDocumento.id == tipo_id))
        db.commit()


def _inserisci_modello(db_engine, tipo_id, *, stato: str, lingua: str = "IT") -> uuid.UUID:
    modello_id = uuid.uuid4()
    with Session(db_engine) as db:
        db.execute(sa.insert(ModelloDocumento).values(
            id=modello_id, tipo_documento_id=tipo_id, codice_categoria="RICERCATORE",
            codice_tipologia="TD", percorso_categorizzazione=["TD", "RICERCATORE"],
            codice=f"modello-{modello_id.hex[:12]}", nome="Modello di prova",
            variante="STANDARD", lingua=lingua, stato=stato,
        ))
        db.commit()
    return modello_id


@pytest.mark.integration
def test_un_modello_eliminato_non_blocca_la_disattivazione(builder_client, db_engine, tipo_isolato):
    """010 FR-029: restando solo modelli eliminati, il tipo torna disattivabile."""
    _inserisci_modello(db_engine, tipo_isolato, stato="ELIMINATO")

    risposta = _disattiva_tipo(builder_client, str(tipo_isolato))

    assert risposta.status_code == 204, (
        "un modello eliminato non deve bloccare la disattivazione: " + risposta.text
    )
    with Session(db_engine) as db:
        assert db.scalar(sa.select(TipoDocumento.stato).where(TipoDocumento.id == tipo_isolato)) == "INATTIVA"


@pytest.mark.integration
def test_un_modello_vivo_blocca_ancora_la_disattivazione(builder_client, db_engine, tipo_isolato):
    """La correzione non deve indebolire la protezione: un modello usabile blocca."""
    _inserisci_modello(db_engine, tipo_isolato, stato="ELIMINATO")
    _inserisci_modello(db_engine, tipo_isolato, stato="ATTIVA", lingua="EN")

    risposta = _disattiva_tipo(builder_client, str(tipo_isolato))

    assert risposta.status_code == 409, "un modello ancora utilizzabile deve bloccare"
    assert risposta.json()["codice"] == "TIPO_DOCUMENTO_HA_MODELLI"


@pytest.mark.integration
def test_conta_modelli_ignora_gli_eliminati(db_engine, tipo_isolato):
    """Il conteggio che protegge la disattivazione, osservato direttamente."""
    _inserisci_modello(db_engine, tipo_isolato, stato="ELIMINATO")
    with Session(db_engine) as db:
        assert configurazione_repository.conta_modelli(db, tipo_isolato) == 0
    _inserisci_modello(db_engine, tipo_isolato, stato="ATTIVA", lingua="EN")
    with Session(db_engine) as db:
        assert configurazione_repository.conta_modelli(db, tipo_isolato) == 1


@pytest.mark.integration
def test_edizione_derivata_ricreabile_dopo_eliminazione(builder_client, db_engine):
    """002 FR-018: eliminare un'edizione libera davvero la coppia (origine, lingua)."""
    origine = _crea_modello(builder_client)
    _pubblica(builder_client, origine["id"])

    prima = builder_client.post(
        f"/api/v1/builder/modelli/{origine['id']}/edizioni-derivate", json={"lingua": "EN"}
    )
    assert prima.status_code == 201, prima.text

    duplicata = builder_client.post(
        f"/api/v1/builder/modelli/{origine['id']}/edizioni-derivate", json={"lingua": "EN"}
    )
    assert duplicata.status_code == 409, "finche' e' viva, la seconda e' un duplicato"
    assert duplicata.json()["codice"] == "EDIZIONE_DERIVATA_DUPLICATA"

    assert builder_client.delete(
        f"/api/v1/builder/modelli/{prima.json()['id']}"
    ).status_code == 204

    dopo = builder_client.post(
        f"/api/v1/builder/modelli/{origine['id']}/edizioni-derivate", json={"lingua": "EN"}
    )
    assert dopo.status_code == 201, (
        "ricreare l'edizione dopo l'eliminazione deve riuscire, non dare 500: " + dopo.text
    )
    assert dopo.json()["id"] != prima.json()["id"]

    with Session(db_engine) as db:
        db.execute(
            sa.delete(ModelloDocumento).where(
                ModelloDocumento.derivato_da_modello_id == origine["id"]
            )
        )
        db.execute(sa.delete(ModelloDocumento).where(ModelloDocumento.id == origine["id"]))
        db.commit()
