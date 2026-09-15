# Data Model - Catalogo Modelli E Contratto Dati GEBAN

## Nota Sull'Ownership Dei Dati (Cascading ADR 0001, 2026-09-15)

`docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md` e le decisioni
`DEC-001-OWNERSHIP-DATI-ESTERNI`/`DEC-002-PORTS-ADAPTERS-DISCOVERY` (entrambe
`CONFERMATA`) cambiano la semantica — non necessariamente lo schema — di
`CategoriaDocumento`, `TipologiaDocumento` e `RegistroContrattiDati` sotto. Per
ogni `TipoDocumento`, la sorgente di queste tre entita' dipende dal tipo di
Ufficio proprietario:

- **Tipo documento integrato** (posseduto da un sistema esterno con propria API,
  oggi `BANDO_CONCORSO` per GEBAN): le righe sono una **cache locale a TTL breve**,
  popolate/aggiornate da un adapter HTTP che chiama l'endpoint di discovery
  registrato per quel tipo documento (schema esatto dell'adapter e della
  registrazione endpoint: `specs/010-configurazione-cataloghi-integrazioni`). Non
  sono piu' un seed permanente: GEMODO non e' la sorgente di verita' per il loro
  contenuto, solo un riferimento locale indicizzabile.
- **Tipo documento self-service** (nessun sistema esterno): le righe restano
  possedute/autorate da GEMODO, create tramite l'interfaccia di configurazione
  (`010`) o il builder (`002`), esattamente come descritto nelle sezioni sotto
  senza ulteriori modifiche.

