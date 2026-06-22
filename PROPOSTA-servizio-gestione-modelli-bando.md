# GEBAN - Servizio Gestione Modelli e Generazione Documenti
## Proposta di progetto, flussi, modello dati, API e piano di sviluppo

---

## 0. Sintesi

Il servizio nasce per gestire la progettazione di modelli documentali e la generazione di
documenti a partire da dati ricevuti da sistemi esterni. Il primo caso d'uso e' la
generazione dei **bandi di concorso** richiesti da GEBAN, ma l'impianto viene progettato in
modo generalizzato per poter supportare anche altre tipologie documentali.

Il servizio si occupa di:

- definire tipi documento;
- definire categorie e sottocategorie documentali;
- progettare modelli documentali versionati;
- definire i campi/etichette richiesti per generare uno specifico modello;
- esporre a GEBAN il catalogo dei modelli disponibili e pubblicati;
- esporre a GEBAN il contratto dati richiesto per un modello;
- ricevere da GEBAN un payload dinamico validato contro il contratto del modello;
- generare PDF bozza o PDF ufficiale;
- salvare il PDF nel documentale configurato, eventualmente basato su S3/storage compatibile;
- restituire a GEBAN il riferimento al documento generato.

La distinzione fondamentale e':

```text
GEBAN
  gestisce processo amministrativo, utenti, stato del bando, workflow e raccolta dati

Servizio Gestione Modelli e Generazione Documenti
  gestisce tipi documento, categorie, modelli, campi richiesti, sezioni, generazione PDF

Documentale / storage configurato
  conserva i file PDF generati
```

Il servizio non legge direttamente il DB GEBAN. GEBAN interagisce tramite API.

---

## 1. Principio Architetturale

Il servizio non deve conoscere a codice tutti i possibili documenti generabili.
La configurazione dei documenti viene gestita nel builder interno.

Per ogni modello pubblicato il servizio espone a GEBAN:

- tipo documento;
- categoria/sottocategoria;
- modello disponibile;
- versione del modello;
- lista dei campi necessari per generare il documento;
- regole di validazione dei campi;
- endpoint di generazione.

GEBAN non replica la logica dei modelli. La interroga passando il contesto del processo,
ad esempio tipologia bando e categoria, e riceve solo i modelli definitivi pubblicati.

```text
Builder modelli
  definisce cosa si puo' generare e quali dati servono

GEBAN
  chiede al servizio cosa e' generabile, mostra la maschera all'utente e invia i dati

Servizio modelli
  valida i dati, genera il documento e restituisce il PDF/riferimento
```

---

## 2. Flusso Di Progettazione Del Modello

Questa fase avviene dentro il modulo builder/manager modelli.

### 2.1 Attori

| Attore | Ruolo |
|---|---|
| Gestore modelli | Crea e modifica tipi documento, categorie, campi e modelli |
| Validatore/Approvatore modello | Approva o pubblica una versione modello |
| Sistema GEBAN | Vede solo modelli pubblicati tramite API |

### 2.2 Flusso

```text
1. Il gestore crea o aggiorna un tipo documento
   Esempio: BANDO_CONCORSO

2. Il gestore crea categorie/sottocategorie del tipo documento
   Esempio: CTER, RICERCATORE, TECNOLOGO, MOBILITA

3. Il gestore crea un modello documentale
   Esempio: Bando CTER tempo indeterminato

4. Il gestore crea una versione del modello
   Esempio: versione 1.0

5. Il gestore definisce le sezioni del modello
   Esempio: intestazione, visti, requisiti, domanda, firma

6. Il gestore definisce i campi richiesti per generare quella versione
   Esempio: PROFILO, LIVELLO, NUM_POSTI, SEDI, RESPONSABILE_PROCEDIMENTO

7. Il gestore usa i campi come placeholder nel testo delle sezioni
   Esempio: "Sono indetti n. {{NUM_POSTI}} posti per il profilo {{PROFILO}}"

8. Il modello passa a revisione/approvazione

9. Solo le versioni pubblicate vengono esposte a GEBAN
```

### 2.3 Stati Del Modello

```text
BOZZA
IN_REVISIONE
APPROVATO
PUBBLICATO
ARCHIVIATO
SOSPESO
```

Regole:

- GEBAN vede solo versioni `PUBBLICATO`;
- lo stato `APPROVATO` resta interno al flusso di revisione e non rende automaticamente
  il modello disponibile ai sistemi esterni;
- una versione usata per generare documenti non viene cancellata;
- modifiche strutturali producono una nuova versione;
- una versione pubblicata non viene modificata sovrascrivendo il contenuto gia' usato.

---

## 3. Flusso GEBAN - Servizio Modelli

Questa e' la fase operativa vista da GEBAN e dagli utenti che lavorano sul processo.

### 3.1 Flusso Utente GEBAN

```text
1. L'utente lavora nel processo GEBAN
   Esempio: deve generare un bando di concorso

2. GEBAN chiama il servizio modelli per ottenere i modelli definitivi disponibili
   passando il contesto del processo
   Esempio: tipo documento, tipologia bando, categoria, data di riferimento

3. GEBAN mostra all'utente le scelte disponibili
   Esempio: Bando di concorso

4. GEBAN mostra categorie/sottocategorie disponibili, se previste dal processo
   Esempio: CTER, Ricercatore, Tecnologo

5. GEBAN mostra i modelli pubblicati disponibili per quella categoria

6. L'utente seleziona il modello da usare

7. GEBAN chiede al servizio modelli i campi richiesti per quella versione modello

8. Il servizio restituisce il contratto dati del modello:
   - codice ed etichetta dei campi;
   - obbligatorieta';
   - tipi dato;
   - eventuali vincoli, valori ammessi e regole di validazione

9. GEBAN costruisce la maschera dinamica usando i campi ricevuti

10. L'utente compila i dati in GEBAN
    I campi non obbligatori possono essere lasciati vuoti

11. GEBAN invia al servizio modelli la richiesta di generazione documento

12. Il servizio valida i dati ricevuti contro il contratto del modello

13. Il servizio genera il PDF, lo salva nel documentale e restituisce il riferimento a GEBAN
```

