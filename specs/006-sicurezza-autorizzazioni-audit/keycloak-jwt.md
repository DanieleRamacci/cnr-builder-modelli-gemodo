# Keycloak e JWT - Configurazione Attesa GEBAN/GEMODO

Questo documento chiarisce come GEMODO si aspetta di ricevere e validare i JWT emessi da
Keycloak. Serve come riferimento per chi configura GEBAN, GEMODO e Keycloak.

## Stato Decisione

- **Riferimento**: `SEC-006-001`
- **Stato**: scelta provvisoria da confermare con il team GEBAN/Keycloak
- **Scelta corrente**: per le operazioni utente da GEBAN verso GEMODO, GEBAN usa un token
  delegato Keycloak con audience GEMODO. Il token deve permettere a GEMODO di identificare
  sia il client chiamante `geban-backend` sia l'utente reale.

## Principio Di Base

GEMODO non gestisce utenti, password o assegnazione ufficiale dei ruoli.

La fonte di identita' e ruoli e':

```text
Keycloak o sistema identita' collegato a Keycloak
```

GEMODO:

- valida il JWT;
- legge utente, client, audience, ruoli e claim;
- applica autorizzazioni lato backend;
- salva riferimenti utili in audit.

GEMODO non deve avere una dashboard per assegnare a persone reali ruoli come
`GEMODO_MODELLI_GESTORE`. Questa assegnazione deve avvenire in Keycloak.

## Client Attesi In Keycloak

| Client | Tipo atteso | Uso |
|---|---|---|
| `geban-frontend` | public client | Login utenti su GEBAN |
| `geban-backend` | confidential client | Chiamate server-to-server da GEBAN a GEMODO e token exchange |
| `gemodo-frontend` | public client | Login utenti che usano il builder GEMODO |
| `gemodo-backend` | resource server / API | API GEMODO protette |

Nomi esatti dei client possono essere adattati allo standard del team, ma devono restare
stabili e documentati.

## Ruoli Applicativi Attesi

### Ruoli GEMODO

Usati per il builder e l'amministrazione interna GEMODO.

| Ruolo | Significato |
|---|---|
| `GEMODO_ADMIN` | Puo' eseguire tutte le operazioni interne GEMODO |
| `GEMODO_MODELLI_GESTORE` | Puo' creare, modificare, pubblicare e archiviare modelli nel builder |
| `GEMODO_MODELLI_VIEWER` | Puo' consultare modelli e configurazioni |

Per ora non e' obbligatorio avere un ruolo separato di approvatore. Se il processo lo
richiedera', si potra' introdurre un ruolo dedicato in una revisione successiva.

### Ruoli/Claim GEBAN

Usati quando il flusso parte da GEBAN.

| Ruolo/claim | Significato |
|---|---|
| `DOCUMENTI_GENERATORE` | Permette di richiedere generazione documento nel contesto GEBAN |
| `DOCUMENTI_VIEWER` | Permette consultazione/download documenti generati se il contesto lo consente |
| `SYSTEM_GEBAN` | Client tecnico per batch/job esplicitamente censiti |

Un ruolo GEMODO builder non abilita automaticamente la generazione da GEBAN. Un ruolo GEBAN
di generazione non abilita l'accesso al builder GEMODO.

## Flusso 1 - Utente Che Usa Il Builder GEMODO

```text
utente -> gemodo-frontend -> Keycloak -> gemodo-backend
```

JWT atteso:

```json
{
  "sub": "user-123",
  "preferred_username": "marco.rossi",
  "aud": ["gemodo-backend"],
  "azp": "gemodo-frontend",
  "resource_access": {
    "gemodo-backend": {
      "roles": ["GEMODO_MODELLI_GESTORE"]
    }
  }
}
```

GEMODO deve validare:

- firma;
- issuer;
- scadenza;
- audience `gemodo-backend`;
- presenza ruolo GEMODO coerente con l'azione richiesta.

## Flusso 2 - Utente GEBAN Che Genera Documento

Scelta provvisoria `SEC-006-001`.

```text
utente -> geban-frontend -> geban-backend -> Keycloak token exchange -> gemodo-backend
```

GEBAN backend ottiene da Keycloak un token destinato a GEMODO, mantenendo l'identita'
dell'utente reale.

JWT atteso:

