# Riferimento API

Elenco completo delle rotte esposte dal backend GEMODO, raggruppate per area,
con il permesso richiesto e il contratto OpenAPI che le descrive. Ogni contratto
si apre in Swagger UI, dove si provano le chiamate con il login Keycloak, o in
ReDoc per la sola lettura.

Inventario ricavato dal codice il 2026-10-07: **56 rotte API** più le pagine di
documentazione. Base di tutte le rotte: `/api/v1`.

## Contratti OpenAPI

| Contratto | Cosa descrive | Swagger UI | ReDoc | YAML |
|---|---|---|---|---|
| `geban-catalog` | Catalogo, campi richiesti, validazione, generazione: le rotte per i sistemi esterni | [apri](/docs/geban-catalog) | [apri](/redoc/geban-catalog) | [scarica](/openapi/geban-catalog.yaml) |
| `generazione-documenti` | Generazione del PDF e sue risposte | [apri](/docs/generazione-documenti) | [apri](/redoc/generazione-documenti) | [scarica](/openapi/generazione-documenti.yaml) |
| `storage-documenti` | Lettura del registro di una generazione per riferimento | [apri](/docs/storage-documenti) | [apri](/redoc/storage-documenti) | [scarica](/openapi/storage-documenti.yaml) |
| `geban-discovery-endpoint` | Il discovery che **il sistema esterno** deve esporre (non è una rotta GEMODO) | [apri](/docs/geban-discovery-endpoint) | [apri](/redoc/geban-discovery-endpoint) | [scarica](/openapi/geban-discovery-endpoint.yaml) |
| `builder-modelli` | Builder: contesti, modelli, versioni, anteprima, cornice, profilo | [apri](/docs/builder-modelli) | [apri](/redoc/builder-modelli) | [scarica](/openapi/builder-modelli.yaml) |
| `builder-discovery` | Struttura disponibile e creazione di modelli e versioni dal discovery | [apri](/docs/builder-discovery) | [apri](/redoc/builder-discovery) | [scarica](/openapi/builder-discovery.yaml) |
| `integrazioni` | Amministrazione delle integrazioni, accessi, verifica, policy | [apri](/docs/integrazioni) | [apri](/redoc/integrazioni) | [scarica](/openapi/integrazioni.yaml) |
| `configurazione-cataloghi` | Definizione della struttura attesa e generazione del contratto da consegnare | [apri](/docs/configurazione-cataloghi) | [apri](/redoc/configurazione-cataloghi) | [scarica](/openapi/configurazione-cataloghi.yaml) |
| `registro-attivita-admin` | Registro attività per gli amministratori | [apri](/docs/registro-attivita-admin) | [apri](/redoc/registro-attivita-admin) | [scarica](/openapi/registro-attivita-admin.yaml) |

Indice generato dal backend: [`/docs`](/docs). Le pagine Swagger sono costruite
dagli stessi file YAML versionati nelle spec: non possono divergere dal contratto.

### Come provare una chiamata

1. Aprire la pagina Swagger UI del contratto.
2. **Authorize**: login con le credenziali CNR (Keycloak). Il token ottenuto vale
   con i permessi del proprio contesto.
3. **Try it out** sulla rotta, compilare i parametri, **Execute**.

## Permessi

