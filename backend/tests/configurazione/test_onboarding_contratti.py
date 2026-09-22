"""Onboarding end-to-end di un tipo documento diverso da BANDO_CONCORSO (010/T049).

Dimostra che il motore e' generico e non modellato sul dominio dei bandi di
concorso: nessun codice qui compare nel resto del sistema (CONTRATTO_APPALTO,
tipologie AS/AL, profili SERV/FORN, attributo `soglia`). Il flusso e' quello
della User Story 1-3: definizione -> generazione dello schema di discovery ->
esportazione -> registrazione dell'endpoint contro un server HTTP reale ->
stato CONNESSO.

Il server di discovery e' un vero server HTTP (fixture `discovery_server`), non
un mock del client: la risposta viaggia davvero sulla rete locale. I valori che
restituisce sono volutamente diversi dagli esempi generati (FR-008: conta la
forma comune, non che i valori coincidano).
"""

from __future__ import annotations

import uuid

import pytest

from tests.configurazione.test_onboarding import admin_client  # noqa: F401  (fixture)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

STRUTTURA_CONTRATTI = {
    "tipologie": [
        {"codice": "AS", "descrizione": "Appalto di servizi"},
        {"codice": "AL", "descrizione": "Appalto di lavori"},
    ],
    "profili": [
        {
            "codice": "SERV",
            "descrizione": "Servizi generali",
            "attributi": [
                {
                    "nome": "soglia",
                    "valori_ammessi": ["SOTTO_SOGLIA", "SOPRA_SOGLIA"],
                    "valore_default": "SOTTO_SOGLIA",
                }
            ],
        },
        {
            "codice": "FORN",
            "descrizione": "Forniture",
            # Stesso attributo con opzioni diverse: e' il punto dell'Acceptance
            # Scenario 2 di US1, il campo eredita dal profilo scelto e non porta
            # una lista propria. La validazione esige l'attributo su ogni profilo,
            # perche' il campo e' dichiarato a livello di tipo documento.
            "attributi": [
                {
                    "nome": "soglia",
                    "valori_ammessi": ["SOTTO_SOGLIA", "SOPRA_SOGLIA", "ESCLUSA"],
                    "valore_default": "ESCLUSA",
                }
            ],
        },
    ],
    "combinazioni": [
        {"codice_tipologia": "AS", "codice_profilo": "SERV"},
        {"codice_tipologia": "AL", "codice_profilo": "FORN"},
    ],
    "lingue_possibili": ["IT"],
    "campi": [
        {
            "codice": "oggetto_contratto",
            "etichetta": "Oggetto del contratto",
            "tipo": "string",
            "lingua": "IT",
            "obbligatorio": True,
            "ordine": 1,
        },
        {
            "codice": "importo_base",
            "etichetta": "Importo a base di gara",
            "tipo": "number",
            "lingua": "IT",
            "obbligatorio": True,
            "ordine": 2,
        },
        {
            "codice": "soglia",
            "etichetta": "Soglia comunitaria",
            "tipo": "string",
            "lingua": "IT",
            "obbligatorio": True,
            "ordine": 3,
            # Acceptance Scenario 2 di US1: nessuna lista di opzioni propria,
            # le eredita dall'attributo del profilo.
            "dipende_da_attributo_profilo": "soglia",
        },
    ],
}

# Valori reali diversi dagli esempi generati: conta la forma comune (FR-008).
RISPOSTA_ENDPOINT = {
    "CONTRATTO_APPALTO": {
        "validita": "2026-09-22T00:00:00Z",
        "nodi": [
            {
                "codice": "AS",
                "descrizione": "Appalto di servizi",
                "tipo_livello": "tipologia",
                "figli": [
                    {
                        "codice": "SERV",
                        "descrizione": "Servizi generali",
                        "tipo_livello": "profilo",
                        "lingue_possibili": ["IT"],
                        "campi": [
                            {
                                "codice": "oggetto_contratto",
                                "etichetta": "Oggetto dell'affidamento",
                                "tipo": "string",
                                "lingua": "IT",
                                "obbligatorio": True,
                                "ordine": 1,
                            },
                            {
                                "codice": "importo_base",
                                "etichetta": "Importo stimato",
                                "tipo": "number",
                                "lingua": "IT",
                                "obbligatorio": True,
                                "ordine": 2,
                            },
                        ],
                    }
                ],
            }
        ],
    }
}


