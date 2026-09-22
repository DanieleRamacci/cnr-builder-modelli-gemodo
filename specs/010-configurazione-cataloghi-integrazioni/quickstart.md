# Quickstart: Configurazione Cataloghi E Integrazioni

Onboarding completo di un tipo documento, dalla definizione fino a un endpoint
di discovery verificato. Lo scenario usa di proposito **un tipo di contratti di
appalto, non un bando di concorso**: serve a dimostrare che il motore e'
generico e non modellato sul dominio GEBAN (decisione del 2026-09-15). Nessuno
dei codici usati qui compare altrove nel sistema.

Tutto il flusso e' coperto da un test reale, non da una procedura scritta a
mano: `backend/tests/configurazione/test_onboarding_contratti.py`. Il test
chiama le API HTTP vere su PostgreSQL reale e interroga un vero server HTTP di
discovery, non un mock del client.

```bash
cd backend && uv run pytest tests/configurazione/test_onboarding_contratti.py -q
```

## Prerequisiti

- PostgreSQL raggiungibile (`DATABASE_URL`, oppure Docker per Testcontainers).
- Un token con ruolo `GEMODO_ADMIN` (FR-012). Negli esempi sotto e' sottinteso
  l'header `Authorization: Bearer <token>`.
- L'origine dell'endpoint di discovery deve essere in
  `GEMODO_INTEGRAZIONI_ALLOWLIST`; per un servizio su rete privata serve anche
  `GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO`. Senza allowlist la configurazione
  viene rifiutata con `DESTINAZIONE_NON_APPROVATA`.

## 1. Definire il tipo documento (User Story 1)

```http
POST /api/v1/configurazione/tipi-documento
```

```json
{
  "codice": "CONTRATTO_APPALTO",
  "nome": "Contratto di appalto",
  "codice_contesto": "demo",
  "struttura": {
    "tipologie": [
      { "codice": "AS", "descrizione": "Appalto di servizi" },
      { "codice": "AL", "descrizione": "Appalto di lavori" }
    ],
    "profili": [
      {
        "codice": "SERV",
        "descrizione": "Servizi generali",
        "attributi": [
          {
            "nome": "soglia",
            "valori_ammessi": ["SOTTO_SOGLIA", "SOPRA_SOGLIA"],
            "valore_default": "SOTTO_SOGLIA"
          }
        ]
      },
      {
        "codice": "FORN",
        "descrizione": "Forniture",
        "attributi": [
          {
            "nome": "soglia",
            "valori_ammessi": ["SOTTO_SOGLIA", "SOPRA_SOGLIA", "ESCLUSA"],
            "valore_default": "ESCLUSA"
          }
        ]
      }
    ],
    "combinazioni": [
      { "codice_tipologia": "AS", "codice_profilo": "SERV" },
      { "codice_tipologia": "AL", "codice_profilo": "FORN" }
    ],
    "lingue_possibili": ["IT"],
    "campi": [
      { "codice": "oggetto_contratto", "etichetta": "Oggetto del contratto", "tipo": "string", "lingua": "IT", "obbligatorio": true, "ordine": 1 },
      { "codice": "importo_base", "etichetta": "Importo a base di gara", "tipo": "number", "lingua": "IT", "obbligatorio": true, "ordine": 2 },
      { "codice": "soglia", "etichetta": "Soglia comunitaria", "tipo": "string", "lingua": "IT", "obbligatorio": true, "ordine": 3, "dipende_da_attributo_profilo": "soglia" }
    ]
  }
}
```

Risposta `201`, con `stato_integrazione` `DEFINITO` o `INCOMPLETO`: il tipo
esiste ma **non e' ancora utilizzabile** per creare modelli (FR-009).

### Il campo ereditato (Acceptance Scenario 2)

`soglia` non porta una propria lista di opzioni: le eredita dall'attributo del
profilo scelto. Lo stesso campo offre tre valori sotto `FORN` e due sotto
`SERV`. Due vincoli da conoscere, entrambi applicati dalla validazione:

