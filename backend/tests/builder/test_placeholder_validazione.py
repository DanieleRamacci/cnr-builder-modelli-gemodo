"""Placeholder validati contro il contratto dati (003 T010-T013).

Il validatore e' quello della `009`: `DEC-003-CORPO-DOCUMENTO-RIPIANIFICATO`
stabilisce che resta li' e che `003` lo usa. Accettava gia'
`placeholder_contratto_dati` senza avere chiamanti; questi test esercitano il
cablaggio che mancava, via HTTP su PostgreSQL reale.
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


def blocco(identificativo: str, placeholder: list[str]) -> dict:
    return {
        "id": identificativo,
        "tipo": "PARAGRAFO",
        "contenuto": f"testo con {', '.join(placeholder) or 'nessun segnaposto'}",
        "posizionamento": "BODY",
        "ordine": 0,
        "placeholder_usati": placeholder,
    }


@pytest.mark.integration
def test_un_placeholder_del_contratto_e_ammesso(builder_client, catalogo_esterno):
    """`codice_bando` e' fra i campi della versione: il documento puo' citarlo."""
    modello = _crea_modello(builder_client, codice="pytest-placeholder-ok")
    versione = _crea_versione(builder_client, modello["id"])

    risposta = builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10,
         "contenuto": [blocco("intro", ["codice_bando"])]},
    ]})

    assert risposta.status_code == 200, risposta.text
    assert risposta.json()["documento"]["placeholder_usati"] == ["codice_bando"]


@pytest.mark.integration
def test_un_placeholder_sconosciuto_e_rifiutato_alla_scrittura(builder_client, catalogo_esterno):
    """003 FR-004/FR-005: non si scrive un documento che cita un campo inesistente."""
    modello = _crea_modello(builder_client, codice="pytest-placeholder-ignoto")
    versione = _crea_versione(builder_client, modello["id"])

    risposta = builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10,
         "contenuto": [blocco("intro", ["campo_che_non_esiste"])]},
    ]})

    assert risposta.status_code == 400, risposta.text
    corpo = risposta.json()
    assert corpo["codice"] == "PLACEHOLDER_NON_VALIDO"
    assert any("campo_che_non_esiste" in d["violazione"] for d in corpo["dettagli"])

    # Nulla e' stato scritto: il rifiuto non lascia una scrittura a meta'.
    letto = builder_client.get(url(modello["id"], versione["id"]))
    assert letto.json()["sezioni"] == []


@pytest.mark.integration
def test_il_messaggio_elenca_tutte_le_violazioni_non_la_prima(builder_client, catalogo_esterno):
    """003 T011: chi compone deve poterle correggere in un giro solo."""
    modello = _crea_modello(builder_client, codice="pytest-placeholder-molte")
    versione = _crea_versione(builder_client, modello["id"])

    risposta = builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10,
         "contenuto": [blocco("intro", ["primo_ignoto", "secondo_ignoto"])]},
        {"codice": "corpo", "ordine": 20,
         "contenuto": [blocco("dettaglio", ["terzo_ignoto"])]},
    ]})

    assert risposta.status_code == 400, risposta.text
    violazioni = " ".join(d["violazione"] for d in risposta.json()["dettagli"])
    for ignoto in ("primo_ignoto", "secondo_ignoto", "terzo_ignoto"):
        assert ignoto in violazioni, f"{ignoto} non segnalato: si ferma alla prima violazione"


@pytest.mark.integration
def test_la_pubblicazione_e_bloccata_se_il_documento_non_regge(
    builder_client, catalogo_esterno, db_engine,
):
    """003 T012: il cancello di pubblicazione protegge `004`.

    Le sezioni vengono scritte **aggirando l'API** - direttamente in banca
    dati - per simulare una versione composta prima che la validazione alla
    scrittura esistesse. Senza il cancello, quella versione arriverebbe a
    `PUBBLICATO` e genererebbe PDF con un buco che nessuno puo' piu' chiudere.
    """
    import uuid as _uuid

    import sqlalchemy as sa
    from sqlalchemy.orm import Session

    from app.catalog.models import SezioneModello

    modello = _crea_modello(builder_client, codice="pytest-placeholder-cancello")
    versione = _crea_versione(builder_client, modello["id"])

    with Session(db_engine) as db:
        db.add(SezioneModello(
            id=_uuid.uuid4(), modello_versione_id=_uuid.UUID(versione["id"]),
            codice="premessa", ordine=10,
            contenuto=[blocco("intro", ["campo_mai_dichiarato"])],
        ))
        db.commit()

    avanzata = builder_client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/invia-revisione")
    assert avanzata.status_code == 200, avanzata.text
    approvata = builder_client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/approva")
    assert approvata.status_code == 200, approvata.text

    pubblicata = builder_client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/pubblica")
    assert pubblicata.status_code == 400, pubblicata.text
    assert pubblicata.json()["codice"] == "PLACEHOLDER_NON_VALIDO"

    with Session(db_engine) as db:
        stato = db.scalar(sa.text(
            "SELECT stato FROM modello_versione WHERE id = :id"), {"id": versione["id"]})
        assert stato == "APPROVATO", "la versione non e' passata a PUBBLICATO"


@pytest.mark.integration
def test_un_documento_coerente_si_pubblica(builder_client, catalogo_esterno):
    """Il cancello non ostacola il caso normale."""
    modello = _crea_modello(builder_client, codice="pytest-placeholder-pubblica")
    versione = _crea_versione(builder_client, modello["id"])
    builder_client.put(url(modello["id"], versione["id"]), json={"sezioni": [
        {"codice": "premessa", "ordine": 10,
         "contenuto": [blocco("intro", ["codice_bando", "titolo_it"])]},
    ]})

    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    assert pubblicata["stato"] == "PUBBLICATO"
