# Feature Specification: Builder Modelli Documentali

**Feature Branch**: `002-builder-modelli`

**Created**: 2026-06-19

**Status**: Updated after clarification - riallineata 2026-09-14 a `DEC-001-UFFICIO-
PROPRIETARIO`/`DEC-001-REGISTRO-CONTRATTI-DATI`/`DEC-002-GESTORE-UFFICIO-MAPPING`
(tutte `CONFERMATA`); `data-model.md`/`plan.md`/`tasks.md` ancora da riallineare

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §2, §4, §8.2-§8.6, §10 e §16.3.

## Clarifications

### Associazione modello e policy dimensione - 2026-09-21

Due nuove entita' (`AssociazioneModello`, `PolicyDimensione`), dettagliate in
`data-model.md`. `AssociazioneModello` collega un modello derivato al modello
di origine (oggi solo per lingua) e alimenta l'annidamento nella risposta
catalogo di `001` (`DEC-002-ASSOCIAZIONE-MODELLO-DERIVATO`). `PolicyDimensione`
dichiara, per nome dimensione e non per nodo, se quella dimensione ammette un
valore generico (fallback) o richiede sempre una scelta esplicita
(`DEC-002-POLICY-DIMENSIONE-CATEGORIZZAZIONE`) - esplicitamente scollegata
dall'esempio di contratto presentazionale (`DefinizioneStruttura`, modulo
`configurazione` di `010`). **Aperto**: dove vive la schermata di
configurazione che la scrive (`002` o `010`), da confermare nella prossima
sessione di pianificazione.

### Decisione MVP 2026-09-17 - ADR 0002