### 3.2 Estensione A Graduatorie, Verbali E Altri Documenti

Lo stesso flusso puo' essere usato anche per graduatorie, verbali e altri documenti
prodotti nel processo GEBAN.

In questo scenario non serve introdurre un'architettura diversa:

- `GRADUATORIA` puo' essere un tipo documento gestito dal builder;
- l'Ufficio Reclutamento puo' definire uno o piu' modelli di graduatoria;
- GEBAN interroga il catalogo per sapere quali modelli pubblicati sono disponibili;
- se per un contesto esiste un solo modello valido, GEBAN puo' selezionarlo
  automaticamente senza mostrare una scelta all'utente;
- se nel tempo cambiano le regole, viene pubblicata una nuova versione o un nuovo modello;
- i modelli precedenti restano storicizzati per le generazioni gia' effettuate.

### 3.3 Ruoli

| Attore | Dove lavora | Cosa fa |
|---|---|---|
| Gestore modelli | Servizio modelli | Progetta tipi documento, categorie, modelli, campi e sezioni |
| Approvatore modelli | Servizio modelli | Approva/pubblica modelli |
| Utente GEBAN | GEBAN | Sceglie documento/modello e compila i dati richiesti |
| GEBAN | API servizio modelli | Interroga catalogo, invia dati, riceve PDF |
| Servizio modelli | Backend | Valida dati, genera PDF, salva e restituisce riferimento |

---

## 4. Categorizzazione Interna

La categorizzazione vive nel servizio modelli.

### 4.1 Tipo Documento

Rappresenta la famiglia documentale generale.

Esempi:

```text
BANDO_CONCORSO
GRADUATORIA
DECRETO
COMUNICAZIONE
VERBALE
ALLEGATO
```

### 4.2 Categoria Documento

Rappresenta una classificazione interna al tipo documento.

Esempio per `BANDO_CONCORSO`:

```text
CTER
RICERCATORE
TECNOLOGO
MOBILITA
CATEGORIE_PROTETTE
TEMPO_DETERMINATO
TEMPO_INDETERMINATO
```

### 4.3 Tipologia

La tipologia e' un ulteriore criterio di filtro usato dal sistema chiamante per individuare
i modelli applicabili al processo.

Nel caso GEBAN puo' corrispondere alla tipologia di bando gia' prevista nel processo.
Il servizio modelli la usa per filtrare il catalogo, ma non deriva da questa una
classificazione separata dei campi.

Esempi:

```text
TI
TD
MOBILITA
```

### 4.4 Modello Documento

Un modello e' associato a:

- tipo documento;
- categoria documento;
- eventuale tipologia del processo GEBAN;
- versione;
- stato;
- periodo di validita';
- sezioni;
- campi richiesti.

Esempio:

```text
Tipo documento: BANDO_CONCORSO
Categoria: CTER
Tipologia processo GEBAN: TI
Modello: Bando CTER tempo indeterminato
Versione: 1.0
Stato: PUBBLICATO
```

---

## 5. Campi Richiesti E Contratto Dati

### 5.1 Approccio Scelto

Il servizio usa un approccio **schema-driven**:

```text
metadati campi nel DB
API che espone i campi a GEBAN
maschera dinamica costruita da GEBAN
payload JSON dinamico inviato a generazione
validazione backend contro i metadati/schema del modello
```

