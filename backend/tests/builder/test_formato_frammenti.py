"""Il formato a frammenti rifiuta cio' che non e' un documento GEMODO (012 T007/T008, SC-005).

Due livelli. Il validatore da solo, per coprire ogni regola senza un giro HTTP
a regola; poi l'API vera su PostgreSQL, perche' SC-005 chiede che il rifiuto
arrivi **a chi scrive**, con il codice del catalogo, e che nulla resti salvato.
"""

from __future__ import annotations

import pytest

from app.documentale.schemas import BloccoDocumento
from app.quality.document_model import violazioni_struttura_blocchi
from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
    _crea_modello,
    _crea_versione,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)


def paragrafo(*frammenti: dict, **altro) -> dict:
    return {"id": "p", "tipo": "PARAGRAFO", "posizionamento": "BODY",
            "frammenti": list(frammenti), **altro}


def violazioni(*blocchi: dict) -> list[str]:
    return violazioni_struttura_blocchi([BloccoDocumento.model_validate(b) for b in blocchi])


def test_un_visto_reale_con_enfasi_mista_e_valido():
    """Il caso per cui esiste la feature non deve inciampare nei controlli."""
    assert violazioni(paragrafo(
        {"testo": "VISTO", "grassetto": True},
        {"testo": " il D.Lgs. 4 giugno 2003, n. 127, recante "},
        {"testo": "“Riordino del Consiglio Nazionale delle Ricerche”", "corsivo": True},
        {"testo": "; 3 < 5 non e' markup", "grassetto": True, "corsivo": True, "sottolineato": True},
        {"testo": "bandi", "collegamento": "https://www.cnr.it/it/lavoro-e-formazione"},
        {"testo": "ufficio", "collegamento": "mailto:concorsi@cnr.it"},
        allineamento="GIUSTIFICATO",
    )) == []


@pytest.mark.parametrize("testo", ["<b>VISTO</b>", "VISTO<br/>", "<script>alert(1)</script>",
                                   '<a href="https://cnr.it">x</a>', "testo <!-- nascosto -->"])
def test_il_markup_nel_testo_e_rifiutato(testo):
    trovate = violazioni(paragrafo({"testo": testo}))
    assert len(trovate) == 1 and "markup" in trovate[0], trovate


@pytest.mark.parametrize("collegamento", ["javascript:alert(1)", "JavaScript:alert(1)",
                                          " javascript:alert(1)", "java\tscript:alert(1)",
                                          "data:text/html,<b>x</b>", "ftp://cnr.it", "https://"])
def test_un_collegamento_fuori_da_http_https_mailto_e_rifiutato(collegamento):
    trovate = violazioni(paragrafo({"testo": "qui", "collegamento": collegamento}))
    assert len(trovate) == 1 and "collegamento" in trovate[0], trovate


def test_un_terzo_livello_di_elenco_e_rifiutato_non_reso_male():
    trovate = violazioni({
        "id": "e", "tipo": "ELENCO", "posizionamento": "BODY",
        "elementi": [
            {"livello": 0, "frammenti": [{"testo": "uno"}]},
            {"livello": 2, "frammenti": [{"testo": "troppo in profondita'"}]},
        ],
    })
    assert len(trovate) == 1 and "livello 2" in trovate[0], trovate


def test_gli_elementi_stanno_solo_su_un_elenco():
    trovate = violazioni(paragrafo({"testo": "x"}, elementi=[{"frammenti": [{"testo": "voce"}]}]))
    assert len(trovate) == 1 and "solo su un blocco ELENCO" in trovate[0], trovate


def test_un_elenco_porta_il_testo_nei_suoi_elementi_non_in_frammenti_propri():
    assert violazioni({"id": "e", "tipo": "ELENCO", "posizionamento": "BODY", "elementi": []}) == [
        "blocco e: elenco senza elementi",
    ]
    trovate = violazioni({"id": "e", "tipo": "ELENCO", "posizionamento": "BODY",
                          "frammenti": [{"testo": "fuori posto"}],
                          "elementi": [{"frammenti": [{"testo": "voce"}]}]})
    assert len(trovate) == 1 and "non porta frammenti propri" in trovate[0], trovate


def test_il_markup_dentro_una_voce_di_elenco_e_rifiutato_come_altrove():
    trovate = violazioni({"id": "e", "tipo": "ELENCO", "posizionamento": "BODY",
                          "elementi": [{"frammenti": [{"testo": "<i>voce</i>"}]}]})
    assert trovate == ["blocco e, elemento 0, frammento 0: il testo contiene markup, non ammesso"]


def url(modello_id: str, versione_id: str) -> str:
    return f"/api/v1/builder/modelli/{modello_id}/versioni/{versione_id}/sezioni"


@pytest.mark.integration
def test_sc005_il_markup_e_rifiutato_a_chi_scrive_e_nulla_resta_salvato(builder_client, catalogo_esterno):
    """Rifiuto, non bonifica: 422 con il codice del catalogo, e le sezioni di prima intatte."""
    modello = _crea_modello(builder_client, codice="pytest-frammenti-markup")
    versione = _crea_versione(builder_client, modello["id"])
    valida = {"sezioni": [{"codice": "premessa", "ordine": 10, "contenuto": [
        paragrafo({"testo": "VISTO", "grassetto": True}, {"testo": " il decreto"}),
    ]}]}
    assert builder_client.put(url(modello["id"], versione["id"]), json=valida).status_code == 200

    risposta = builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": [
            paragrafo({"testo": "<b>VISTO</b>"}, {"testo": "qui", "collegamento": "javascript:alert(1)"}),
        ]},
    ]})

    assert risposta.status_code == 422, risposta.text
    corpo = risposta.json()
    assert corpo["codice"] == "MODELLO_DOCUMENTALE_NON_VALIDO"
    # Tutte le violazioni in un giro solo, non la prima.
    assert len(corpo["dettagli"]) == 2, corpo["dettagli"]

    salvate = builder_client.get(url(modello["id"], versione["id"])).json()["sezioni"]
    assert [f["testo"] for f in salvate[0]["contenuto"][0]["frammenti"]] == ["VISTO", " il decreto"]


@pytest.mark.integration
def test_la_forma_vecchia_con_contenuto_stringa_non_entra(builder_client, catalogo_esterno):
    """FR-016: una sola forma. Il rifiuto e' quello di `extra="forbid"`, prima del dominio."""
    modello = _crea_modello(builder_client, codice="pytest-frammenti-forma-vecchia")
    versione = _crea_versione(builder_client, modello["id"])

    risposta = builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10, "contenuto": [
            {"id": "p", "tipo": "PARAGRAFO", "posizionamento": "BODY", "contenuto": "testo"},
        ]},
    ]})

    assert risposta.status_code == 400, risposta.text
    assert any("contenuto" in d["campo"] for d in risposta.json()["dettagli"])
