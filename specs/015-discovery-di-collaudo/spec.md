# Feature Specification: Discovery di collaudo

**Feature Branch**: `test`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Generare una spec per un endpoint discovery di
test da deployare e integrare nell'ambiente di test, per provare piu' documenti
e piu' sottocategorie, verificare la flessibilita' del contratto e trovare
eventuali bug; usarlo anche per simulare l'integrazione e la verifica di un
contesto diverso. Deve essere marcato come di test."

Riferimento del contratto che il servizio esercita: `docs/contratto-dati.md`.

## Clarifications

### Session 2026-10-07

- Q: Il token attuale (contesto `geban`) basta? → A: Dipende dal contesto con
  cui si registra l'integrazione di collaudo. I permessi di un contesto arrivano
  **solo** dai ruoli che il token porta in `contexts.<contesto>.roles`, tradotti
  dal profilo di accesso dell'integrazione (`backend/app/configurazione/accessi.py`).
  Quindi:
  - registrata con contesto nel token `geban`, l'integrazione di collaudo
    funziona subito con il token attuale. Si provano flessibilita', piu' tipi
    documento, piu' livelli e bug, ma non l'isolamento fra contesti;
  - registrata con un contesto nuovo, per esempio `gemodo-test`, serve che il
    sistema di autenticazione CNR (ACE) assegni quel contesto e i suoi ruoli
    all'utente. Senza, il token attuale non ottiene nessun permesso su quel
    contesto. E' comunque utile per la meta' negativa: l'amministratore puo'
    registrarla e verificarla, e si controlla che un utente `geban` non veda ne'
    modifichi nulla di quel contesto.
- Q: Una soluzione "senza controllo"? → A: No. L'unico interruttore esistente,
  `GEMODO_USE_MOCK_PRINCIPAL`, spegne l'autenticazione per **tutto** il backend:
  su un server raggiungibile chiunque diventerebbe l'utente finto. Resta
  riservato ai test locali.
- Q: Come si riconosce che e' di test? → A: Il nome dell'integrazione inizia con
  `TEST - `, i codici dei tipi documento iniziano con `TEST_`, le descrizioni
  dei nodi radice contengono "(collaudo)", e il servizio risponde con l'header
  `X-Gemodo-Collaudo: true`.
- Q: Dove vive il servizio? → A: Un servizio a parte nel compose del server di
  test, non una rotta del backend, cosi' GEMODO lo chiama come una vera
  integrazione esterna, passando dalla lista delle destinazioni autorizzate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Collegare il discovery di collaudo (Priority: P1)

Come amministratore GEMODO, voglio registrare il discovery di collaudo come una
nuova integrazione e farla risultare connessa, cosi' da avere un secondo sistema
esterno su cui provare GEMODO senza toccare GEBAN.

**Why this priority**: senza un secondo endpoint controllato, ogni prova sulla
flessibilita' dipende dai dati reali di GEBAN.

**Independent Test**: dopo il deploy, l'amministratore crea l'integrazione
`TEST - Discovery di collaudo` con URL dello scenario `base`, la verifica, e
l'esito e' `CONFORME` con i tre tipi documento `TEST_*` dichiarati.

**Acceptance Scenarios**:

1. **Given** il servizio deployato e la sua origine nelle destinazioni
   autorizzate, **When** l'amministratore verifica l'endpoint `base`, **Then**
   l'integrazione risulta connessa.
2. **Given** l'origine non autorizzata, **When** si verifica, **Then** GEMODO
   risponde `DESTINAZIONE_NON_APPROVATA` e non effettua la chiamata.
3. **Given** l'integrazione connessa con contesto nel token `geban`, **When** un
   gestore del contesto `geban` apre i modelli, **Then** vede i tipi documento
   `TEST_*` accanto a `BANDO_CONCORSO`, senza che GEBAN cambi nulla.

---

### User Story 2 - Provare la flessibilita' del contratto (Priority: P1)

Come gestore modelli, voglio creare modelli su tipi documento con profondita',
dimensioni e campi diversi da quelli di GEBAN, cosi' da verificare che builder,
catalogo, validazione e generazione siano davvero generici.

**Why this priority**: e' lo scopo principale del collaudo.

