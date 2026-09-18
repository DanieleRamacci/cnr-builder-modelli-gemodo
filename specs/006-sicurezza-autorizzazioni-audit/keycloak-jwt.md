# Keycloak e JWT - Configurazione Attesa GEBAN/GEMODO

Questo documento chiarisce come GEMODO si aspetta di ricevere e validare i JWT emessi da
Keycloak. Serve come riferimento per chi configura GEBAN, GEMODO e Keycloak.

## Stato Decisione

- **Riferimento**: `SEC-006-001`
- **Stato**: **risolta** il 2026-07-29; **estesa** il 2026-09-14 con modalita'
  ACE/context roles.
- **Scelta definitiva aggiornata**: per le operazioni di generazione da GEBAN verso
  GEMODO sono ammessi due canali coerenti: il client tecnico `geban-backend`, mantenuto
  come doppio di test/CI, e i client ACE reali indicati dal team GEBAN. I token ACE
  devono essere emessi dal realm `cnr`, contenere audience `gemodo-backend` e portare i
  ruoli GEBAN nel claim `contexts.geban.roles`. GEMODO normalizza ruoli client GEMODO e
  ruoli ACE/GEBAN in permessi applicativi propri tramite mapping configurabile.
- **Motivazione**: il token exchange richiede una funzionalita' Keycloak non abilitata di
  default e sviluppo dedicato lato backend GEBAN; il token tecnico e' uno standard OAuth2
  supportato da qualunque backend e sblocca l'integrazione senza dipendere da un intervento
  del team GEBAN oltre alla chiamata API stessa.
- **Evoluzione futura possibile**: se un requisito di audit piu' stringente lo richiedera',
  si potra' introdurre token exchange o mapping piu' granulare per singolo procedimento
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

## Stato Configurazione Test (aggiornato 2026-09-14)

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
  `azp`, `resource_access.gemodo-backend.roles`): da mantenere per test e CI.
- Client ACE reale comunicato dal team GEBAN: negli esempi ricevuti il claim `azp` vale
  `geri-angular-public`. **Corretto 2026-09-16**: il token ACE reale non contiene `aud`
  (il valore visto in un primo esempio era stato impostato a mano lato client durante un
  test) ne', di norma, `resource_access.gemodo-backend.roles` - contiene solo ruoli ACE/
  GEBAN nel claim `contexts.geban.roles`, eventualmente insieme ad altri contesti dello
  stesso utente per altri applicativi ACE (es. `contexts.geri.roles`), che GEMODO ignora
  perche' non li conosce.
- Mapper ACE: il team GEBAN usa un mapper di tipo ACE che, con contesto `geban`, aggiunge
  al token claim nella forma `contexts.geban.roles`. Questo mapper non imposta `aud`: per
  i token ACE, `aud` resta assente per design (vedi "Come Leggere Il Token ACE/GEBAN"
  sotto) - non e' un requisito da imporre lato ACE.

## Principio Di Base

Aggiornamento normativo 2026-09-18: per l'accesso utenti via ACE non si
assegnano ruoli GEMODO aggiuntivi in Keycloak. I permessi sono derivati da
`contexts.<contesto>.roles` tramite mapping backend. Il client di login
autorizzato non deve comparire nei client tecnici di ogni integrazione.
Questa regola sostituisce le indicazioni di assegnazione manuale dei ruoli
utente riportate sotto per il precedente setup diretto; i service account
mantengono i controlli tecnici. Riferimento comune per tutte le integrazioni:
[ADR 0003](../../docs/adr/0003-accesso-utenti-contesti-ace.md).

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
| `geri-angular-public` / client ACE equivalente | public o confidential secondo configurazione ACE | Client reale indicato dal team GEBAN; emette token con `contexts.geban.roles` e audience `gemodo-backend` |
| `gemodo-frontend` | public client | Login utenti che usano il builder GEMODO |
| `gemodo-backend` | resource server / API | API GEMODO protette |

Nomi esatti dei client possono essere adattati allo standard del team, ma devono restare
stabili e documentati.

