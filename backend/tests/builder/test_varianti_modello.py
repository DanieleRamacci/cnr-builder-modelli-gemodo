"""Varianti del modello sulla stessa categorizzazione (002 FR-019, T046).

Il difetto che questi test chiudono era silenzioso e grave: due modelli sulla
stessa categorizzazione nascevano entrambi `STANDARD`, e alla pubblicazione del
secondo il primo veniva archiviato senza che nessuno lo avesse chiesto - e'
`get_versione_pubblicata_corrente` che filtra proprio su quella chiave. Chi
aveva pubblicato il primo se ne accorgeva dal catalogo, non dal builder.

Gira su PostgreSQL reale e passa dalle API HTTP, come il resto della cartella.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    CAMPI_BASE,
    _crea_versione,
    _pubblica_fino_in_fondo,
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
    policy_url,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

PERCORSO = ["TD", "RICERCATORE"]


def _crea(client: TestClient, *, nota: str | None = None, livello: str = "VI") -> dict:
    payload = {
        "codice_tipo_documento": "BANDO_CONCORSO",
        "percorso_categorizzazione": PERCORSO,
        "lingua": "IT",
        "livello_professionale": livello,
    }
    if nota is not None:
        payload["nota"] = nota
    return client.post("/api/v1/builder/modelli", json=payload)


@pytest.fixture()
def slot_pulito(db_engine):
    """Lascia lo slot di categorizzazione com'era.

    Senza questa pulizia il primo test occuperebbe lo slot e i successivi
    vedrebbero un modello che non hanno creato loro: il comportamento sotto
    esame dipende proprio da cosa c'e' gia' li'.
    """
    with Session(db_engine) as db:
        creati_prima = set(db.scalars(sa.text("SELECT id FROM modello_documento")).all())
    yield
    with Session(db_engine) as db:
        nuovi = [
            id_ for id_ in db.scalars(sa.text("SELECT id FROM modello_documento")).all()
            if id_ not in creati_prima
        ]
        if nuovi:
            db.execute(
                sa.text("DELETE FROM audit_evento_modello WHERE modello_documento_id = ANY(:ids)"),
                {"ids": nuovi},
            )
            db.execute(
                sa.text("DELETE FROM modello_documento WHERE id = ANY(:ids)"), {"ids": nuovi}
            )
            db.commit()


@pytest.mark.integration
def test_il_primo_modello_della_categorizzazione_e_standard(builder_client, catalogo_esterno, slot_pulito):
    risposta = _crea(builder_client)

    assert risposta.status_code == 201, risposta.text
    assert risposta.json()["variante"] == "STANDARD"
    assert risposta.json()["nota"] is None


@pytest.mark.integration
def test_un_secondo_modello_senza_nota_e_rifiutato_dicendo_quale_esiste(
    builder_client, catalogo_esterno, slot_pulito,
):
    primo = _crea(builder_client).json()

    risposta = _crea(builder_client)

    assert risposta.status_code == 409, risposta.text
    corpo = risposta.json()
    assert corpo["codice"] == "MODELLO_VARIANTE_RICHIESTA"
    # Il frontend costruisce su questo la proposta di creare una variante: senza
    # il modello occupante mostrerebbe un rifiuto e nient'altro.
    assert corpo["dettagli"][0]["modello_id"] == primo["id"]
    assert corpo["dettagli"][0]["codice"] == primo["codice"]


@pytest.mark.integration
def test_due_varianti_coesistono_pubblicate_con_nomi_distinti(
    builder_client, catalogo_esterno, slot_pulito,
):
    primo = _crea(builder_client).json()
    seconda = _crea(builder_client, nota="Senza prova preselettiva")

    assert seconda.status_code == 201, seconda.text
    variante = seconda.json()
    assert variante["variante"] == "VARIANTE_1"
    assert variante["nota"] == "Senza prova preselettiva"
    # T044: nomi e codici generati devono essere distinti, altrimenti in elenco
    # i due modelli sono indistinguibili.
    assert variante["nome"] != primo["nome"]
    assert variante["codice"] != primo["codice"]

    for modello in (primo, variante):
        versione = _crea_versione(builder_client, modello["id"])
        _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    # Il cuore di FR-019: il secondo non archivia il primo.
    for modello in (primo, variante):
        dettaglio = builder_client.get(f"/api/v1/builder/modelli/{modello['id']}").json()
        assert dettaglio["versioni"][0]["stato"] == "PUBBLICATO", dettaglio


@pytest.mark.integration
def test_la_stessa_descrizione_di_variante_e_rifiutata(builder_client, catalogo_esterno, slot_pulito):
    _crea(builder_client)
    _crea(builder_client, nota="Con prova preselettiva")

    risposta = _crea(builder_client, nota="  con PROVA preselettiva  ")

    # Confronto senza spazi e maiuscole: due etichette che l'utente legge uguali
    # sono uguali, anche se i byte no.
    assert risposta.status_code == 409, risposta.text
    assert risposta.json()["codice"] == "MODELLO_VARIANTE_DUPLICATA"


@pytest.mark.integration
def test_la_variante_si_crea_anche_dal_modello_esistente(builder_client, catalogo_esterno, slot_pulito):
    origine = _crea(builder_client).json()

    risposta = builder_client.post(
        f"/api/v1/builder/modelli/{origine['id']}/varianti",
        json={"nota": "Riservata al personale interno"},
    )

    assert risposta.status_code == 201, risposta.text
    variante = risposta.json()
    assert variante["variante"] == "VARIANTE_1"
    # Eredita la categorizzazione: e' cio' che la distingue da un'edizione
    # derivata, che invece cambia il valore di una dimensione.
    assert variante["percorso_categorizzazione"] == origine["percorso_categorizzazione"]
    assert variante["dimensioni"] == origine["dimensioni"]
    assert variante["derivato_da_modello_id"] is None


@pytest.mark.integration
def test_la_numerazione_prosegue_oltre_la_prima_variante(builder_client, catalogo_esterno, slot_pulito):
    origine = _crea(builder_client).json()

    prima = builder_client.post(
        f"/api/v1/builder/modelli/{origine['id']}/varianti", json={"nota": "Prima"},
    ).json()
    seconda = builder_client.post(
        f"/api/v1/builder/modelli/{origine['id']}/varianti", json={"nota": "Seconda"},
    ).json()

    assert [prima["variante"], seconda["variante"]] == ["VARIANTE_1", "VARIANTE_2"]


@pytest.mark.integration
def test_due_varianti_simultanee_non_ottengono_lo_stesso_codice(
    builder_client, catalogo_esterno, slot_pulito, db_engine,
):
    """La corsa che il solo controllo applicativo non chiude (T047).

    Due richieste simultanee leggono lo stesso massimo e sceglierebbero lo
    stesso `VARIANTE_1`: il lock sul tipo documento le serializza e l'indice
    parziale e' la rete sotto. Quel che non deve succedere e' un 500 o due
    modelli con lo stesso codice di variante.
    """
    origine = _crea(builder_client).json()

    def crea(nota: str):
        return builder_client.post(
            f"/api/v1/builder/modelli/{origine['id']}/varianti", json={"nota": nota},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        esiti = [f.result() for f in [pool.submit(crea, "Una"), pool.submit(crea, "Due")]]

    codici = sorted(r.status_code for r in esiti)
    assert codici in ([201, 201], [201, 409]), [r.text for r in esiti]
    assert all(r.status_code != 500 for r in esiti)
    varianti = [r.json()["variante"] for r in esiti if r.status_code == 201]
    assert len(varianti) == len(set(varianti))


@pytest.mark.integration
def test_una_versione_pubblicata_si_archivia_e_si_sospende_da_endpoint(
    builder_client, catalogo_esterno, slot_pulito,
):
    """002 T032: le due transizioni erano ammesse ma non esposte.

    Senza endpoint l'unico modo di togliere dal catalogo una versione era
    pubblicarne un'altra sullo stesso slot: un effetto collaterale, non una
    scelta.
    """
    primo = _crea(builder_client, nota="Da sospendere").json()
    versione = _crea_versione(builder_client, primo["id"])
    _pubblica_fino_in_fondo(builder_client, primo["id"], versione["id"])
    base = f"/api/v1/builder/modelli/{primo['id']}/versioni/{versione['id']}"

    sospesa = builder_client.post(f"{base}/sospendi")
    assert sospesa.status_code == 200, sospesa.text
    assert sospesa.json()["stato"] == "SOSPESO"

    archiviata = builder_client.post(f"{base}/archivia")
    assert archiviata.status_code == 200, archiviata.text
    assert archiviata.json()["stato"] == "ARCHIVIATO"

    # Da ARCHIVIATO non si torna indietro: lo dice la macchina a stati.
    assert builder_client.post(f"{base}/sospendi").status_code == 409


@pytest.mark.integration
def test_il_catalogo_distingue_le_varianti_nella_descrizione(
    builder_client, catalogo_esterno, slot_pulito,
):
    """Per GEBAN la nota e' l'unico modo di distinguerle (T045)."""
    origine = _crea(builder_client).json()
    variante = builder_client.post(
        f"/api/v1/builder/modelli/{origine['id']}/varianti", json={"nota": "Senza prova"},
    ).json()

    for modello in (origine, variante):
        versione = _crea_versione(builder_client, modello["id"])
        _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    catalogo = builder_client.get(
        "/api/v1/catalogo/modelli",
        params={"tipo_documento": "BANDO_CONCORSO", "profilo": "RICERCATORE",
                "codice_tipologia": "TD", "lingua": "IT", "livello_professionale": "VI"},
    )
    assert catalogo.status_code == 200, catalogo.text
    descrizioni = {m["codice"]: m["descrizione"] for m in catalogo.json()["modelli"]}
    # Il nome generato resta, la nota si aggiunge: non si sostituisce.
    assert descrizioni[variante["codice"]].endswith(" - Senza prova")
    assert descrizioni[origine["codice"]] == origine["nome"]
