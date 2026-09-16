# Flusso Configurazione, Builder E Generazione Documento

Descrizione end-to-end del flusso GEBAN &harr; GEMODO cosi' come definito nelle
spec `001`, `002`, `010` e implementato al 2026-09-16. Ogni sezione dice
esplicitamente cosa e' **reale e testato oggi** e cosa e' **solo specificato**
(non ancora costruito), per rendere facile trovare buchi.

## Stato In Un Colpo D'occhio

| Fase | Stato | Dove vive |
|---|---|---|
| 1. Definire struttura (tipologie/profili/campi) e generare il contratto per l'integratore | **Solo specificato** (`010`); fatto a mano una volta per GEBAN | `specs/010-configurazione-cataloghi-integrazioni/spec.md`, `docs/adr/0001-esempio-discovery-geban.json`, `specs/010.../contracts/geban-discovery-endpoint.openapi.yaml` |
| 2. Registrare l'endpoint esterno e attivare l'integrazione | **Solo specificato** (`010`), non costruito | `specs/010-configurazione-cataloghi-integrazioni/data-model.md` (entita' `EndpointIntegrazione`) |
| 3. Creare un modello e salvarlo nel DB | **Reale, testato su Postgres** | `backend/app/builder/`, `backend/app/discovery/` |
| 4. Pubblicare il modello | **Reale, testato su Postgres** | `backend/app/builder/service.py` |
| 5. Generare un documento da un modello pubblicato | **Reale** (validazione), risposta ancora placeholder (nessun PDF) | `backend/app/validation/` |

---

## 1. Configurazione Della Struttura E Generazione Del Contratto Per L'integratore

**Chi**: un operatore GEMODO (non lo sviluppatore di GEBAN).

**Obiettivo**: definire, per un tipo documento (es. `BANDO_CONCORSO`), quali
tipologie/profili/campi esistono, e produrre da quella definizione un
documento/contratto che il team esterno (GEBAN) usa per implementare il
proprio endpoint di discovery.

### Come e' specificato (`010`, non ancora costruito)

1. L'operatore apre l'interfaccia di amministrazione (visualizzazione JSON ad
   albero, apribile/richiudibile) e definisce: tipo documento, tipologie,
   profili per tipologia, campi del contratto dati (una volta sola, non
   ripetuti per ogni combinazione), eventuali attributi profilo-dipendenti
   (es. "livello": valori ammessi diversi per profilo).
2. Il sistema genera automaticamente uno schema/esempio JSON che rappresenta
   la risposta attesa dall'endpoint che l'esterno deve implementare
   (`FR-006`/`FR-007` di `010`).
3. Quel documento viene esportato/consegnato al team esterno.

**Nessuna di queste tre azioni ha oggi un'interfaccia o un'API**: la
generazione dello schema (passo 2) non esiste come funzionalita' eseguibile.

### Come e' stato fatto per davvero, stasera (percorso manuale, sostituto temporaneo del passo 2)

Non essendoci ancora l'interfaccia che genera il contratto, il contratto per
GEBAN e' stato scritto a mano, partendo pero' da dati verificati (non
inventati):

1. Codici di tipologie e profili verificati chiamando le API di test reali di
   GEBAN (`https://geban-service.test.si.cnr.it/api/v1/profili`,
   `/api/v1/tipoSols`) il 2026-09-15.
2. Campi del contratto dati presi da quelli gia' usati oggi da GEMODO
   (`CAMPI_DEMO` in `backend/alembic/versions/0005_classificazione_catalogo_geban.py`)
   piu' un settimo campo nuovo (`livello`), confermato necessario dal product
   owner ma il cui meccanismo esatto lato API GEBAN resta da validare con
   loro.
3. Il risultato e' pubblicato come contratto OpenAPI vero (non solo un file
   JSON), visibile su Swagger/ReDoc:
   `GET /docs/geban-discovery-endpoint`, `GET /redoc/geban-discovery-endpoint`
   (sorgente: `specs/010-configurazione-cataloghi-integrazioni/contracts/geban-discovery-endpoint.openapi.yaml`).
   Il file descrive esplicitamente che **non e' un'API GEMODO**: e' il
   contratto che GEBAN deve implementare dal proprio lato.

**Buco esplicito**: se domani cambia un campo o una tipologia, oggi va
rifatto a mano lo stesso lavoro. Non c'e' ancora modo di rigenerare questo
contratto da una configurazione salvata.

