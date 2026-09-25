"""Filtri dell'elenco modelli applicati lato server (007 FR-028).

La decisione di filtrare nel backend non e' stilistica: `GET /builder/modelli`
e' paginata e il frontend pagina davvero, quindi un filtro applicato nel client
filtrerebbe la pagina in mano invece dell'insieme, con risultati silenziosamente
sbagliati dalla seconda pagina in poi. Il test `test_il_filtro_precede_la_paginazione`
e' quello che impedisce una regressione verso quel comportamento.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.catalog.models import ModelloDocumento

from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    CAMPI_BASE,
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

URL = "/api/v1/builder/modelli"


def _crea(client, *, tipologia: str = "TD", categoria: str = "RICERCATORE",
          lingua: str = "IT", livello: str | None = None, nota: str | None = None) -> dict:
    # 002 FR-019: la categorizzazione di prova e' gia' occupata dal modello demo
    # del seed, quindi qui si creano varianti e ognuna deve dire in cosa
    # differisce. La nota generata tiene i modelli distinti fra loro.
    response = client.post(URL, json={
        "codice_tipo_documento": "BANDO_CONCORSO",
        "codice_categoria": categoria,
        "codice_tipologia": tipologia,
        "lingua": lingua,
        "livello_professionale": livello,
        "nota": nota or f"filtri {tipologia} {categoria} {lingua} {livello} {uuid.uuid4().hex[:8]}",
    })
    assert response.status_code == 201, response.text
    return response.json()


def _codici(client, **filtri) -> set[str]:
    response = client.get(URL, params={"codice_contesto": "geban", "limit": 100, **filtri})
    assert response.status_code == 200, response.text
    return {m["codice"] for m in response.json()}


@pytest.fixture()
def modelli_di_prova(builder_client, db_engine):
    creati = [
        _crea(builder_client, lingua="IT", livello="IV"),
        _crea(builder_client, lingua="EN", livello="IV"),
        _crea(builder_client, lingua="IT"),
    ]
    yield creati
    with Session(db_engine) as db:
        db.execute(sa.delete(ModelloDocumento).where(
            ModelloDocumento.id.in_([m["id"] for m in creati])
        ))
        db.commit()


@pytest.mark.integration
def test_filtro_per_lingua(builder_client, modelli_di_prova):
    it, en, _ = modelli_di_prova
    codici = _codici(builder_client, lingua="EN")

    assert en["codice"] in codici
    assert it["codice"] not in codici


@pytest.mark.integration
def test_filtro_per_livello_esplicito_e_generico(builder_client, modelli_di_prova):
    con_livello, _, generico = modelli_di_prova

    espliciti = _codici(builder_client, livello_professionale="IV")
    assert con_livello["codice"] in espliciti
    assert generico["codice"] not in espliciti

    # Senza un token dedicato un modello a livello NULL non sarebbe filtrabile:
    # "assente" nel filtro significa gia' "non filtrare".
    generici = _codici(builder_client, livello_professionale="TUTTI")
    assert generico["codice"] in generici
    assert con_livello["codice"] not in generici


@pytest.mark.integration
def test_filtri_combinati_sono_in_and(builder_client, modelli_di_prova):
    it_iv, en_iv, it_generico = modelli_di_prova

    codici = _codici(builder_client, lingua="IT", livello_professionale="IV")

    assert codici >= {it_iv["codice"]}
    assert en_iv["codice"] not in codici
    assert it_generico["codice"] not in codici


@pytest.mark.integration
def test_filtro_per_stato_versione(builder_client, modelli_di_prova):
    modello = modelli_di_prova[0]
    versione = builder_client.post(
        f"{URL}/{modello['id']}/versioni", json={"campi": CAMPI_BASE}
    )
    assert versione.status_code == 201, versione.text

    bozze = _codici(builder_client, stato_versione="BOZZA")
    pubblicati = _codici(builder_client, stato_versione="PUBBLICATO")

    assert modello["codice"] in bozze
    assert modello["codice"] not in pubblicati


@pytest.mark.integration
def test_filtro_senza_corrispondenze_e_elenco_vuoto_non_errore(builder_client, modelli_di_prova):
    response = builder_client.get(URL, params={
        "codice_contesto": "geban", "codice_tipologia": "SDIP", "lingua": "EN",
        "livello_professionale": "VIII",
    })

    assert response.status_code == 200, "un filtro senza risultati non e' un errore"
    assert response.json() == []


@pytest.mark.integration
def test_il_filtro_precede_la_paginazione(builder_client, modelli_di_prova):
    """Il motivo per cui il filtro sta nel server e non nel client.

    Con `limit=1` il client vedrebbe una sola riga per pagina: se filtrasse
    dopo averla ricevuta, un modello che sta in fondo all'elenco non
    comparirebbe mai fra i risultati filtrati.
    """
    _, en, _ = modelli_di_prova

    prima_pagina = builder_client.get(URL, params={
        "codice_contesto": "geban", "lingua": "EN", "limit": 1, "offset": 0,
    })

    assert prima_pagina.status_code == 200, prima_pagina.text
    codici = {m["codice"] for m in prima_pagina.json()}
    assert codici == {en["codice"]}, (
        "la prima pagina filtrata deve contenere il modello EN, non il primo "
        "modello in ordine di creazione poi scartato dal client"
    )


@pytest.mark.integration
def test_filtro_sconosciuto_viene_rifiutato(builder_client):
    response = builder_client.get(URL, params={
        "codice_contesto": "geban", "lingua": "ES",
    })

    assert response.status_code == 400, response.text
    assert response.json()["codice"] == "CONTESTO_NON_VALIDO"


@pytest.mark.integration
def test_voci_filtro_dai_modelli_esistenti(builder_client, modelli_di_prova):
    """Le voci vengono dai modelli presenti, non dall'albero discovery."""
    response = builder_client.get("/api/v1/builder/modelli/filtri", params={"codice_contesto": "geban"})

    assert response.status_code == 200, response.text
    voci = response.json()
    assert "TD" in voci["codici_tipologia"]
    assert "RICERCATORE" in voci["codici_categoria"]
    assert set(voci["lingue"]) >= {"IT", "EN"}
    # L'albero di prova dichiara molte foglie: se le voci venissero di la',
    # comparirebbero tipologie senza alcun modello.
    assert "SDIP" not in voci["codici_tipologia"]