L'API di generazione ha una struttura fissa, ma i dati del documento sono dinamici.
Il builder/generatore e' la fonte del contratto dati: per ogni modello pubblicato espone
a GEBAN l'elenco dei campi da valorizzare, con obbligatorieta', tipi dato e vincoli.
GEBAN non deve applicare classificazioni proprie ai campi: deve usare il contratto
restituito dall'API per costruire la maschera e inviare i dati.

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "codice_tipologia": "TI",
  "modello_versione_id": 27,
  "formato_output": "PDF",
  "dati": {
    "PROFILO": "Collaboratore Tecnico Enti di Ricerca",
    "LIVELLO": "VI",
    "NUM_POSTI": 2,
    "RESPONSABILE_PROCEDIMENTO": "Mario Rossi"
  }
}
```

La parte stabile e':

- `sistema_richiedente`;
- `external_context_id`;
- `codice_tipologia`, quando il sistema chiamante la prevede;
- `modello_versione_id`;
- `formato_output`;
- `dati`.

La parte variabile e' il contenuto di `dati`.

### 5.2 Perche' Non Usare Campi Fissi

Non vengono creati DTO diversi per ogni documento.

Esempio da evitare:

```text
GeneraBandoCterRequest
GeneraBandoRicercatoreRequest
GeneraDecretoRequest
GeneraVerbaleRequest
```

Questa soluzione obbligherebbe a sviluppare codice nuovo per ogni modello.

La soluzione adottata prevede invece un unico payload generico validato contro il
contratto del modello.

### 5.3 Campi Richiesti

Ogni versione modello dichiara i propri campi richiesti.

Esempio:

| Codice | Etichetta | Tipo | Obbligatorio |
|---|---|---|---|
| `PROFILO` | Profilo professionale | string | si |
| `LIVELLO` | Livello | string | si |
| `NUM_POSTI` | Numero posti | number | si |
| `SEDI` | Sedi di destinazione | array | si |
| `RESPONSABILE_PROCEDIMENTO` | Responsabile procedimento | string | si |
| `DATA_SCADENZA` | Data scadenza domanda | date | no |

La tipologia bando e la categoria aiutano a filtrare i modelli disponibili, ma e' la
**versione del modello** a definire il contratto esatto dei dati richiesti.

### 5.4 Validazione

Il backend valida il payload ricevuto da GEBAN:

1. il modello esiste;
2. la versione e' pubblicata;
3. tutti i campi obbligatori sono presenti;
4. i tipi dati sono corretti;
5. i valori rispettano eventuali vincoli;
6. i campi non ammessi vengono rifiutati o segnalati;
7. i placeholder del modello sono risolvibili con i dati ricevuti.

### 5.5 JSON Schema

I metadati dei campi possono essere esposti anche come JSON Schema.

Esempio:

```json
{
  "type": "object",
  "required": ["PROFILO", "LIVELLO", "NUM_POSTI"],
  "additionalProperties": false,
  "properties": {
    "PROFILO": { "type": "string" },
    "LIVELLO": { "type": "string" },
    "NUM_POSTI": { "type": "number" },
    "DATA_SCADENZA": { "type": "string", "format": "date" }
  }
}
```

La prima implementazione puo' salvare i metadati campo in tabella e generare lo schema
in risposta API.

---

## 6. Placeholder E Sezioni

Le sezioni del modello usano placeholder nel formato:

```text
{{PROFILO}}
{{LIVELLO}}
{{NUM_POSTI}}
{{RESPONSABILE_PROCEDIMENTO}}
```

Regole:

- ogni placeholder usato nel testo deve corrispondere a un campo richiesto o a un campo calcolato;
- una versione modello non puo' essere pubblicata se contiene placeholder non dichiarati;
- la generazione fallisce se mancano dati per placeholder obbligatori;
- la risoluzione placeholder avviene nel backend;
- GEBAN non risolve direttamente i placeholder.

---

## 7. Proprietario Dei Dati

### 7.1 Dati Proprietari Di GEBAN

GEBAN resta proprietario dei dati di processo:

- id del processo/bando;
- codice bando;
- stato del procedimento;
- utenti e ruoli nel processo;
- dati amministrativi raccolti;
- avanzamento del workflow;
- riferimenti al documento generato.

### 7.2 Dati Proprietari Del Servizio Modelli

Il servizio modelli resta proprietario di:

- tipi documento;
- categorie documento;
- modelli;
- versioni modello;
- sezioni;
- campi richiesti;
- validazioni;
- generazioni documento;
- riferimenti ai PDF prodotti;
- audit interno.

### 7.3 Snapshot

Il servizio salva uno snapshot dei dati ricevuti nella richiesta di generazione.
Lo snapshot e' una copia locale minima dei dati usati per generare il documento.

Serve a:

- ricostruire con quali dati e' stato generato il PDF;
- rigenerare il documento in modo controllato;
- evitare dipendenze dirette dal DB GEBAN;
- confrontare eventuali aggiornamenti successivi.

Lo snapshot non replica l'intero DB GEBAN e non sostituisce le anagrafiche ufficiali.

---

## 8. Schema Dati Proposto

### 8.1 Enum

```sql
CREATE TYPE stato_modello_versione AS ENUM (
    'BOZZA',
    'IN_REVISIONE',
    'APPROVATO',
    'PUBBLICATO',
    'ARCHIVIATO',
    'SOSPESO'
);

CREATE TYPE stato_generazione_documento AS ENUM (
    'RICHIESTA',
    'VALIDATA',
    'GENERATA',
    'FALLITA',
    'ANNULLATA'
);