@pytest.mark.integration
def test_contratti_onboarding_definizione_schema_endpoint_connesso(
    admin_client, monkeypatch, discovery_server
):
    client, _ = admin_client
    base_url, responses, requests = discovery_server
    responses["/discovery"] = (200, RISPOSTA_ENDPOINT)
    codice_tipo = "CONTRATTO_APPALTO_" + uuid.uuid4().hex[:8]
    base = f"/api/v1/configurazione/tipi-documento/{codice_tipo}"

    # 1. Definizione (US1): il tipo nasce definito ma non connesso.
    creato = client.post(
        "/api/v1/configurazione/tipi-documento",
        json={
            "codice": codice_tipo,
            "nome": "Contratto di appalto",
            "codice_contesto": "demo",
            "struttura": STRUTTURA_CONTRATTI,
        },
    )
    assert creato.status_code == 201, creato.text
    assert creato.json()["stato_integrazione"] in {"DEFINITO", "INCOMPLETO"}

    # 2. Il campo che referenzia un attributo profilo non porta opzioni proprie.
    struttura = client.get(base + "/struttura")
    assert struttura.status_code == 200, struttura.text
    campo_soglia = next(
        c for c in struttura.json()["campi"] if c["codice"] == "soglia"
    )
    assert campo_soglia["dipende_da_attributo_profilo"] == "soglia"
    assert not campo_soglia.get("valori_ammessi")

    # 3. Generazione dello schema di discovery (US2) ed esportazione.
    schema = client.post(base + "/schema-discovery")
    assert schema.status_code in {200, 201}, schema.text
    versione = schema.json()["versione"]
    esportato = client.get(f"{base}/schema-discovery/{versione}")
    assert esportato.status_code == 200, esportato.text
    contenuto = esportato.json()
    testo = str(contenuto)
    assert codice_tipo in testo
    assert "SOTTO_SOGLIA" in testo and "SOPRA_SOGLIA" in testo, (
        "lo schema generato deve esporre i valori ereditati dall'attributo profilo"
    )
    assert "ESCLUSA" in testo, (
        "ogni profilo porta le proprie opzioni: FORN ne ha una in piu' di SERV"
    )

    # 4. Registrazione dell'endpoint e verifica (US3) -> CONNESSO.
    integrazione = client.post(
        "/api/v1/configurazione/integrazioni",
        json={
            "codice": "APPALTI_" + uuid.uuid4().hex[:12],
            "nome": "Gestionale appalti",
            "codice_contesto": "demo",
        },
    )
    assert integrazione.status_code == 201, integrazione.text
    integrazione_id = integrazione.json()["id"]
    monkeypatch.setenv("GEMODO_INTEGRAZIONI_ALLOWLIST", base_url)
    monkeypatch.setenv("GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO", base_url)
    configurata = client.put(
        f"/api/v1/configurazione/integrazioni/{integrazione_id}",
        json={
            "revisione_attesa": 1,
            "nome": "Gestionale appalti",
            "url": base_url + "/discovery",
            "timeout_ms": 5000,
        },
    )
    assert configurata.status_code == 200, configurata.text
    verificata = client.post(
        f"/api/v1/configurazione/integrazioni/{integrazione_id}/verifica",
        json={"revisione_attesa": configurata.json()["revisione"]},
    )
    assert verificata.status_code == 200, verificata.text
    esito = verificata.json()
    assert esito["stato"] == "CONNESSO"
    assert esito["ultima_verifica"]["esito"] == "CONFORME"
    assert esito["ultima_verifica"]["errori"] == []
    assert requests == ["/discovery"], "la verifica deve leggere l'endpoint una sola volta"