---

## 2. Flusso Admin: Registrare E Abilitare Un'integrazione

**Chi**: un operatore GEMODO, dopo che il team esterno ha implementato il
proprio endpoint di discovery seguendo il contratto del punto 1.

### Come e' specificato (`010`, non ancora costruito)

1. L'operatore registra l'URL reale dell'endpoint esterno per quel tipo
   documento (entita' `EndpointIntegrazione`).
2. Il sistema esegue un test di connessione: chiama l'endpoint e verifica che
   la risposta rispetti lo schema generato al punto 1.
3. Se il test riesce, il tipo documento passa a stato `CONNESSO` e diventa
   disponibile per la creazione di modelli (sezione 3). Se fallisce (schema
   non rispettato o endpoint irraggiungibile), resta `ERRORE`/`DEFINITO`, con
   un motivo esplicito — mai un errore generico o uno stato ambiguo.
4. Una dashboard mostra lo stato (definito / connesso / errore) di ogni tipo
   documento configurato.
5. Se il tipo documento e' **self-service** (nessun sistema esterno, GEMODO
   stesso autora la struttura), questo intero passo si salta: il contesto
   diventa utilizzabile subito dopo il passo 1.

**Stato oggi**: nessuna di queste azioni esiste. Non c'e' una tabella
`EndpointIntegrazione`, non c'e' un test di connessione, non c'e' una
dashboard. `BANDO_CONCORSO` e' trattato come se fosse gia' "connesso" perche'
il suo `codice_contesto` (`geban`) e i suoi dati sono presenti direttamente
nel database (vedi sezione 3) — non perche' un endpoint sia stato registrato
e verificato per davvero.

**Buco esplicito**: oggi non c'e' nessun controllo automatico che impedisca
di creare un modello per un tipo documento "integrato" la cui integrazione
reale non e' mai stata verificata. La sezione 3 sotto funziona comunque,
appoggiandosi a dati locali — il che va bene per il fixture di sviluppo
usato stasera, ma e' esattamente il gap che il flusso del punto 2 dovrebbe
chiudere prima di andare in produzione con un'integrazione vera.

---

## 3. Creazione Di Un Modello E Salvataggio Nel DB

**Chi**: un gestore modelli (`GEMODO_MODELLI_GESTORE`), autenticato con un
token il cui `contexts.<nome>.roles` corrisponde al `codice_contesto` del
tipo documento target (`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO` — non esiste
un'entita' "Ufficio" separata: il contesto del token e' direttamente il
segnale di autorizzazione).

### 3.1 Da dove arriva la categorizzazione (tipologie/profili)

**Comportamento**: il builder non legge mai direttamente le tabelle
catalogo. Passa sempre da un'interfaccia astratta, la **porta di discovery**
(`backend/app/discovery/port.py`, `PortaDiscovery`), che oggi ha una sola
implementazione reale:

- **`AdapterLocale`** (`backend/app/discovery/adapter_locale.py`): legge
  `ClassificazioneCatalogo` + `TipologiaBandoSOL` + `CategoriaDocumento`
  (tabelle Postgres reali, popolate da `infra/local/postgres/seed-demo-catalog.yaml`
  tramite le migration `0004`/`0005`/`0006`/`0007`).