**Independent Test**: per ciascuno dei tre tipi documento `TEST_*` si crea,
compone, pubblica e genera un modello; per ciascuno una richiesta con dati
validi produce un PDF e una con dati sbagliati produce gli errori attesi.

**Acceptance Scenarios**:

1. **Given** `TEST_BANDO` con tre livelli, **When** il gestore crea un modello,
   **Then** naviga i tre livelli fino alla foglia e vede le dimensioni lingua e
   livello con il default proposto.
2. **Given** `TEST_CONTRATTO` con un solo livello e nessuna lingua, **When** il
   gestore crea un modello, **Then** non gli viene chiesta nessuna lingua e il
   catalogo restituisce `lingua: null`.
3. **Given** `TEST_AVVISO` con la dimensione `area_geografica`, **When**
   l'amministratore apre le policy, **Then** la dimensione compare come non
   configurata; dopo averla configurata, il catalogo filtra con
   `dimensione[area_geografica]=NORD`.
4. **Given** una foglia con campi `string`, `number`, `date`, `boolean`, **When**
   si valida un payload con un valore del tipo sbagliato per ciascuno, **Then**
   ogni campo produce `TIPO_NON_VALIDO`.

---

### User Story 3 - Simulare l'evoluzione dell'albero (Priority: P2)

Come amministratore, voglio cambiare l'URL dell'integrazione verso una versione
"evoluta" dello stesso albero, cosi' da verificare cosa succede ai modelli
esistenti quando il sistema esterno aggiunge, toglie o cambia campi e rami.

**Why this priority**: e' il comportamento promesso da `docs/contratto-dati.md`
("Cosa puo' cambiare l'integratore senza toccare GEMODO") e oggi non ha una
prova ripetibile.

**Independent Test**: con modelli pubblicati sullo scenario `base`, si passa
all'URL `evoluzione`; i modelli pubblicati continuano a validare con i campi
salvati, le nuove versioni vedono i cambiamenti.

**Acceptance Scenarios**:

1. **Given** un modello pubblicato, **When** l'albero aggiunge un campo, **Then**
   la versione pubblicata non lo chiede e una nuova versione puo' includerlo.
2. **Given** un campo che diventa obbligatorio, **When** si valida contro la
   versione pubblicata, **Then** l'obbligatorieta' resta quella salvata.
3. **Given** un campo rimosso, **When** si crea una nuova versione che lo
   include, **Then** GEMODO risponde `CAMPO_NON_AMMESSO`.
4. **Given** una foglia rimossa, **When** si crea una nuova versione di un
   modello su quella foglia, **Then** GEMODO risponde che il ramo non e' piu'
   disponibile, e i modelli esistenti restano consultabili.
5. **Given** una nuova dimensione, **When** si aprono le policy, **Then** compare
   come non configurata.

---

### User Story 4 - Verificare la diagnosi degli errori (Priority: P2)

Come amministratore, voglio puntare l'integrazione su scenari volutamente
difformi o non raggiungibili, cosi' da verificare che l'esito della verifica
dica cosa non va e dove.

**Why this priority**: e' la parte del contratto che con GEBAN reale non si puo'
provare senza rompere GEBAN.

**Independent Test**: per ogni scenario negativo la verifica riporta l'esito
atteso e, per i difformi, il percorso del punto difforme.

**Acceptance Scenarios**:

1. **Given** ciascuno scenario `non-conforme/*`, **When** si verifica, **Then**
   l'esito e' `NON_CONFORME` con un messaggio che nomina la regola violata.
2. **Given** gli scenari `errore-503`, `lento` e `non-json`, **When** si
   verifica, **Then** l'esito e' `NON_RAGGIUNGIBILE` (i primi due) o
   `NON_CONFORME` (il terzo).
3. **Given** lo scenario `paginato`, **When** si verifica, **Then** l'esito e'
   `CONFORME` e i nodi delle pagine sono uniti.
4. **Given** lo scenario `alias`, **When** si verifica, **Then** `lingue`/`ENG`
   e `livelloBase` sono accettati come `lingue_possibili`/`EN` e `livello_base`.

---

### User Story 5 - Isolamento fra contesti (Priority: P3)

