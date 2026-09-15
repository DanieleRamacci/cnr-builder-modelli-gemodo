# ADR 0001: Ownership Dei Dati Esterni E Onboarding Dei Contesti Documentali

**Status**: Accepted (2026-09-15)

**Deciso da**: product owner, in questa sessione di lavoro (2026-09-14/15), a seguito
di una riunione con il team che gestisce ACE/Keycloak e di una revisione
architetturale del posizionamento di GEMODO in un ecosistema di microservizi.

**Decisioni collegate**: `docs/decision-register.yaml` —
`DEC-001-OWNERSHIP-DATI-ESTERNI`, `DEC-001-ONBOARDING-STRUTTURA-DOCUMENTO`,
`DEC-002-PORTS-ADAPTERS-DISCOVERY`, `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI`.
Supera (senza cancellarle, referenziandole) `DEC-001-CATEGORIE-INIZIALI`,
`DEC-001-REGISTRO-CONTRATTI-DATI`, `DEC-001-CONFIG-PROFILO-GEBAN`.

## Contesto

Fino a questa sessione, GEMODO seedava/possedeva localmente (file YAML + migration
Alembic) la categorizzazione (categorie, tipologie) e il contratto dati di GEBAN —
cioè dati che, nel dominio applicativo, appartengono a GEBAN, non a GEMODO. In una
riunione con il team GEBAN/ACE e' emerso un dubbio esplicito su questo punto:
copiare dati di cui un altro sistema e' proprietario in un DB diverso e' un
anti-pattern in un'architettura a microservizi (stale copy, doppia sorgente di
verita', responsabilita' di aggiornamento ambigua).

Parallelamente, si e' discusso come GEMODO deve gestire l'onboarding di nuovi
"contesti documentali" (tipo documento + categorizzazione + contratto dati +
endpoint di provenienza) sia per applicazioni con un proprio backend esterno (GEBAN,
e futuri sistemi con team di sviluppo dedicato) sia per uffici GEMODO-interni senza
un sistema esterno proprio (es. un futuro "Contratti" self-service).

## Decisione

### 1. Ownership dei dati: si referenzia, non si copia

Per un tipo documento **integrato** (posseduto da un sistema esterno con propria API,
es. `BANDO_CONCORSO` per GEBAN), GEMODO **non** possiede piu' la categorizzazione
completa come sorgente di verita'. Possiede solo:

- la **struttura del modello** che GEMODO stesso definisce (blocchi, sezioni,
  versioni, stato — questo resta sempre e comunque di proprieta' di GEMODO, nessun
  sistema esterno ha voce in capitolo su come e' fatto un modello documentale);
- il **codice di riferimento** (es. `"RICERCATORE"`) che un modello specifico usa,
  salvato come snapshot al momento della creazione — necessario per poter
  indicizzare/filtrare i propri modelli, e distinto dal possedere la *definizione*
  di quel codice (etichetta, stato attivo, regole), che resta autoritativa nel
  sistema esterno.

Questo e' lo stesso principio delle foreign key in un sistema distribuito: un
riferimento a un ID non e' una copia dei dati che quell'ID rappresenta. L'errore da
evitare non e' "salvare un codice", e' "salvare l'elenco completo come se fosse
proprio e tenerlo aggiornato a mano".

Per un tipo documento **self-service** (nessun sistema esterno, es. un futuro
Ufficio Contratti prima di dotarsi di un proprio backend), GEMODO resta l'unico
proprietario possibile: non c'e' nessun altro sistema a cui riferirsi, quindi
possiede la categorizzazione per davvero (stesso Registro Contratti Dati gia'
disegnato, ma scoped esplicitamente al caso senza sistema esterno).

### 2. Confine di servizio: un solo servizio, non frammentazione fisica

"Microservizi" qui significa *confini di ownership dei dati*, non necessariamente
*N servizi fisicamente separati con DB separati*. GEMODO resta un solo servizio
backend con un solo schema Postgres, organizzato in moduli interni con
responsabilita' chiare (catalogo/consultazione, builder/scrittura, generazione
documento). Non c'e' un vincolo organizzativo noto che imponga la frammentazione
fisica; se emergesse (team diversi, esigenze di scala diverse) si puo' estrarre un
modulo in un servizio separato in un secondo momento — la disciplina di ownership
dei dati descritta sopra resta valida ed e' anzi il prerequisito per farlo senza
dolore in futuro.