**Regola sui ruoli GEMODO**: tutti i ruoli applicativi GEMODO elencati sotto sono ruoli
client del client `gemodo-backend`, mai ruoli realm. Il realm `cnr` e' condiviso con altre
applicazioni CNR: un ruolo realm rischierebbe collisioni di nome con ruoli di altre app e
finirebbe nella lista ruoli globale del realm invece che scoperto solo per GEMODO.

**Regola sui ruoli ACE/GEBAN**: i ruoli ACE presenti in `contexts.geban.roles` non
sostituiscono direttamente i ruoli GEMODO. GEMODO li normalizza tramite mapping
configurabile verso permessi applicativi GEMODO.

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

### Mapping Ruoli ACE/GEBAN

Per il contesto `geban`, il mapping iniziale confermato e':

| Ruolo esterno ACE | Permesso GEMODO derivato | Uso ammesso |
|---|---|---|
| `ROLE_GESTORE#geban` | `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` | Creazione/generazione documenti GEBAN |
| `ROLE_MANAGER#geban` | `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER`, `GEMODO_MODELLI_GESTORE` | Creazione/generazione documenti GEBAN e gestione modelli nel perimetro GEBAN |
| `ROLE_COORDINATOR#geban` | `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` | Creazione/generazione documenti GEBAN |
| `ROLE_USER#geban` | `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` | Creazione/generazione documenti GEBAN |

Il mapping deve essere configurabile per contesto applicativo. Nuovi ruoli ACE, nuovi
contesti o nuovi applicativi non devono essere aggiunti come condizioni hard-coded dentro
le singole API.

### Dove Vive La Configurazione Del Mapping

La configurazione applicativa GEMODO del mapping vive nel profilo di integrazione, oggi
`infra/local/integration-profiles.local.yaml`.

Questo file tiene insieme il perimetro GEBAN:

- client ammessi a chiamare GEMODO;
- audience attesa (`gemodo-backend`);
- contesti ACE letti dal token (`geban`);
- tipologie/categorie/modelli ammessi;
- mapping da ruoli esterni ACE/GEBAN a permessi interni GEMODO.

Il seed catalogo (`infra/local/postgres/seed-demo-catalog.yaml`) resta invece la sorgente
delle entita' di dominio disponibili, come categorie/profili e tipologie bando. Non deve
contenere autorizzazioni specifiche GEBAN/ACE, cosi' le stesse categorie possono essere
riusate da altri applicativi con una mappatura ruoli diversa.

Esempio di forma attesa:

```yaml
client_applicativi:
  - client_id: geri-angular-public
    audience_attesa: gemodo-backend
    token_contexts:
      - geban

profili_integrazione:
  - codice: GEBAN_RECLUTAMENTO_V1
    client_ammessi:
      - geri-angular-public
    role_mappings:
      - token_context: geban
        external_role: ROLE_MANAGER#geban
        internal_permissions:
          - DOCUMENTI_GENERATORE
          - DOCUMENTI_VIEWER
          - GEMODO_MODELLI_GESTORE
```

La configurazione Keycloak resta separata: il mapper ACE va aggiunto al client che emette
il token, non al resource server `gemodo-backend`. GEMODO poi legge il token ricevuto e
applica la mappa sopra.

### Come Leggere Il Token ACE/GEBAN