@pytest.mark.integration
def test_voci_filtro_espone_il_livello_generico(builder_client, modelli_di_prova):
    voci = builder_client.get(
        "/api/v1/builder/modelli/filtri", params={"codice_contesto": "geban"}
    ).json()

    assert "TUTTI" in voci["livelli_professionali"], (
        "senza il token i modelli a livello nullo non sarebbero selezionabili"
    )
    assert "IV" in voci["livelli_professionali"]


@pytest.mark.integration
def test_ogni_voce_produce_almeno_un_risultato(builder_client, modelli_di_prova):
    """La promessa dell'endpoint: nessuna tendina che dia sempre elenco vuoto."""
    voci = builder_client.get(
        "/api/v1/builder/modelli/filtri", params={"codice_contesto": "geban"}
    ).json()

    for tipologia in voci["codici_tipologia"]:
        assert _codici(builder_client, codice_tipologia=tipologia), tipologia
    for livello in voci["livelli_professionali"]:
        assert _codici(builder_client, livello_professionale=livello), livello


@pytest.mark.integration
def test_ricerca_testuale_lato_server(builder_client, modelli_di_prova):
    it_iv, en_iv, _ = modelli_di_prova

    per_codice = _codici(builder_client, ricerca=it_iv["codice"][:30])
    assert it_iv["codice"] in per_codice

    # La ricerca compone con gli altri filtri invece di sostituirli.
    combinata = _codici(builder_client, ricerca="ricercatore", lingua="EN")
    assert en_iv["codice"] in combinata
    assert it_iv["codice"] not in combinata


@pytest.mark.integration
def test_la_ricerca_precede_la_paginazione(builder_client, modelli_di_prova):
    """Stesso motivo dei filtri: cercare nella pagina ricevuta e' un difetto."""
    _, en, _ = modelli_di_prova

    response = builder_client.get(URL, params={
        "codice_contesto": "geban", "ricerca": en["codice"], "limit": 1, "offset": 0,
    })

    assert response.status_code == 200, response.text
    assert {m["codice"] for m in response.json()} == {en["codice"]}


@pytest.mark.integration
def test_voci_filtro_richiede_autorizzazione_sul_contesto(builder_client):
    response = builder_client.get(
        "/api/v1/builder/modelli/filtri", params={"codice_contesto": "altro-contesto"}
    )

    assert response.status_code == 403, response.text