In ambienti locali/test, `infra/local/postgres/seed-demo-catalog.yaml` continua a
esistere e a popolare queste tabelle — ma per `BANDO_CONCORSO` questo ruolo passa
da "seed di produzione" a **fixture per un adapter locale/mock** (stesso principio
gia' in uso in questo repo per `mock-geban/`), utile per sviluppo e test senza
dipendere da una chiamata di rete reale verso GEBAN. In produzione, l'adapter HTTP
verso l'endpoint registrato in `010` e' la sorgente effettiva per `BANDO_CONCORSO`.

## Entities

### Ufficio

*(nuova entita', `DEC-001-UFFICIO-PROPRIETARIO`, 2026-09-14)* Gruppo organizzativo
proprietario di uno o piu' `TipoDocumento`. Distinto da `ProfiloDiIntegrazione`: un
Ufficio possiede/autora i tipi documento (lato scrittura), un'Applicazione li consuma
se autorizzata (lato lettura/generazione), indipendentemente da chi li possiede.
Esempio: `UFFICIO_RECLUTAMENTO` possiede `BANDO_CONCORSO`; GEBAN (applicazione) puo'
essere autorizzato a consultarlo senza esserne proprietario, e potrebbe in futuro
essere autorizzato anche a `GRADUATORIA_CONCORSO` posseduto da un ufficio diverso.

Fields:

- `codice`: identificativo funzionale, univoco.
- `nome`: es. "Ufficio Reclutamento".
- `stato`: `ATTIVO` o `INATTIVO`.
- `created_at`
- `updated_at`

Validation:

- `codice` obbligatorio e univoco.
- un utente MUST avere un ruolo di gestore scoped a un Ufficio per creare/editare
  categorie, tipologie, contratti dati o modelli dei tipi documento che quell'Ufficio
  possiede (FR-031).

**Seed**: sezione `uffici:` in `infra/local/postgres/seed-demo-catalog.yaml` (stesso
file di `tipi_documento:`), caricata da migration Alembic come le altre entita' del
catalogo. Rinominare il file quando arrivera' un secondo tipo documento reale: il
nome attuale dichiara "seed demo" ma contiene gia' nomenclatura GEBAN di produzione.

### TipoDocumento

Rappresenta una famiglia documentale generale.

Fields:

- `codice`: identificativo funzionale, univoco.
- `descrizione`: testo descrittivo.
- `codice_ufficio_proprietario`: riferimento a `Ufficio` che possiede/autora questo
  tipo documento (FR-031). Determina transitivamente la proprieta' di categorie,
  tipologie, contratti dati e modelli legati a questo tipo documento.
- `attivo`: indica se il tipo e' usabile per configurazioni operative.
- `created_at`
- `updated_at`

Validation:

- `codice` obbligatorio e univoco.
- `codice_ufficio_proprietario` obbligatorio e deve riferire un Ufficio esistente.
- tipi non attivi non vengono proposti come nuovi elementi operativi.
- un'Applicazione (`ProfiloDiIntegrazione`) puo' consultare/generare per questo tipo
  documento solo se lo ha nel proprio `tipi_documento_ammessi` (FR-025..FR-027),
  indipendentemente da quale Ufficio lo possiede.

### CategoriaDocumento

Classificazione interna collegata a un tipo documento.

Fields:

- `codice_tipo_documento`: riferimento a `TipoDocumento`.
- `codice`: identificativo profilo.
- `descrizione`
- `attiva`
- `created_at`
- `updated_at`

Validation:

- chiave logica: `codice_tipo_documento + codice`.
- profili non attivi non vengono proposti per nuovi filtri operativi.

**Sorgente**: vedi "Nota Sull'Ownership Dei Dati" in cima al documento — per un tipo
documento integrato queste righe sono una cache locale sincronizzata dall'adapter
di discovery, non un seed posseduto da GEMODO.

### ModelloDocumento

Contenitore logico di un modello.

Fields:

- `id`
- `codice`: identificativo funzionale del modello.
- `descrizione`
- `codice_tipo_documento`
- `codice_categoria`: riferimento interno al profilo esposto nelle API come `profilo`.
- `codice_tipologia`: opzionale, dipende dal processo GEBAN.
- `variante`: etichetta funzionale obbligatoria; default `STANDARD`.
- `attivo`
- `created_at`
- `updated_at`

Validation:

- il modello deve riferire tipo e profilo esistenti.
- `variante` non puo' essere vuota; se manca viene assegnata `STANDARD`.
- la combinazione `codice_tipo_documento + profilo + codice_tipologia + variante`
  identifica una variante funzionale nel catalogo.
- se presente, `codice_tipologia` deve corrispondere a una `TipologiaDocumento`
  configurata per lo stesso `codice_tipo_documento` (FR-020).
- la proprieta' (chi puo' modificare questo modello) e' quella dell'`Ufficio`
  proprietario del `TipoDocumento` referenziato, non un campo proprio (FR-031).

### TipologiaDocumento

*(rinominata da `TipologiaBandoSOL`, `DEC-001-GENERALIZZAZIONE-TIPOLOGIA`, 2026-09-14)*
Seconda dimensione di classificazione di un tipo documento, accanto a
`CategoriaDocumento`. Generalizzata da subito (non dopo, per non riscrivere schema e
codice quando arrivera' un secondo tipo documento con una classificazione concettuale
diversa da quella dei bandi GEBAN): scoped per `TipoDocumento`, non piu' globale, e con
un riferimento esterno opzionale invece che un `codice_sol` obbligatorio legato solo
all'integrazione GEBAN-SOL.

Fields:

- `codice_tipo_documento`: riferimento a `TipoDocumento` (nuovo: prima la tabella era
  globale, non partizionata).
- `codice`: identificativo funzionale usato come `codice_tipologia`, ad esempio `TD`.
- `riferimento_esterno`: opzionale (era `codice_sol`, obbligatorio). Per GEBAN resta
  popolato coi codici dell'integrazione SOL (es. `F:jconon_call_tdet:folder`); per un
  tipo documento senza un sistema esterno equivalente resta vuoto.
- `descrizione`
- `attiva`
- `created_at`

Validation:

- chiave logica: `codice_tipo_documento + codice` (prima: `codice` globale).
- perimetro GEBAN per `BANDO_CONCORSO`: TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB
  (verificati sugli endpoint di test reali di GEBAN il 2026-09-15, vedi
  `docs/adr/0001-esempio-discovery-geban.json`); altri tipi documento definiranno il
  proprio elenco indipendente, senza collidere sui codici.

**Sorgente**: vedi "Nota Sull'Ownership Dei Dati" in cima al documento — per
`BANDO_CONCORSO` queste righe sono una cache locale sincronizzata dall'adapter di
discovery verso GEBAN, non piu' un seed permanente come nella versione precedente
di questo documento (2026-09-14).

### ClassificazioneCatalogo

Configurazione dell'albero operativo esposto a GEBAN per un tipo documento.

Fields:

- `codice_tipo_documento`: riferimento a `TipoDocumento`.
- `codice_tipologia`: nodo di primo livello, riferimento a `TipologiaDocumento`.
- `codice_categoria`: profilo selezionabile sotto la tipologia, riferimento interno a
  `CategoriaDocumento`.
- `attiva`
- `created_at`

Validation:

- chiave logica: `codice_tipo_documento + codice_tipologia + profilo`.
- il riferimento esterno (`riferimento_esterno`, es. codice SOL per GEBAN) resta
  metadato interno della `TipologiaDocumento` e non viene esposto all'utente come
  valore da comprendere o digitare.
- l'endpoint di classificazione restituisce l'albero tipologie -> profili;
  la ricerca modelli puo' poi usare `codice_tipologia` e `profilo` come filtri
  derivati dalla scelta nell'albero.

**Sorgente**: come `CategoriaDocumento`/`TipologiaDocumento` — per un tipo documento
integrato, le combinazioni tipologia-profilo arrivano dall'adapter di discovery
(campo `tipologie[].profili[]` nella risposta, vedi
`docs/adr/0001-esempio-discovery-geban.json`), non sono piu' definite localmente da
GEMODO. Per GEBAN queste combinazioni non sono ancora confermate con dati reali
(vedi note `_confermato: false` nell'esempio).

### RegistroContrattiDati

*(nuova entita', `DEC-001-REGISTRO-CONTRATTI-DATI`, 2026-09-14)* Contratto dati
riusabile e versionato, scoped per `TipoDocumento` (proprieta' ereditata
transitivamente dall'Ufficio che possiede quel tipo documento). Referenziato da
`ProfiloDiIntegrazione.contratti_dati_ammessi`; vincola quali campi un modello legato
a quel tipo documento puo' dichiarare (stessa forma di `ModelloCampoRichiesto`).
Distinto dal contratto dati di livello 1 (`ModelloCampoRichiesto`, gia' implementato,
specifico di una singola versione modello): questo e' il livello 2, riusabile fra piu'
modelli dello stesso tipo documento.

Fields:

- `codice`: identificativo funzionale, univoco per tipo documento (es.
  `bando-concorso-common-fields-v1`).
- `codice_tipo_documento`: riferimento a `TipoDocumento`.
- `versione`
- `campi`: lista di definizioni campo (stessa struttura di `ModelloCampoRichiesto`:
  codice, etichetta, tipo dato, obbligatorieta', lingua, ordine, vincoli).
- `stato`: `ATTIVO` o `INATTIVO`.
- `created_at`
- `updated_at`

Validation:

- chiave logica: `codice_tipo_documento + codice`.
- ogni riferimento in `ProfiloDiIntegrazione.contratti_dati_ammessi` MUST corrispondere
  a un `RegistroContrattiDati` esistente (FR-029); un riferimento a un contratto dati
  inesistente MUST essere rifiutato al caricamento, non ignorato silenziosamente.

**Sorgente**: come le entita' sopra — per `BANDO_CONCORSO` il campo `campi` arriva
dall'adapter di discovery (campo `campi[]` nella risposta), non e' piu' autorato
localmente da GEMODO. Include anche campi il cui elenco di opzioni dipende dal
profilo scelto (es. "livello", vedi entita' `Attributo Profilo` in
`specs/010-configurazione-cataloghi-integrazioni/spec.md`) — non modellato in questo
documento prima del 2026-09-15.

### ProfiloDiIntegrazione *(riferimento)*

Entita' introdotta dalla `009`, definita per intero in
`specs/009-fondamenta-mock-test-qualita/data-model.md`; qui solo i campi rilevanti per
l'enforcement di questa feature (FR-025..FR-030). Rappresenta un'Applicazione (es.
GEBAN) autorizzata a **consumare** (consultare/validare/generare), non a possedere.

Fields rilevanti:

- `tipi_documento_ammessi`: lista di `TipoDocumento.codice` che questo profilo puo'
  consultare/consumare, indipendentemente da quale `Ufficio` li possiede.
- `categorie_ammessi`, `tipologie_ammessi`: stesso principio, dentro un tipo documento
  ammesso.
- `modelli_versioni_ammessi`: lista di `modello_versione_id` (o codici) che questo
  profilo puo' usare per generazione, anche se posseduti da un tipo documento/Ufficio
  diverso da quello "principale" del profilo — e' il meccanismo di concessione
  cross-ufficio (es. GEBAN autorizzato a un modello di un tipo documento posseduto da
  un altro ufficio).
- `contratti_dati_ammessi`: lista di `RegistroContrattiDati.codice` ammessi.

Validation:

- FR-026: ogni richiesta catalogo/validazione/generazione MUST verificare che tipo
  documento, categoria, tipologia e modello_versione_id richiesti siano in una di
  queste liste per il profilo risolto dal chiamante.

### ModelloDocumentoVersione

Versione specifica selezionabile da GEBAN.

Fields:

- `id`: UUID interno persistente, coerente con la baseline tecnica `009`.
- `public_id`: identificativo intero `int64` esposto a GEBAN come
  `modello_versione_id` nel contratto OpenAPI.
- `modello_documento_id`
- `versione`
- `stato`: `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`.
- `data_inizio_validita`: opzionale.
- `data_fine_validita`: opzionale.
- `pubblicato_at`: obbligatorio quando lo stato diventa `PUBBLICATO`.
- `created_at`
- `updated_at`

Validation:

- solo `PUBBLICATO` e' utilizzabile in modalita' operativa.
- per la stessa combinazione di tipo documento, profilo, tipologia e variante puo'
  esistere al massimo una versione `PUBBLICATO`.
- quando una nuova versione della stessa variante diventa `PUBBLICATO`, la precedente
  versione `PUBBLICATO` passa ad `ARCHIVIATO`.
- piu' varianti pubblicate possono essere visibili nello stesso contesto; la scelta
  operativa usa sempre il `public_id` esposto come `modello_versione_id`.
- una versione non piu' `PUBBLICATO` non e' validabile per uso operativo.
- le modifiche contenutistiche a una versione pubblicata creano una bozza derivata e non
  aggiornano direttamente la versione pubblicata.

### ModelloCampoRichiesto

Campo dichiarato nel contratto dati di una versione modello.

Fields:

- `id`
- `modello_versione_id`
- `codice`
- `etichetta`
- `descrizione`
- `tipo_dato`: `string`, `number`, `date`, `boolean`, `array`, `object`.
- `lingua`: `IT` o `EN`, default `IT` (FR-021, `DEC-001-LINGUA-IT-EN`).
- `obbligatorio`
- `ordine`
- `formato`: opzionale.
- `valore_default`: opzionale.
- `opzioni`: opzionale, struttura per valori ammessi o metadati.
- `validazione`: opzionale, vincoli dichiarativi.
- `created_at`
- `updated_at`

Validation:

- chiave logica: `modello_versione_id + codice`.
- `ordine` univoco per versione modello.
- campi extra nel payload sono errore.
- un campo con `lingua = EN` e `obbligatorio = true` e' richiesto in validazione solo
  quando il payload contiene `bando_inglese = true`; altrimenti resta facoltativo
  (FR-021, FR-022). Campi con `lingua = IT` seguono `obbligatorio` senza condizioni.

### ValidazionePayload

Non necessariamente tabella persistente nella feature 001; rappresenta il risultato della
validazione.

Fields:

- `valido`: boolean.
- `errori`: lista di `ErroreValidazione`.
- `modello_versione_id`
- `bando_inglese`: boolean opzionale nel payload, default `false`; quando `true`
  attiva l'obbligatorieta' dei campi con `lingua = EN` (FR-021, FR-022).

### PrincipalGEMODO

Identita' applicativa ricostruita dal JWT Keycloak per proteggere le API operative della
`001`. Non e' una tabella persistente in questa feature.

Fields:

- `subject`: soggetto del token.
- `client_id`: client chiamante, ricavato da `azp` o claim equivalente.
- `audience`: audience validate, deve includere `gemodo-backend`.
- `ruoli`: ruoli client letti da `resource_access.gemodo-backend.roles`.
- `issuer`: issuer Keycloak validato.

Validation:

- il token deve avere firma valida tramite JWKS, issuer atteso, audience attesa e
  scadenza non superata.
- per chiamate GEBAN il client deve essere `geban-backend`.
- catalogo e contratto dati richiedono `DOCUMENTI_VIEWER` o `DOCUMENTI_GENERATORE`.
- validazione payload richiede `DOCUMENTI_GENERATORE`.
- il principal mock e' ammesso solo se abilitato esplicitamente per profili locali/test.

### ErroreValidazione

Errore funzionale restituito a GEBAN.

Fields:

- `campo`: opzionale per errori di richiesta generale.
- `codice`: codice errore stabile.
- `messaggio`: messaggio funzionale.

Common error codes:

- `CAMPO_OBBLIGATORIO`
- `TIPO_NON_VALIDO`
- `CAMPO_NON_AMMESSO`
- `MODELLO_VERSIONE_NON_PUBBLICATO`
- `MODELLO_VERSIONE_NON_TROVATO`
- `CONTESTO_NON_VALIDO`
- `TIPOLOGIA_SOL_NON_VALIDA` (FR-020): `codice_tipologia` non corrisponde a una
  `TipologiaDocumento` configurata per il tipo documento richiesto. Il nome del codice
  resta invariato per compatibilita' col contratto OpenAPI gia' pubblicato, anche se
  l'entita' sottostante non si chiama piu' `TipologiaBandoSOL`.
- `PROFILO_INTEGRAZIONE_NON_ABILITATO` (FR-027; gia' descritto in
  `infra/openapi/errors.md`, owner `006`, mai raggiunto da codice reale prima di
  questo incremento): tipo documento, categoria, tipologia o
  modello_versione_id richiesti non sono nel perimetro ammesso dal profilo del
  chiamante risolto — distinto da un elenco vuoto (nel perimetro, nessun modello
  pubblicato ancora).
- `CAMPO_INGLESE_MANCANTE` (FR-022): campo con `lingua = EN` obbligatorio assente
  quando `bando_inglese = true`.
- `ACCESSO_NON_AUTENTICATO`: JWT mancante, scaduto o non valido per firma, issuer o
  audience.
- `ACCESSO_NON_AUTORIZZATO`: JWT valido ma client o ruolo non abilitato per la route.

Questi codici sono coerenti con `infra/openapi/errors.md` (catalogo errori
trasversale della `009`); eventuali nuovi codici funzionali di questa feature vanno
aggiunti in entrambi i posti.

## Relationships

```text
Ufficio 1--N TipoDocumento (proprieta')
TipoDocumento 1--N CategoriaDocumento
TipoDocumento 1--N TipologiaDocumento
TipoDocumento 1--N ModelloDocumento
TipoDocumento 1--N RegistroContrattiDati
CategoriaDocumento 1--N ModelloDocumento
TipologiaDocumento 1--N ModelloDocumento
TipoDocumento 1--N ClassificazioneCatalogo
TipologiaDocumento 1--N ClassificazioneCatalogo
CategoriaDocumento 1--N ClassificazioneCatalogo
ModelloDocumento 1--N ModelloDocumentoVersione
ModelloDocumentoVersione 1--N ModelloCampoRichiesto
ModelloDocumentoVersione 1--N ValidazionePayload (runtime)
ValidazionePayload 1--N ErroreValidazione
PrincipalGEMODO 1--N Operazione API (runtime)
ProfiloDiIntegrazione N--N TipoDocumento (consumo, indipendente dalla proprieta' Ufficio)
ProfiloDiIntegrazione N--N ModelloDocumentoVersione (concessione esplicita, FR-025..FR-027)
```

## State Rules

- `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `ARCHIVIATO`, `SOSPESO` non sono operative per GEBAN.
- `PUBBLICATO` e' l'unico stato operativo.
- Il contratto dati e la validazione richiedono sempre `modello_versione_id`.
- Il servizio non sceglie automaticamente l'ultima versione pubblicata.
- Il catalogo operativo espone al massimo una versione `PUBBLICATO` per variante.
- Le versioni precedenti della stessa variante sono `ARCHIVIATO` e disponibili solo nello
  storico.
- Il catalogo puo' esporre piu' varianti pubblicate per lo stesso tipo/profilo/tipologia.
- Le route operative della `001` sono eseguite solo con `PrincipalGEMODO` valido.
