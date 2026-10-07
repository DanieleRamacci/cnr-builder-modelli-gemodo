# Feature Specification: Generazione senza archivio, registro e verifica

**Feature Branch**: `013-generazione-registro-verifica` (lavoro sul branch `test`)

**Created**: 2026-10-05

**Status**: Draft

**Input**: Riscontro di GEBAN del 2026-10-05: "l'utente stampa il bando, scopre
un errore, lo modifica e rilancia la generazione. Questo puo' farlo tante volte
fino a quando non consolida il tutto (il bando diventa definitivo)". GEBAN usa
come `external_context_id` la chiave del bando, come gli abbiamo indicato
(`docs/api-per-geban.md`), e con la regola attuale la seconda generazione con
dati corretti riceve 409.

## Perche' questa spec esiste

La `005` ha deciso che GEMODO conservi ogni PDF generato e che la stessa chiave
(sistema + `external_context_id` + versione del modello) con dati diversi sia un
conflitto (FR-005, FR-007, FR-012). La rigenerazione dopo una correzione doveva
passare da "una nuova chiave funzionale o una revisione esplicita"; e' stata
realizzata solo la prima strada. Il risultato, per GEBAN, e' che un bando non si
puo' rigenerare dopo averlo corretto.

Rileggendo a cosa serve l'archivio dei PDF:

- GEBAN riceve il PDF nella risposta di `genera` e ne e' il sistema di
  riferimento: il bando, le sue correzioni e il definitivo sono suoi.
- Nessuno usa il download da GEMODO; e oggi i file si perdono a ogni redeploy
  (il backend non ha un volume), senza che nessuno se ne sia accorto.
- Cio' che a GEMODO serve davvero non e' il file, ma **poter dimostrare** che un
  PDF e' quello che ha prodotto, con quali dati e da quale modello.

## Decisioni (product owner, 2026-10-05)

- GEMODO **genera e consegna**; non conserva il file. Se in futuro servira'
  conservarli, sara' un modulo a parte.
- Ogni generazione si registra, comprese quelle con dati non validi.
- Dei dati ricevuti si conserva **solo l'impronta**, non il contenuto; deve pero'
  essere possibile verificare se un insieme di dati corrisponde a una
  generazione.
- Il riferimento della generazione sta **solo nei metadati** del PDF, non nel
  testo visibile.
- I registri si conservano **per sempre**, per ora.
- La registrazione deve essere robusta: un problema dei log non deve far cadere
  il sistema.
- Un **registro attivita'** consultabile solo dagli amministratori: chi ha
  fatto cosa, compresa la creazione e la modifica di modelli e configurazioni e
  le chiamate API che agiscono sul sistema.

Questa spec sostituisce FR-005, FR-007, FR-012 e la parte di conservazione e
download della `005`, e l'idempotenza di FR-018 della `004`. La generazione lato
server con dati controllati sul contratto del modello (`004`) non cambia.

### Decisione 2026-10-06: verifica PDF/dati rinviata

La verifica amministrativa di un PDF o di un insieme di dati resta una esigenza
di prodotto, ma non viene implementata in questo incremento. Questa spec chiude
prima il blocco necessario a GEBAN: generazione ripetibile con la stessa chiave,
registro di ogni chiamata, niente archivio file, riferimento documentale e
registro attivita'. Le User Story 2 e 3, con relative API, pagina admin e test,
sono rinviate a una spec successiva.

Il riferimento nei metadati del PDF rimane in scope: non espone una verifica,
ma prepara il collegamento tecnico necessario quando la spec futura verra'
sviluppata.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rigenerare lo stesso bando finche' non e' definitivo (Priority: P1)

Come GEBAN, voglio chiedere il PDF dello stesso bando, con la stessa chiave,
tutte le volte che serve mentre l'utente lo corregge.

**Why this priority**: e' il flusso reale di GEBAN e oggi e' bloccato.

**Independent Test**: due `genera` con lo stesso `external_context_id` e dati
diversi restituiscono due PDF, ciascuno coi suoi dati, e due righe di registro.

**Acceptance Scenarios**:

1. **Given** un bando gia' generato, **When** GEBAN chiede di nuovo il PDF con la
   stessa chiave e dati corretti, **Then** riceve il PDF con i dati nuovi.
2. **Given** la stessa chiave e gli stessi dati, **When** GEBAN ripete la
   chiamata (per esempio dopo un timeout), **Then** riceve un PDF con lo stesso
   contenuto e il registro ha una riga per ciascuna chiamata.
