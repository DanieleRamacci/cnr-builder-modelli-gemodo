# Feature Specification: Builder Modelli Documentali

**Feature Branch**: `002-builder-modelli`

**Created**: 2026-06-19

**Status**: Updated after clarification - riallineata 2026-09-14 a `DEC-001-UFFICIO-
PROPRIETARIO`/`DEC-001-REGISTRO-CONTRATTI-DATI`; `DEC-002-GESTORE-UFFICIO-MAPPING`
resta aperta, `data-model.md`/`plan.md`/`tasks.md` ancora da riallineare

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §2, §4, §8.2-§8.6, §10 e §16.3.

## Clarifications

### Session 2026-06-19

- Q: Le versioni pubblicate della stessa variante possono sovrapporsi? -> A: No, per stessa combinazione tipo documento, categoria, tipologia e variante esiste una sola versione pubblicata corrente; modelli simili coesistono come varianti distinte.
- Q: Come si modifica il contenuto di una versione pubblicata? -> A: Una versione pubblicata non e' modificabile nel contenuto; le modifiche creano una bozza derivata che, se approvata, diventa nuova versione pubblicata corrente della stessa variante.
- Q: Quale workflow stati deve seguire una versione modello? -> A: Per ora gli stati restano separati: BOZZA, IN_REVISIONE, APPROVATO, PUBBLICATO, ARCHIVIATO/SOSPESO; dopo approvazione una versione puo' essere pubblicata e poi archiviata.
- Q: Cosa succede alla versione corrente precedente quando una nuova versione della stessa variante viene pubblicata? -> A: La precedente versione pubblicata corrente passa automaticamente ad ARCHIVIATO; solo la nuova resta PUBBLICATO e visibile nel catalogo operativo.
- Q: La variante modello e' obbligatoria? -> A: Si', ogni modello ha una variante obbligatoria; se non specificata dal gestore viene usata la variante `STANDARD`.

### Session 2026-07-31

- Q: Quale workflow stati e ruoli di pubblicazione deve usare la prima release della 002? -> A: Stati separati `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`; `GEMODO_MODELLI_GESTORE` puo' approvare e pubblicare senza separazione obbligatoria revisore/approvatore.

### Session 2026-09-14 (propagazione da `001`)

Decisioni confermate nella `001` (`docs/decision-register.yaml`) che impattano il
design del builder quando verra' pianificato:

- `DEC-001-UFFICIO-PROPRIETARIO`: `GEMODO_MODELLI_GESTORE` non e' un ruolo globale.
  Il builder MUST autorizzare creazione/modifica di categorie, tipologie, contratti
  dati e modelli solo per i tipi documento posseduti dall'Ufficio a cui il gestore
  chiamante e' scoped, non per qualunque tipo documento.
- `DEC-001-REGISTRO-CONTRATTI-DATI`: il builder MUST vincolare i campi che un gestore
  puo' inserire in un modello ai contratti dati ammessi per il tipo documento di quel
  modello (registro scoped per tipo documento, non per singolo sistema richiedente).
- `DEC-001-GENERALIZZAZIONE-TIPOLOGIA`: la seconda dimensione di classificazione
  (`TipologiaDocumento`, ex `TipologiaBandoSOL`) e' scoped per tipo documento; il
  builder non deve assumere un vocabolario di tipologie condiviso fra tipi documento
  diversi.
- `DEC-001-CONFIG-PROFILO-GEBAN`: profili/uffici/contratti dati vivono in tabelle
  Postgres popolate inizialmente da file versionato; un'eventuale interfaccia
  self-service del builder per la creazione di profili/uffici scrivera' sulle stesse
  tabelle.

### Session 2026-09-14 (riallineamento, seconda parte)

Risolve le implicazioni concrete della sessione precedente per questa spec.

- Q: Il gestore modelli puo' creare un nuovo Tipo Documento tramite il builder?
  -> A: No. L'onboarding di un Tipo Documento (e dell'Ufficio che lo possiede) resta
  un'azione centrale GEMODO fuori da questa spec (file di configurazione + deploy,
  `DEC-001-CONFIG-PROFILO-GEBAN`; nessuna interfaccia admin in questo incremento,
  vedi `001`). FR-001 si riduce quindi a consultazione dei tipi documento esistenti
  e attivi, non alla loro creazione: rimossa dallo scope di questa spec.
