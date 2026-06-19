# Feature Specification: Builder Modelli Documentali

**Feature Branch**: `002-builder-modelli`

**Created**: 2026-06-19

**Status**: Draft

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §2, §4, §8.2-§8.6, §10 e §16.3.

## Clarifications

### Session 2026-06-19

- Q: Le versioni pubblicate della stessa variante possono sovrapporsi? -> A: No, per stessa combinazione tipo documento, categoria, tipologia e variante esiste una sola versione pubblicata corrente; modelli simili coesistono come varianti distinte.
- Q: Come si modifica il contenuto di una versione pubblicata? -> A: Una versione pubblicata non e' modificabile nel contenuto; le modifiche creano una bozza derivata che, se approvata, diventa nuova versione pubblicata corrente della stessa variante.
- Q: Quale workflow stati deve seguire una versione modello? -> A: Per ora gli stati restano separati: BOZZA, IN_REVISIONE, APPROVATO, PUBBLICATO, ARCHIVIATO/SOSPESO; dopo approvazione una versione puo' essere pubblicata e poi archiviata.
- Q: Cosa succede alla versione corrente precedente quando una nuova versione della stessa variante viene pubblicata? -> A: La precedente versione pubblicata corrente passa automaticamente ad ARCHIVIATO; solo la nuova resta PUBBLICATO e visibile nel catalogo operativo.
- Q: La variante modello e' obbligatoria? -> A: Si', ogni modello ha una variante obbligatoria; se non specificata dal gestore viene usata la variante `STANDARD`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurare tipi e categorie documento (Priority: P1)

Come gestore modelli, voglio creare e mantenere tipi documento e categorie, cosi' da
classificare correttamente i modelli disponibili per GEBAN.

**Why this priority**: tipi e categorie sono la base del catalogo operativo.

**Independent Test**: dato un tipo documento e una categoria attivi, il gestore puo'
renderli disponibili alla configurazione di un modello.

**Acceptance Scenarios**:

1. **Given** non esiste un tipo documento, **When** il gestore lo crea, **Then** il tipo
   diventa disponibile per la configurazione di categorie e modelli.
2. **Given** un tipo documento attivo, **When** il gestore crea una categoria, **Then** la
   categoria risulta associata al tipo documento.
3. **Given** una categoria disattivata, **When** viene usata nel builder, **Then** non puo'
   essere selezionata per nuovi modelli operativi.

---

### User Story 2 - Gestire modelli e versioni (Priority: P1)

Come gestore modelli, voglio creare modelli documentali e versioni, cosi' da preparare
nuove configurazioni senza modificare codice applicativo.

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

Come approvatore modelli, voglio pubblicare o archiviare versioni modello, cosi' da
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

- **FR-001**: Il sistema MUST permettere la gestione di tipi documento attivi e non attivi.
- **FR-002**: Il sistema MUST permettere la gestione di categorie associate a un tipo documento.
- **FR-003**: Il sistema MUST permettere la creazione di modelli documentali associati a tipo, categoria e tipologia quando prevista.
- **FR-003a**: Il sistema MUST assegnare a ogni modello una variante obbligatoria; se il gestore non ne indica una, il sistema MUST usare la variante `STANDARD`.
- **FR-004**: Il sistema MUST gestire versioni modello con stati `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO` e `SOSPESO`.
- **FR-004a**: Il sistema MUST consentire il passaggio da `APPROVATO` a `PUBBLICATO` e da `PUBBLICATO` ad `ARCHIVIATO` o `SOSPESO`.
- **FR-004b**: La specifica non vincola per ora il numero di figure coinvolte nell'approvazione; i ruoli e le autorizzazioni dettagliate sono definiti nella spec sicurezza.
- **FR-005**: Il sistema MUST impedire modifiche contenutistiche dirette a versioni pubblicate.
- **FR-006**: Il sistema MUST creare una bozza derivata quando cambia una configurazione gia' pubblicata.
- **FR-007**: Il sistema MUST garantire al massimo una versione pubblicata corrente per la stessa combinazione di tipo documento, categoria, tipologia e variante.
- **FR-008**: Il sistema MUST registrare chi crea, approva, pubblica o archivia una versione modello.
- **FR-009**: Il sistema MUST rendere disponibili al catalogo operativo solo versioni pubblicate.
- **FR-010**: Quando una nuova versione della stessa variante viene pubblicata, il sistema MUST passare automaticamente la precedente versione pubblicata corrente ad `ARCHIVIATO`; solo la nuova versione resta `PUBBLICATO` e visibile nel catalogo operativo.
- **FR-011**: Il sistema MUST mantenere consultabili nello storico le versioni archiviate.

### Key Entities

- **Tipo Documento**: famiglia generale del documento.
- **Categoria Documento**: classificazione interna al tipo documento.
- **Modello Documento**: contenitore logico del modello.
- **Variante Modello**: etichetta funzionale obbligatoria che distingue modelli simili nello stesso tipo, categoria e tipologia; `STANDARD` rappresenta la variante predefinita.
- **Versione Modello**: configurazione versionata del modello.
- **Identificativo Versione Modello**: identificativo univoco della versione usato da GEBAN per scegliere contratto dati, validazione e generazione.
- **Stato Versione**: stato di workflow della versione.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Il 100% dei modelli operativi e' associato a tipo documento e categoria.
- **SC-002**: Il 100% delle versioni pubblicate mantiene storico non sovrascritto.
- **SC-003**: Nessuna versione non pubblicata e' visibile nel catalogo operativo.
- **SC-004**: Il 100% delle varianti pubblicate correnti e' selezionabile senza ambiguita' tramite `modello_versione_id`.
- **SC-005**: Per ogni combinazione tipo, categoria, tipologia e variante esiste al massimo una versione pubblicata corrente.

## Assumptions

- La lista iniziale dei tipi documento e categorie verra' confermata prima del seed iniziale.
- Il numero di figure coinvolte nell'approvazione verra' definito nella spec sicurezza/autorizzazioni.
- Le regole di autorizzazione dettagliate sono definite nella spec sicurezza.
