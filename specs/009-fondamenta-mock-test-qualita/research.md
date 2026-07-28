# Research - Fondamenta Mock Test E Qualita

## Decision: ambiente locale containerizzato e ripetibile

**Rationale**: la feature richiede backend, frontend, database, Keycloak e documentale
mock. Un ambiente locale orchestrato riduce differenze tra sviluppatori e permette
verifiche ripetibili su contratti, seed e scenari end-to-end.

**Alternatives considered**:

- Servizi installati manualmente: scartato perche' introduce troppa conoscenza implicita.
- Solo test in memoria: scartato perche' non copre migrations, Keycloak, PostgreSQL e
  documentale mock.

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

## Decision: sicurezza locale realistica ma non bloccata dalle decisioni differite

**Rationale**: la spec 006 contiene decisioni provvisorie su token delegato e separazione
ruoli. La `009` deve preparare Keycloak locale e scenari autorizzativi usando le assunzioni
documentate, marcando i punti da riaprire prima dell'implementazione delle parti impattate.

**Alternatives considered**:

- Rimandare ogni scenario sicurezza: scartato perche' audit e autorizzazioni sono
  requisiti costituzionali.
- Stabilire qui la soluzione definitiva Keycloak/GEBAN: scartato perche' owner della
  decisione e' la spec 006 con il team GEBAN/Keycloak.