Come amministratore, voglio registrare il collaudo con un contesto diverso da
`geban`, cosi' da verificare che i permessi di un contesto non valgano nell'altro.

**Why this priority**: richiede un contesto ACE dedicato (dipendenza esterna);
la meta' negativa si prova anche senza.

**Independent Test**: con integrazione nel contesto `gemodo-test`, un token che
porta solo `geban` non vede i modelli di collaudo (404 sulle rotte per
identificativo, 403 sulla ricerca esplicita per tipo documento) e non puo'
crearne.

**Acceptance Scenarios**:

1. **Given** un token con solo `geban`, **When** chiede un modello di collaudo
   per identificativo, **Then** riceve 404 `MODELLO_VERSIONE_NON_TROVATO`.
2. **Given** lo stesso token, **When** cerca il catalogo per `TEST_BANDO`,
   **Then** riceve 403.
3. **Given** un token con ruoli in `gemodo-test` (quando ACE lo fornisce),
   **When** opera sui modelli di collaudo, **Then** puo' farlo, ma non sui
   modelli `geban` se non ha ruoli anche li'.

---

### Edge Cases

- Il servizio di collaudo e' giu': GEMODO tratta l'integrazione come qualunque
  integrazione irraggiungibile; GEBAN non e' toccato.
- Si cambia l'URL da `base` a `evoluzione` e ritorno: la verifica va ripetuta a
  ogni cambio, come per qualsiasi modifica della configurazione.
- I codici `TEST_*` non collidono con `BANDO_CONCORSO`: lo stesso tipo
  documento non puo' appartenere a due integrazioni
  (`TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE`).
- Fine del collaudo: l'integrazione di test si elimina dall'interfaccia; i
  modelli di collaudo vanno eliminati prima.

## Requirements *(mandatory)*

### Functional Requirements

#### Servizio

- **FR-001**: Il servizio MUST rispondere in sola lettura, con richieste `GET`
  senza autenticazione, come previsto dal contratto discovery per questa
  versione.
- **FR-002**: Ogni scenario MUST essere un URL distinto con una risposta fissa,
  versionata nel repository, cosi' che una prova sia ripetibile e citabile.
- **FR-003**: Il servizio MUST esporre almeno gli scenari della tabella
  "Catalogo degli scenari".
- **FR-004**: Ogni risposta MUST portare l'header `X-Gemodo-Collaudo: true`;
  `GET /` MUST elencare gli scenari con l'esito atteso dalla verifica GEMODO.
- **FR-005**: Il servizio MUST essere deployabile come servizio separato nel
  compose del server di test e MUST NOT far parte di un deploy di produzione.
- **FR-006**: Gli scenari conformi MUST essere validi contro il contratto
  discovery attivo (oggi 0.7.0); lo scenario `articolato` MUST essere valido
  contro lo schema 0.8.0 di `specs/014-articolazioni-bando/contracts/`.

#### Marcatura

- **FR-007**: Tutti i tipi documento MUST avere codice con prefisso `TEST_` e
  le descrizioni dei nodi radice MUST contenere "(collaudo)".
- **FR-008**: La procedura di collaudo MUST registrare l'integrazione con nome
  che inizia con `TEST - `.

#### Collegamento a GEMODO

- **FR-009**: La documentazione di deploy MUST indicare come aggiungere
  l'origine del servizio a `GEMODO_INTEGRAZIONI_ALLOWLIST` e, essendo una
  destinazione HTTP interna alla rete del compose, a
  `GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO`.
- **FR-010**: La procedura MUST descrivere le due modalita' di contesto (stesso
  contesto `geban`, contesto dedicato) e cosa ciascuna permette di provare.
- **FR-011**: Il collaudo MUST NOT richiedere `GEMODO_USE_MOCK_PRINCIPAL` ne'
  altri interruttori che indeboliscano l'autenticazione.

#### Esiti attesi

- **FR-012**: Per ogni scenario la spec MUST dichiarare l'esito atteso della
  verifica, cosi' che un esito diverso sia un bug di GEMODO o dello scenario,
  mai un'ambiguita'.
- **FR-013**: Gli esiti attesi MUST essere verificati da un test automatico che
  esegue l'adapter HTTP di GEMODO contro il servizio reale avviato in locale.