**Corretto 2026-09-16** (`DEC-006-AUD-ASSENTE-NEI-TOKEN-ACE`): il primo esempio di token
ricevuto dal team GEBAN mostrava un claim `aud` con `gemodo-backend` gia' presente - ma
quel valore era stato impostato **a mano lato client durante un test**, non da ACE. Un
token emesso davvero da ACE **non contiene `aud`** ne', di norma, `resource_access.
gemodo-backend.roles`: contiene solo il claim `contexts`, con potenzialmente piu' di un
contesto per lo stesso utente (uno per ogni applicativo ACE a cui e' abilitato).

```json
{
  "iss": "https://sso.test.si.cnr.it/auth/realms/cnr",
  "sub": "user-123",
  "azp": "geri-angular-public",
  "contexts": {
    "geri": {
      "roles": ["ROLE_ADMIN#geri"]
    },
    "geban": {
      "roles": ["ROLE_COORDINATOR#geban"]
    }
  }
}
```

- **Nessun `aud`**: ACE non lo valorizza. GEMODO non puo' e non deve pretenderlo per
  questo tipo di token - un token ACE senza `aud` e' autenticato su firma/issuer/scadenza,
  poi autorizzato in base al contesto riconosciuto (sotto).
- `azp` indica il client che ha ottenuto il token (es. `geri-angular-public`), censito nel
  profilo di integrazione GEMODO (`client_ammessi`). Resta un controllo, ma da solo non
  basta a sapere "per quale applicativo" e' questa chiamata: lo stesso client ACE puo'
  essere condiviso da piu' sistemi (nell'esempio, l'utente ha sia il contesto "geri" sia
  "geban").
- **Il contesto e' il segnale di destinazione**, non `aud`: `contexts.geban.roles` dice
  "questa parte del token riguarda GEBAN". GEMODO considera solo i contesti che conosce
  (qui: `geban`) e ignora silenziosamente gli altri (qui: `geri`) - non e' un errore avere
  contesti che GEMODO non usa, e' normale per un utente abilitato a piu' applicativi ACE.
  I ruoli dentro il contesto riconosciuto (`ROLE_COORDINATOR#geban`, o gli altri ruoli
  GEBAN gia' visti: `ROLE_GESTORE#geban`, `ROLE_MANAGER#geban`, `ROLE_USER#geban`) vengono
  tradotti in permessi GEMODO tramite `role_mappings` nel profilo di integrazione.
- `resource_access.gemodo-backend.roles` resta un meccanismo valido, ma per i **client
  diretti GEMODO** (`gemodo-frontend`, `geban-backend`), non per il flusso ACE - quei
  client continuano a impostare `aud: gemodo-backend` e ruoli diretti, vedi Flusso 1 sotto.

```text
resource_access.gemodo-backend.roles -> permessi GEMODO diretti (client diretti GEMODO, aud presente e verificato)
contexts.<nome>.roles -> mapping configurato -> permessi GEMODO derivati (ACE, aud assente per design)
```

Regola di validazione aggiornata: se `aud` e' presente nel token, deve contenere
`gemodo-backend` (rifiutato altrimenti); se `aud` e' assente, il token resta valido e
l'autorizzazione si basa sul contesto riconosciuto. Implementato in
`backend/app/common/security.py::_ensure_audience_if_declared`, verificato con test reali
(`backend/tests/common/test_security_jwt.py`).

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

Se il frontend GEMODO viene configurato per usare un client ACE invece di
`gemodo-frontend`, il token deve comunque contenere audience `gemodo-backend`. Le azioni
builder possono essere abilitate da ruoli ACE solo tramite mapping esplicito; per il
perimetro GEBAN solo `ROLE_MANAGER#geban` puo' derivare `GEMODO_MODELLI_GESTORE`.

## Flusso 2 - Utente GEBAN Che Genera Documento

Scelta aggiornata `SEC-006-001` (risolta il 2026-07-29, estesa il 2026-09-14).

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
ruolo o ruolo esterno mappato). Il `contesto_autorizzativo` nel payload non viene mai usato per decidere se la
richiesta e' permessa: serve esclusivamente per popolare lo snapshot di generazione e
l'audit trail con l'utente reale e il contesto applicativo. Una chiamata con token valido
ma payload privo di contesto utente coerente viene comunque rifiutata (FR-003b), cosi' da
non perdere tracciabilita' anche se l'autorizzazione tecnica sarebbe superata.

### Variante Reale ACE Con Context Roles

