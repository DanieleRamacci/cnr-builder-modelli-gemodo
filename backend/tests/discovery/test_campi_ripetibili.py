"""Contratto discovery 0.8.0: campi ripetibili e grammatica chiusa (014 US1, T010-T011).

Il trasporto HTTP e' simulato perche' l'integratore e' un sistema esterno; la
lettura e la validazione sono quelle vere dell'adapter.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from app.discovery.adapter_http import AdapterHTTP
from app.discovery.errors import DiscoveryError

URL = "https://integratore.example/api/discovery"
GEBAN_TEST = Path(__file__).parent / "dati" / "geban_test_2026-10-26.json"


def _campo(codice: str, tipo: str = "string", ordine: int = 1, **altro) -> dict:
    return {"codice": codice, "etichetta": codice.replace("_", " ").title(), "tipo": tipo,
            "obbligatorio": True, "ordine": ordine, **altro}


ARTICOLAZIONI = _campo(
    "articolazioni", "array", 3, obbligatorio=False,
    descrizione="Sottobandi del bando",
    campi=[
        _campo("codice_bando", "string", 1),
        _campo("numero_posti", "number", 2),
        _campo("sede_lavoro", "string", 3),
        _campo("comune_sede_lavoro", "string", 4, obbligatorio=False),
        _campo("data_presa_servizio", "date", 5, obbligatorio=False),
    ],
)


@pytest.fixture
def albero():
    return {
        "BANDO_CONCORSO": {
            "validita": "2026-10-26T00:00:00Z",
            "nodi": [{
                "codice": "TD", "descrizione": "Tempo Determinato", "tipo_livello": "tipologia",
                "figli": [{
                    "codice": "COLLABORATORE_TECNICO_ER", "descrizione": "Collaboratore Tecnico E.R.",
                    "tipo_livello": "profilo", "livelli_possibili": ["IV", "V", "VI"], "lingue": ["IT", "ENG"],
                    "campi": [_campo("codice_bando", "string", 1), _campo("numero_posti", "number", 2),
                              deepcopy(ARTICOLAZIONI)],
                }],
            }],
        },
    }


def _leggi(albero):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=albero)))
    return AdapterHTTP(URL, client=client).catalogo_discovery("BANDO_CONCORSO", forza_aggiornamento=True)


def _campi_foglia(albero) -> list[dict]:
    return albero["BANDO_CONCORSO"]["nodi"][0]["figli"][0]["campi"]


def _non_conforme(albero) -> DiscoveryError:
    with pytest.raises(DiscoveryError) as errore:
        _leggi(albero)
    assert errore.value.codice == "DISCOVERY_NON_CONFORME"
    return errore.value


def test_un_campo_ripetibile_si_legge_con_i_suoi_sotto_campi(albero):
    foglia = _leggi(albero).indice_percorsi()[("TD", "COLLABORATORE_TECNICO_ER")]

    articolazioni = next(c for c in foglia.campi if c.codice == "articolazioni")
    assert articolazioni.ripetibile
    assert [s.codice for s in articolazioni.campi] == [
        "codice_bando", "numero_posti", "sede_lavoro", "comune_sede_lavoro", "data_presa_servizio",
    ]
    assert [s.tipo for s in articolazioni.campi] == ["string", "number", "string", "string", "date"]
    # Lo stesso codice al primo livello e fra i sotto-campi e' ammesso: sono due campi diversi.
    assert next(c for c in foglia.campi if c.codice == "numero_posti").tipo == "number"
    assert not next(c for c in foglia.campi if c.codice == "numero_posti").ripetibile


def test_un_array_senza_campi_resta_una_lista_semplice(albero):
    """FR-005: chi gia' usava `array` senza struttura non vede differenze."""
    _campi_foglia(albero)[-1] = _campo("lingue_richieste", "array", 3, obbligatorio=False)

    foglia = _leggi(albero).indice_percorsi()[("TD", "COLLABORATORE_TECNICO_ER")]

    lista = next(c for c in foglia.campi if c.codice == "lingue_richieste")
    assert lista.tipo == "array"
    assert lista.campi is None
    assert not lista.ripetibile


def test_l_albero_geban_di_test_resta_conforme_con_la_0_8_0():
    """SC-001: l'albero reale del 2026-10-26 (65 foglie) passa senza modifiche lato GEBAN."""
    reale = json.loads(GEBAN_TEST.read_text(encoding="utf-8"))

    catalogo = _leggi(reale)

    foglie = [n for n in catalogo.indice_percorsi().values() if n.campi is not None]
    assert len(foglie) == 65
    assert not any(c.ripetibile for f in foglie for c in f.campi)


def test_l_albero_geban_con_le_articolazioni_aggiunte_e_conforme():
    reale = json.loads(GEBAN_TEST.read_text(encoding="utf-8"))
    td = next(n for n in reale["BANDO_CONCORSO"]["nodi"] if n["codice"] == "TD")
    cter = next(f for f in td["figli"] if f["codice"] == "COLLABORATORE_TECNICO_ER")
    cter["campi"].append({**deepcopy(ARTICOLAZIONI), "ordine": 14})

    foglia = _leggi(reale).indice_percorsi()[("TD", "COLLABORATORE_TECNICO_ER")]

    assert foglia.campi[-1].codice == "articolazioni"
    assert foglia.campi[-1].ripetibile


def test_una_chiave_che_inizia_con_trattino_basso_e_un_annotazione(albero):
    _campi_foglia(albero)[0]["_comment"] = "nota per chi legge"
    _campi_foglia(albero)[-1]["campi"][0]["_origine"] = "tabella bandi"

    foglia = _leggi(albero).indice_percorsi()[("TD", "COLLABORATORE_TECNICO_ER")]

    assert foglia.campi[0].codice == "codice_bando"


@pytest.mark.parametrize(
    ("modifica", "nel_motivo", "nel_percorso"),
    [
        pytest.param(lambda campi: campi[0].update(obligatorio=True),
                     "obligatorio", "campi.0.obligatorio", id="chiave-sconosciuta-nel-campo"),
        pytest.param(lambda campi: campi[-1]["campi"][1].update(formato="intero"),
                     "formato", "campi.2.campi.1.formato", id="chiave-sconosciuta-nel-sotto-campo"),
        pytest.param(lambda campi: campi[0].update(campi=[_campo("x")]),
                     "codice_bando", "campi.0", id="campi-su-un-campo-non-array"),
        pytest.param(lambda campi: campi[-1].update(campi=[]),
                     "articolazioni", "campi.2", id="campi-vuota"),
        pytest.param(lambda campi: campi[-1]["campi"].append(_campo("sedi", "array", 6)),
                     "tipo", "campi.2.campi.5.tipo", id="sotto-campo-array"),
        pytest.param(lambda campi: campi[-1]["campi"].append(_campo("dettagli", "object", 6)),
                     "tipo", "campi.2.campi.5.tipo", id="sotto-campo-object"),
        pytest.param(lambda campi: campi[-1]["campi"].append(_campo("numero_posti", "number", 6)),
                     "duplicati", "campi.2", id="codici-di-sotto-campo-duplicati"),
    ],
)
def test_un_campo_fuori_grammatica_rende_il_discovery_non_conforme(albero, modifica, nel_motivo, nel_percorso):
    modifica(_campi_foglia(albero))

    errore = _non_conforme(albero)

    testo = errore.messaggio + " ".join(d["messaggio"] for d in errore.dettagli or [])
    assert nel_motivo in testo
    assert any(d["percorso"].endswith(nel_percorso) for d in errore.dettagli or []), errore.dettagli
