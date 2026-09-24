"""API delle sezioni della versione modello (003 T006-T009).

Test HTTP reali contro PostgreSQL: nessuna logica simulata.
"""

from __future__ import annotations

import pytest

from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
    _crea_modello,
    _crea_versione,
    _pubblica_fino_in_fondo,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def url(modello_id: str, versione_id: str) -> str:
    return f"/api/v1/builder/modelli/{modello_id}/versioni/{versione_id}/sezioni"


def blocco(identificativo: str, *, ordine: int = 0, placeholder: list[str] | None = None) -> dict:
    return {
        "id": identificativo,
        "tipo": "PARAGRAFO",
        "contenuto": f"testo di {identificativo}",
        "posizionamento": "BODY",
        "ordine": ordine,
        "placeholder_usati": placeholder or [],
    }


@pytest.mark.integration
def test_una_bozza_accetta_composizione_riordino_e_rimozione(builder_client, catalogo_esterno):
    """Ogni invio e' la definizione completa: il riordino e' un invio, non una sequenza."""
    modello = _crea_modello(builder_client, codice="pytest-sezioni-bozza")
    versione = _crea_versione(builder_client, modello["id"])
    indirizzo = url(modello["id"], versione["id"])

    vuoto = builder_client.get(indirizzo)
    assert vuoto.status_code == 200, vuoto.text
    assert vuoto.json()["sezioni"] == []
    assert vuoto.json()["modificabile"] is True

    composto = builder_client.put(indirizzo, json={"sezioni": [
        {"codice": "premessa", "ordine": 10,
         "contenuto": [blocco("intro", placeholder=["codice_bando"])]},
        {"codice": "corpo", "ordine": 20, "contenuto": [blocco("dettaglio")]},
    ]})
    assert composto.status_code == 200, composto.text
    assert [s["codice"] for s in composto.json()["sezioni"]] == ["premessa", "corpo"]
    assert composto.json()["documento"]["placeholder_usati"] == ["codice_bando"]

    # Riordino: stesso insieme, ordini scambiati.
    riordinato = builder_client.put(indirizzo, json={"sezioni": [
        {"codice": "premessa", "ordine": 20,
         "contenuto": [blocco("intro", placeholder=["codice_bando"])]},
        {"codice": "corpo", "ordine": 10, "contenuto": [blocco("dettaglio")]},
    ]})
    assert riordinato.status_code == 200, riordinato.text
    assert [s["codice"] for s in riordinato.json()["sezioni"]] == ["corpo", "premessa"]

    # Un invio che omette una sezione la rimuove: e' una definizione completa.
    ridotto = builder_client.put(indirizzo, json={"sezioni": [
        {"codice": "corpo", "ordine": 10, "contenuto": [blocco("dettaglio")]},
    ]})
    assert ridotto.status_code == 200, ridotto.text
    assert [s["codice"] for s in ridotto.json()["sezioni"]] == ["corpo"]
    assert builder_client.get(indirizzo).json()["sezioni"][0]["codice"] == "corpo"


@pytest.mark.integration
def test_una_versione_pubblicata_non_si_modifica_ma_si_legge(builder_client, catalogo_esterno):
    """002 FR-005, finalmente messo alla prova da un percorso di scrittura che potrebbe violarlo."""
    modello = _crea_modello(builder_client, codice="pytest-sezioni-pubblicata")
    versione = _crea_versione(builder_client, modello["id"])
    indirizzo = url(modello["id"], versione["id"])
    builder_client.put(indirizzo, json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": [blocco("intro")]},
    ]})
    _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    rifiutato = builder_client.put(indirizzo, json={"sezioni": [
        {"codice": "riscritta", "ordine": 10, "contenuto": [blocco("nuovo")]},
    ]})
    assert rifiutato.status_code == 409, rifiutato.text
    assert rifiutato.json()["codice"] == "MODELLO_VERSIONE_NON_MODIFICABILE"

    # La lettura resta: vedere com'e' fatto un documento pubblicato e' lecito.
    letto = builder_client.get(indirizzo)
    assert letto.status_code == 200, letto.text
    assert [s["codice"] for s in letto.json()["sezioni"]] == ["premessa"]
    assert letto.json()["modificabile"] is False


@pytest.mark.integration
def test_due_sezioni_con_lo_stesso_codice_sono_rifiutate(builder_client, catalogo_esterno):
    modello = _crea_modello(builder_client, codice="pytest-sezioni-duplicate")
    versione = _crea_versione(builder_client, modello["id"])

    risposta = builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": []},
        {"codice": "premessa", "ordine": 20, "contenuto": []},
    ]})
    assert risposta.status_code == 400, risposta.text


@pytest.mark.integration
def test_un_blocco_di_tipo_sconosciuto_non_entra(builder_client, catalogo_esterno):
    """Il documento e' una struttura controllata: niente contenuto arbitrario."""
    modello = _crea_modello(builder_client, codice="pytest-sezioni-blocco-invalido")
    versione = _crea_versione(builder_client, modello["id"])

    risposta = builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": [
            {"id": "x", "tipo": "SCRIPT_ARBITRARIO", "posizionamento": "BODY"},
        ]},
    ]})
    assert risposta.status_code == 400, risposta.text


@pytest.mark.integration
def test_la_versione_deve_appartenere_al_modello_indicato(builder_client, catalogo_esterno):
    """Senza il controllo, un id di versione noto basterebbe a scavalcare l'autorizzazione dell'URL."""
    primo = _crea_modello(builder_client, codice="pytest-sezioni-primo")
    secondo = _crea_modello(builder_client, codice="pytest-sezioni-secondo", lingua="EN")
    versione_del_secondo = _crea_versione(builder_client, secondo["id"])

    risposta = builder_client.get(url(primo["id"], versione_del_secondo["id"]))
    assert risposta.status_code == 404, risposta.text
    assert risposta.json()["codice"] == "MODELLO_VERSIONE_NON_TROVATO"


@pytest.mark.integration
def test_una_versione_nuova_eredita_le_sezioni_della_precedente(builder_client, catalogo_esterno):
    """003 T004 attraverso le API: la nuova versione parte da com'era il documento."""
    modello = _crea_modello(builder_client, codice="pytest-sezioni-eredita")
    prima = _crea_versione(builder_client, modello["id"])
    builder_client.put(url(modello["id"], prima["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": [blocco("intro")]},
    ]})

    derivata = builder_client.post(
        f"/api/v1/builder/modelli/{modello['id']}/edizioni-derivate", json={"lingua": "EN"},
    )
    assert derivata.status_code == 201, derivata.text
    nuovo_modello = derivata.json()
    dettaglio = builder_client.get(f"/api/v1/builder/modelli/{nuovo_modello['id']}").json()
    nuova_versione = dettaglio["versioni"][0]

    sezioni = builder_client.get(url(nuovo_modello["id"], nuova_versione["id"]))
    assert sezioni.status_code == 200, sezioni.text
    assert [s["codice"] for s in sezioni.json()["sezioni"]] == ["premessa"]
