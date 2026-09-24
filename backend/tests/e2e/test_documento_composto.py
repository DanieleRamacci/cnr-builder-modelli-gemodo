"""Dal modello composto al PDF con i valori dentro (003 T018/T019/T021).

Percorso intero su PostgreSQL reale e HTTP: compone le sezioni, pubblica,
genera, e legge il PDF prodotto.

Il testo si cerca nei **byte grezzi** del PDF: `renderer` usa `compress=False`
proprio per restare ispezionabile, quindi non serve una libreria di lettura
PDF in piu' solo per verificare cosa c'e' scritto.
"""

from __future__ import annotations

import uuid

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


def sezioni_del_bando() -> list[dict]:
    return [
        {"codice": "intestazione", "ordine": 10, "contenuto": [
            {"id": "titolo", "tipo": "TITOLO",
             "contenuto": "Bando di concorso {{codice_bando}}",
             "posizionamento": "TOP", "ordine": 0,
             "placeholder_usati": ["codice_bando"]},
        ]},
        {"codice": "corpo", "ordine": 20, "contenuto": [
            {"id": "oggetto", "tipo": "PARAGRAFO",
             "contenuto": "E' indetto il concorso {{titolo_it}} presso {{sede_prescelta_it}}.",
             "posizionamento": "BODY", "ordine": 0,
             "placeholder_usati": ["titolo_it", "sede_prescelta_it"]},
            {"id": "posti", "tipo": "PARAGRAFO",
             "contenuto": "I posti messi a concorso sono {{numero_posti}}.",
             "posizionamento": "BODY", "ordine": 1,
             "placeholder_usati": ["numero_posti"]},
        ]},
    ]


def dati_completi() -> dict:
    return {
        "codice_bando": "BND-2026-0042",
        "titolo_it": "Ricercatore in fisica applicata",
        "sede_prescelta_it": "Area della Ricerca di Roma 1",
        "numero_posti": 7,
        "titolo_en": "Researcher in applied physics",
        "livello": "VI",
    }


@pytest.mark.integration
def test_il_pdf_contiene_il_testo_composto_con_i_valori_sostituiti(builder_client, catalogo_esterno):
    """Il punto di arrivo della `003`: un bando, non una scheda dati."""
    modello = _crea_modello(builder_client, codice="pytest-e2e-composto")
    versione = _crea_versione(builder_client, modello["id"])
    composto = builder_client.put(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/sezioni",
        json={"sezioni": sezioni_del_bando()},
    )
    assert composto.status_code == 200, composto.text
    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    generato = builder_client.post("/api/v1/documenti/genera", json={
        "sistema_richiedente": "PYTEST_E2E",
        "external_context_id": uuid.uuid4().hex[:12],
        "modello_versione_id": pubblicata["public_id"],
        "dati": dati_completi(),
    })

    assert generato.status_code == 200, generato.text
    assert generato.headers["content-type"] == "application/pdf"
    pdf = generato.content

    # Il testo del documento, non le etichette dei campi.
    assert b"Bando di concorso BND-2026-0042" in pdf
    assert b"Ricercatore in fisica applicata" in pdf
    assert b"Area della Ricerca di Roma 1" in pdf
    assert b"I posti messi a concorso sono 7." in pdf
    # Nessun segnaposto sopravvive alla generazione.
    assert b"{{" not in pdf
    # ADR 0002 / T020: comporre il corpo non rende ufficiale il documento.
    assert b"NON UFFICIALE" in pdf


@pytest.mark.integration
def test_un_valore_mancante_ferma_la_generazione_invece_di_lasciare_un_buco(
    builder_client, catalogo_esterno,
):
    """003 T019: un buco nel testo sembra completo, ed e' peggio di un documento non generato.

    Il segnaposto e' su un campo **opzionale** (`livello`): per un campo
    obbligatorio interviene prima la validazione del payload, che e' il
    controllo giusto per quel caso. L'errore di T019 copre cio' che quella
    validazione non puo' vedere - un campo che il contratto non pretende, ma
    che il **testo** di questo documento cita.
    """
    modello = _crea_modello(builder_client, codice="pytest-e2e-valore-mancante")
    versione = _crea_versione(builder_client, modello["id"])
    sezioni = sezioni_del_bando()
    sezioni[1]["contenuto"].append({
        "id": "livello", "tipo": "PARAGRAFO",
        "contenuto": "Livello professionale: {{livello}}.",
        "posizionamento": "BODY", "ordine": 2,
        "placeholder_usati": ["livello"],
    })
    builder_client.put(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/sezioni",
        json={"sezioni": sezioni},
    )
    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    dati = dati_completi()
    del dati["livello"]
    generato = builder_client.post("/api/v1/documenti/genera", json={
        "sistema_richiedente": "PYTEST_E2E",
        "external_context_id": uuid.uuid4().hex[:12],
        "modello_versione_id": pubblicata["public_id"],
        "dati": dati,
    })

    assert generato.status_code == 200, generato.text
    esito = generato.json()
    assert esito["stato"] == "DATI_NON_VALIDI"
    assert "livello" in esito["messaggio"]


@pytest.mark.integration
def test_un_modello_senza_sezioni_resta_l_elenco_di_prima(builder_client, catalogo_esterno):
    """Nulla di gia' pubblicato cambia forma da sotto."""
    modello = _crea_modello(builder_client, codice="pytest-e2e-senza-sezioni")
    versione = _crea_versione(builder_client, modello["id"])
    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    generato = builder_client.post("/api/v1/documenti/genera", json={
        "sistema_richiedente": "PYTEST_E2E",
        "external_context_id": uuid.uuid4().hex[:12],
        "modello_versione_id": pubblicata["public_id"],
        "dati": dati_completi(),
    })

    assert generato.status_code == 200, generato.text
    pdf = generato.content
    # La forma vecchia: etichetta e valore, non un testo composto.
    assert b"codice_bando" in pdf, "l'elenco riporta i campi"
    assert b"I posti messi a concorso sono" not in pdf, "nessun testo composto"
