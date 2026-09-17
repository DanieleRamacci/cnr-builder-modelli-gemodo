# Definizione Ed Export - Incremento Backend US1/US2

Questo incremento aggiunge API backend, non un'interfaccia Angular.
L'esempio configurato dall'amministratore e' proprietario GEMODO e non viene
riempito con risposte scaricate dal discovery GEBAN. Un catalogo reale puo'
contenere valori diversi e profondita' diverse: gli esempi non lo vincolano.

## API Disponibili

Tutte richiedono token Keycloak e ruolo `GEMODO_ADMIN`:

- `POST /api/v1/configurazione/tipi-documento`: crea il tipo e la prima revisione.
- `PUT /api/v1/configurazione/tipi-documento/{codice}/struttura`: nuova revisione.
- `POST /api/v1/configurazione/tipi-documento/{codice}/schema-discovery`: genera esempio versionato.
- `GET /api/v1/configurazione/tipi-documento/{codice}/schema-discovery/{versione}`: esporta quella versione.
- `GET /api/v1/configurazione/tipi-documento`: elenco amministrativo e stato.

Documentazione: `/docs/configurazione-cataloghi` e `/redoc/configurazione-cataloghi`,
entrambi sul contratto `/openapi/configurazione-cataloghi.yaml`.
Registrazione/test URL US3 sono indicati come pianificati nel contratto e
non sono ancora route runtime. Il guard rifiuta il solo ruolo gestore modelli.

## Esempio Di Definizione

Body della POST, con codice demo sostituibile per evitare duplicati:

```json
{
  "codice": "CONTRATTO_DEMO",
  "nome": "Contratto dimostrativo",
  "codice_contesto": "demo",
  "struttura": {
    "tipologie": [{"codice": "RICERCA", "descrizione": "Ricerca"}],
    "profili": [{"codice": "COLLABORAZIONE", "descrizione": "Collaborazione"}],
    "combinazioni": [{"codice_tipologia": "RICERCA", "codice_profilo": "COLLABORAZIONE"}],
    "campi": [{"codice": "titolo", "etichetta": "Titolo", "tipo": "string", "lingua": "IT", "obbligatorio": true, "ordine": 1}]
  }
}
```

La risposta e' 201 e stato `DEFINITO`, non `CONNESSO`.
La POST `/api/v1/configurazione/tipi-documento/CONTRATTO_DEMO/schema-discovery`
produce versione 1. La GET con suffisso `/schema-discovery/1` restituisce la
stessa documentazione, anche dopo successive modifiche della definizione.
`schema` contiene la mappa tipo documento -> validita/nodi/figli/campi.
Una definizione incompleta si puo' salvare, ma non generare (400 con mancanze).

Per campi dipendenti, `dipende_da_attributo_profilo` identifica un attributo
del profilo: l'esempio generato risolve `enum` e `default` in ciascun ramo,
senza richiedere opzioni duplicate nella definizione del campo. Non si tratta
ancora della risoluzione dinamica dei riferimenti simbolici nel builder live.

## Persistenza E Controlli

Migration 0011 aggiunge revisioni `definizione_struttura`, riferimento alla
revisione negli schemi ed `audit_evento_configurazione`. Una FK composita
impedisce di collegare schemi a definizioni di altri tipi. Salvataggio e audit
sono atomici. Il lock sul tipo serializza modifiche e generazioni.
Modificare la definizione o generare un nuovo schema riporta un endpoint
precedentemente connesso a `DEFINITO`; schemi e modelli storici non cambiano.

Nessuna migration su DB operativo. Prima del deploy fare backup: il backend
applica le migration pendenti all'avvio, inclusa 0009 se ancora non applicata.

## Stato Della Verifica

Test su PostgreSQL reale, route runtime e sorgenti Swagger/ReDoc. La review
esterna e' rinviata su richiesta dell'utente: questo incremento non dichiara
conclusa la feature 010 o superato il quality gate. Hash/runner e soglie
restano rinviati; connessione US3 e frontend restano da implementare.

Esito finale locale: 221 passati, 12 e2e PDF esclusi, nessuno saltato (26.35s).
Test amministrativi mirati: 15 passati. Sono coperti anche rollback su errore
audit, isolamento dell'export, reset della connessione e revisioni/generazioni
concorrenti serializzate per tipo documento. `git diff --check` pulito.