### Catalogo degli scenari

Prefisso `GET /discovery/`.

| Scenario | Contenuto | Esito atteso della verifica |
|---|---|---|
| `base` | Tre tipi documento: `TEST_BANDO` (3 livelli: area, tipologia, profilo; lingue IT/EN, livelli con default); `TEST_CONTRATTO` (1 livello, nessuna lingua); `TEST_AVVISO` (2 livelli, dimensione `area_geografica`, campi `string`/`number`/`date`/`boolean`, vincoli `minLength`/`minimum`, campo con `fonte_opzioni`). Piu' rami per livello. | `CONFORME` |
| `evoluzione` | Come `base`, con: un campo aggiunto, un campo reso obbligatorio, un campo rimosso, una foglia rimossa, una foglia nuova, una dimensione nuova. | `CONFORME` |
| `alias` | `lingue` con `ENG` al posto di `lingue_possibili`/`EN`; `livelloBase` al posto di `livello_base`. | `CONFORME` |
| `paginato` | Envelope `_embedded.discovery` su tre pagine con `_links.next.href`. | `CONFORME` |
| `profondo` | Un ramo a 8 livelli. | `CONFORME` |
| `articolato` | `TEST_BANDO` con campo ripetibile `articolazioni` (0.8.0). | 0.7.0: `CONFORME`, sotto-campi ignorati; dopo `014`: `CONFORME`, sotto-campi letti |
| `non-conforme/figli-e-campi` | Un nodo con `figli` e `campi`. | `NON_CONFORME` |
| `non-conforme/nodo-vuoto` | Un nodo senza `figli` ne' `campi`. | `NON_CONFORME` |
| `non-conforme/codici-duplicati` | Due fratelli con lo stesso `codice`. | `NON_CONFORME` |
| `non-conforme/campo-incompleto` | Un campo senza `etichetta`. | `NON_CONFORME` |
| `non-conforme/tipo-sconosciuto` | Un campo con `tipo: "enum"`. | `NON_CONFORME` |
| `non-conforme/validita-senza-fuso` | `validita` senza fuso orario. | `NON_CONFORME` |
| `non-conforme/default-fuori-livelli` | `livello_base` non compreso in `livelli_possibili`. | `NON_CONFORME` |
| `non-conforme/alias-discordanti` | `lingue` e `lingue_possibili` con valori diversi. | `NON_CONFORME` |
| `non-conforme/chiavi-duplicate` | Un oggetto JSON con la stessa chiave due volte. | `NON_CONFORME` |
| `non-json` | Risposta 200 con `Content-Type: text/plain`. | `NON_CONFORME` |
| `errore-503` | Risposta 503. | `NON_RAGGIUNGIBILE` |
| `lento` | Risponde dopo 15 secondi, oltre il limite di 10. | `NON_RAGGIUNGIBILE` |

### Key Entities *(include if feature involves data)*

- **Scenario**: una risposta discovery fissa, con nome, URL ed esito atteso.
- **Integrazione di collaudo**: integrazione GEMODO marcata `TEST - `, che punta
  a uno scenario.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tutti gli scenari producono l'esito atteso nel test automatico e
  sul server di test.
- **SC-002**: Per ognuno dei tre tipi documento `TEST_*` si completa il ciclo
  crea, pubblica, genera, senza interventi sul database.
- **SC-003**: Ogni divergenza trovata fra esito atteso ed esito reale e'
  registrata come bug con lo scenario che la riproduce.
- **SC-004**: Durante il collaudo GEBAN non subisce cambiamenti e il suo test di
  connessione resta `CONFORME`.
- **SC-005**: Rimuovere il servizio e l'integrazione di collaudo non lascia
  configurazioni di test attive.

## Assumptions

- Il server di test e' l'unico ambiente in cui il servizio viene deployato.
- L'utente ha gia' il ruolo di amministratore e quello di gestore nel contesto
  `geban`.
- Il contesto ACE dedicato (`gemodo-test`) e' una richiesta esterna: la User
  Story 5 si completa quando e' disponibile.
- Il contratto attivo e' 0.7.0; quando la spec `014` sara' implementata, lo
  scenario `articolato` cambiera' esito come indicato in tabella.