- Q: Il gestore modelli puo' creare/modificare categorie, tipologie e modelli per
  qualunque tipo documento? -> A: No. Solo per i tipi documento posseduti
  dall'Ufficio a cui il gestore chiamante e' scoped (`DEC-001-UFFICIO-PROPRIETARIO`).
  Un tentativo di scrivere su un tipo documento posseduto da un altro Ufficio MUST
  essere rifiutato con lo stesso errore funzionale gia' introdotto lato consumo dalla
  `001` (`PROFILO_INTEGRAZIONE_NON_ABILITATO`), non un errore builder-specifico
  separato.
- Q: Il gestore puo' inserire in un modello qualunque campo voglia? -> A: No. I campi
  del contratto dati di una versione modello (`ModelloCampoRichiesto`) devono
  provenire dal Registro Contratti Dati del tipo documento del modello
  (`DEC-001-REGISTRO-CONTRATTI-DATI`); il builder MUST rifiutare un campo non
  presente nel contratto dati ammesso per quel tipo documento, non accettarlo come
  campo libero.
- Q: Come si risolve a quale Ufficio appartiene il gestore che chiama (`client_id`/
  ruolo Keycloak non porta oggi nessun concetto di Ufficio)? -> A: Decisione ancora
  aperta (`DEC-002-GESTORE-UFFICIO-MAPPING`, nuova, `APERTA`): la direzione piu'
  coerente con quanto gia' fatto per l'ACE/GEBAN (`006`, mapping ruolo esterno ->
  permesso GEMODO tramite `role_mappings` configurabili) e' un meccanismo analogo
  ruolo/gruppo Keycloak -> Ufficio, ma non e' stata confermata col product owner e va
  chiusa prima di generare i task implementativi che toccano scrittura.

## Out of Scope

- Frontend builder e consultazione grafica, coperti dalla spec `007`.
- Sezioni, placeholder, layout e struttura documentale a blocchi, coperti dalla spec `003`.
- Generazione PDF, storage e idempotenza, coperti dalle spec `004` e `005`.
- API dedicate di profilo integrazione GEBAN e autorizzazioni fini per profilo, tracciate dalla spec `006` e dalle decisioni sospese della `001`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurare categorie e tipologie per un tipo documento posseduto (Priority: P1)

*(riallineata 2026-09-14, `DEC-001-UFFICIO-PROPRIETARIO`)* Come gestore modelli
scoped a un Ufficio, voglio creare e mantenere categorie e tipologie per i tipi
documento che il mio Ufficio possiede, cosi' da classificare correttamente i modelli
disponibili per le applicazioni autorizzate a consumarli. La creazione del tipo
documento stesso (e la sua assegnazione a un Ufficio proprietario) resta un'azione
centrale GEMODO fuori da questa storia (vedi Clarifications).

**Why this priority**: categorie e tipologie sono la base del catalogo operativo per
un tipo documento gia' onboardato.

**Independent Test**: dato un tipo documento gia' posseduto dall'Ufficio del gestore,
il gestore puo' creare/modificare categorie e tipologie e renderle disponibili alla
configurazione di un modello; un gestore di un Ufficio diverso non puo'.

**Acceptance Scenarios**:

1. **Given** un tipo documento attivo posseduto dall'Ufficio del gestore, **When** il
   gestore crea una categoria o una tipologia, **Then** risulta associata al tipo
   documento e disponibile per nuovi modelli.
2. **Given** un tipo documento posseduto da un Ufficio diverso da quello del gestore,
   **When** il gestore prova a creare/modificare una categoria o tipologia per quel
   tipo documento, **Then** il sistema rifiuta l'operazione con
   `PROFILO_INTEGRAZIONE_NON_ABILITATO`.
3. **Given** una categoria disattivata, **When** viene usata nel builder, **Then** non puo'
   essere selezionata per nuovi modelli operativi.

---

### User Story 2 - Gestire modelli e versioni (Priority: P1)

Come gestore modelli, voglio creare modelli documentali e versioni, cosi' da preparare
nuove configurazioni senza modificare codice applicativo. *(riallineata 2026-09-14)*
Il modello deve appartenere a un tipo documento posseduto dall'Ufficio del gestore, e
i suoi campi devono provenire dal Registro Contratti Dati di quel tipo documento
(`DEC-001-REGISTRO-CONTRATTI-DATI`), non essere liberi.

**Why this priority**: il modello versionato e' il centro del builder.

**Independent Test**: dato un modello in bozza, il gestore puo' creare una versione,
modificarla e portarla a uno stato di revisione/pubblicazione.