**Il punto da capire bene**: oggi, anche per `BANDO_CONCORSO` (che e'
concettualmente un tipo documento "integrato" con GEBAN), i dati di
tipologia/profilo vengono letti da questo **seed locale**, non da una
chiamata live all'endpoint di GEBAN. Il secondo adapter previsto
(`AdapterHTTP`, che chiamerebbe l'endpoint registrato al punto 2) **non e'
stato implementato**. Il seed locale funziona oggi come fixture di sviluppo
per lo stesso tipo documento che in produzione dovrebbe essere sincronizzato
dall'esterno — finche' `AdapterHTTP` e il passo 2 non esistono, questa e' di
fatto anche la sorgente "di produzione".

Endpoint per leggere cosa e' disponibile (usa `AdapterLocale`):

```text
GET /api/v1/builder/tipi-documento/{codiceTipoDocumento}/struttura-disponibile
```

Risponde con l'elenco di tipologie (ognuna con i propri profili ammessi) e
l'elenco di campi disponibili (vedi 3.2).

### 3.2 Da dove arrivano i campi del contratto dati

**Comportamento**: i campi che un modello puo' dichiarare **non sono
liberi**: devono provenire dal **Registro Contratti Dati**
(`backend/app/catalog/models.py::RegistroContrattiDati`, tabella
`registro_contratti_dati`), scoped per tipo documento.

Per `BANDO_CONCORSO`, questa tabella e' popolata da un'unica riga
(`bando-concorso-common-fields-v1`), inserita direttamente dalla migration
`backend/alembic/versions/0008_contesto_registro_contratti_audit.py` con i 7
campi reali: `codice_bando`, `titolo_it`, `descrizione_ridotta_it`,
`sede_prescelta_it`, `numero_posti`, `titolo_en`, `livello`.

**Punto da capire bene**: questa riga e' stata scritta **a mano dentro la
migration**, non generata dal flusso del punto 1 ne' sincronizzata da
nessun adapter. E' lo stesso identico limite descritto in 3.1: la sorgente
"vera" (in teoria l'endpoint esterno, tramite `AdapterHTTP`) non esiste
ancora, quindi oggi si usa un dato locale fissato manualmente.

`AdapterLocale.campi_disponibili(codice_tipo_documento)` legge questa
tabella e la espone tramite lo stesso endpoint del punto 3.1.

### 3.3 Creazione del modello (scrittura nel DB)

```text
POST /api/v1/builder/modelli
{
  "codice": "...",
  "nome": "...",
  "codice_tipo_documento": "BANDO_CONCORSO",
  "codice_categoria": "RICERCATORE",
  "codice_tipologia": "TD",
  "variante": "STANDARD"
}
```

Comportamento (`backend/app/builder/service.py::BuilderService.crea_modello`):

1. Risolve il `TipoDocumento` per codice, legge il suo `codice_contesto`.
2. Verifica che il chiamante sia autorizzato **per quello specifico
   contesto** (`verify_scrittura_su_contesto`, `backend/app/common/security.py`)
   — mai sulla lista di permessi gia' appiattita su tutti i contesti del
   token, per evitare che un ruolo di gestore in un contesto autorizzi la
   scrittura su un tipo documento di un contesto diverso.
3. Verifica che la categoria scelta sia ammessa per la tipologia scelta,
   leggendo la struttura disponibile (3.1) — non una verifica isolata sulla
   sola tabella `CategoriaDocumento`.
4. Crea una riga in `ModelloDocumento` (stato `ATTIVA`, `public_id`
   assegnato progressivamente).
5. Registra un evento in `AuditEventoModello` (`MODELLO_CREATO`).

### 3.4 Creazione della versione (i campi effettivi scelti)

```text
POST /api/v1/builder/modelli/{modelloId}/versioni
{ "campi": [{"codice": "codice_bando", "lingua": "IT"}, ...] }
```

Comportamento (`crea_versione`):

1. Per ogni campo richiesto, lo cerca fra i `campi_disponibili` (3.2) per
   quel tipo documento — se non lo trova, errore `CAMPO_NON_AMMESSO`.
2. Copia etichetta/tipo dato/obbligatorieta'/ordine/validazione dal registro
   dentro nuove righe `ModelloCampoRichiesto`, legate alla nuova
   `ModelloDocumentoVersione` (stato iniziale `BOZZA`).

**Punto architetturale importante**: da questo momento in poi,
`ModelloCampoRichiesto` e' uno **snapshot permanente** — una copia, non un
riferimento vivo al registro. Se domani il registro cambia, i modelli gia'
creati non cambiano: e' il meccanismo che garantisce che un documento
generato mesi fa resti ricostruibile identico (`DEC-001-OWNERSHIP-DATI-ESTERNI`).

### 3.5 Pubblicazione

```text
POST /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/invia-revisione
POST /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/approva
POST /api/v1/builder/modelli/{modelloId}/versioni/{versioneId}/pubblica
```

Ogni passo ri-verifica l'autorizzazione per contesto (3.3, punto 2). Quando
la transizione a `PUBBLICATO` avviene, il sistema cerca automaticamente
un'altra versione gia' `PUBBLICATO` per la stessa combinazione tipo
documento/categoria/tipologia/variante e, se la trova, la porta ad
`ARCHIVIATO` nella stessa operazione — non possono mai coesistere due
versioni correnti pubblicate per la stessa variante.

**Buco esplicito**: questo controllo e' solo applicativo (leggi-poi-scrivi),
non un vincolo a livello database. Con scritture concorrenti sullo stesso
modello, in teoria potrebbero risultare due versioni `PUBBLICATO` correnti.
Accettabile con un solo operatore alla volta (oggi), da chiudere prima di un
uso multi-utente reale.

---

## 4. Generazione Di Un Documento Da Un Modello Pubblicato

Questa parte esisteva gia' prima di stasera (spec `001`) e **non e' stata
modificata**: la prova che funziona con i modelli nuovi appena descritti e'
proprio la dimostrazione che il motore e' generico.

```text
GET  /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=...
GET  /api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti
POST /api/v1/documenti/valida
POST /api/v1/documenti/genera
```

1. GEBAN cerca i modelli disponibili per un tipo/profilo/tipologia che gia'
   conosce (primo endpoint) e ottiene `modello_versione_id` (l'intero
   `public_id` stabile, non l'UUID interno).
2. Facoltativo: consulta il contratto dati di quella versione (secondo
   endpoint) per sapere quali campi mandare.
3. `POST /documenti/valida`: il servizio (`backend/app/validation/service.py`)
   carica `ModelloCampoRichiesto` **solo per quella versione** (lo snapshot
   di 3.4) e valida il payload ricevuto contro quello — nessuna lettura del
   registro contratti dati o della categorizzazione a questo punto.
4. `POST /documenti/genera`: stessa validazione, poi restituisce un esito
   "generazione simulata" con un link placeholder. **Non produce ancora un
   PDF reale**: il motore di rendering (spec `004`) non e' implementato.

**Perche' questo dimostra che il motore e' generico**: lo stesso identico
endpoint, senza modifiche, valida e "genera" sia i modelli demo pre-esistenti
sia i modelli nuovi creati stasera tramite il builder — la genericita' non
e' teorica, e' stata provata con un test end-to-end reale
(`backend/tests/builder/test_builder_flow_api.py::test_flusso_completo_creazione_pubblicazione_e_generazione_documento`).

---

## Punti Aperti Da Verificare (elenco esplicito dei buchi noti)

- **Nessun adapter HTTP verso GEBAN**: tutto il flusso di categorizzazione/
  campi (sezioni 3.1/3.2) oggi dipende da dati locali fissati a mano, non da
  una fonte esterna viva. Finche' non esiste `AdapterHTTP` + il passo 2, ogni
  modifica reale del catalogo GEBAN richiede un intervento manuale qui.
- **Nessuna interfaccia che genera il contratto per l'integratore** (passo
  1): il file consegnato a GEBAN stasera e' stato scritto a mano.
- **Nessun test di connessione/stato "connesso"** (passo 2): un tipo
  documento puo' essere usato per creare modelli senza che nessuna
  integrazione reale sia mai stata verificata.
- **Nessuna modifica/derivazione di una versione gia' pubblicata**: solo
  creazione di versioni nuove da zero.
- **Nessuna route dedicata per archiviare/sospendere** una versione
  pubblicata fuori dal ciclo automatico di pubblicazione.
- **Nessun vincolo database anti-doppia-pubblicazione concorrente** (solo
  applicativo, vedi 3.5).
- **`/documenti/genera` non produce un PDF reale** (placeholder, in attesa
  della spec `004`).
- **Nessun contratto OpenAPI pubblicato** per le route `/api/v1/builder/*`
  descritte in questa pagina (esistono ma non sono ancora documentate
  formalmente, a differenza delle route `001`).

## Riferimenti

- `specs/001-catalogo-contratto-geban/` — catalogo, contratto dati,
  validazione/generazione (sezione 4).
- `specs/002-builder-modelli/` — builder, creazione modello/versione,
  pubblicazione (sezione 3).
- `specs/010-configurazione-cataloghi-integrazioni/` — configurazione
  struttura, generazione contratto, registrazione endpoint (sezioni 1 e 2,
  non ancora implementate).
- `docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md` — perche'
  la categorizzazione di un tipo documento integrato non deve restare un
  seed permanente.
- `docs/decision-register.yaml` — `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`,
  `DEC-002-PORTS-ADAPTERS-DISCOVERY`, `DEC-001-OWNERSHIP-DATI-ESTERNI`.