```json
{
  "sub": "user-123",
  "preferred_username": "mario.rossi",
  "aud": ["gemodo-backend"],
  "azp": "geban-backend",
  "resource_access": {
    "gemodo-backend": {
      "roles": ["DOCUMENTI_GENERATORE"]
    }
  },
  "geban_context": {
    "external_context_id": "BANDO-12345",
    "azioni": ["GENERA_DOCUMENTO"]
  }
}
```

GEMODO deve validare:

- firma;
- issuer;
- scadenza;
- audience `gemodo-backend`;
- client chiamante `geban-backend`;
- identita' utente reale;
- ruolo `DOCUMENTI_GENERATORE` o claim equivalente;
- coerenza del contesto GEBAN con la richiesta ricevuta.

## Flusso 3 - Chiamata Tecnica O Batch

```text
job/batch GEBAN -> geban-backend/client tecnico -> gemodo-backend
```

JWT atteso:

```json
{
  "sub": "geban-backend",
  "aud": ["gemodo-backend"],
  "azp": "geban-backend",
  "resource_access": {
    "gemodo-backend": {
      "roles": ["SYSTEM_GEBAN"]
    }
  }
}
```

Regole:

- il ruolo `SYSTEM_GEBAN` e' ammesso solo su API tecniche esplicitamente censite;
- non sostituisce il flusso utente ordinario;
- ogni chiamata tecnica deve essere auditata con client, azione, timestamp e payload
  minimo utile.

## Configurazione Attesa In Keycloak

Da confermare col team Keycloak, ma l'impostazione attesa e':

1. Creare/configurare i client applicativi:
   - `geban-frontend`
   - `geban-backend`
   - `gemodo-frontend`
   - `gemodo-backend`
2. Configurare `gemodo-backend` come audience delle API GEMODO.
3. Definire i ruoli applicativi sul client/realm secondo lo standard del team:
   - `GEMODO_ADMIN`
   - `GEMODO_MODELLI_GESTORE`
   - `GEMODO_MODELLI_VIEWER`
   - `DOCUMENTI_GENERATORE`
   - `DOCUMENTI_VIEWER`
   - `SYSTEM_GEBAN`
4. Assegnare i ruoli agli utenti o ai gruppi in Keycloak, non in GEMODO.
5. Abilitare/configurare token exchange per `geban-backend` se confermata la scelta
   `SEC-006-001`.
6. Assicurare che i JWT destinati a GEMODO contengano:
   - `iss`
   - `sub`
   - `aud`
   - `azp` o claim equivalente del client chiamante
   - ruoli applicativi
   - eventuale `geban_context`
7. Tenere i token brevi e non salvare mai il JWT completo in audit/log applicativi.

## Regole Di Validazione In GEMODO

GEMODO deve rifiutare la richiesta quando:

- manca il token;
- firma o issuer non sono validi;
- token scaduto;
- audience non contiene GEMODO;
- manca il ruolo/claim richiesto;
- una chiamata GEBAN utente non contiene utente reale;
- il client chiamante non e' quello atteso;
- un ruolo GEBAN viene usato per azioni builder;
- un ruolo GEMODO builder viene usato per generazione/download GEBAN;
- il contesto GEBAN e' mancante o incoerente dove richiesto.

## Audit

Auditare sempre:

- `sub` o identificativo utente;
- username se presente;
- client chiamante;
- ruoli/claim rilevanti;
- azione richiesta;
- target dell'azione;
- esito;
- timestamp;
- motivo del rifiuto in caso di errore autorizzativo.

Non salvare mai:

- JWT completo;
- refresh token;
- client secret;
- password;
- credenziali tecniche;
- dati non necessari alla ricostruzione dell'evento.

## Domanda Aperta Da Confermare

```text
Rif. SEC-006-001

Confermate che per le chiamate utente da GEBAN verso GEMODO useremo token exchange /
token delegato Keycloak, con un JWT destinato a GEMODO che contenga sia il client
chiamante geban-backend sia l'identita' utente reale?

In alternativa, preferite un modello con solo token tecnico GEBAN e utente reale passato
nel payload/audit?
```

## Riferimenti

- Keycloak token exchange: https://www.keycloak.org/securing-apps/token-exchange
- Keycloak Server Administration Guide: https://www.keycloak.org/docs/latest/server_admin/