Il team GEBAN puo' chiamare GEMODO con un token emesso da un client ACE ammesso, ad
esempio `geri-angular-public`, purche' contenga il contesto `geban`. **Corretto
2026-09-16**: questo token non contiene `aud` (ACE non lo valorizza) - la richiesta e'
destinata a GEMODO perche' porta un contesto che GEMODO riconosce, non perche' lo dichiara
esplicitamente in un'audience. L'utente puo' avere anche altri contesti nello stesso
token per altri applicativi ACE: GEMODO deriva permessi solo da quello che conosce.

JWT atteso:

```json
{
  "iss": "https://sso.test.si.cnr.it/auth/realms/cnr",
  "sub": "user-123",
  "azp": "geri-angular-public",
  "contexts": {
    "geri": {
      "roles": ["ROLE_ADMIN#geri"]
    },
    "geban": {
      "roles": ["ROLE_COORDINATOR#geban"]
    }
  },
  "preferred_username": "nome.cognome"
}
```

GEMODO deve validare:

- firma, issuer, scadenza del token;
- se `aud` e' presente, deve contenere `gemodo-backend` (rifiutato altrimenti); se
  assente, nessun controllo di audience e' possibile ne' richiesto per questo token;
- client chiamante presente nella lista dei client ammessi;
- ruoli GEMODO in `resource_access.gemodo-backend.roles` (se presente) oppure ruoli ACE/
  GEBAN in `contexts.geban.roles` mappabili a permessi GEMODO - GEMODO ignora
  silenziosamente i contesti che non conosce (es. `contexts.geri` sopra) invece di
  trattarli come errore;
- coerenza tra contesto token `geban`, payload `sistema_richiedente: GEBAN` e azione
  richiesta.

Per la generazione documento, i ruoli `ROLE_GESTORE#geban`, `ROLE_MANAGER#geban`,
`ROLE_COORDINATOR#geban` e `ROLE_USER#geban` derivano `DOCUMENTI_GENERATORE`. Per il
builder modelli nel perimetro GEBAN, solo `ROLE_MANAGER#geban` deriva
`GEMODO_MODELLI_GESTORE`.

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
   - client ACE reale indicato da GEBAN (es. `geri-angular-public`), con mapper ACE per
     `contexts.geban.roles` e audience `gemodo-backend`
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
   service account del client `geban-backend` dove si usa il doppio tecnico di test.