**Acceptance Scenarios**:

1. **Given** esiste tipo e categoria, **When** il gestore crea un modello, **Then** il
   modello e' associato alla classificazione scelta.
2. **Given** un modello esistente, **When** il gestore crea una nuova versione, **Then** la
   versione parte in stato modificabile.
3. **Given** una versione pubblicata, **When** il gestore vuole modificarne il contenuto,
   **Then** il sistema crea una bozza derivata e non modifica la versione pubblicata.
4. **Given** esistono modelli simili per stessa categoria e tipologia, **When** hanno
   differenze funzionali, **Then** il gestore li distingue tramite variante modello.

---

### User Story 3 - Pubblicare e archiviare versioni modello (Priority: P1)

Come gestore modelli autorizzato, voglio pubblicare o archiviare versioni modello, cosi' da
controllare cosa GEBAN puo' usare operativamente.

**Why this priority**: solo versioni pubblicate devono uscire verso GEBAN.

**Independent Test**: una versione non pubblicata non appare nel catalogo operativo; una
versione pubblicata valida appare nel catalogo.

**Acceptance Scenarios**:

1. **Given** una versione approvata, **When** un utente autorizzato la pubblica, **Then**
   diventa utilizzabile da GEBAN se valida nel periodo definito.
2. **Given** una versione pubblicata, **When** l'approvatore la archivia, **Then** non e'
   piu' proposta per nuove generazioni.
3. **Given** una bozza derivata viene approvata e pubblicata, **When** diventa corrente,
   **Then** la versione pubblicata precedente della stessa variante passa automaticamente
   ad `ARCHIVIATO`.

### Edge Cases