Prevale sui riferimenti storici a registri locali e seed: il manager naviga
il discovery live delle integrazioni CONNESSE autorizzate fino alla foglia.
Identita': integrazione + tipo + percorso completo. Campi e classificazione
provengono dalla sorgente, non dall'esempio amministrativo. Nel DB restano
solo i riferimenti e il contratto delle versioni modello, non il catalogo.
Vedi [ADR 0002](../../docs/adr/0002-integrazioni-contesti-modelli-test.md).
Questo e' il target confermato: non certifica il runtime corrente e non avvia
l'implementazione di questa spec; la feature attiva resta 010.


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
- Q: Come si risolve a quale Ufficio appartiene il gestore che chiama? -> A:
  Confermato (`DEC-002-GESTORE-UFFICIO-MAPPING`). Nessun meccanismo GEMODO separato
  (login o gruppo Keycloak dedicato): il gestore arriva dallo stesso token
  ACE/contesto gia' costruito per il consumo GEBAN (`contexts.<app>.roles`) — chi ha
  `ROLE_MANAGER#geban` (gia' mappato a `GEMODO_MODELLI_GESTORE`) e' il gestore. Ogni
  voce di `role_mappings` il cui `internal_permissions` include
  `GEMODO_MODELLI_GESTORE` guadagna un campo esplicito `ufficio:` che dichiara a
  quale Ufficio quel ruolo da' diritto di scrittura, configurato a mano dall'admin
  GEMODO in coordinamento con chi gestisce ACE/Keycloak — stesso processo operativo
  gia' in uso oggi per `role_mappings`, nessuna interfaccia self-service. Resta
  pero' aperto (`DEC-002-SORGENTE-UFFICIO-TOKEN`, in attesa di risposta dal team
  ACE) se il segnale ufficio arrivi come claim diretto nel token (indipendente dal
  contesto/servizio chiamante) o si inferisca dal contesto/servizio stesso (es. il
  contesto "geban" implica Ufficio Reclutamento) — cambia lo schema esatto da
  implementare, non solo il processo di configurazione gia' confermato sopra.
  *(2026-09-15: risolto, vedi sotto — niente claim/inferenza aggiuntiva, il
  contesto stesso e' il valore)*

### Session 2026-09-15

- Q: L'Ufficio resta un'entita' separata come deciso il 2026-09-14? -> A: No
  (`DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`, CONFERMATA, supersede
  `DEC-001-UFFICIO-PROPRIETARIO` e la parte di `DEC-002-GESTORE-UFFICIO-MAPPING`
  sul campo `ufficio:`). Il **contesto** del token (`contexts.<nome>.roles`,
  gia' implementato per GEBAN) e' l'unita' di scoping, senza un'entita'/tabella
  aggiuntiva sopra: `TipoDocumento` porta un campo diretto `codice_contesto`. Un
  gestore e' autorizzato a scrivere su un tipo documento se il proprio token
  contiene quel contesto con un ruolo che, **in quel contesto specifico**, deriva
  `GEMODO_MODELLI_GESTORE` — mai sulla lista di permessi gia' appiattita su tutti
  i contesti del token (un utente con piu' contesti, es. "geban" e un futuro
  "contratti", va verificato separatamente per ciascuno; un ruolo di gestore in
  un contesto non deve autorizzare la scrittura in un altro). FR-002/FR-003/
  FR-014/FR-015 e Key Entities aggiornati di conseguenza sotto.
- Q: FR-002 dice che il builder gestisce (crea/modifica) categorie e tipologie —
  resta cosi' dopo che `specs/010-configurazione-cataloghi-integrazioni` e' nata
  apposta per "definire la struttura di un tipo documento" (tipologie, profili,
  campi)? -> A: No, e' un'incongruenza emersa lavorando su `010`: la
  *definizione* della struttura (tipologie/profili/campi) e' scope della `010`
  (User Story 1 li'), non di questa spec. Questa spec (`002`) legge la struttura
  gia' definita/connessa (via `PortaDiscovery`, `DEC-002-PORTS-ADAPTERS-
  DISCOVERY`) e la usa per **creare modelli** — non crea ne' modifica categorie
  o tipologie essa stessa. FR-002 corretto sotto da "gestione" a "lettura"; la
  User Story 1 di questa spec e' riscritta di conseguenza.

## Out of Scope

- Frontend builder e consultazione grafica, coperti dalla spec `007`.
- Sezioni, placeholder, layout e struttura documentale a blocchi, coperti dalla spec `003`.
- Generazione PDF, storage e idempotenza, coperti dalle spec `004` e `005`.
- API dedicate di profilo integrazione GEBAN e autorizzazioni fini per profilo, tracciate dalla spec `006` e dalle decisioni sospese della `001`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Leggere la struttura disponibile per un tipo documento connesso (Priority: P1)

*(riscritta 2026-09-15, `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO` +
chiarimento di confine con `010`)* Come gestore modelli il cui token contiene il
contesto di un tipo documento, voglio consultare le categorie, tipologie e campi
del contratto dati gia' definiti/connessi per quel tipo documento (tramite la
porta di discovery, `DEC-002-PORTS-ADAPTERS-DISCOVERY`), cosi' da sapere cosa
posso usare per creare un modello. La *definizione* di categorie/tipologie/campi
(albero JSON, generazione del contratto per un sistema esterno, registrazione
endpoint) e' interamente scope della `010`, non di questa storia: qui si legge,
non si scrive.

**Why this priority**: senza sapere cosa e' disponibile per un tipo documento, il
gestore non puo' creare un modello coerente (User Story 2).

**Independent Test**: dato un tipo documento connesso (self-service o con endpoint
di discovery verificato), il gestore il cui token contiene quel contesto vede le
categorie/tipologie/campi disponibili; un gestore senza quel contesto non li vede.

**Acceptance Scenarios**:

1. **Given** un tipo documento connesso e un contesto presente nel token del
   gestore, **When** il gestore consulta la struttura disponibile, **Then**
   ottiene categorie, tipologie e campi correnti (via `PortaDiscovery`).
2. **Given** un tipo documento il cui `codice_contesto` NON e' fra i contesti del
   token del gestore, **When** il gestore prova a consultarne la struttura,
   **Then** il sistema rifiuta con `PROFILO_INTEGRAZIONE_NON_ABILITATO`.
3. **Given** una categoria o tipologia disattivata nella definizione (`010`),
   **When** il gestore consulta la struttura disponibile, **Then** non compare
   fra le opzioni selezionabili per un nuovo modello.

---

### User Story 2 - Gestire modelli e versioni (Priority: P1)

Come gestore modelli, voglio creare modelli documentali e versioni, cosi' da preparare
nuove configurazioni senza modificare codice applicativo. *(riallineata 2026-09-15)*
Il modello deve appartenere a un tipo documento il cui `codice_contesto` e' fra i
contesti del token del gestore, e i suoi campi devono provenire dal Registro
Contratti Dati di quel tipo documento (`DEC-001-REGISTRO-CONTRATTI-DATI`), letto
tramite la struttura disponibile della User Story 1 — non essere liberi.

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
- **FR-002**: *(corretto 2026-09-15: da "gestione" a "lettura", la definizione e'
  scope della `010`)* Il sistema MUST permettere la lettura (non la creazione o
  modifica) delle categorie e tipologie disponibili per un tipo documento
  connesso, tramite la porta di discovery (`DEC-002-PORTS-ADAPTERS-DISCOVERY`),
  limitata ai tipi documento il cui `codice_contesto` e' fra i contesti del token
  del gestore chiamante (FR-014).
- **FR-003**: Il sistema MUST permettere la creazione di modelli documentali associati
  a tipo, categoria e tipologia quando prevista, limitata ai tipi documento il cui
  `codice_contesto` e' fra i contesti del token del gestore (FR-014); i campi del
  contratto dati del modello MUST provenire dalla foglia discovery selezionata
  nell'integrazione autorizzata (FR-015).
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
- **FR-014**: *(corretto 2026-09-15, `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`)* Il
  sistema MUST verificare che il token del gestore chiamante contenga il
  `codice_contesto` del tipo documento target, con un ruolo che **in quel
  contesto specifico** (mai sulla lista di permessi gia' appiattita su tutti i
  contesti del token) deriva `GEMODO_MODELLI_GESTORE` tramite `role_mappings`
  (stesso meccanismo del consumo GEBAN), e MUST rifiutare con
  `PROFILO_INTEGRAZIONE_NON_ABILITATO` qualunque lettura di struttura (FR-002) o
  scrittura (modello, versione) su un tipo documento il cui contesto non e'
  presente nel token.
- **FR-015**: *(nuovo 2026-09-14)* Quando un gestore aggiunge un campo al contratto
  dati di una versione modello, il sistema MUST verificare che il campo sia presente
  nella foglia discovery selezionata per il modello, e MUST rifiutare campi
  estranei a quella foglia. L'esempio amministrativo non limita i campi ammessi.

- **FR-016**: Il manager MUST poter creare una versione di test in BOZZA senza
  editor visuale, con struttura minima automatica della 003. La creazione
  MUST NOT pubblicare automaticamente: generazione dopo normale pubblicazione.
- **FR-017**: Il modello MUST includere i campi obbligatori della foglia e
  distinguere obbligatorieta' sorgente dalla presenza richiesta degli opzionali
  selezionati secondo il contratto della 001.

- **FR-018** (2026-09-22, difetto trovato verificando la pulizia dell'ambiente):
  l'eliminazione di un'edizione derivata MUST liberare davvero la coppia
  (modello origine, lingua), cosi' che la stessa edizione possa essere
  ricreata. Oggi il codice applicativo gia' si comporta cosi'
  (`builder/repository.py:get_edizione_derivata` esclude `ELIMINATO`), ma il
  vincolo di database `uq_modello_derivato_padre_lingua`, creato dalla
  migration `0017`, **non** esclude le righe eliminate: il controllo
  applicativo passa, l'INSERT viola il vincolo e l'`IntegrityError` non
  gestito raggiunge il chiamante come **HTTP 500**. Verificato end-to-end il
  2026-09-22 (`psycopg.errors.UniqueViolation: duplicate key value violates
  unique constraint "uq_modello_derivato_padre_lingua"`). Il vincolo di
  database MUST esprimere la stessa intenzione del codice, e ogni residua
  violazione concorrente MUST essere tradotta in un conflitto funzionale
  (`EDIZIONE_DERIVATA_DUPLICATA`, 409), mai in un errore 500 - come gia'
  avviene per i duplicati di tipo documento.

### Key Entities

- **Tipo Documento**: famiglia generale del documento; consultabile ma non creabile
  da questa spec (definizione/onboarding sono scope della `010`; proprieta' via
  `codice_contesto`, vedi `001`).
- **Categoria Documento**, **Tipologia Documento**: classificazione interna al tipo
  documento; definite dalla `010`, lette da questa spec tramite `PortaDiscovery`
  (FR-002), non create/modificate qui.
- **Foglia Discovery**: sorgente esterna dei campi selezionabili (FR-015), letta
  tramite 010; non costituisce un registro locale del catalogo.
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
  `002` e restano nella spec sicurezza; l'autorizzazione di proprieta'/scrittura via
  `codice_contesto` (FR-014) e' invece parte di questa spec.
- L'onboarding di nuovi tipi documento (definizione struttura, generazione
  contratto, registrazione endpoint) e' interamente scope della `010`, non di
  questa spec — `002` consuma la struttura gia' connessa, non la definisce.