3. **Given** dati non validi, **When** GEBAN chiama `genera`, **Then** riceve gli
   errori per campo, nessun PDF, e la chiamata e' nel registro con esito
   "dati non validi".

---

### User Story 2 - Dimostrare che un PDF e' quello generato da GEMODO (Priority: P1)

**Stato 2026-10-06**: rinviata a spec futura. Non implementare API o UI di
verifica PDF in questo incremento.

Come amministratore, davanti a un PDF contestato, voglio sapere se e' identico a
quello che GEMODO ha consegnato, quando, a chi, da quale modello.

**Why this priority**: e' la garanzia per cui la generazione avviene lato server.

**Independent Test**: carico il PDF ricevuto da `genera` e GEMODO lo riconosce;
cambio un byte e GEMODO dice che non corrisponde.

**Acceptance Scenarios**:

1. **Given** un PDF consegnato da GEMODO, **When** l'amministratore lo verifica,
   **Then** vede la generazione: data e ora, utente e client, sistema e
   `external_context_id`, modello e versione.
2. **Given** lo stesso PDF modificato anche di un solo carattere, **When** lo
   verifica, **Then** GEMODO risponde che non corrisponde a nessuna generazione.
3. **Given** un PDF che non viene da GEMODO, **When** lo verifica, **Then** la
   risposta e' la stessa del caso 2.

---

### User Story 3 - Verificare che dei dati siano quelli di una generazione (Priority: P2)

**Stato 2026-10-06**: rinviata a spec futura. Non implementare API o UI di
verifica dati in questo incremento.

Come amministratore, data una generazione e un insieme di dati (per esempio
quelli che GEBAN dice di aver inviato), voglio sapere se corrispondono.

**Why this priority**: completa la verifica senza conservare i dati in chiaro.

**Independent Test**: con i dati inviati la verifica dice "corrispondono"; con
un valore cambiato dice "non corrispondono".

**Acceptance Scenarios**:

1. **Given** una generazione e gli stessi dati inviati, anche in un ordine
   diverso dei campi, **When** l'amministratore li verifica, **Then** GEMODO
   risponde che corrispondono.
2. **Given** gli stessi dati con un valore diverso, **When** li verifica,
   **Then** GEMODO risponde che non corrispondono.

---

### User Story 4 - Registro attivita' per gli amministratori (Priority: P2)

Come amministratore, voglio vedere in un unico elenco chi ha fatto cosa nel
sistema, filtrare e esportare.

**Why this priority**: oggi gli eventi sono in tre tabelle senza una schermata.

**Independent Test**: creo un modello, lo pubblico, genero un PDF, provo una
chiamata senza permesso; il registro mostra le quattro azioni con chi, quando e
l'esito; un utente non amministratore non vede la pagina e riceve 403
dall'API.

**Acceptance Scenarios**:

1. **Given** azioni su modelli, configurazione, integrazioni e generazioni,
   **When** l'amministratore apre il registro, **Then** le vede in ordine di
   tempo, con filtri per periodo, utente, azione, oggetto ed esito.
2. **Given** un filtro, **When** l'amministratore esporta, **Then** ottiene un
   CSV con le stesse righe.
3. **Given** un utente senza `GEMODO_ADMIN`, **When** chiede il registro,
   **Then** riceve 403.

---

### Edge Cases

- Il database non accetta la riga del registro delle generazioni: il PDF **non**
  si consegna (FR-006).
- Il registro attivita' non accetta un evento: l'azione va avanti, l'errore
  finisce nel log applicativo (FR-013).
- Un evento con un dettaglio enorme: il dettaglio si tronca, l'evento si scrive.
- Molte chiamate negate (401) da uno stesso client in poco tempo: si registrano
  tutte, ma col minimo indispensabile (FR-012).
- `numero_posti` inviato come `2`, `2.0` o `"2"`: per l'impronta sono dati
  diversi; la verifica deve usare i dati esattamente come sono stati inviati.
- Righe di `documento_generato` gia' esistenti: restano nel registro, con il
  percorso del file non piu' usato.

## Requirements *(mandatory)*

### Functional Requirements

**Generazione**

- **FR-001**: Ogni `POST /documenti/genera` con dati validi MUST produrre il PDF
  e restituirlo, qualunque sia la storia di quella chiave.
- **FR-002**: La stessa chiave (sistema, `external_context_id`, versione del
  modello) MUST poter essere usata un numero illimitato di volte, anche con dati
  diversi. Non esiste piu' il conflitto `RICHIESTA_IDEMPOTENTE_IN_CONFLITTO`.
