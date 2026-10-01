"""Cornice di pagina configurata dall'amministratore sul tipo documento (012 T047).

PostgreSQL reale e HTTP. La prova che conta e' l'ultima: configurata la cornice,
la bozza di un modello di quel tipo la porta nel PDF, senza che il gestore
abbia toccato nulla (FR-011: si configura una volta, vale per tutti).
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from tests.builder.test_anteprima_api import _anteprima, _bozza_composta
from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.pdf import estrai_testo
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

CORNICE = {
    "intestazione": [
        {"testo": "Consiglio Nazionale delle Ricerche", "grassetto": True},
        {"testo": "\nUfficio Reclutamento del Personale"},
    ],
    "pie_pagina": [{"testo": "Piazzale Aldo Moro 7 - Roma"}],
    "numerazione_pagine": True,
}


def _url(integrazione_id, codice: str = "BANDO_CONCORSO") -> str:
    return f"/api/v1/configurazione/integrazioni/{integrazione_id}/tipi-documento/{codice}/cornice"


@pytest.fixture(autouse=True)
def senza_cornice(db_engine):
    """Il database di test e' condiviso: la cornice di un test non resta agli altri."""
    yield
    with Session(db_engine) as db:
        db.execute(sa.text("UPDATE tipo_documento SET cornice_pagina = NULL"))
        db.commit()


@pytest.mark.integration
def test_un_tipo_documento_nasce_senza_cornice(builder_client, integrazione_connessa):
    risposta = builder_client.get(_url(integrazione_connessa))
    assert risposta.status_code == 200, risposta.text
    assert risposta.json()["cornice"] is None
    # Il logo dell'ente non e' nel repository: nessun logo da proporre.
    assert risposta.json()["loghi_disponibili"] == []


@pytest.mark.integration
def test_la_cornice_salvata_si_rilegge(builder_client, integrazione_connessa):
    salvata = builder_client.put(_url(integrazione_connessa), json=CORNICE)
    assert salvata.status_code == 200, salvata.text

    letta = builder_client.get(_url(integrazione_connessa)).json()["cornice"]
    assert letta["intestazione"][0] == {
        "testo": "Consiglio Nazionale delle Ricerche", "grassetto": True, "corsivo": False,
        "sottolineato": False, "collegamento": None,
    }
    assert letta["numerazione_pagine"] is True


@pytest.mark.integration
def test_fr011_la_cornice_del_tipo_arriva_nel_pdf_di_ogni_suo_modello(builder_client, integrazione_connessa):
    modello, versione = _bozza_composta(builder_client, "cornice-nel-pdf")
    prima = estrai_testo(_anteprima(builder_client, modello, versione).content)
    assert "Consiglio Nazionale delle Ricerche" not in prima

    assert builder_client.put(_url(integrazione_connessa), json=CORNICE).status_code == 200
    dopo = estrai_testo(_anteprima(builder_client, modello, versione).content)

    assert "Consiglio Nazionale delle Ricerche Ufficio Reclutamento del Personale" in dopo
    assert "Piazzale Aldo Moro 7 - Roma" in dopo
    assert "Pagina 1 di 1" in dopo


@pytest.mark.integration
def test_markup_logo_sconosciuto_e_troppe_righe_sono_rifiutati(builder_client, integrazione_connessa):
    risposta = builder_client.put(_url(integrazione_connessa), json={
        "logo_ref": "logo-altro-ente",
        "intestazione": [{"testo": "<b>CNR</b>\nuno\ndue\ntre"}],
    })

    assert risposta.status_code == 422, risposta.text
    corpo = risposta.json()
    assert corpo["codice"] == "MODELLO_DOCUMENTALE_NON_VALIDO"
    violazioni = " | ".join(d["violazione"] for d in corpo["dettagli"])
    assert "markup" in violazioni and "4 righe" in violazioni and "logo-altro-ente" in violazioni
    # Niente e' stato salvato.
    assert builder_client.get(_url(integrazione_connessa)).json()["cornice"] is None


@pytest.mark.integration
def test_tipo_documento_che_l_integrazione_non_dichiara(builder_client, integrazione_connessa):
    risposta = builder_client.put(_url(integrazione_connessa, "INESISTENTE"), json=CORNICE)
    assert risposta.status_code == 404, risposta.text


@pytest.mark.integration
def test_solo_l_amministratore_configura_la_cornice(builder_client, integrazione_connessa, monkeypatch):
    """Il gestore compone i modelli; la cornice e' dell'ente (US3, due attori)."""
    monkeypatch.setenv("GEMODO_MOCK_ROLES", "DOCUMENTI_VIEWER")
    risposta = builder_client.put(_url(integrazione_connessa), json=CORNICE)
    assert risposta.status_code == 403, risposta.text