5. Per i client ACE reali, verificare che il token includa:
   - `azp`/client id del client ACE ammesso;
   - `contexts.geban.roles` con i ruoli GEBAN concordati;
   - **nessun `aud` atteso** (ACE non lo valorizza, corretto 2026-09-16 - non richiederlo
     in configurazione ne' in validazione per questo tipo di token);
   - opzionalmente anche `resource_access.gemodo-backend.roles`, se ACE continua a
     valorizzare ruoli GEMODO nel token.
6. Configurare in GEMODO la mappa ruoli esterni -> permessi GEMODO, mantenendo separati
   generazione documenti e gestione modelli.
7. Verificare se il server Keycloak CNR supporta token exchange (da controllare lato admin);
   non e' richiesto per la prima release ma va tracciato come dato noto per l'evoluzione futura.
8. Assicurare che i JWT destinati a GEMODO contengano:
   - `iss`
   - `sub`
   - `aud` con `gemodo-backend` **per i client diretti GEMODO** (`gemodo-frontend`,
     `geban-backend`); i token ACE non lo contengono e non devono contenerlo (corretto
     2026-09-16, vedi "Come Leggere Il Token ACE/GEBAN")
   - `azp` o claim equivalente del client chiamante
   - ruoli applicativi in `resource_access.gemodo-backend.roles` oppure ruoli esterni in
     `contexts.<app>.roles` mappabili a permessi GEMODO
9. Tenere i token brevi e non salvare mai il JWT completo in audit/log applicativi.

### Configurazione ACE Mapper

Sul client che emette il token usato verso GEMODO deve essere presente un mapper ACE che
inserisce nel token i ruoli del contesto GEBAN. Il client puo' essere il client ACE reale
indicato dal team GEBAN (es. `geri-angular-public`) o, se il frontend GEMODO dovra'
autenticare utenti usando il proprio client, anche `gemodo-frontend`.

Configurazione attesa, coerente con la schermata condivisa dal team GEBAN:

```text
Clients -> <client che emette il token> -> Mappers -> ACE Mapper

Protocol: openid-connect
Name: ACE Mapper
Mapper Type: ace mapper
Ace Contexts: geban
Add to ID token: OFF
Add to access token: ON
Add to userinfo: OFF
```

Se il client e' gia' usato da piu' applicativi ACE, il campo `Ace Contexts` puo' contenere
piu' valori separati da virgola, ad esempio:

```text
geri,gebov,geban
```

GEMODO considera solo i contesti dichiarati nella propria configurazione di mapping. Per
il flusso GEBAN il contesto richiesto e' `geban`, quindi nel token deve comparire:

```json
{
  "contexts": {
    "geban": {
      "roles": [
        "ROLE_COORDINATOR#geban"
      ]
    }
  }
}
```

Il mapper ACE serve solo a popolare `contexts.geban.roles`. **Corretto 2026-09-16**: non
imposta ne' richiede un `aud` verso `gemodo-backend` - i token ACE restano validi senza
audience, vedi "Come Leggere Il Token ACE/GEBAN" sopra.

## Regole Di Validazione In GEMODO

GEMODO deve rifiutare la richiesta quando:

- manca il token;
- firma o issuer non sono validi;
- token scaduto;
- `aud` e' presente ma non contiene GEMODO (se `aud` e' assente, nessun rifiuto per
  questo motivo: e' il caso atteso per i token ACE);
- manca il ruolo/claim richiesto;
- il token ACE contiene `contexts.geban.roles` ma il ruolo non e' presente nella mappa
  configurata;
- il token ACE contiene un ruolo GEBAN valido per generare documenti ma tenta azioni di
  builder non coperte da `ROLE_MANAGER#geban`;
- il token ACE contiene un contesto diverso da quello atteso per il sistema richiedente;
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
(client credentials) del client geban-backend con ruolo DOCUMENTI_GENERATORE, oppure
token ACE reali con audience gemodo-backend e ruoli in contexts.geban.roles mappati a
permessi GEMODO. Il client geban-backend resta doppio di test/CI; l'integrazione reale
GEBAN puo' usare client ACE ammessi come geri-angular-public. Token exchange/token
delegato restano evoluzione futura non richiesta per la prima release.
```

```text
Rif. SEC-006-002 (risolta il 2026-07-29)

Per la prima release non serve separazione effettiva tra gestore, revisore e approvatore:
il ruolo GEMODO_MODELLI_GESTORE che porta il modello da BOZZA a PUBBLICATO vale come
approvazione. GEMODO_MODELLI_REVISORE e GEMODO_MODELLI_APPROVATORE restano definiti ma
inattivi, da attivare in futuro se il processo CNR richiedera' un'approvazione da parte
di altri soggetti oltre al gestore.
```

```text
Rif. SEC-006-003 (risolta il 2026-09-14, corretta il 2026-09-16)

I token ACE con contexts.geban.roles sono accettabili per GEBAN, con i ruoli esterni
trasformati da una mappa configurabile in permessi GEMODO. ROLE_GESTORE#geban,
ROLE_MANAGER#geban, ROLE_COORDINATOR#geban e ROLE_USER#geban possono generare documenti;
solo ROLE_MANAGER#geban puo' gestire modelli nel perimetro GEBAN. Corretto 2026-09-16
(DEC-006-AUD-ASSENTE-NEI-TOKEN-ACE): questi token NON contengono audience gemodo-backend -
ACE non la valorizza, un primo esempio che la mostrava era stato impostato a mano lato
client durante un test. L'audience resta verificata solo quando il token la dichiara
(client diretti GEMODO); un token ACE senza aud e' valido, l'autorizzazione si basa sul
contesto riconosciuto.
```

Nessuna decisione bloccante differita al momento.

## Riferimenti

- Keycloak token exchange: https://www.keycloak.org/securing-apps/token-exchange
- Keycloak Server Administration Guide: https://www.keycloak.org/docs/latest/server_admin/
