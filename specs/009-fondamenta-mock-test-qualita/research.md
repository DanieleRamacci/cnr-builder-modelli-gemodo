# Research - Fondamenta Mock Test E Qualita

## Decision: ambiente locale containerizzato e ripetibile

**Rationale**: la feature richiede backend, frontend, database, Keycloak e documentale
mock. Un ambiente locale orchestrato riduce differenze tra sviluppatori e permette
verifiche ripetibili su contratti, seed e scenari end-to-end.

**Alternatives considered**:

- Servizi installati manualmente: scartato perche' introduce troppa conoscenza implicita.
- Solo test in memoria: scartato perche' non copre migrations, Keycloak, PostgreSQL e
  documentale mock.

## Decision: Keycloak CNR di test reale invece di solo container locale

**Rationale**: il team GEMODO ha ottenuto un'utenza amministratore sul realm Keycloak CNR di
test (`sso.test.si.cnr.it`, realm `cnr`, dominio applicativo `*.test.si.cnr.it`). Sviluppo e
test si configurano direttamente contro questo Keycloak reale tramite variabili d'ambiente
(issuer URL, client id/secret, audience), invece di dipendere solo da un Keycloak
containerizzato locale. Il passaggio in produzione richiede solo la stessa configurazione
richiesta al referente infrastruttura Keycloak CNR e lo swap delle variabili d'ambiente, senza
cambi di modello applicativo.

**Alternatives considered**:

- Solo Keycloak containerizzato locale: scartato come unica opzione perche' introduce un
  secondo modello di configurazione da mantenere allineato a quello reale, senza reale
  beneficio ora che l'accesso al Keycloak di test e' disponibile self-service.
- Keycloak containerizzato resta comunque un'opzione di fallback per sviluppo offline o CI
  senza accesso di rete al Keycloak CNR, ma non e' piu' il percorso primario.

## Decision: stack della proposta come baseline di planning

**Rationale**: la proposta indica FastAPI, Angular, PostgreSQL, Keycloak locale,
documentale locale/mock e OpenAPI/Swagger. La `009` non deve decidere ogni dettaglio di
implementazione, ma puo' usare questa baseline per rendere coerente il piano e generare
task concreti.

**Alternatives considered**:

- Lasciare ogni voce come non chiarita: scartato perche' bloccherebbe il piano
  pur avendo una baseline esplicita nella proposta.
- Cambiare stack durante il planning: scartato perche' richiederebbe decisione
  architetturale fuori perimetro della `009`.

## Decision: mock GEBAN contract-first

**Rationale**: il mock deve esercitare catalogo, campi/schema, validazione, generazione,
stato e download usando gli stessi contratti pubblici previsti per GEBAN. Questo evita
mock troppo permissivi o agganciati a dettagli interni GEMODO.

**Alternatives considered**:

- Mock basato su funzioni interne backend: scartato perche' bypassa i contratti GEBAN.
- Mock solo statico: scartato perche' non verifica idempotenza, stati, autorizzazioni e
  audit.

## Decision: seed demo marcati e privi di dati reali

**Rationale**: i seed devono consentire scenari ripetibili senza rischi privacy o
confusione con dati amministrativi reali. Ogni dato demo deve essere riconoscibile e
resettable.

**Alternatives considered**:

- Copiare esempi reali da GEBAN: scartato per rischio dati sensibili e dipendenza dal
  sistema reale.
- Seed minimi solo tecnici: scartato perche' non coprono i casi funzionali richiesti da
  mock e contratti.

## Decision: registro decisioni aperte come gate di planning/tasks

**Rationale**: la proposta contiene decisioni ancora da confermare. Il piano deve
consentire avanzamento con assunzioni esplicite, ma impedire che parti impattate entrino
in implementazione senza chiusura, sospensione o rischio tracciato.

**Alternatives considered**:

- Bloccare tutto fino a chiusura di ogni decisione: scartato perche' rallenta anche aree
  non impattate.
- Procedere senza registro: scartato perche' trasformerebbe assunzioni in scelte
  implicite.

## Decision: matrice di copertura tra spec, scenari, contratti e task futuri

**Rationale**: la `009` e' trasversale. Una matrice rende verificabile che ogni scenario
end-to-end copra requisiti e spec owner, e diventera' input per `/speckit-tasks` e
`/speckit-analyze`.

**Alternatives considered**:

- Affidarsi solo ai test automatici: scartato perche' i test non spiegano sempre quale
  requisito o decisione coprono.
- Annotazioni libere nei README: scartato perche' difficili da validare e mantenere.

## Decision: Keycloak per identita' e GEMODO per autorizzazioni fini

