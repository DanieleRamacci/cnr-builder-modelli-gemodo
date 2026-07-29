# Keycloak e JWT - Configurazione Attesa GEBAN/GEMODO

Questo documento chiarisce come GEMODO si aspetta di ricevere e validare i JWT emessi da
Keycloak. Serve come riferimento per chi configura GEBAN, GEMODO e Keycloak.

## Stato Decisione

- **Riferimento**: `SEC-006-001`
- **Stato**: **risolta** il 2026-07-29
- **Scelta definitiva**: per le operazioni di generazione da GEBAN verso GEMODO, GEBAN usa
  un token tecnico Keycloak (client credentials) del client `geban-backend`, con ruolo
  applicativo `DOCUMENTI_GENERATORE` (o `DOCUMENTI_VIEWER`) assegnato al client stesso.
  L'identita' dell'utente reale e il contesto GEBAN (bando, azioni autorizzate) viaggiano
  nel payload della richiesta come dati applicativi e di audit, non come claim del token.
- **Motivazione**: il token exchange richiede una funzionalita' Keycloak non abilitata di
  default e sviluppo dedicato lato backend GEBAN; il token tecnico e' uno standard OAuth2
  supportato da qualunque backend e sblocca l'integrazione senza dipendere da un intervento
  del team GEBAN oltre alla chiamata API stessa.
- **Evoluzione futura possibile**: se un requisito di audit piu' stringente lo richiedera',
  si potra' introdurre il token delegato/token exchange (identita' utente reale nel JWT)
  senza cambiare il contratto pubblico dell'API di generazione.

## Ambiente Keycloak Di Test

- **Endpoint**: `https://sso.test.si.cnr.it/auth`.
- **Realm**: `cnr` (realm condiviso con altre applicazioni CNR, non dedicato a GEMODO).
- **Dominio applicativo disponibile**: wildcard `*.test.si.cnr.it` per esporre frontend/backend
  GEMODO di test.
