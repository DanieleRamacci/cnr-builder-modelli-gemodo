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

**Rationale**: `009` ha confermato (`DEC-001-TIPOLOGIE-SOL`) la validazione contro un
elenco configurato; il perimetro iniziale dei bandi e' ora espresso come procedure
GEBAN/SOL (CP, TD, TI, IR, MOB), ciascuna con codice SOL o placeholder interno da
configurare. Il servizio deve trattare una tipologia sconosciuta come errore
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

## Decision: profilo GEBAN e autorizzazione fine restano fuori scope *(primo incremento; superata dal secondo incremento sotto)*

**Rationale**: `DEC-001-PROFILO-GEBAN` e le decisioni collegate
(`DEC-001-CONFIG-PROFILO-GEBAN`, `DEC-001-RELAZIONE-PROFILO-CATALOGO`,
`DEC-001-API-PROFILO-GEBAN`) erano sospese esplicitamente per il primo incremento
produttivo della `001`. Il catalogo del primo incremento filtra solo per stato di
pubblicazione, contesto, tipologia e versione modello; l'autorizzazione fine per
sistema richiedente e profilo di integrazione resta implementata a partire dal
secondo incremento (vedi sezione dedicata sotto, decisioni ora `CONFERMATA`).

**Alternatives considered**:

- Implementare gia' un filtro per profilo GEBAN nel primo incremento: scartato allora,
  le decisioni da cui dipende (formato profilo, relazione con il catalogo, API
  dedicate) non erano ancora chiuse; implementarlo avrebbe significato costruire su
  assunzioni non confermate.

---

## Secondo incremento (2026-09-14): perimetro per-profilo, Ufficio, registro contratti dati

Le decisioni sotto sono `CONFERMATA` in `docs/decision-register.yaml` (readiness gate
verde per PLAN/TASKS sulla `001`). Riguardano il design, non ancora l'implementazione:
`tasks.md` di questo incremento resta da generare.

### Decision: Ufficio come entita' separata da ProfiloDiIntegrazione