| Sigla | Significato |
|---|---|
| **Admin** | Ruolo diretto `GEMODO_ADMIN` |
| **Gestore** | `GEMODO_MODELLI_GESTORE` nel contesto della risorsa, verificato sulla risorsa stessa |
| **Viewer** | `DOCUMENTI_VIEWER` nel contesto della risorsa (vedi [Lacune note](#lacune-note)) |
| **Generatore** | `DOCUMENTI_GENERATORE` nel contesto della risorsa |
| **Autenticato** | Qualsiasi token valido da un client ammesso |
| **Gestore o Admin** | `GEMODO_MODELLI_GESTORE` nel contesto del tipo documento, oppure `GEMODO_ADMIN` |
| **Pubblica** | Nessun token |

## Sistemi esterni: catalogo e generazione

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| GET | `/api/v1/catalogo/modelli` | Viewer | `geban-catalog`, `builder-modelli` |
| GET | `/api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti` | Viewer | `geban-catalog` |
| POST | `/api/v1/documenti/valida` | Generatore | `geban-catalog` |
| POST | `/api/v1/documenti/genera` | Generatore | `geban-catalog`, `generazione-documenti` |

Guida d'uso: [Integrare un sistema esterno](integrazione-sistema-esterno.md).

## Builder: contesti e struttura

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| GET | `/api/v1/builder/profilo` | Autenticato | `builder-modelli` |
| GET | `/api/v1/builder/contesti` | Gestore (elenca i contesti in cui lo si è) | `builder-modelli` |
| GET | `/api/v1/builder/integrazioni` | Gestore (elenca le integrazioni dei suoi contesti) | `integrazioni` |
| GET | `/api/v1/builder/integrazioni/{integrazioneId}/tipi-documento` | Gestore | `integrazioni` |
| GET | `/api/v1/builder/integrazioni/{integrazioneId}/tipi-documento/{codice}/struttura` | Gestore | `integrazioni` |
| GET | `/api/v1/builder/tipi-documento/{codiceTipoDocumento}/struttura-disponibile` | Gestore | `builder-discovery`, `builder-modelli` |
| GET | `/api/v1/builder/tipi-documento/{codiceTipoDocumento}/policy-dimensioni` | Gestore | `builder-modelli` |

## Builder: modelli

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| GET | `/api/v1/builder/modelli` | Gestore | `builder-modelli` |
| GET | `/api/v1/builder/modelli/filtri` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli` | Gestore | `builder-discovery`, `builder-modelli` |
| GET | `/api/v1/builder/modelli/{modelloId}` | Gestore | `builder-modelli` |
| DELETE | `/api/v1/builder/modelli/{modelloId}` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/varianti` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/edizioni-derivate` | Gestore | `builder-modelli` |
| GET | `/api/v1/builder/modelli/{modelloId}/cornice` | Gestore | `builder-modelli` |

## Builder: versioni

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| POST | `/api/v1/builder/modelli/{modelloId}/versioni` | Gestore | `builder-discovery`, `builder-modelli` |
| GET | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/sezioni` | Gestore | **nessuno** |
| PUT | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/sezioni` | Gestore | **nessuno** |
| POST | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/anteprima` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/impaginazione` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/invia-revisione` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/approva` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/pubblica` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/sospendi` | Gestore | `builder-modelli` |
| POST | `/api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/archivia` | Gestore | `builder-modelli` |

Le sezioni del documento seguono il formato
[GEMODO_DOCUMENT_V1](formato-documentale.md).

## Builder: cornice di pagina

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| GET | `/api/v1/builder/integrazioni/{integrazioneId}/tipi-documento/{codice}/cornice` | Gestore o Admin | `builder-modelli` |
| PUT | `/api/v1/builder/integrazioni/{integrazioneId}/tipi-documento/{codice}/cornice` | Gestore o Admin | `builder-modelli` |
| GET | `/api/v1/builder/integrazioni/{integrazioneId}/tipi-documento/{codice}/cornice/logo` | Gestore o Admin | `builder-modelli` |
| PUT | `/api/v1/builder/integrazioni/{integrazioneId}/tipi-documento/{codice}/cornice/logo` | Gestore o Admin | `builder-modelli` |
| DELETE | `/api/v1/builder/integrazioni/{integrazioneId}/tipi-documento/{codice}/cornice/logo` | Gestore o Admin | `builder-modelli` |

## Amministrazione: integrazioni

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| GET | `/api/v1/configurazione/integrazioni` | Admin | `integrazioni` |
| POST | `/api/v1/configurazione/integrazioni` | Admin | `integrazioni` |
| GET | `/api/v1/configurazione/integrazioni/{integrazione_id}` | Admin | `integrazioni` |
| PUT | `/api/v1/configurazione/integrazioni/{integrazione_id}` | Admin | `integrazioni` |
| DELETE | `/api/v1/configurazione/integrazioni/{integrazione_id}` | Admin | `integrazioni` |
| POST | `/api/v1/configurazione/integrazioni/{integrazione_id}/verifica` | Admin | `integrazioni` |
| GET | `/api/v1/configurazione/integrazioni/{integrazione_id}/accessi` | Admin | `integrazioni` |
| PUT | `/api/v1/configurazione/integrazioni/{integrazione_id}/accessi` | Admin | `integrazioni` |
| GET | `/api/v1/configurazione/integrazioni/{integrazione_id}/tipi-documento` | Admin | `integrazioni` |
| GET | `/api/v1/configurazione/integrazioni/{integrazione_id}/tipi-documento/{codice}/struttura` | Admin | `integrazioni` |
| GET | `/api/v1/configurazione/integrazioni/{integrazione_id}/tipi-documento/{codice}/policy-dimensioni` | Admin | `integrazioni`, `builder-modelli` |
| PUT | `/api/v1/configurazione/integrazioni/{integrazione_id}/tipi-documento/{codice}/policy-dimensioni` | Admin | `integrazioni`, `builder-modelli` |

## Amministrazione: struttura attesa e contratto da consegnare

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| GET | `/api/v1/configurazione/tipi-documento` | Admin | `configurazione-cataloghi` |
| POST | `/api/v1/configurazione/tipi-documento` | Admin | `configurazione-cataloghi` |
| DELETE | `/api/v1/configurazione/tipi-documento/id/{tipo_id}` | Admin | `configurazione-cataloghi` |
| GET | `/api/v1/configurazione/tipi-documento/{codice}/struttura` | Admin | `configurazione-cataloghi` |
| PUT | `/api/v1/configurazione/tipi-documento/{codice}/struttura` | Admin | `configurazione-cataloghi` |
| POST | `/api/v1/configurazione/tipi-documento/{codice}/schema-discovery` | Admin | `configurazione-cataloghi` |
| GET | `/api/v1/configurazione/tipi-documento/{codice}/schema-discovery/{versione}` | Admin | `configurazione-cataloghi` |

## Amministrazione: registri

| Metodo | Rotta | Permesso | Contratto |
|---|---|---|---|
| GET | `/api/v1/admin/attivita` | Admin | `registro-attivita-admin` |
| GET | `/api/v1/admin/attivita.csv` | Admin | `registro-attivita-admin` |
| GET | `/api/v1/documenti/{riferimento}` | Admin | `storage-documenti` |

`/api/v1/documenti/{riferimento}` restituisce la **riga del registro** di una
generazione (chi, quando, versione, impronte), non il PDF: GEMODO non lo
conserva.

## Servizio e documentazione

| Metodo | Rotta | Permesso | Note |
|---|---|---|---|
| GET | `/health` | Pubblica | Stato del servizio |
| GET | `/docs` | Pubblica | Indice dei contratti |
| GET | `/docs/{contratto}` | Pubblica | Swagger UI di un contratto |
| GET | `/redoc/{contratto}` | Pubblica | ReDoc di un contratto |
| GET | `/openapi/{contratto}.yaml` | Pubblica | Sorgente YAML del contratto |
| GET | `/docs/oauth2-redirect.html` | Pubblica | Ritorno del login Keycloak in Swagger UI |
| GET | `/docs/{contratto}/oauth2-redirect` | Pubblica | Ritorno del login Keycloak in Swagger UI, per contratto |

## Codici di errore

Il corpo di un errore è `{ "codice", "messaggio" }`; gli errori di validazione
dei dati sono `{ "campo", "codice", "messaggio" }` dentro la risposta di
`valida` o `genera`.

### Accesso

| Codice | HTTP | Quando |
|---|---|---|
| `ACCESSO_NON_AUTENTICATO` | 401 | Token assente, scaduto o non valido |
| `ACCESSO_NON_AUTORIZZATO` | 403 | Token valido ma client, ruolo o contesto non autorizzano l'operazione |

### Catalogo, validazione e generazione

| Codice | HTTP | Quando |
|---|---|---|
| `MODELLO_VERSIONE_NON_TROVATO` | 404 | Versione inesistente o di un altro contesto |
| `MODELLO_VERSIONE_NON_PUBBLICATO` | 409 | Versione non pubblicata |
| `CONTESTO_NON_VALIDO` | 400 | `tipo_documento` non configurato o non attivo (ricerca nel catalogo) |
| `RICHIESTA_NON_VALIDA` | 400 | Valori in conflitto per la stessa dimensione nella ricerca |
| `CAMPO_OBBLIGATORIO` | (in `errori`) | Campo obbligatorio assente o `null` |
| `CAMPO_NON_AMMESSO` | (in `errori`) | Campo non previsto dalla versione |
| `TIPO_NON_VALIDO` | (in `errori`) | Valore del tipo sbagliato |
| `REGISTRO_GENERAZIONI_NON_DISPONIBILE` | 503 | Generazione non registrata: PDF non consegnato, ripetere |
| `DOCUMENTO_NON_TROVATO` | 404 | Riferimento documentale sconosciuto |

### Builder

| Codice | HTTP | Quando |
|---|---|---|
| `CONTESTO_NON_VALIDO` | 400/404/409 | Percorso non foglia, codici incoerenti, ramo non più disponibile, valore di dimensione non ammesso |
| `DIMENSIONE_RICHIEDE_VALORE` | 400 | La policy della dimensione richiede un valore esplicito |
| `DIMENSIONE_NON_DICHIARATA` | 400 | Si indica una dimensione che la foglia non dichiara |
| `CAMPO_NON_AMMESSO` | 400/404 | Campo non presente nella foglia scelta, o duplicato nella versione |
| `MODELLO_NON_TROVATO` | 404 | Modello inesistente o di un altro contesto |
| `MODELLO_VARIANTE_DUPLICATA`, `EDIZIONE_DERIVATA_DUPLICATA` | 409 | Esiste già un modello per quella combinazione |
| `MODELLO_VERSIONE_NON_MODIFICABILE` | 409 | La versione non è più in bozza |
| `TRANSIZIONE_STATO_NON_VALIDA` | 409 | Passaggio di stato non ammesso dal ciclo di vita |
| `MODELLO_DOCUMENTALE_NON_VALIDO` | 422 | Il documento non rispetta il formato `GEMODO_DOCUMENT_V1` |
| `PLACEHOLDER_NON_VALIDO` | 400 | Segnaposto non presente fra i campi della versione |

### Integrazioni e discovery

| Codice | HTTP | Quando |
|---|---|---|
| `INTEGRAZIONE_NON_CONNESSA` | 409 | L'integrazione non ha superato la verifica |
| `TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE` | 409 | Il tipo documento appartiene già a un'altra integrazione |
| `INTEGRAZIONE_HA_MODELLI`, `INTEGRAZIONE_HA_DOCUMENTI` | 409 | Eliminazione rifiutata: esistono modelli o generazioni registrate |
| `DESTINAZIONE_NON_APPROVATA` | 422 | URL del discovery non autorizzato dal deploy |
| `REVISIONE_SUPERATA` | 409 | La configurazione è cambiata nel frattempo: rileggerla |
| `VERIFICA_IN_CORSO` | 409 | Una verifica è già avviata |
| `DISCOVERY_NON_DISPONIBILE` | 503 | Discovery non raggiungibile o risposta HTTP diversa da 200 |
| `DISCOVERY_TIMEOUT` | 504 | Tempo disponibile scaduto |
| `DISCOVERY_NON_CONFORME` | 502 | Risposta fuori contratto |

Il catalogo storico, con i codici ritirati, è in `infra/openapi/errors.md`.

## Lacune note

- **Permessi del catalogo.** La rotta accetta in ingresso `DOCUMENTI_VIEWER` o
  `DOCUMENTI_GENERATORE`, ma con l'isolamento per contesto attivo (deploy) il
  controllo sul contesto chiede `DOCUMENTI_VIEWER`. Un profilo di accesso che
  concede solo `DOCUMENTI_GENERATORE` può validare e generare ma non cercare nel
  catalogo. Il profilo GEBAN concede entrambi, quindi oggi non ha effetti.

- Le rotte delle **sezioni** (`GET`/`PUT …/versioni/{versioneId}/sezioni`)
  non hanno un contratto OpenAPI: il formato è descritto solo in
  [Formato documentale](formato-documentale.md).
- Il contratto `configurazione-cataloghi` dichiara ancora
  `POST …/tipi-documento/{codice}/endpoint-integrazione` e `…/verifica`, che il
  backend non espone più: registrazione e verifica passano dalle rotte
  `integrazioni`.
- `infra/openapi/errors.md` non elenca tutti i codici in uso: la tabella sopra
  è ricavata dal codice.