- **Accesso**: il team GEMODO dispone di un'utenza amministratore del realm `cnr` in test e puo'
  creare e configurare autonomamente i client applicativi (`gemodo-frontend`, `gemodo-backend`
  e, se non gia' presenti, placeholder di test per `geban-frontend`/`geban-backend`).
- **Produzione**: la configurazione Keycloak di produzione NON e' self-service; va richiesta al
  referente infrastruttura Keycloak CNR dopo che la configurazione di test e' stata validata.
  L'obiettivo e' che il passaggio in produzione sia solo una replica della configurazione di
  test piu' uno swap delle variabili d'ambiente (issuer URL, client id/secret), senza modifiche
  di modello.

## Stato Configurazione Test (aggiornato 2026-07-29)

Setup eseguito manualmente in Admin Console sul realm `cnr` di test:

- `gemodo-frontend`: creato. Public client, Standard Flow ON, Implicit/Direct Access
  Grants/Device Grant OFF, Consent Required OFF, PKCE `S256`. Redirect URI e Web Origins
  puntano a `http://localhost:4200` come placeholder di sviluppo (da estendere con il
  dominio reale quando assegnato). Audience mapper verso `gemodo-backend` configurato.
- `gemodo-backend`: creato. Access Type `bearer-only` (resource server puro). Creati tutti
  gli 8 ruoli client: `GEMODO_ADMIN`, `GEMODO_MODELLI_GESTORE`, `GEMODO_MODELLI_REVISORE`,
  `GEMODO_MODELLI_APPROVATORE`, `GEMODO_MODELLI_VIEWER`, `DOCUMENTI_GENERATORE`,
  `DOCUMENTI_VIEWER`, `SYSTEM_GEBAN` (nessuno composite, per tenere l'autorizzazione fine
  esplicita nel backend GEMODO e non implicita in Keycloak).
- `geban-backend`: creato come **doppio di test**, non collegato al vero sistema GEBAN.
  Confidential client, Service Accounts Enabled ON, Standard/Implicit/Direct Access Grants
  OFF, audience mapper verso `gemodo-backend`. Service account con ruoli
  `DOCUMENTI_GENERATORE` e `DOCUMENTI_VIEWER` assegnati su `gemodo-backend`. Resta utile a
  tempo indeterminato per test locali/CI, indipendentemente dall'integrazione reale con
  GEBAN (vedi punto sotto).
- Verifica token tecnico (`client_credentials` su `geban-backend`, controllo `iss`, `aud`,
  `azp`, `resource_access.gemodo-backend.roles`): da eseguire.

**Domanda aperta per il team GEBAN** (non bloccante, da chiarire prima dell'integrazione
reale, non dei test locali): il team GEBAN ha detto di lavorare con un client Keycloak
gia' esistente nello stesso realm `cnr` chiamato `ace`. Da verificare con loro:

- `ace` ha *Service Accounts Enabled* attivo (puo' fare client credentials grant), oppure
  e' il client con cui gli utenti GEBAN fanno login da browser (caso diverso, non adatto
  alle chiamate server-to-server verso GEMODO)?
- E' `ace` il client che chiamera' le API GEMODO, o ne useranno/creeranno uno dedicato?
- Quando confermato, va aggiunto al client reale lo stesso ruolo (`DOCUMENTI_GENERATORE`/
  `DOCUMENTI_VIEWER`) e lo stesso audience mapper gia' configurati su `geban-backend` di
  test; va coordinato con GEBAN prima di modificare un client che loro gestiscono, anche se
  tecnicamente l'accesso admin sul realm lo permetterebbe.

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
| `geban-backend` | confidential client, service account abilitato | Chiamate server-to-server da GEBAN a GEMODO (client credentials); token exchange resta opzione futura non richiesta |
| `gemodo-frontend` | public client | Login utenti che usano il builder GEMODO |
| `gemodo-backend` | resource server / API | API GEMODO protette |

Nomi esatti dei client possono essere adattati allo standard del team, ma devono restare
stabili e documentati.

**Regola sui ruoli**: tutti i ruoli applicativi elencati sotto sono ruoli client del client
`gemodo-backend`, mai ruoli realm. Il realm `cnr` e' condiviso con altre applicazioni CNR:
un ruolo realm rischierebbe collisioni di nome con ruoli di altre app e finirebbe nella lista
ruoli globale del realm invece che scoperto solo per GEMODO.

## Ruoli Applicativi Attesi

### Ruoli GEMODO

Usati per il builder e l'amministrazione interna GEMODO.

| Ruolo | Significato |
|---|---|
| `GEMODO_ADMIN` | Puo' eseguire tutte le operazioni interne GEMODO |
| `GEMODO_MODELLI_GESTORE` | Puo' creare, modificare, pubblicare e archiviare modelli nel builder |
| `GEMODO_MODELLI_REVISORE` | Ruolo riservato per revisione separata delle versioni modello |
| `GEMODO_MODELLI_APPROVATORE` | Ruolo riservato per approvazione, pubblicazione e archiviazione separate |
| `GEMODO_MODELLI_VIEWER` | Puo' consultare modelli e configurazioni |

Per ora non e' obbligatorio attivare ruoli separati di revisore e approvatore. Se il
processo CNR richiede separazione dei compiti nella prima release, pubblicazione e
archiviazione devono essere limitate a `GEMODO_ADMIN` e `GEMODO_MODELLI_APPROVATORE`;
in caso contrario il flusso minimo resta coperto da `GEMODO_ADMIN` e
`GEMODO_MODELLI_GESTORE`.

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

Scelta definitiva `SEC-006-001` (risolta il 2026-07-29).

```text
utente -> geban-frontend -> geban-backend -> Keycloak (client credentials) -> gemodo-backend
```

GEBAN backend ottiene da Keycloak un token tecnico per il proprio client (`geban-backend`),
senza scambio/delega di identita'. L'utente reale e il contesto bando viaggiano nel body
della richiesta HTTP verso GEMODO, non nel JWT.

JWT atteso:

```json
{
  "sub": "geban-backend",
  "aud": ["gemodo-backend"],
  "azp": "geban-backend",
  "resource_access": {
    "gemodo-backend": {
      "roles": ["DOCUMENTI_GENERATORE"]
    }
  }
}
```

Payload della richiesta (esempio, coerente con `PROPOSTA` §12.7):

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "modello_versione_id": 27,
  "formato_output": "PDF",
  "dati": { "...": "..." },
  "contesto_autorizzativo": {
    "utente_richiedente": "mario.rossi",
    "ruoli_geban": ["REFERENTE_BANDO"],
    "azioni_autorizzate": ["GENERA_DOCUMENTO", "SCARICA_DOCUMENTO"]
  }
}
```

GEMODO deve validare:

- firma, issuer, scadenza del token;
- audience `gemodo-backend`;
- client chiamante `geban-backend`;
- ruolo `DOCUMENTI_GENERATORE` (o `DOCUMENTI_VIEWER` per consultazione) sul token;
- presenza di un `contesto_autorizzativo` coerente nel payload (utente richiedente e azione
  richiesta), altrimenti rifiuta la richiesta come incompleta.

L'autorizzazione della chiamata si basa **sempre e solo** sul token verificato (client +
ruolo). Il `contesto_autorizzativo` nel payload non viene mai usato per decidere se la
richiesta e' permessa: serve esclusivamente per popolare lo snapshot di generazione e
l'audit trail con l'utente reale e il contesto applicativo. Una chiamata con token valido
ma payload privo di contesto utente coerente viene comunque rifiutata (FR-003b), cosi' da
non perdere tracciabilita' anche se l'autorizzazione tecnica sarebbe superata.

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
- ogni chiamata tecnica deve essere auditata con client, azione, target, esito, timestamp
  e payload minimo utile;
- una chiamata tecnica non deve completare operazioni sensibili se l'audit obbligatorio
  non viene registrato o non e' ricostruibile.

## Configurazione Attesa In Keycloak

Per l'ambiente di **test** (`sso.test.si.cnr.it`, realm `cnr`) il team GEMODO ha accesso
amministratore e puo' configurare autonomamente quanto segue. Per la **produzione** la stessa
configurazione va richiesta al referente infrastruttura Keycloak CNR, replicando quanto
validato in test:

1. Creare/configurare i client applicativi:
   - `gemodo-frontend` (public client, PKCE)
   - `gemodo-backend` (confidential client / resource server, audience delle API GEMODO)
   - `geban-backend` (confidential client, service account abilitato per client credentials) —
     placeholder di test se non gia' gestito dal team GEBAN
   - `geban-frontend` — placeholder di test se non gia' gestito dal team GEBAN
2. Configurare `gemodo-backend` come audience delle API GEMODO (audience mapper se necessario,
   Keycloak non aggiunge un client all'`aud` di default).
3. Definire i ruoli applicativi come **client roles sul client `gemodo-backend`** (non realm
   roles, vedi regola sui ruoli sopra):
   - `GEMODO_ADMIN`
   - `GEMODO_MODELLI_GESTORE`
   - `GEMODO_MODELLI_REVISORE`
   - `GEMODO_MODELLI_APPROVATORE`
   - `GEMODO_MODELLI_VIEWER`
   - `DOCUMENTI_GENERATORE`
   - `DOCUMENTI_VIEWER`
   - `SYSTEM_GEBAN`
4. Assegnare i ruoli utente (`GEMODO_*`) a utenti/gruppi in Keycloak, non in GEMODO;
   assegnare i ruoli tecnici (`DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER`, `SYSTEM_GEBAN`) al
   service account del client `geban-backend`.
5. Verificare se il server Keycloak CNR supporta token exchange (da controllare lato admin);
   non e' richiesto per la prima release ma va tracciato come dato noto per l'evoluzione futura.
6. Assicurare che i JWT destinati a GEMODO contengano:
   - `iss`
   - `sub`
   - `aud`
   - `azp` o claim equivalente del client chiamante
   - ruoli applicativi in `resource_access.gemodo-backend.roles`
7. Tenere i token brevi e non salvare mai il JWT completo in audit/log applicativi.

## Regole Di Validazione In GEMODO

GEMODO deve rifiutare la richiesta quando:

- manca il token;
- firma o issuer non sono validi;
- token scaduto;
- audience non contiene GEMODO;
- manca il ruolo/claim richiesto;
- una chiamata di generazione GEBAN non contiene un `contesto_autorizzativo` coerente nel
  payload;
- il client chiamante non e' quello atteso;
- un ruolo GEBAN viene usato per azioni builder;
- un ruolo GEMODO builder viene usato per generazione/download GEBAN;
- il contesto GEBAN e' mancante o incoerente dove richiesto;
- il payload contiene un contesto autorizzativo non supportato da claim verificabili nel
  token;
- una chiamata tecnica usa `SYSTEM_GEBAN` su API non censita per uso batch/tecnico.

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

## AI/MCP

I tool AI/MCP che accedono a dati GEMODO devono usare lo stesso modello autorizzativo
delle API ordinarie:

- ruoli e claim vengono letti da token validi;
- ogni azione viene auditata con attore, client, target, esito e timestamp;
- pubblicazione modello, archiviazione, generazione PDF ufficiale e download documenti
  richiedono conferma esplicita quando invocati tramite AI/MCP;
- prompt, risposte e audit non devono contenere token, secret o credenziali.

## Decisioni Risolte

```text
Rif. SEC-006-001 (risolta il 2026-07-29)

Le chiamate di generazione da GEBAN verso GEMODO usano un token tecnico Keycloak
(client credentials) del client geban-backend con ruolo DOCUMENTI_GENERATORE.
L'utente reale e il contesto bando viaggiano nel payload della richiesta per audit,
non nel JWT. Token exchange/token delegato restano evoluzione futura non richiesta
per la prima release.
```

```text
Rif. SEC-006-002 (risolta il 2026-07-29)

Per la prima release non serve separazione effettiva tra gestore, revisore e approvatore:
il ruolo GEMODO_MODELLI_GESTORE che porta il modello da BOZZA a PUBBLICATO vale come
approvazione. GEMODO_MODELLI_REVISORE e GEMODO_MODELLI_APPROVATORE restano definiti ma
inattivi, da attivare in futuro se il processo CNR richiedera' un'approvazione da parte
di altri soggetti oltre al gestore.
```

Nessuna decisione bloccante differita al momento.

## Riferimenti

- Keycloak token exchange: https://www.keycloak.org/securing-apps/token-exchange
- Keycloak Server Administration Guide: https://www.keycloak.org/docs/latest/server_admin/