CREATE TYPE formato_output AS ENUM ('PDF', 'HTML');
```

### 8.2 `tipo_documento`

```sql
CREATE TABLE tipo_documento (
    codice        VARCHAR(50) PRIMARY KEY,
    descrizione   VARCHAR(300) NOT NULL,
    attivo        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Esempi:

```text
BANDO_CONCORSO
GRADUATORIA
DECRETO
COMUNICAZIONE
VERBALE
```

### 8.3 `categoria_documento`

```sql
CREATE TABLE categoria_documento (
    codice_tipo_documento VARCHAR(50) NOT NULL REFERENCES tipo_documento(codice),
    codice                VARCHAR(50) NOT NULL,
    descrizione           VARCHAR(300) NOT NULL,
    attiva                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (codice_tipo_documento, codice)
);
```

Esempi per `BANDO_CONCORSO`:

```text
CTER
RICERCATORE
TECNOLOGO
MOBILITA
```

### 8.4 `modello_documento`

```sql
CREATE TABLE modello_documento (
    id                       BIGSERIAL PRIMARY KEY,
    codice                   VARCHAR(100) NOT NULL UNIQUE,
    descrizione              VARCHAR(500) NOT NULL,
    codice_tipo_documento    VARCHAR(50) NOT NULL REFERENCES tipo_documento(codice),
    codice_categoria         VARCHAR(50) NOT NULL,
    codice_tipologia         VARCHAR(50),
    attivo                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),

    FOREIGN KEY (codice_tipo_documento, codice_categoria)
        REFERENCES categoria_documento(codice_tipo_documento, codice)
);
```

### 8.5 `modello_documento_versione`

```sql
CREATE TABLE modello_documento_versione (
    id                    BIGSERIAL PRIMARY KEY,
    modello_documento_id   BIGINT NOT NULL REFERENCES modello_documento(id),
    numero_versione        INTEGER NOT NULL,
    stato                 stato_modello_versione NOT NULL DEFAULT 'BOZZA',
    data_inizio_validita   DATE NOT NULL,
    data_fine_validita     DATE,
    creato_da             VARCHAR(150),
    approvato_da          VARCHAR(150),
    pubblicato_da         VARCHAR(150),
    motivo_versione        TEXT,
    schema_json            JSONB,
    version               INTEGER NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (modello_documento_id, numero_versione)
);
```

Regola: non possono esistere due versioni `PUBBLICATO` dello stesso modello con periodi
di validita' sovrapposti.

### 8.6 `modello_campo_richiesto`

```sql
CREATE TABLE modello_campo_richiesto (
    id                         BIGSERIAL PRIMARY KEY,
    modello_documento_versione_id BIGINT NOT NULL REFERENCES modello_documento_versione(id) ON DELETE CASCADE,
    codice                     VARCHAR(100) NOT NULL,
    etichetta                  VARCHAR(300) NOT NULL,
    descrizione                TEXT,
    tipo_dato                  VARCHAR(50) NOT NULL,
    obbligatorio               BOOLEAN NOT NULL DEFAULT FALSE,
    ordine                     INTEGER NOT NULL,
    formato                    VARCHAR(100),
    valore_default             TEXT,
    opzioni                    JSONB,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (modello_documento_versione_id, codice)
);
```

Esempi di `tipo_dato`:

```text
string
number
date
boolean
array
object
```

### 8.7 `sezione_catalogo`

```sql
CREATE TABLE sezione_catalogo (
    id                       BIGSERIAL PRIMARY KEY,
    codice                   VARCHAR(100) NOT NULL UNIQUE,
    descrizione              VARCHAR(500) NOT NULL,
    testo_modificabile       BOOLEAN NOT NULL DEFAULT TRUE,
    attiva                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 8.8 `sezione_catalogo_versione`

```sql
CREATE TABLE sezione_catalogo_versione (
    id                    BIGSERIAL PRIMARY KEY,
    sezione_catalogo_id    BIGINT NOT NULL REFERENCES sezione_catalogo(id),
    numero_versione        INTEGER NOT NULL,
    stato                 stato_modello_versione NOT NULL DEFAULT 'BOZZA',
    testo_template         TEXT NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (sezione_catalogo_id, numero_versione)
);
```

### 8.9 `modello_documento_voce`

```sql
CREATE TABLE modello_documento_voce (
    id                         BIGSERIAL PRIMARY KEY,
    modello_documento_versione_id BIGINT NOT NULL REFERENCES modello_documento_versione(id) ON DELETE CASCADE,
    ordine                     INTEGER NOT NULL,
    tipo_voce                  VARCHAR(30) NOT NULL,
    sezione_catalogo_versione_id BIGINT REFERENCES sezione_catalogo_versione(id),
    descrizione                VARCHAR(500),
    testo_default              TEXT,
    obbligatoria               BOOLEAN NOT NULL DEFAULT FALSE,
    page_break_before          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (modello_documento_versione_id, ordine)
);
```

`tipo_voce`:

```text
SEZIONE_REF
LIBERA
FIRMA
```

### 8.10 `documento_generato`

```sql
CREATE TABLE documento_generato (
    id                         BIGSERIAL PRIMARY KEY,
    sistema_richiedente         VARCHAR(100) NOT NULL,
    external_context_id         VARCHAR(150) NOT NULL,
    modello_documento_versione_id BIGINT NOT NULL REFERENCES modello_documento_versione(id),
    stato                      stato_generazione_documento NOT NULL DEFAULT 'RICHIESTA',
    formato_output             formato_output NOT NULL DEFAULT 'PDF',
    dati_input_snapshot         JSONB NOT NULL DEFAULT '{}',
    esito_validazione           JSONB NOT NULL DEFAULT '{}',
    documentale_uri            TEXT,
    filename                   VARCHAR(300),
    sha256                     VARCHAR(64),
    generato_at                TIMESTAMPTZ,
    richiesto_da               VARCHAR(150),
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (sistema_richiedente, external_context_id, modello_documento_versione_id)
);
```

### 8.11 `audit_event`

```sql
CREATE TABLE audit_event (
    id              BIGSERIAL PRIMARY KEY,
    aggregate_type  VARCHAR(100) NOT NULL,
    aggregate_id    VARCHAR(100) NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    actor           VARCHAR(150),
    payload         JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 9. API Esposte Verso GEBAN

Base path: `/api/v1`.

### 9.1 Catalogo tipi documento

```http
GET /catalogo/tipi-documento
```

Risposta:

```json
{
  "items": [
    {
      "codice": "BANDO_CONCORSO",
      "descrizione": "Bando di concorso"
    },
    {
      "codice": "GRADUATORIA",
      "descrizione": "Graduatoria"
    },
    {
      "codice": "DECRETO",
      "descrizione": "Decreto"
    }
  ]
}
```

### 9.2 Categorie per tipo documento

```http
GET /catalogo/tipi-documento/{codiceTipoDocumento}/categorie
```

Esempio:

```http
GET /catalogo/tipi-documento/BANDO_CONCORSO/categorie
```

Risposta:

```json
{
  "tipo_documento": "BANDO_CONCORSO",
  "categorie": [
    {
      "codice": "CTER",
      "descrizione": "Collaboratore Tecnico Enti di Ricerca"
    },
    {
      "codice": "RICERCATORE",
      "descrizione": "Ricercatore"
    }
  ]
}
```

### 9.3 Modelli disponibili

```http
GET /catalogo/modelli?tipo_documento=BANDO_CONCORSO&codice_tipologia=TI&categoria=CTER
```

Regola: vengono restituiti solo modelli con versione `PUBBLICATO` e validi alla data di
riferimento, filtrati sul contesto passato da GEBAN.
Il contesto puo' includere tipo documento, categoria, tipologia e data di riferimento.
Questi parametri servono solo a selezionare i modelli disponibili; i campi da compilare
sono definiti dalla versione del modello e vengono letti dall'API dei campi richiesti.

Risposta:

```json
{
  "tipo_documento": "BANDO_CONCORSO",
  "codice_tipologia": "TI",
  "categoria": "CTER",
  "modelli": [
    {
      "modello_id": 12,
      "modello_versione_id": 27,
      "codice": "BANDO_CTER_TI",
      "descrizione": "Bando CTER tempo indeterminato",
      "versione": 1,
      "data_inizio_validita": "2026-01-01",
      "data_fine_validita": null
    }
  ]
}
```

Se la risposta contiene un solo modello valido, GEBAN puo' selezionarlo automaticamente
o mostrarlo all'utente in base alle proprie regole di interfaccia.

### 9.4 Campi richiesti per un modello

```http
GET /catalogo/modelli/{modelloVersioneId}/campi-richiesti
```

Risposta:

```json
{
  "modello_versione_id": 27,
  "tipo_documento": "BANDO_CONCORSO",
  "categoria": "CTER",
  "campi": [
    {
      "codice": "PROFILO",
      "etichetta": "Profilo professionale",
      "tipo": "string",
      "obbligatorio": true,
      "ordine": 1
    },
    {
      "codice": "LIVELLO",
      "etichetta": "Livello",
      "tipo": "string",
      "obbligatorio": true,
      "ordine": 2
    },
    {
      "codice": "NUM_POSTI",
      "etichetta": "Numero posti",
      "tipo": "number",
      "obbligatorio": true,
      "ordine": 3
    },
    {
      "codice": "SEDI",
      "etichetta": "Sedi",
      "tipo": "array",
      "obbligatorio": true,
      "ordine": 4
    },
    {
      "codice": "NOTE_INTEGRATIVE",
      "etichetta": "Note integrative",
      "tipo": "string",
      "obbligatorio": false,
      "ordine": 5
    }
  ],
  "schema": {
    "type": "object",
    "required": ["PROFILO", "LIVELLO", "NUM_POSTI", "SEDI"],
    "additionalProperties": false,
    "properties": {
      "PROFILO": { "type": "string" },
      "LIVELLO": { "type": "string" },
      "NUM_POSTI": { "type": "number" },
      "SEDI": { "type": "array" },
      "NOTE_INTEGRATIVE": { "type": "string" }
    }
  }
}
```

### 9.5 Validazione dati prima della generazione

```http
POST /documenti/valida
```

Request:

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "codice_tipologia": "TI",
  "modello_versione_id": 27,
  "dati": {
    "PROFILO": "Collaboratore Tecnico Enti di Ricerca",
    "LIVELLO": "VI",
    "NUM_POSTI": 2,
    "SEDI": [
      {
        "codice_sede": "RM001",
        "denominazione": "Istituto ...",
        "citta": "Roma",
        "num_posti": 2
      }
    ],
    "NOTE_INTEGRATIVE": ""
  }
}
```

Risposta positiva:

```json
{
  "valido": true,
  "errori": []
}
```

Risposta con errori:

```json
{
  "valido": false,
  "errori": [
    {
      "campo": "NUM_POSTI",
      "codice": "TIPO_NON_VALIDO",
      "messaggio": "Il campo NUM_POSTI deve essere numerico"
    },
    {
      "campo": "RESPONSABILE_PROCEDIMENTO",
      "codice": "CAMPO_OBBLIGATORIO",
      "messaggio": "Campo obbligatorio mancante"
    }
  ]
}
```

### 9.6 Generazione documento

```http
POST /documenti/genera
```

Request:

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "codice_tipologia": "TI",
  "modello_versione_id": 27,
  "formato_output": "PDF",
  "dati": {
    "CODICE_BANDO": "TI/CTER/2026/001",
    "PROFILO": "Collaboratore Tecnico Enti di Ricerca",
    "LIVELLO": "VI",
    "NUM_POSTI": 2,
    "SEDI": [
      {
        "codice_sede": "RM001",
        "denominazione": "Istituto ...",
        "citta": "Roma",
        "num_posti": 2
      }
    ],
    "NOTE_INTEGRATIVE": "",
    "RESPONSABILE_PROCEDIMENTO": "Mario Rossi",
    "DATA_SCADENZA": "2026-07-31"
  },
  "opzioni": {
    "tipo_pdf": "UFFICIALE",
    "salva_su_documentale": true
  }
}
```

Risposta:

```json
{
  "documento_generato_id": 501,
  "stato": "GENERATA",
  "filename": "bando-TI-CTER-2026-001.pdf",
  "documentale_uri": "documentale://geban/bandi/501",
  "sha256": "f4a7...",
  "download_url": "/api/v1/documenti-generati/501/download"
}
```

### 9.7 Download documento generato

```http
GET /documenti-generati/{id}/download
```

### 9.8 Stato generazione

```http
GET /documenti-generati/{id}
```

Risposta:

```json
{
  "id": 501,
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "modello_versione_id": 27,
  "stato": "GENERATA",
  "documentale_uri": "documentale://geban/bandi/501",
  "sha256": "f4a7..."
}
```

---

## 10. API Interne Del Builder Modelli

Le API interne sono usate dal frontend del servizio per progettare e pubblicare modelli.

```http
GET    /tipi-documento
POST   /tipi-documento
PUT    /tipi-documento/{codice}

GET    /tipi-documento/{codice}/categorie
POST   /tipi-documento/{codice}/categorie
PUT    /tipi-documento/{codice}/categorie/{categoria}

GET    /modelli
POST   /modelli
GET    /modelli/{id}

POST   /modelli/{id}/versioni
GET    /modelli/{id}/versioni/{versioneId}
PUT    /modelli/{id}/versioni/{versioneId}
POST   /modelli/{id}/versioni/{versioneId}/campi
POST   /modelli/{id}/versioni/{versioneId}/sezioni
POST   /modelli/{id}/versioni/{versioneId}/pubblica
POST   /modelli/{id}/versioni/{versioneId}/archivia
```

---

## 11. Frontend Del Servizio

### 11.1 Area Builder Modelli

Funzioni:

- gestione tipi documento;
- gestione categorie per tipo documento;
- gestione modelli;
- gestione versioni modello;
- definizione campi richiesti;
- definizione schema/validazioni;
- composizione sezioni;
- anteprima modello;
- approvazione/pubblicazione modello;
- archiviazione modello.

### 11.2 Area Consultazione Generazioni

Funzioni:

- lista documenti generati;
- filtro per sistema richiedente;
- filtro per tipo documento/categoria;
- stato generazione;
- download PDF;
- visualizzazione payload dati ricevuto;
- visualizzazione esito validazione;
- audit generazione.

### 11.3 GEBAN

GEBAN non usa il frontend del builder per compilare i dati.
GEBAN interroga le API catalogo, costruisce la propria maschera e invia la richiesta di
generazione.

---

## 12. Sicurezza, Autenticazione E Autorizzazione

Il servizio viene protetto tramite SSO centralizzato **Keycloak**.
Tutte le chiamate API devono arrivare con token JWT Bearer valido.

Il backend valida:

- firma del token;
- issuer;
- audience/client;
- scadenza;
- ruoli applicativi;
- eventuali claim contestuali trasmessi da GEBAN.

### 12.1 Scelta Di Integrazione Autenticativa

Per il flusso ordinario di generazione documenti viene adottata la propagazione
dell'identita' dell'utente autenticato in GEBAN verso GEMODO tramite Keycloak.

La chiamata GEBAN -> GEMODO deve permettere a GEMODO di verificare:

- quale utente ha richiesto l'operazione;
- che la chiamata arriva dal backend GEBAN;
- che il token e' destinato alle API GEMODO;
- che l'utente ha le autorizzazioni necessarie nel contesto GEBAN.

La soluzione prevista e':

```text
Utente -> GEBAN frontend -> GEBAN backend -> GEMODO backend
                         token utente / token exchange Keycloak
```

Il token ricevuto da GEMODO deve contenere o rendere verificabili:

- identita' utente;
- client chiamante GEBAN;
- audience GEMODO;
- ruoli applicativi;
- eventuale contesto autorizzativo GEBAN.

Esempio di token/claim attesi:

```json
{
  "sub": "user-123",
  "preferred_username": "mario.rossi",
  "azp": "geban-backend",
  "aud": ["gemodo-backend"],
  "realm_access": {
    "roles": ["DOCUMENTI_GENERATORE"]
  },
  "geban_context": {
    "external_context_id": "BANDO-12345",
    "azioni": ["GENERA_DOCUMENTO", "SCARICA_DOCUMENTO"]
  }
}
```

Il client tecnico `SYSTEM_GEBAN` resta previsto solo per chiamate tecniche, batch o
integrazioni non legate a una specifica azione utente. Nel flusso ordinario di
generazione documento viene mantenuta la tracciabilita' dell'utente reale.

### 12.2 Client Keycloak Previsti

| Client | Tipo | Uso |
|---|---|---|
| `geban-frontend` | public client | Login utente su GEBAN |
| `geban-backend` | confidential client | Backend GEBAN autorizzato a chiamare GEMODO e a propagare/scambiare token |
| `gemodo-frontend` | public client | Login utenti che usano il builder modelli |
| `gemodo-backend` | resource server/API | API GEMODO protette |

Regole:

- `gemodo-backend` accetta token con audience corretta;
- `geban-backend` deve essere riconosciuto come client chiamante autorizzato;
- il token utente propagato deve contenere ruoli o claim sufficienti alla generazione;
- le chiamate tecniche senza utente usano client tecnico dedicato e ruolo `SYSTEM_GEBAN`.

### 12.3 Tipologie Di Accesso

Sono previsti due canali principali:

| Canale | Descrizione |
|---|---|
| Utenti interni del servizio modelli | Accedono al frontend builder per creare, revisionare e pubblicare modelli |
| Sistema GEBAN | Chiama le API catalogo/generazione propagando l'identita' utente o, per batch, con client tecnico |

### 12.4 Ruoli Applicativi

| Ruolo | Permessi |
|---|---|
| `MODELLI_ADMIN` | Gestione completa di configurazioni, tipi documento, categorie e modelli |
| `MODELLI_GESTORE` | Creazione e modifica di modelli in stato `BOZZA` |
| `MODELLI_REVISORE` | Revisione delle versioni modello prima della pubblicazione |
| `MODELLI_APPROVATORE` | Approvazione/pubblicazione versioni modello |
| `MODELLI_VIEWER` | Consultazione modelli e configurazioni |
| `DOCUMENTI_GENERATORE` | Richiesta di generazione documento |
| `DOCUMENTI_VIEWER` | Consultazione documenti generati e download, se autorizzato |
| `SYSTEM_GEBAN` | Chiamate tecniche da GEBAN verso catalogo, validazione e generazione |

### 12.5 Autorizzazione Alla Progettazione Dei Modelli

Le operazioni interne al builder richiedono ruoli specifici:

| Operazione | Ruoli ammessi |
|---|---|
| Creare tipo documento | `MODELLI_ADMIN` |
| Creare categoria documento | `MODELLI_ADMIN`, `MODELLI_GESTORE` |
| Creare modello | `MODELLI_ADMIN`, `MODELLI_GESTORE` |
| Modificare versione in bozza | `MODELLI_ADMIN`, `MODELLI_GESTORE` |
| Mandare modello in revisione | `MODELLI_ADMIN`, `MODELLI_GESTORE` |
| Approvare/pubblicare modello | `MODELLI_ADMIN`, `MODELLI_APPROVATORE` |
| Archiviare modello | `MODELLI_ADMIN`, `MODELLI_APPROVATORE` |

La pubblicazione di un modello richiede sempre controllo backend.
Il frontend abilita o disabilita le azioni, ma la regola viene applicata dal servizio.

### 12.6 Autorizzazione Alla Generazione Documenti

GEBAN puo' richiedere la generazione solo se il token ricevuto da GEMODO consente di
verificare:

- identita' dell'utente richiedente;
- client chiamante `geban-backend`;
- audience `gemodo-backend`;
- ruolo applicativo `DOCUMENTI_GENERATORE` o claim contestuale equivalente;
- autorizzazione dell'utente sul processo GEBAN specifico.

Esempio di claim contestuale:

```json
{
  "sub": "mario.rossi",
  "preferred_username": "mario.rossi",
  "azp": "geban-backend",
  "aud": ["gemodo-backend"],
  "roles": ["DOCUMENTI_GENERATORE"],
  "geban_context": {
    "external_context_id": "BANDO-12345",
    "azioni": ["GENERA_DOCUMENTO", "SCARICA_DOCUMENTO"]
  }
}
```

Il servizio verifica che la richiesta di generazione sia coerente con:

- sistema richiedente;
- modello richiesto;
- stato del modello;
- permessi del chiamante;
- eventuale contesto GEBAN ricevuto.

### 12.7 Payload Di Generazione E Dati Autorizzativi

La richiesta di generazione contiene i dati del documento e puo' contenere una sezione
di contesto/autorizzazione trasmessa da GEBAN. Questa sezione non sostituisce il token:
serve per audit e per registrare il contesto applicativo della generazione.

Esempio:

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "modello_versione_id": 27,
  "formato_output": "PDF",
  "dati": {
    "CODICE_BANDO": "TI/CTER/2026/001",
    "PROFILO": "Collaboratore Tecnico Enti di Ricerca",
    "LIVELLO": "VI",
    "NUM_POSTI": 2
  },
  "contesto_autorizzativo": {
    "utente_richiedente": "mario.rossi",
    "ruoli_geban": ["REFERENTE_BANDO"],
    "azioni_autorizzate": ["GENERA_DOCUMENTO", "SCARICA_DOCUMENTO"]
  }
}
```

Il token resta la fonte primaria dell'autenticazione.
Il `contesto_autorizzativo` serve come informazione applicativa trasmessa da GEBAN e viene
salvato nello snapshot della generazione per audit.

### 12.8 Chiamate Tecniche E Batch

Per chiamate non riconducibili a un utente specifico, ad esempio job schedulati o
sincronizzazioni tecniche, GEBAN usa un client tecnico Keycloak con ruolo `SYSTEM_GEBAN`.

Regole:

- le API di generazione ordinaria richiedono identita' utente propagata;
- le API tecniche abilitate a `SYSTEM_GEBAN` devono essere esplicitamente censite;
- ogni chiamata tecnica viene auditata con client chiamante, timestamp e payload.

### 12.9 Audit Sicurezza

Devono essere auditati:

- creazione modello;
- modifica versione modello;
- richiesta approvazione;
- pubblicazione modello;
- archiviazione modello;
- richiesta generazione documento;
- validazione fallita;
- generazione PDF;
- download PDF;
- errori di autorizzazione.

---

## 13. Storage PDF

Il PDF generato viene salvato nel documentale gia' usato dai moduli applicativi, in modo
che sia disponibile a GEBAN, Selezioni Online e agli altri moduli autorizzati.
S3 o uno storage compatibile possono restare un dettaglio tecnico interno del documentale,
ma il contratto verso GEBAN deve restituire il riferimento documentale.

Il servizio salva:

- `documentale_uri`;
- filename;
- hash SHA-256;
- data generazione;
- modello/versione usata;
- payload dati ricevuto;
- esito validazione.

---

## 14. Idempotenza

La generazione deve essere idempotente rispetto a:

```text
sistema_richiedente
external_context_id
modello_versione_id
tipo_pdf/formato_output
```

Regole:

- se la stessa richiesta arriva due volte con stessi dati, il servizio restituisce il
  documento gia' generato;
- se la stessa chiave arriva con dati diversi, il servizio restituisce `409 CONFLICT`;
- se GEBAN vuole rigenerare un documento deve inviare una nuova richiesta con un contesto
  o una revisione esplicita.

---

## 15. Predisposizione Per AI, Documentazione Assistita E MCP

Il servizio viene progettato con una struttura dati e API documentate in modo da poter
essere usato in futuro anche da strumenti AI interni, senza rendere l'AI necessaria per
il flusso principale.

La generazione dei documenti resta deterministica:

```text
modello pubblicato + dati validati + template = PDF generato
```

L'AI puo' supportare gli utenti e gli amministratori, ma non deve modificare o generare
atti ufficiali senza validazione, audit e conferma umana.

### 15.1 Casi D'Uso AI Ammessi

Possibili evoluzioni:

- assistente per consultare la documentazione del servizio;
- assistente per spiegare quali campi servono per un modello;
- supporto alla ricerca di modelli disponibili;
- suggerimento di nuove sezioni o placeholder durante la progettazione;
- confronto tra versioni di modello;
- riepilogo delle differenze tra versioni pubblicate;
- supporto alla scrittura di bozze testuali non ufficiali.

Non rientrano nel primo rilascio:

- generazione automatica non supervisionata del testo ufficiale;
- modifica automatica di modelli pubblicati;
- pubblicazione automatica di versioni modello;
- invio automatico di documenti senza validazione deterministica.

### 15.2 MCP Come Possibile Integrazione Futura

Il **Model Context Protocol (MCP)** e' uno standard aperto per collegare applicazioni AI
a sistemi esterni, dati e strumenti. MCP segue un'architettura client-server e consente
ai server di esporre strumenti, risorse e prompt riutilizzabili.

Per GEMODO si puo' prevedere in futuro un server MCP interno che esponga in sola lettura:

- catalogo tipi documento;
- categorie documento;
- modelli pubblicati;
- campi richiesti per modello;
- schema JSON dei dati richiesti;
- stato generazioni;
- documentazione tecnica e contratti API.

Eventuali tool MCP di scrittura devono essere molto limitati e protetti:

- creazione bozza modello;
- generazione PDF bozza;
- validazione payload;
- confronto versioni.

Azioni come pubblicazione modello, archiviazione, generazione PDF ufficiale e download di
documenti devono restare soggette a ruoli, audit e conferma esplicita.

### 15.3 Accortezze Di Sicurezza AI

L'uso di AI/MCP introduce rischi specifici, in particolare prompt injection, uso improprio
dei tool, fuga di dati e confusione tra contenuto generato e contenuto approvato.

Regole:

- nessun output AI viene considerato ufficiale senza validazione applicativa;
- i tool AI devono rispettare gli stessi ruoli Keycloak delle API ordinarie;
- i tool MCP devono esporre solo dati coerenti con i permessi dell'utente;
- ogni azione eseguita tramite AI deve essere auditata;
- i documenti ufficiali vengono generati solo da modelli pubblicati e dati validati;
- i contenuti proposti dall'AI devono essere marcati come bozza/suggerimento;
- nessun prompt o risposta AI deve contenere segreti, token o credenziali.

### 15.4 Documentazione AI-Ready

Per rendere il servizio piu' facile da usare anche con strumenti AI, la documentazione deve
essere mantenuta in forma strutturata:

- OpenAPI aggiornata per tutte le API;
- esempi JSON per catalogo, campi richiesti, validazione e generazione;
- schema JSON generato per ogni modello pubblicato;
- changelog delle versioni modello;
- ADR per decisioni architetturali;
- documentazione dei ruoli e delle autorizzazioni.

### 15.5 Collocazione Nel Piano

AI e MCP non sono prerequisiti del primo rilascio.
Il primo rilascio deve consegnare:

- builder modelli;
- API catalogo;
- validazione dati;
- generazione PDF;
- sicurezza Keycloak;
- audit.

La predisposizione AI consiste nel progettare API, documentazione e permessi in modo
compatibile con una futura esposizione MCP o con assistenti interni.

---

## 16. Piano Di Sviluppo

### 16.1 Fondamenta

- [ ] Setup backend Python FastAPI
- [ ] Setup frontend Angular
- [ ] Setup PostgreSQL
- [ ] Setup documentale locale/mock
- [ ] Setup Keycloak locale
- [ ] OpenAPI/Swagger

### 16.2 Database

- [ ] Enum stati modello e generazione
- [ ] Tabella `tipo_documento`
- [ ] Tabella `categoria_documento`
- [ ] Tabella `modello_documento`
- [ ] Tabella `modello_documento_versione`
- [ ] Tabella `modello_campo_richiesto`
- [ ] Tabella `sezione_catalogo`
- [ ] Tabella `sezione_catalogo_versione`
- [ ] Tabella `modello_documento_voce`
- [ ] Tabella `documento_generato`
- [ ] Tabella `audit_event`
- [ ] Seed tipi documento/categorie/modelli demo

### 16.3 Backend Builder

- [ ] CRUD tipi documento
- [ ] CRUD categorie documento
- [ ] CRUD modelli documento
- [ ] CRUD versioni modello
- [ ] Gestione campi richiesti
- [ ] Generazione JSON Schema da campi richiesti
- [ ] Gestione sezioni modello
- [ ] Pubblicazione modello
- [ ] Archiviazione modello
- [ ] Validazione placeholder contro campi richiesti

### 16.4 Backend API GEBAN

- [ ] API catalogo tipi documento
- [ ] API categorie per tipo documento
- [ ] API modelli disponibili
- [ ] API campi richiesti/schema
- [ ] API validazione dati
- [ ] API generazione documento
- [ ] API download documento
- [ ] API stato generazione
- [ ] Idempotenza generazione
- [ ] Gestione errori di validazione
- [ ] OpenAPI completa con esempi JSON

### 16.5 Generazione PDF

- [ ] Rendering HTML da modello e dati
- [ ] Risoluzione placeholder
- [ ] Sanitizzazione HTML
- [ ] Generazione PDF
- [ ] Salvataggio nel documentale
- [ ] Calcolo hash
- [ ] Restituzione riferimento a GEBAN

### 16.6 Frontend Builder

- [ ] Gestione tipi documento
- [ ] Gestione categorie
- [ ] Gestione modelli
- [ ] Editor campi richiesti
- [ ] Editor sezioni
- [ ] Anteprima modello
- [ ] Pubblicazione/archiviazione
- [ ] Consultazione generazioni

### 16.7 Mock E Test

- [ ] Mock GEBAN per interrogare catalogo
- [ ] Mock GEBAN per inviare payload generazione
- [ ] Test validazione schema
- [ ] Test generazione PDF
- [ ] Test idempotenza
- [ ] Test end-to-end catalogo -> campi -> generazione -> download

---

## 17. Decisioni Da Confermare

1. Nome definitivo del servizio.
2. Stati definitivi di approvazione/pubblicazione modello.
3. Lista iniziale dei tipi documento.
4. Lista iniziale categorie per `BANDO_CONCORSO`.
5. Regole definitive di idempotenza e rigenerazione.
6. Storage definitivo per PDF.
7. Regole di sicurezza per API catalogo e generazione.
8. Formato dei campi complessi, ad esempio sedi e liste.
9. Necessita' di generare solo PDF o anche altri formati.
10. Priorita' futura di integrazione AI/MCP.
