# Research - Catalogo Modelli E Contratto Dati GEBAN

## Decision: FastAPI backend per la feature 001

**Rationale**: la scelta aggiornata del progetto e' usare Python FastAPI per il backend.
La feature richiede API REST contract-first, validazione di payload dinamici, OpenAPI,
persistenza relazionale e integrazione futura con Keycloak. FastAPI si allinea bene a
Pydantic, type hints, JSON Schema e documentazione OpenAPI.

**Alternatives considered**:

- Backend generico non definito: scartato perche' avrebbe prodotto task poco eseguibili.
- Implementazione frontend-first: scartata perche' GEBAN consuma API backend.

## Decision: PostgreSQL con migrations Alembic

**Rationale**: il dominio ha stati, vincoli univoci, relazioni e storico versioni. Le
migrations rendono esplicite le evoluzioni dello schema.

**Alternatives considered**:

- Storage file/JSON: insufficiente per vincoli e interrogazioni.
- Database GEBAN: vietato dalla costituzione.

## Decision: API REST contract-first con OpenAPI

**Rationale**: GEBAN deve costruire maschere dinamiche e validare payload usando contratti
espliciti. OpenAPI consente versionamento, esempi e test di contratto.

**Alternatives considered**:

- Contratto solo documentato in Markdown: utile ma non abbastanza verificabile.
- GraphQL: non richiesto e meno coerente con proposta REST.

## Decision: validazione payload strict

**Rationale**: i campi extra sono considerati errore. Questo evita che dati non dichiarati
entrino nello snapshot o alterino la generazione.

**Alternatives considered**:

- Ignorare campi extra con warning: rischia divergenza tra GEBAN e servizio modelli.
- Salvare campi extra: viola il principio di contratto dati esplicito.

## Decision: variante modello distinta da versione modello

**Rationale**: modelli simili per stesso tipo, categoria e tipologia possono coesistere
come varianti funzionali, senza abusare del concetto di versione. Le versioni rappresentano
l'evoluzione storica della stessa variante.

**Alternatives considered**:

- Piu' versioni operative sovrapposte della stessa variante: scartato perche' crea
  ambiguita' operativa.
- Un solo modello per contesto: troppo rigido per casi con differenze funzionali.

## Decision: `modello_versione_id` obbligatorio nelle chiamate operative successive

**Rationale**: quando esistono piu' varianti pubblicate nello stesso contesto,
l'identificativo della versione scelta elimina ambiguita'. Il servizio non seleziona
automaticamente "l'ultima" versione. In modalita' operativa esiste una sola versione
pubblicata corrente per variante.

**Alternatives considered**:

- Fallback all'ultima pubblicata: comodo ma ambiguo.
- Selezione per solo codice modello: insufficiente quando piu' varianti sono pubblicate.

## Decision: modalita' catalogo operativa e storica

**Rationale**: GEBAN ha bisogno del catalogo operativo per scegliere versioni utilizzabili,
mentre consultazioni interne possono richiedere storico e filtri di pubblicazione.

**Alternatives considered**:

- Solo catalogo corrente: perde visibilita' storica.
- Solo catalogo completo: troppo rumoroso per il flusso operativo.

## Decision: tipologia GEBAN/SOL validata contro un elenco configurato

**Rationale**: `009` ha confermato (`DEC-001-TIPOLOGIE-SOL`) il perimetro iniziale
delle tipologie GEBAN/SOL (TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB), ciascuna
con codice SOL. Il servizio deve trattare una tipologia sconosciuta come errore
funzionale esplicito, non come filtro che restituisce silenziosamente zero risultati,
per evitare che GEBAN interpreti un errore di configurazione come "nessun modello
disponibile".

**Alternatives considered**:

- Nessuna validazione, tipologia come stringa libera: scartato, nasconde errori di
  integrazione GEBAN-SOL.
- Validazione lato GEBAN soltanto: scartato, il servizio modelli resta responsabile
  del proprio contratto dati indipendentemente dal chiamante.

## Decision: campo con lingua e obbligatorieta' condizionata da `bando_inglese`

**Rationale**: `009` ha confermato (`DEC-001-LINGUA-IT-EN`) che, quando GEBAN invia
`Bando Inglese = Si`, servono anche i campi inglesi corrispondenti. Il modo piu'
semplice per restare dentro al contratto dati dinamico gia' esistente (senza introdurre
un secondo meccanismo di validazione) e' aggiungere `lingua` (`IT`/`EN`, default `IT`)
a `ModelloCampoRichiesto` e rendere l'obbligatorieta' dei campi `EN` condizionata al
flag booleano `bando_inglese` nel payload.

**Alternatives considered**:

- Due contratti dati separati (uno IT, uno EN): scartato, raddoppia la manutenzione dei
  modelli e complica la generazione a doppio output della `004`.
- Validare la lingua interamente lato GEBAN prima dell'invio: scartato, sposterebbe la
  responsabilita' del contratto dati fuori dal servizio modelli.

## Decision: campi comuni GEBAN, bando multiplo e ribando restano dati, non nuovi meccanismi

**Rationale**: FR-029 (dati demo `009`), bando multiplo e ribando (chiariti in `009`
il 2026-07-28) sono contenuto del contratto dati dinamico gia' previsto da questa
feature (`ModelloCampoRichiesto`), non richiedono nuove entita' o un nuovo motore di
validazione. `Data inizio` resta esclusa dai campi gestiti per decisione esplicita.

**Alternatives considered**:

- Modellare bando multiplo/ribando come entita' di dominio proprie in questa feature:
  scartato, la generazione (PDF unico sul padre, nuovo protocollo per il ribando) e'
  responsabilita' di `004`/`005`; questa feature valida solo dati, non li interpreta.

## Decision: `modello_versione_id` resta intero (int64)

**Rationale**: il contratto OpenAPI di questa feature tipizza gia' `modello_id` e
`modello_versione_id` come interi. `009` usa identificativi stringa nei propri
manifest demo (es. `demo-bando-concorso-standard-v1`), ma solo come etichette
leggibili nei manifest di qualita', non come contratto API. Cambiare tipo qui sarebbe
una modifica breaking non necessaria finche' GEBAN non richiede esplicitamente un
formato diverso. La decisione resta tracciata come `ASSUNTA_PROVVISORIA`
(`DEC-001-IDENTIFICATIVI-MODELLO`) perche' la conferma definitiva richiede
allineamento con GEBAN.

**Alternatives considered**:

- Passare a identificativo stringa per coerenza con i manifest demo `009`: scartato per
  ora, e' un cambio breaking senza un requisito che lo richieda esplicitamente.

## Decision: profilo GEBAN e autorizzazione fine restano fuori scope

**Rationale**: `DEC-001-PROFILO-GEBAN` e le decisioni collegate (`DEC-001-CONFIG-PROFILO-GEBAN`,
`DEC-001-RELAZIONE-PROFILO-CATALOGO`, `DEC-001-API-PROFILO-GEBAN`) restano aperte.
Il catalogo di questa feature continua a filtrare solo per stato di pubblicazione;
l'autorizzazione fine per sistema richiedente e profilo di integrazione (Keycloak per
identita' generale, GEMODO per profili) e' responsabilita' della `006` e non entra qui
come assunzione implicita.

**Alternatives considered**:

- Implementare gia' un filtro per profilo GEBAN in questa feature: scartato, le
  decisioni da cui dipende (formato profilo, relazione con il catalogo, API dedicate)
  non sono ancora chiuse; implementarlo ora significherebbe costruire su assunzioni non
  confermate.