- Creazione di modello con codice duplicato.
- Pubblicazione di versione senza campi richiesti o sezioni minime.
- Archiviazione di versione gia' usata da documenti generati.
- Tentativo di eliminare dati gia' usati in generazioni storiche.
- Tentativo di pubblicare due versioni correnti per la stessa variante.
- Creazione di varianti con etichette duplicate nello stesso contesto.
- Creazione di modello senza variante esplicita: il sistema assegna la variante `STANDARD`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema MUST permettere la consultazione dei tipi documento attivi e
  non attivi. La creazione o disattivazione di un tipo documento NOT e' parte di
  questa spec: resta un'azione centrale GEMODO fuori dal builder (`DEC-001-CONFIG-
  PROFILO-GEBAN`). *(corretto 2026-09-14: la versione precedente permetteva
  creazione/gestione qui, superata da `DEC-001-UFFICIO-PROPRIETARIO`)*.
- **FR-002**: Il sistema MUST permettere la gestione di categorie e tipologie
  associate a un tipo documento, limitata ai tipi documento posseduti dall'Ufficio a
  cui il gestore chiamante e' scoped (FR-014).
- **FR-003**: Il sistema MUST permettere la creazione di modelli documentali associati
  a tipo, categoria e tipologia quando prevista, limitata ai tipi documento posseduti
  dall'Ufficio del gestore (FR-014); i campi del contratto dati del modello MUST
  provenire dal Registro Contratti Dati ammesso per quel tipo documento (FR-015).
- **FR-003a**: Il sistema MUST assegnare a ogni modello una variante obbligatoria; se il gestore non ne indica una, il sistema MUST usare la variante `STANDARD`.
- **FR-004**: Il sistema MUST gestire versioni modello con stati `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO` e `SOSPESO`.
- **FR-004a**: Il sistema MUST consentire il passaggio da `APPROVATO` a `PUBBLICATO` e da `PUBBLICATO` ad `ARCHIVIATO` o `SOSPESO`.
- **FR-004b**: Nel primo rilascio il ruolo `GEMODO_MODELLI_GESTORE` MUST poter approvare e pubblicare una versione modello; ruoli separati revisore/approvatore restano riservati e inattivi finche' non saranno attivati dalla spec sicurezza.
- **FR-005**: Il sistema MUST impedire modifiche contenutistiche dirette a versioni pubblicate.
- **FR-006**: Il sistema MUST creare una bozza derivata quando cambia una configurazione gia' pubblicata.
- **FR-007**: Il sistema MUST garantire al massimo una versione pubblicata corrente per la stessa combinazione di tipo documento, categoria, tipologia e variante.
- **FR-008**: Il sistema MUST registrare chi crea, approva, pubblica o archivia una versione modello.
- **FR-009**: Il sistema MUST rendere disponibili al catalogo operativo solo versioni pubblicate.
- **FR-010**: Quando una nuova versione della stessa variante viene pubblicata, il sistema MUST passare automaticamente la precedente versione pubblicata corrente ad `ARCHIVIATO`; solo la nuova versione resta `PUBBLICATO` e visibile nel catalogo operativo.
- **FR-011**: Il sistema MUST mantenere consultabili nello storico le versioni archiviate.
- **FR-012**: Le API interne builder MUST richiedere JWT Bearer Keycloak valido con audience `gemodo-backend`; le letture richiedono ruolo `GEMODO_MODELLI_VIEWER` o `GEMODO_MODELLI_GESTORE`, le scritture e transizioni richiedono `GEMODO_MODELLI_GESTORE`.
- **FR-013**: Il sistema MUST restituire errori stabili `ACCESSO_NON_AUTENTICATO` e `ACCESSO_NON_AUTORIZZATO` quando autenticazione o autorizzazione builder falliscono.
- **FR-014**: *(nuovo 2026-09-14)* Il sistema MUST risolvere l'Ufficio a cui e' scoped
  il gestore chiamante e MUST rifiutare con `PROFILO_INTEGRAZIONE_NON_ABILITATO`
  qualunque scrittura (categoria, tipologia, modello, versione) su un tipo documento
  non posseduto da quell'Ufficio. Il meccanismo di risoluzione gestore -> Ufficio
  resta una decisione aperta (`DEC-002-GESTORE-UFFICIO-MAPPING`).
- **FR-015**: *(nuovo 2026-09-14)* Quando un gestore aggiunge un campo al contratto
  dati di una versione modello, il sistema MUST verificare che il campo sia presente
  nel Registro Contratti Dati ammesso per il tipo documento del modello, e MUST
  rifiutare campi non presenti li'.

### Key Entities

- **Tipo Documento**: famiglia generale del documento; consultabile ma non creabile
  da questa spec (proprieta' di un Ufficio, vedi `001`).
- **Ufficio** *(riferimento, entita' definita in `001`)*: proprietario di uno o piu'
  tipi documento; determina chi puo' scrivere categorie/tipologie/modelli per quel
  tipo documento (FR-014).
- **Categoria Documento**: classificazione interna al tipo documento.
- **Registro Contratti Dati** *(riferimento, entita' definita in `001`)*: vincola i
  campi che un modello di un dato tipo documento puo' dichiarare (FR-015).
- **Modello Documento**: contenitore logico del modello.
- **Variante Modello**: etichetta funzionale obbligatoria che distingue modelli simili nello stesso tipo, categoria e tipologia; `STANDARD` rappresenta la variante predefinita.
- **Versione Modello**: configurazione versionata del modello.
- **Identificativo Versione Modello**: identificativo univoco della versione usato da GEBAN per scegliere contratto dati, validazione e generazione.
- **Stato Versione**: stato di workflow della versione.
- **Principal GEMODO**: identita' applicativa ricostruita dal token Keycloak usata per autorizzare e auditare le operazioni builder.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei modelli operativi e' associato a tipo documento e categoria.
- **SC-002**: Il 100% delle versioni pubblicate mantiene storico non sovrascritto.
- **SC-003**: Nessuna versione non pubblicata e' visibile nel catalogo operativo.
- **SC-004**: Il 100% delle varianti pubblicate correnti e' selezionabile senza ambiguita' tramite `modello_versione_id`.
- **SC-005**: Per ogni combinazione tipo, categoria, tipologia e variante esiste al massimo una versione pubblicata corrente.

## Assumptions

- Tipi, categorie e tipologie iniziali derivano dalla documentazione GEBAN gia' recepita dalla `001` e restano dati configurabili/versionabili, non costanti applicative.
- La separazione revisore/approvatore non e' obbligatoria nel primo rilascio; il gestore modelli autorizzato puo' completare approvazione e pubblicazione.
- Le autorizzazioni fini per profili di integrazione (consumo) non fanno parte della
  `002` e restano nella spec sicurezza; l'autorizzazione di proprieta'/scrittura per
  Ufficio (FR-014) e' invece parte di questa spec.
- L'onboarding di nuovi tipi documento e Uffici resta un'azione centrale GEMODO fuori
  da questa spec (file di configurazione + deploy), non un'API/UI builder, per
  decisione esplicita del product owner (`001`).
