"""Le pagine dell'anteprima, per l'editor (012 T080).

`GET .../impaginazione` e' la misura dell'anteprima: deve dire tante pagine
quante ne ha il PDF dell'anteprima, e nominare i blocchi come li conosce
l'editor (sezione e `id`), non per posizione nel documento piatto.
"""

from __future__ import annotations

import pytest
from io import BytesIO

from pypdf import PdfReader

from tests.builder.test_anteprima_api import _anteprima
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
from tests.e2e.test_documento_composto import sezioni_del_bando
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def _visti(quanti: int) -> dict:
    """Una sezione lunga come quella dei visti di un bando vero."""
    return {"codice": "VISTI", "ordine": 15, "contenuto": [
        {"id": f"v{i}", "tipo": "PARAGRAFO", "posizionamento": "BODY", "ordine": i,
         "allineamento": "GIUSTIFICATO", "placeholder_usati": [],
         "frammenti": [{"testo": "VISTO", "grassetto": True},
                       {"testo": f" il decreto numero {i}, recante disposizioni sul riordino degli "
                                 "enti pubblici di ricerca e sulla semplificazione delle loro attivita';"}]}
        for i in range(quanti)
    ]}


def _bozza_lunga(client, codice: str) -> tuple[dict, dict]:
    modello = _crea_modello(client, codice=codice)
    versione = _crea_versione(client, modello["id"])
    risposta = client.put(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/sezioni",
        json={"sezioni": [*sezioni_del_bando(), _visti(70)]},
    )
    assert risposta.status_code == 200, risposta.text
    return modello, versione


def _impaginazione(client, modello: dict, versione: dict, sezioni: list | None = None):
    return client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/impaginazione",
        json={"sezioni": sezioni} if sezioni is not None else None,
    )


@pytest.mark.integration
def test_le_pagine_sono_quelle_del_pdf_dell_anteprima(builder_client):
    modello, versione = _bozza_lunga(builder_client, "impaginazione-visti")

    risposta = _impaginazione(builder_client, modello, versione)

    assert risposta.status_code == 200, risposta.text
    corpo = risposta.json()
    pagine_pdf = len(PdfReader(BytesIO(_anteprima(builder_client, modello, versione).content)).pages)
    assert corpo["pagine"] == pagine_pdf >= 3
    assert [inizio["pagina"] for inizio in corpo["inizi_pagina"]] == list(range(2, pagine_pdf + 1))
    # I blocchi sono nominati come li conosce l'editor: sezione e id.
    for inizio in corpo["inizi_pagina"]:
        assert inizio["sezione"] == "VISTI"
        assert inizio["blocco"].startswith("v")
        assert inizio["voce"] is None


@pytest.mark.integration
def test_il_testo_non_salvato_si_misura_senza_scriverlo(builder_client):
    """012 T081: i fogli seguono cio' che si scrive, prima del salvataggio."""
    modello, versione = _bozza_lunga(builder_client, "impaginazione-non-salvata")
    salvate = _impaginazione(builder_client, modello, versione).json()
    url_sezioni = f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/sezioni"
    prima = builder_client.get(url_sezioni).json()["sezioni"]

    piu_lunghe = _impaginazione(
        builder_client, modello, versione, [*sezioni_del_bando(), _visti(140)],
    )

    assert piu_lunghe.status_code == 200, piu_lunghe.text
    assert piu_lunghe.json()["pagine"] > salvate["pagine"]
    # Niente e' stato scritto: le sezioni salvate sono quelle di prima.
    assert builder_client.get(url_sezioni).json()["sezioni"] == prima
    assert _impaginazione(builder_client, modello, versione).json() == salvate


@pytest.mark.integration
def test_il_testo_non_salvato_con_markup_e_rifiutato_come_al_salvataggio(builder_client):
    modello, versione = _bozza_lunga(builder_client, "impaginazione-markup")
    sporche = [*sezioni_del_bando(), _visti(1)]
    sporche[-1]["contenuto"][0]["frammenti"] = [{"testo": "<b>VISTO</b>"}]

    risposta = _impaginazione(builder_client, modello, versione, sporche)

    assert risposta.status_code == 422, risposta.text


@pytest.mark.integration
def test_su_una_versione_pubblicata_si_risponde_come_per_l_anteprima(builder_client):
    modello, versione = _bozza_lunga(builder_client, "impaginazione-pubblicata")
    _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    risposta = _impaginazione(builder_client, modello, versione)

    assert risposta.status_code == 409, risposta.text
    assert risposta.json()["codice"] == "MODELLO_VERSIONE_NON_MODIFICABILE"


@pytest.mark.integration
def test_chi_sa_solo_generare_non_misura_le_bozze(builder_client, monkeypatch):
    modello, versione = _bozza_lunga(builder_client, "impaginazione-generatore")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "geri-angular-public")
    monkeypatch.delenv("GEMODO_MOCK_CONTEXT")
    monkeypatch.delenv("GEMODO_MOCK_CONTEXT_ROLES")
    monkeypatch.setenv("GEMODO_MOCK_ROLES", "DOCUMENTI_GENERATORE")

    assert _impaginazione(builder_client, modello, versione).status_code == 403
