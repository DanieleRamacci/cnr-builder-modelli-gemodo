"""La struttura definita dall'amministratore usa la stessa grammatica del discovery (014 FR-006, T014)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.configurazione.schemas import StrutturaInput
from app.configurazione.service import documentazione


def _struttura(campi: list[dict]) -> dict:
    return {
        "tipologie": [{"codice": "TD", "descrizione": "Tempo determinato"}],
        "profili": [{"codice": "CTER", "descrizione": "Collaboratore tecnico", "attributi": []}],
        "combinazioni": [{"codice_tipologia": "TD", "codice_profilo": "CTER"}],
        "lingue_possibili": ["IT"],
        "campi": campi,
    }


ARTICOLAZIONI = {
    "codice": "articolazioni", "etichetta": "Tematiche", "tipo": "array", "obbligatorio": False, "ordine": 2,
    "campi": [
        {"codice": "codice_bando", "etichetta": "Codice", "tipo": "string", "obbligatorio": True, "ordine": 1},
        {"codice": "numero_posti", "etichetta": "Posti", "tipo": "number", "obbligatorio": True, "ordine": 2},
    ],
}
CODICE = {"codice": "codice_bando", "etichetta": "Codice bando", "tipo": "string", "obbligatorio": True, "ordine": 1}


def test_la_struttura_accetta_un_campo_ripetibile_e_l_esportazione_lo_riporta():
    struttura = StrutturaInput.model_validate(_struttura([CODICE, ARTICOLAZIONI]))

    esportata = documentazione("BANDO_TEST", struttura, datetime(2026, 10, 26, tzinfo=timezone.utc))

    campi = esportata["BANDO_TEST"]["nodi"][0]["figli"][0]["campi"]
    articolazioni = next(c for c in campi if c["codice"] == "articolazioni")
    assert [s["codice"] for s in articolazioni["campi"]] == ["codice_bando", "numero_posti"]
    assert "campi" not in next(c for c in campi if c["codice"] == "codice_bando")


@pytest.mark.parametrize(
    "campo",
    [
        pytest.param({**CODICE, "campi": ARTICOLAZIONI["campi"]}, id="campi-su-campo-non-array"),
        pytest.param({**ARTICOLAZIONI, "campi": [{**ARTICOLAZIONI["campi"][0], "tipo": "array"}]}, id="sotto-campo-array"),
        pytest.param({**CODICE, "formato": "testo"}, id="chiave-sconosciuta"),
    ],
)
def test_la_struttura_rifiuta_cio_che_il_discovery_rifiuta(campo):
    with pytest.raises(ValidationError):
        StrutturaInput.model_validate(_struttura([campo]))