**Rationale** (`DEC-001-UFFICIO-PROPRIETARIO`): ownership (chi puo' autorare
categorie/tipologie/contratti dati/modelli di un tipo documento) e autorizzazione al
consumo (chi puo' consultare/generare, es. GEBAN) sono due dimensioni indipendenti. Un
singolo profilo consumer (GEBAN) potra' essere autorizzato a piu' tipi documento
posseduti da Uffici diversi (es. `BANDO_CONCORSO` di Ufficio Reclutamento e, in
futuro, `GRADUATORIA_CONCORSO` di un ufficio diverso — coerente con Principio III
della costituzione, che nomina esplicitamente le graduatorie fra i tipi documento
futuri attesi). Un `TipoDocumento` riferisce esattamente un `Ufficio` proprietario;
`ProfiloDiIntegrazione.tipi_documento_ammessi` (gia' una lista, `009`) referenzia
liberamente tipi documento indipendentemente da chi li possiede.

**Alternatives considered**:

- Flag `tipo_integrazione: APPLICAZIONE|UFFICIO` su `ProfiloDiIntegrazione`: scartato,
  mescolava ownership e consumo nella stessa entita', impedendo il caso GEBAN
  multi-tipo-documento con proprietari diversi descritto sopra.
- Nessuna entita' Ufficio, proprieta' implicita nel codice: scartato, non scala oltre
  GEBAN senza redesign quando arrivera' un secondo sistema con propri Ufficio/tipo
  documento.

### Decision: registro contratti dati scoped per tipo documento

**Rationale** (`DEC-001-REGISTRO-CONTRATTI-DATI`): `contratti_dati_ammessi` su
`ProfiloDiIntegrazione` (`009`) referenzia oggi una stringa priva di definizione
(`bando-concorso-common-fields-v1`). Si introduce un registro di contratti dati
riusabili, scoped per `TipoDocumento` (proprieta' ereditata dall'Ufficio, non dal
profilo consumer), stessa forma di `ModelloCampoRichiesto`. Il builder (`002`/`003`)
vincolera' i campi che un gestore puo' dichiarare in un modello a quelli ammessi dal
contratto dati del tipo documento.

**Alternatives considered**:

- Lasciare `contratti_dati_ammessi` come riferimento libero non risolto: scartato,
  e' esattamente l'assunzione silenziosa che la costituzione (Contract-First
  Integration) e FR-018 vietano.
- Un contratto dati per singolo profilo consumer invece che per tipo documento:
  scartato, impedirebbe la condivisione di un contratto fra piu' Applicazioni
  autorizzate allo stesso tipo documento.

### Decision: generalizzare `TipologiaBandoSOL` a `TipologiaDocumento` ora

**Rationale** (`DEC-001-GENERALIZZAZIONE-TIPOLOGIA`): la tabella `tipologia_bando_sol`
era globale (non scoped per tipo documento) e nominata/modellata specificamente per
l'integrazione GEBAN-SOL (`codice_sol` obbligatorio). Rinominata subito, su richiesta
esplicita del product owner, invece che rimandata a quando ci sara' piu' codice sopra
da riscrivere: diventa `tipologia_documento`, scoped per `tipo_documento_id` (come gia'
`categoria_documento`), con `riferimento_esterno` opzionale. Il parametro pubblico
`codice_tipologia` e il codice errore `TIPOLOGIA_SOL_NON_VALIDA` restano invariati:
nessun impatto sul contratto OpenAPI gia' pubblicato.

**Alternatives considered**:

- Rimandare la generalizzazione a quando arrivera' un secondo tipo documento reale:
  scartato su richiesta esplicita, il costo di un rename cresce con la quantita' di
  codice che dipende dal nome/forma attuali (repository, service, test, seed, doc).

### Decision: profili/uffici migrano da YAML-in-memoria a tabelle Postgres

**Rationale** (`DEC-001-CONFIG-PROFILO-GEBAN`): oggi `SistemaRichiedente`/
`ProfiloDiIntegrazione` sono solo YAML letto e cachato in memoria di processo
(`_load_sistemi_richiedenti_cached`, `@lru_cache` senza scadenza in
`backend/app/common/security.py`) — mai persistito. Il file YAML diventa il seed
iniziale che popola vere tabelle Postgres (stesso pattern gia' in uso per il catalogo,
migration `0005`-`0007`: rilegge lo YAML, upsert, disattiva le righe non piu' presenti).
`security.py` legge dalle tabelle invece che dalla cache eterna del file. Un futuro
punto di modifica (interfaccia web di amministrazione profili/uffici) scrivera' sulle
stesse tabelle, senza richiedere un cambio di schema in quel momento.

**Alternatives considered**:

- Mantenere lo YAML in memoria e aggiungere un TTL alla cache: scartato, risolve solo
  parzialmente la staleness e non prepara il terreno per un futuro editor.
- Passare subito a una UI di amministrazione: scartato per questo incremento, fuori
  scope rispetto all'obiettivo "produzione con GEBAN prima, resto dopo" confermato dal
  product owner.

### Decision: enforcement del perimetro dentro le route esistenti

**Rationale** (`DEC-001-RELAZIONE-PROFILO-CATALOGO`, `DEC-001-API-PROFILO-GEBAN`,
`DEC-006-AUTORIZZAZIONI-PROFILO-GEBAN`): le route catalogo/validazione
(`backend/app/catalog/api.py`) oggi risolvono `PrincipalGEMODO` solo per il controllo
di ruolo JWT grezzo e lo scartano (`_: PrincipalGEMODO`). Devono invece risolvere il
profilo di integrazione del chiamante e verificare che tipo documento, categoria,
tipologia e `modello_versione_id` richiesti siano nel suo perimetro. Nessun nuovo
endpoint dedicato al profilo: la verifica entra nelle route esistenti. Attiva un
codice errore funzionale gia' descritto in `infra/openapi/errors.md` ma mai raggiunto
da codice reale (`PROFILO_INTEGRAZIONE_NON_ABILITATO`, owner `006`, vedi
`data-model.md`), distinto dall'elenco vuoto (nel perimetro, nessun modello
pubblicato).

**Alternatives considered**:

- Endpoint dedicati per-profilo separati da quelli generali: scartato
  (`DEC-001-API-PROFILO-GEBAN`), duplicherebbe la superficie API senza necessita'.
- Riusare `TIPOLOGIA_SOL_NON_VALIDA`/`CONTESTO_NON_VALIDO` invece di un codice nuovo:
  scartato, confonderebbe "codice inesistente nel catalogo" con "codice esistente ma
  fuori dal perimetro contrattuale del chiamante" — due cause diverse che chi integra
  deve poter distinguere.

## Decision: protezione JWT Keycloak minima nelle API operative della 001

**Rationale**: il progetto ha gia' configurato Keycloak e la costituzione richiede che le
API protette validino JWT Bearer. La `001` quindi implementa il minimo corretto per le
proprie route: firma/JWKS, issuer, audience `gemodo-backend`, scadenza, client tecnico
`geban-backend` per il canale GEBAN e ruoli client `DOCUMENTI_VIEWER` /
`DOCUMENTI_GENERATORE`. Questo non sostituisce la `006`: audit completo, profili di
integrazione e autorizzazioni fini restano fuori scope.

**Alternatives considered**:

- Lasciare le API senza sicurezza fino alla `006`: scartato, non coerente con la
  costituzione e con la configurazione Keycloak gia' disponibile.
- Implementare tutta la sicurezza `006` dentro `001`: scartato, confonderebbe ownership
  e introdurrebbe profili/audit/workflow non necessari per catalogo, contratto e
  validazione payload.

---

## Terzo incremento (2026-09-15): cascading ADR 0001

### Decision: categoria/tipologia di un tipo documento integrato diventano cache, non seed

**Rationale**: dopo una riunione col team GEBAN/ACE, copiare la categorizzazione di
un sistema esterno come sorgente di verita' locale e' stato riconosciuto come
anti-pattern (dati duplicati, doppia sorgente di verita' — vedi
`docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md`,
`DEC-001-OWNERSHIP-DATI-ESTERNI`). Per `BANDO_CONCORSO`, `CategoriaDocumento`,
`TipologiaDocumento`, `ClassificazioneCatalogo` e `RegistroContrattiDati` passano
da seed permanente (migration `0007`) a cache locale a TTL breve, sincronizzata
da un adapter HTTP verso l'endpoint di discovery registrato in
`specs/010-configurazione-cataloghi-integrazioni`. Lo schema esatto dell'adapter e
della cache e' progettato li', non duplicato in questa spec.

**Alternatives considered**:

- Mantenere il seed locale come sorgente permanente: scartato, e' esattamente
  l'anti-pattern identificato nella riunione — rischio di copia non aggiornata.
- Progettare l'adapter/cache direttamente in `001` invece che in una spec dedicata:
  scartato, l'adapter serve anche alla `002` (Ports & Adapters,
  `DEC-002-PORTS-ADAPTERS-DISCOVERY`) e a ogni futura integrazione — una spec
  dedicata (`010`) evita di riprogettarlo per ogni tipo documento.

## Quarto incremento (2026-09-15): il contesto del token sostituisce Ufficio

**Decision**: `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO` (CONFERMATA) rimuove
l'entita' `Ufficio` progettata nel secondo incremento (sopra). `TipoDocumento`
porta un campo diretto `codice_contesto`, verificato contro
`contexts.<codice_contesto>.roles` nel token del chiamante — lo stesso
meccanismo gia' implementato per GEBAN, senza un'entita' aggiuntiva sopra.

**Rationale**: il product owner ha chiarito che l'unita' di scoping e' gia'
il "contesto" del token ACE (un utente puo' averne piu' di uno, ciascuno coi
propri ruoli) — costruire un'entita' Ufficio separata sopra un meccanismo che
gia' risolve lo stesso problema avrebbe aggiunto un livello ridondante. La
correttezza multi-contesto (un ruolo in un contesto non deve autorizzare un
altro contesto) richiede pero' di risolvere l'autorizzazione **per singolo
contesto**, non sulla lista di permessi gia' appiattita su tutti i contesti del
token come fa oggi `PrincipalGEMODO.ruoli`.

**Alternatives considered**:

- Mantenere l'entita' `Ufficio` come pianificata nel secondo incremento: scartato
  esplicitamente dal product owner — livello ridondante sopra un meccanismo
  (contesto del token) che gia' basta.
- Inferire un'etichetta Ufficio dal contesto senza tabella dedicata (scenario B
  di `DEC-002-SORGENTE-UFFICIO-TOKEN`, 2026-09-14): scartato anche questo, va
  oltre il necessario — il contesto stesso e' gia' il valore da usare, non serve
  nemmeno l'etichetta intermedia.