- **FR-003**: GEMODO MUST NOT conservare il file PDF generato.
- **FR-004**: Ogni generazione MUST avere un riferimento nuovo e univoco,
  restituito nell'header `X-Riferimento-Documentale` e scritto nei metadati del
  PDF, non nel testo visibile.

**Registro delle generazioni**

- **FR-005**: Ogni chiamata a `genera` MUST lasciare una riga nel registro delle
  generazioni con: riferimento, sistema richiedente, `external_context_id`,
  versione del modello, utente, client, ruoli, data e ora, esito (generato,
  dati non validi, errore), impronta SHA-256 dei dati normalizzati e, se
  generato, impronta SHA-256 e dimensione del PDF consegnato.
- **FR-006**: Il PDF MUST essere consegnato solo dopo che la riga e' registrata:
  un PDF senza riga non sarebbe verificabile. Se la registrazione fallisce, la
  chiamata risponde con un errore e GEBAN puo' ripeterla.
- **FR-007**: I dati ricevuti MUST NOT essere conservati in chiaro; si conserva
  solo l'impronta, calcolata su una forma normalizzata (chiavi ordinate) cosi'
  che l'ordine dei campi non conti.

**Verifica**

- **FR-008** *(rinviato a spec futura)*: Un amministratore MUST poter verificare un PDF: GEMODO ne calcola
  l'impronta e risponde con la generazione corrispondente o con "non
  corrisponde".
- **FR-009** *(rinviato a spec futura)*: Un amministratore MUST poter verificare se un insieme di dati
  corrisponde a una generazione, indicata dal riferimento.
- **FR-010** *(rinviato a spec futura)*: La verifica MUST mostrare il modello e la versione usati dalla
  generazione.

**Registro attivita'**

- **FR-011**: Un registro attivita', consultabile solo con `GEMODO_ADMIN`, MUST
  mostrare in un unico elenco gli eventi di modelli, configurazione,
  integrazioni, generazioni, validazioni, verifiche e accessi negati, con:
  data e ora, utente, client, contesto, azione, oggetto, esito, dettaglio.
- **FR-012**: Gli accessi negati (401, 403) MUST essere registrati con il minimo:
  data e ora, client e soggetto se noti, percorso, esito.
- **FR-013**: Un errore nella scrittura del registro attivita' MUST NOT
  interrompere ne' modificare l'azione registrata; MUST finire nel log
  applicativo.
- **FR-014**: Il registro attivita' MUST essere filtrabile per periodo, utente,
  azione, oggetto ed esito, paginato, ed esportabile in CSV.
- **FR-015**: Le letture semplici (catalogo, pagine, consultazioni) MUST NOT
  essere registrate.
- **FR-016**: I registri MUST essere conservati senza scadenza.

**Contratti e compatibilita'**

- **FR-017**: Il download dei documenti generati MUST essere tolto; la lettura di
  una generazione per riferimento resta, solo per amministratori.
- **FR-018**: I contratti 004 e 005, `docs/api-per-geban.md` e il catalogo
  errori MUST riflettere le regole nuove; GEBAN va avvisato.

### Key Entities

- **Generazione**: una chiamata a `genera` e il suo esito; le impronte di dati e
  PDF; nessun file. Evolve da `documento_generato`.
- **Evento attivita'**: chi, quando, cosa, su quale oggetto, con quale esito.
  Le tabelle di audit esistenti (modelli, configurazione, integrazioni) restano
  la fonte dei loro eventi; il registro le mostra insieme.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: GEBAN rigenera lo stesso bando con la stessa chiave e dati diversi
  10 volte di seguito: 10 PDF, 10 righe di registro, nessun errore.
- **SC-002** *(rinviato a spec futura)*: Il 100% dei PDF consegnati e'
  riconosciuto dalla verifica; un PDF con un solo byte cambiato non lo e' mai.
- **SC-003**: Con il registro attivita' non scrivibile, generazioni, modifiche
  ai modelli e configurazione continuano a funzionare.
- **SC-004**: Nessuna copia dei PDF sul disco del backend dopo una generazione.

## Assumptions

- L'impronta dimostra che un PDF e' identico a quello registrato, nei limiti
  dell'integrita' del database di GEMODO. Un valore legale pieno richiede un
  sigillo elettronico sul PDF: e' fuori da questa spec.
- Il registro delle generazioni sta nello stesso database, nella stessa
  transazione che rende la generazione consegnabile (FR-006); il registro
  attivita' e' best-effort e separato (FR-013).
- I PDF gia' generati e salvati prima di questa spec non vengono migrati: i loro
  file sono comunque persi al primo redeploy.