- Il campo dev'essere di tipo `string`.
- L'attributo referenziato deve esistere su **ogni** profilo, perche' il campo
  e' dichiarato a livello di tipo documento. Se manca anche solo su un profilo,
  la definizione viene rifiutata con
  `Attributo profilo mancante o senza opzioni obbligatorie`.

Dichiarare `enum`, `default` o `fonte_opzioni` nella `validazione` di un campo
dipendente e' un errore: quei valori arrivano dal profilo.

## 2. Generare ed esportare il contratto (User Story 2)

```http
POST /api/v1/configurazione/tipi-documento/CONTRATTO_APPALTO/schema-discovery
GET  /api/v1/configurazione/tipi-documento/CONTRATTO_APPALTO/schema-discovery/{versione}
```

La generazione restituisce la `versione` dello schema; l'esportazione
restituisce il documento da consegnare al team esterno. Lo schema espone i
valori ereditati dagli attributi profilo, `SOTTO_SOGLIA`/`SOPRA_SOGLIA` per
`SERV` ed `ESCLUSA` in piu' per `FORN`.

Una definizione incompleta blocca la generazione con `DEFINIZIONE_INCOMPLETA` e
l'elenco di cosa manca.

## 3. Registrare e verificare l'endpoint (User Story 3)

Dopo il pivot FR-017 del 2026-09-17 l'endpoint appartiene all'**Integrazione**,
non al tipo documento: un'integrazione con un solo URL puo' servire piu' tipi.

```http
POST /api/v1/configurazione/integrazioni
PUT  /api/v1/configurazione/integrazioni/{id}
POST /api/v1/configurazione/integrazioni/{id}/verifica
```

La creazione parte da `stato: DEFINITO`, `url: null`, `revisione: 1`. La `PUT`
registra URL e timeout e incrementa la revisione; la verifica va richiesta con
`revisione_attesa` pari a quella corrente, altrimenti risponde `409`
`REVISIONE_SUPERATA` (blocco ottimistico, nessuna sovrascrittura silenziosa).

La verifica riuscita porta a:

```json
{
  "stato": "CONNESSO",
  "ultima_verifica": { "esito": "CONFORME", "errori": [], "revisione": 2 }
}
```

**I valori reali non devono coincidere con gli esempi generati** (FR-008): nel
test l'endpoint restituisce etichette diverse ("Oggetto dell'affidamento" invece
di "Oggetto del contratto") e la verifica passa comunque, perche' conta la forma
comune. Una risposta che viola la forma resta `ERRORE` e non diventa mai
`CONNESSO`.

L'endpoint viene letto **una sola volta** per verifica.

### Cosa succede dopo

- Cambiare l'URL riporta lo stato a `DEFINITO`: serve una nuova verifica.
  Rinominare l'integrazione no, la connessione resta valida.
- Rimuovere l'URL elimina la riga dell'endpoint.
- Una verifica gia' in corso rifiuta la successiva con `VERIFICA_IN_CORSO`; il
  tentativo scade, quindi una verifica bloccata non blocca per sempre.
- Finche' l'integrazione non e' `CONNESSO`, la lettura live risponde
  `INTEGRAZIONE_NON_CONNESSA` senza interrogare l'adapter (FR-009).

## Esiti registrati (2026-09-22)

```text
backend non-E2E:                  319 passed, 12 esclusi (PostgreSQL reale)
tests/configurazione + discovery: 97 passed, 0 skipped
test_onboarding_contratti.py:     1 passed
```

Fuori da questo scenario restano, per decisione esplicita: FR-010
(self-service, rinviato fuori dall'incremento FR-016), FR-014 e FR-015
(firma del contratto e verifica periodica, rinviati nel MVP) e la User Story 5
sulla policy per dimensione, non ancora implementata.
