"""Storico di un modello e autore nell'elenco (richiesta dell'utente 2026-10-07).

Test HTTP reali contro PostgreSQL: gli eventi letti sono quelli che il builder
scrive davvero, non righe inserite a mano.
"""

from __future__ import annotations

import uuid

import pytest

from app.common.security import PrincipalGEMODO, require_principal
from app.main import app
from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    _crea_modello,
    _crea_versione,
    _pubblica_fino_in_fondo,
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.builder.test_sezioni_api import blocco, url
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def _storico(client, modello_id: str):
    return client.get(f"/api/v1/builder/modelli/{modello_id}/storico")


@pytest.mark.integration
def test_lo_storico_dice_chi_ha_fatto_cosa_su_quale_versione(builder_client, catalogo_esterno):
    modello = _crea_modello(builder_client, codice="pytest-storico")
    versione = _crea_versione(builder_client, modello["id"])
    indirizzo = url(modello["id"], versione["id"])
    assert builder_client.put(indirizzo, json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": [blocco("intro")]},
        {"codice": "corpo", "ordine": 20, "contenuto": [blocco("dettaglio")]},
    ]}).status_code == 200
    # Secondo salvataggio: una sezione cambia, una sparisce, una nasce.
    assert builder_client.put(indirizzo, json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": [blocco("intro-rivista")]},
        {"codice": "allegati", "ordine": 30, "contenuto": [blocco("elenco")]},
    ]}).status_code == 200
    _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    risposta = _storico(builder_client, modello["id"])

    assert risposta.status_code == 200, risposta.text
    corpo = risposta.json()
    assert corpo["modello_id"] == modello["id"]
    eventi = corpo["eventi"]
    # Dal piu' recente: la pubblicazione chiude, la creazione apre.
    assert eventi[0]["azione"] == "VERSIONE_PUBBLICATO"
    assert eventi[0]["descrizione"] == "Pubblicata"
    assert eventi[-1]["azione"] == "MODELLO_VARIANTE_CREATA" or eventi[-1]["azione"] == "MODELLO_CREATO"
    modifiche = [e for e in eventi if e["azione"] == "SEZIONI_AGGIORNATE"]
    assert len(modifiche) == 2
    ultima = modifiche[0]
    assert ultima["dettaglio"]["aggiunte"] == ["allegati"]
    assert ultima["dettaglio"]["modificate"] == ["premessa"]
    assert ultima["dettaglio"]["rimosse"] == ["corpo"]
    assert "modificate: premessa" in ultima["descrizione"]
    assert all(e["versione"] == 1 for e in eventi if e["azione"].startswith("VERSIONE_") or e in modifiche)
    # L'utente e il canale: il client di prova non e' quello di login di GEMODO.
    assert {e["utente"] for e in eventi} == {eventi[0]["utente"]}
    assert all(e["canale"] == "API" and e["client_id"] == "geri-angular-public" for e in eventi)


@pytest.mark.integration
def test_lo_storico_include_le_generazioni_dalle_versioni_del_modello(builder_client, catalogo_esterno):
    from tests.builder.test_builder_flow_api import CAMPI_BASE  # noqa: F401

    modello = _crea_modello(builder_client, codice="pytest-storico-genera")
    versione = _crea_versione(builder_client, modello["id"])
    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])
    chiave = uuid.uuid4().hex[:12]
    generato = builder_client.post("/api/v1/documenti/genera", json={
        "sistema_richiedente": "PYTEST",
        "external_context_id": chiave,
        "modello_versione_id": pubblicata["public_id"],
        "dati": {"codice_bando": "B-1", "titolo_it": "T", "sede_prescelta_it": "Roma",
                 "numero_posti": 1, "titolo_en": "T", "livello": "III"},
    })
    assert generato.status_code == 200, generato.text

    eventi = _storico(builder_client, modello["id"]).json()["eventi"]

    generazioni = [e for e in eventi if e["azione"].startswith(("DOCUMENTO_", "GENERAZIONE_"))]
    assert len(generazioni) == 1
    assert generazioni[0]["versione"] == 1
    assert generazioni[0]["dettaglio"]["external_context_id"] == chiave
    assert chiave in generazioni[0]["descrizione"]


@pytest.mark.integration
def test_lo_storico_e_solo_per_gli_amministratori(builder_client, catalogo_esterno):
    modello = _crea_modello(builder_client, codice="pytest-storico-gestore")
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "solo-gestore", "geri-angular-public", ("gemodo-backend",), ("GEMODO_MODELLI_GESTORE",),
        "https://sso.example.test", ruoli_diretti=(),
        ruoli_contesto=(("geban", ("ROLE_MANAGER",)),),
        permessi_contesto=(("geban", ("GEMODO_MODELLI_GESTORE",)),),
    )
    try:
        assert _storico(builder_client, modello["id"]).status_code == 403
    finally:
        app.dependency_overrides.pop(require_principal, None)


@pytest.mark.integration
def test_l_elenco_dei_modelli_dice_chi_ha_creato_ciascuno(builder_client, catalogo_esterno):
    modello = _crea_modello(builder_client, codice="pytest-creato-da")
    autore = _storico(builder_client, modello["id"]).json()["eventi"][-1]["utente"]

    elenco = builder_client.get("/api/v1/builder/modelli", params={"codice_contesto": "geban", "limit": 100})

    assert elenco.status_code == 200, elenco.text
    riga = next(m for m in elenco.json() if m["id"] == modello["id"])
    assert riga["creato_da"] == autore


@pytest.mark.integration
def test_un_modello_inesistente_non_ha_storico(builder_client):
    assert _storico(builder_client, str(uuid.uuid4())).status_code == 404