**Rationale**: Keycloak deve restare il sistema di identita', autenticazione, client
tecnici, audience e ruoli/claim generali. Le abilitazioni fini su sistemi richiedenti,
profili di integrazione, tipi documento, categorie, tipologie, modelli/versioni, contratti
dati e operazioni appartengono invece a GEMODO, perche' sono dominio documentale e devono
seguire versionamento, pubblicazione e audit del servizio.

**Alternatives considered**:

- Mettere in Keycloak la lista di modelli, categorie e contratti: scartato perche' rende
  fragile il versionamento e sposta fuori da GEMODO decisioni di dominio documentale.
- Gestire utenti, password o segreti in GEMODO: scartato perche' duplica il sistema di
  identita' e viola il confine con SSO/Keycloak.
- Usare solo ruoli generici senza profili applicativi GEMODO: scartato perche' non basta a
  distinguere GEBAN, GRADUATORIE, CHECKIN e futuri chiamanti sui rispettivi modelli.

## Decision: modello documentale controllato per builder visuale e PDF

**Rationale**: il builder deve offrire un'esperienza visuale simile a un word processor
limitato, con intestazioni, loghi, titoli, paragrafi, tabelle, colonne, firme, footer,
interruzioni pagina, stili ammessi e placeholder. Per mantenere validazione, sicurezza e
riproducibilita', la sorgente salvata deve essere una struttura documentale controllata e
versionata. L'utente non scrive HTML/CSS libero; eventuali formati tecnici intermedi sono
prodotti dal renderer.

**Alternatives considered**:

- HTML/CSS libero salvato dall'utente: scartato per rischi di sicurezza, layout non
  validabile e bassa riproducibilita'.
- File office binario come sorgente primaria: scartato perche' rende difficile validare
  placeholder, versionare semanticamente e controllare le regole di pubblicazione.
- Solo sezioni testuali ordinate: scartato perche' non copre logo, firme posizionate,
  tabelle, colonne e layout amministrativi reali.

## Decision: documentazione API contract-first con OpenAPI, Swagger e ReDoc

**Rationale**: GEBAN e gli altri sistemi chiamanti devono poter leggere, testare e
integrare le API senza dipendere dal codice sorgente o da conoscenza implicita del team.
La documentazione interattiva riduce ambiguita' su request, response, JWT, audience,
autorizzazioni, stati e codici errore. Per questo ogni API pubblica o di integrazione deve
avere OpenAPI versionato prima dello sviluppo runtime dell'endpoint; la stessa sorgente
deve alimentare Swagger UI, ReDoc o documentazione equivalente in locale/test.

**Alternatives considered**:

- Documentazione solo nel README: scartata perche' non valida automaticamente schemi,
  esempi e contratti.
- Swagger generato solo dal codice runtime: scartato come unica fonte perche' invertirebbe
  il principio contract-first.
- Esempi informali non versionati: scartati perche' rischiano drift rispetto agli endpoint.

## Decision: readiness open source e riuso PA

**Rationale**: Il progetto e' destinato a essere open source e riusabile da altre
pubbliche amministrazioni. La documentazione deve permettere a un soggetto esterno di
capire scelte, vincoli, API e modalita' operative senza accedere a documenti privati o
chiedere conoscenza orale al team. Il repository deve quindi avere documentazione testuale,
navigabile e pubblicabile per setup da zero, sviluppo locale, produzione, architettura,
configurazione, sicurezza, contributi, segnalazione vulnerabilita', test, release e
licenza. La licenza definitiva resta da confermare con il project owner prima della
pubblicazione pubblica.

**Alternatives considered**:

- Rinviare la documentazione open source a fine progetto: scartato perche' renderebbe
  difficile verificare da subito pubblicabilita' di esempi, assenza di segreti e chiarezza
  delle decisioni.
- Pubblicare solo codice e Spec Kit: scartato perche' non basta per installazione,
  integrazione, sicurezza e manutenzione da parte di terzi.

## Decision: sicurezza realistica basata su decisioni ormai risolte

**Rationale**: la spec 006 ha risolto sia `SEC-006-001` (token tecnico `geban-backend` +
contesto utente nel payload, non token delegato) sia `SEC-006-002` (nessuna separazione
gestore/revisore/approvatore nella prima release, pubblicazione del gestore vale come
approvazione), entrambe il 2026-07-29. La `009` deve preparare gli scenari autorizzativi
contro il Keycloak CNR di test reale usando direttamente il modello risolto, senza piu'
assunzioni provvisorie da marcare come bloccanti.

**Alternatives considered**:

- Rimandare ogni scenario sicurezza: scartato perche' audit e autorizzazioni sono
  requisiti costituzionali.
- Stabilire qui la soluzione definitiva Keycloak/GEBAN: scartato perche' owner della
  decisione resta la spec 006.