### 3. Come il builder ottiene "cosa e' disponibile": Ports & Adapters

Il builder, quando un gestore crea/modifica un modello, deve poter chiedere "quali
categorie/tipologie/campi sono disponibili per questo tipo documento" senza sapere
se la risposta viene da una chiamata HTTP esterna o dal catalogo interno di GEMODO.
Si adotta il pattern **Ports & Adapters (architettura esagonale)**:

- una **porta** (interfaccia astratta) definisce il contratto: dato un tipo
  documento, restituisci categorie/tipologie/campi disponibili;
- un **adapter HTTP** implementa quella porta chiamando l'endpoint di discovery
  registrato per un tipo documento integrato (con cache a TTL breve, mai come fonte
  di verita' permanente — vedi §6);
- un **adapter locale** implementa la stessa porta leggendo dal Registro Contratti
  Dati interno di GEMODO per un tipo documento self-service.

Il resto del sistema (builder, generazione del contratto atteso, validazione) lavora
sempre contro la porta astratta, mai contro l'uno o l'altro adapter direttamente.

### 4. Flusso di onboarding unificato

Stesso flusso per GEBAN e per ogni futuro contesto (integrato o self-service),
eseguito da un'interfaccia di amministrazione GEMODO (non piu' un file YAML — vedi
§5):

1. **Definizione struttura documento**: un operatore GEMODO (o, in futuro, un
   utente autorizzato del contesto stesso) definisce, tramite l'interfaccia admin,
   il tipo documento, le sue categorie/tipologie e i campi dati necessari
   (codice, etichetta, tipo, obbligatorieta'). Per GEBAN questo passo lo esegue
   oggi il team GEMODO, sulla base delle specifiche fornite da GEBAN — stesso
   meccanismo, stesso strumento, nessun trattamento speciale.
2. **Generazione del contratto atteso**: questa definizione produce/documenta lo
   schema (JSON Schema / OpenAPI) che un endpoint di discovery esterno deve
   rispettare per integrarsi — invece di far indovinare al team esterno cosa
   GEMODO si aspetta, GEMODO pubblica la specifica esatta da implementare.
3. **Registrazione dell'endpoint**: quando il team esterno ha implementato il
   proprio endpoint (o, nel caso self-service, questo passo non esiste: l'adapter
   locale e' gia' pronto), l'URL viene registrato nella stessa interfaccia admin.
4. **Contesto "connesso"**: una volta registrato un endpoint funzionante (o
   confermato l'adapter locale), il contesto risulta "connesso"/integrato nella
   dashboard admin, e diventa possibile creare modelli per quel tipo documento. Un
   contesto definito ma non ancora connesso non e' utilizzabile operativamente.

Resta fermo un principio gia' confermato: **nessun auto-provisioning**. Un token con
un contesto sconosciuto a GEMODO viene sempre rifiutato; l'onboarding e' sempre
un'azione amministrativa esplicita (passi 1-4 sopra), mai qualcosa che scatta
automaticamente perche' e' arrivato un JWT con un claim nuovo.

### 5. Interfaccia di amministrazione, non file di configurazione

Confermato per questo incremento (non rimandato a un secondo tempo, per scelta
esplicita del product owner): i passi 1 e 3 del flusso sopra sono eseguiti tramite
un'**interfaccia admin**, non tramite un file YAML modificato a mano + deploy. I dati
(Ufficio, tipo documento, categorie, tipologie, endpoint registrati) vivono in
tabelle Postgres scritte direttamente dall'interfaccia — coerente con (e reso
possibile da) la migrazione da YAML-in-memoria a tabelle Postgres gia' disegnata in
`DEC-001-CONFIG-PROFILO-GEBAN`, qui estesa: l'interfaccia diventa il punto di
scrittura fin da subito, non solo un consumer futuro delle stesse tabelle.

### 6. Versioning dei riferimenti esterni

Ogni modello registra la data di riferimento/validita' della categorizzazione
esterna al momento della sua creazione, mostrata insieme al modello nelle liste.
Se il sistema esterno restituisce dati non attesi (campi extra non dichiarati nello
schema generato al passo 2), GEMODO tratta questo come errore funzionale, non come
dato da accettare silenziosamente — coerente con la validazione stretta gia' in uso
per il payload GEBAN (campi extra = errore bloccante). Il comportamento esatto
(come si visualizza la data di riferimento, quali soglie generano errore vs
avviso) resta da affinare: trattato come decisione `ASSUNTA_PROVVISORIA`, non
completamente chiuso.

### 7. Fallback a sistema esterno irraggiungibile

In fase di **creazione/modifica modello** (serve il menu live delle opzioni
disponibili), un endpoint esterno irraggiungibile blocca l'operazione con un errore
esplicito. In fase di **consultazione** (il modello e' gia' pubblicato, i
riferimenti sono gia' congelati nella struttura del modello), l'indisponibilita'
del sistema esterno non deve bloccare la consultazione dei modelli gia' pubblicati
— i dati necessari sono gia' negli snapshot locali.

## Conseguenze

**Positive**:

- Nessuna copia non autorevole della categorizzazione GEBAN in GEMODO; la
  responsabilita' di tenerla aggiornata resta dove appartiene.
- Lo stesso flusso di onboarding serve sia GEBAN sia qualunque futuro contesto,
  integrato o self-service — non due percorsi da mantenere separatamente.
- Il pattern Ports & Adapters rende il builder indifferente alla sorgente dei dati,
  facilitando l'aggiunta di nuovi tipi di adapter in futuro (es. un contesto che
  passa da self-service a integrato quando si dota di un proprio backend).

**Costi/rischi**:

- Supera lavoro gia' fatto e confermato in questa stessa sessione: la migration
  `0007` (nomenclatura GEBAN seedata localmente) e le decisioni
  `DEC-001-CATEGORIE-INIZIALI`/`DEC-001-REGISTRO-CONTRATTI-DATI` presumevano GEMODO
  come sorgente di record. Le tabelle create da quella migration non vengono
  buttate via: diventano una **cache locale** (TTL breve) sincronizzata
  dall'endpoint GEBAN, non piu' un seed autoritativo — stesso schema possibile,
  semantica diversa, da riflettere in `data-model.md`.
- Richiede la costruzione di un'interfaccia admin reale (frontend + API di
  scrittura + autorizzazione amministrativa) prima di andare in produzione con
  GEBAN, invece del percorso piu' rapido file+deploy considerato in precedenza.
  Scelta esplicita del product owner, consapevole del costo aggiuntivo.
- GEBAN deve implementare un endpoint di discovery reale (non solo fornire dati
  via documentazione statica come oggi) prima che il flusso end-to-end funzioni:
  dipendenza dal team GEBAN, da coordinare.

## Esempio Concreto: Contratto Di Discovery Per GEBAN

[`0001-esempio-discovery-geban.json`](./0001-esempio-discovery-geban.json) e' un
esempio della risposta attesa dall'endpoint di discovery che GEBAN dovra' esporre
per `BANDO_CONCORSO` (passo 2 del flusso in §4), verificato il 2026-09-15 contro gli
endpoint di test reali (`https://geban-service.test.si.cnr.it/api/v1/profili`,
`/api/v1/tipoSols`) per i codici tipologia/profilo. Da consegnare al team GEBAN come
riferimento per l'implementazione. Contiene marcatori `_confermato: true/false` per
distinguere cosa e' verificato sui dati reali da cosa e' ancora una proposta di
GEMODO:

- **Confermato**: i 10 codici tipologia e i 7 codici profilo (nomenclatura gia'
  allineata dalla migration `0007`).
- **Da confermare con GEBAN**: le combinazioni tipologia-profilo esatte (oggi solo
  proposte, riprese da `infra/local/postgres/seed-demo-catalog.yaml`; 5 tipologie
  su 10 non hanno ancora nessuna combinazione proposta); e se il campo `livello`
  (trovato come `livelliPossibili`/`livelloBase` su `/api/v1/profili`, non presente
  nel contratto dati odierno) debba entrare nel contratto come campo dipendente dal
  profilo scelto, invece che generico come gli altri.

## Prossimi Passi

Non ancora eseguiti in questa sessione (deliberatamente, per confermare prima
questo ADR nel suo complesso):

- Aggiornare `data-model.md`/`plan.md`/`tasks.md` di `001` e `002` per riflettere
  il nuovo modello (adapter HTTP/locale, interfaccia admin, tabelle come cache per
  GEBAN).
- Progettare lo schema esatto del "contratto atteso" generato al passo 2 del
  flusso di onboarding (§4).
- Coordinarsi con il team GEBAN sull'implementazione del loro endpoint di
  discovery.
