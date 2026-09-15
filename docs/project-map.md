# Project Map - GEBAN Builder Modelli GEMODO

Questo documento collega la proposta sorgente alle specifiche Spec Kit.
La regola di lavoro e': nessuna sezione della proposta deve restare senza owner.

## Fonti

- Documento sorgente: `PROPOSTA-servizio-gestione-modelli-bando.md`
- Costituzione: `.specify/memory/constitution.md`

## Spec Inventory

| Spec | Area | Stato | Fonte proposta | Note |
|---|---|---|---|---|
| `001-catalogo-contratto-geban` | Catalogo modelli, contratto dati, validazione payload verso GEBAN | Primo incremento implementato (2026-07-31), 73/73 task completati; nomenclatura categorie/tipologie riallineata a GEBAN (2026-09-14, migration `0007`); secondo incremento (FR-025..FR-031: perimetro per-profilo, Ufficio proprietario vs Applicazione consumatrice, registro contratti dati, generalizzazione `TipologiaDocumento`) con decisioni `CONFERMATA` (2026-09-14), gate readiness verde per PLAN/TASKS; design puntuale in `plan.md` ancora da scrivere, nessuna implementazione; suite `pytest -m "not e2e"` verde | §3, §4, §5, §9.1-§9.5 | Prima spec operativa; espone catalogo, contratto campi, validazione payload e protezione JWT Keycloak minima. UUID resta chiave interna DB, mentre `public_id` intero stabile e' esposto a GEBAN come `modello_versione_id`. L'allow-list per-profilo (`categorie_ammessi`/`tipologie_ammessi`) e i `contratti_dati_ammessi` non sono ancora applicati dalle API reali (solo dal fixture di test mock-GEBAN) — bloccante prima di andare in produzione con generazione reale per GEBAN; direzione confermata, implementazione da pianificare in `plan.md` |
| `002-builder-modelli` | Builder backend per tipi, categorie, modelli, versioni e pubblicazione | Spec/plan/tasks aggiornati (2026-07-31), 0/64 task implementati; readiness gate `TASKS` verde | §2, §4, §8.2-§8.6, §10, §16.3 | Stati definitivi confermati: `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`; `GEMODO_MODELLI_GESTORE` puo' approvare/pubblicare nel primo rilascio. La `002` espone API builder protette da Keycloak e riusa il dominio catalogo condiviso della `001`, senza duplicare tabelle |
| `003-sezioni-placeholder-versionamento` | Sezioni proprie della versione modello, placeholder, JSON schema e contenuti strutturati | Attiva; spec/plan/tasks aggiornati (2026-07-31), 0/69 task implementati; readiness gate `TASKS` verde | §5.5, §6, §8.7-§8.9, §16.3 | Formato visuale confermato: editor controllato, non HTML libero; modello `GEMODO_DOCUMENT_V1` con blocchi ammessi, posizionamenti controllati, asset versionati, stili consentiti e placeholder validati. La `003` estende API builder protette da Keycloak e alimenta il renderer della `004` |
| `004-generazione-documenti-pdf` | Generazione documenti, rendering, PDF bozza/ufficiale | Draft di copertura | §9.6, §13, §16.5 | Si ferma alla generazione e metadati documento; bando multiplo, ribando e bando inglese integrale chiariti in `009` il 2026-07-28; resta da chiarire confine con stampa/pubblicazione SOL |
| `005-storage-idempotenza-consultazione` | Storage documentale, idempotenza, download e stato generazione | Draft di copertura | §9.7-§9.8, §13, §14, §11.2 | Da confermare storage definitivo; ribando chiarito in `009` come nuovo bando collegato al precedente; resta da chiarire nuova pubblicazione/riferimento documentale verso sistemi esterni |
| `006-sicurezza-autorizzazioni-audit` | Keycloak, ruoli, autorizzazioni, audit sicurezza | Implementazione ACE/context roles completata localmente (2026-09-14), tasks 23/23 completati; suite `pytest -m "not e2e"` verde; quality review esterno bloccato da login reviewer | §12, §8.11, §12.9 | `keycloak-jwt.md`; decisioni confermate/estese: GEBAN puo' chiamare GEMODO con token ACE utente dal realm `cnr`, client censito (es. `geri-angular-public`), audience obbligatoria `gemodo-backend` e ruoli in `contexts.geban.roles`; GEMODO normalizza ruoli diretti `resource_access.gemodo-backend.roles` e ruoli ACE/GEBAN tramite mapping configurato in `infra/local/integration-profiles.local.yaml`. `geban-backend` resta doppio tecnico per test/CI; solo `ROLE_MANAGER#geban` deriva `GEMODO_MODELLI_GESTORE`, mentre `ROLE_GESTORE#geban`, `ROLE_MANAGER#geban`, `ROLE_COORDINATOR#geban` e `ROLE_USER#geban` derivano permessi di generazione/consultazione documenti |
| `007-frontend-builder-consultazione` | Frontend builder e consultazione generazioni | Draft integrata | §11, §16.6 | Dipende da API builder e generazioni |
| `008-ai-mcp-readiness` | Predisposizione AI, MCP, documentazione AI-ready | Draft integrata | §15 | Non prerequisito del primo rilascio |
| `009-fondamenta-mock-test-qualita` | Fondamenta tecniche, mock, test, qualita', documentazione API e readiness riuso PA | Implementata (Fase 1-5, T001-T058); Polish in corso | §16.1, §16.2, §16.7, §17 | Attiva; ambiente locale, mock GEBAN, registro decisioni (28 voci) e matrice di copertura reali e testati (109 test pytest); raccoglie setup, criteri cross-cutting, ownership decisioni, OpenAPI/Swagger/ReDoc, portale documentazione e vincoli open source/PA |
| `010-configurazione-cataloghi-integrazioni` | Interfaccia di amministrazione per definire tipi documento/tipologie/profili/campi, generare il contratto di discovery per un sistema esterno e registrarne l'endpoint | Spec/plan/research/data-model/tasks scritti (2026-09-15), 0/52 task implementati; readiness gate `PLAN` verde, `TASKS` bloccato da `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI` (esplicitato in `tasks.md`, non silenziato) | n/d (nata da `docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md`, non dalla `PROPOSTA` originale) | Nuova spec nata dal cambio di paradigma su ownership dei dati esterni (referenziare non copiare, `DEC-001-OWNERSHIP-DATI-ESTERNI`); sostituisce, per questo incremento, il percorso file+deploy previsto da `DEC-001-CONFIG-PROFILO-GEBAN`. Primo caso d'uso reale: GEBAN/`BANDO_CONCORSO`, esempio in `docs/adr/0001-esempio-discovery-geban.json`. Eroga anche il sostituto funzionale delle tre API di classificazione GEBAN-facing ritirate dalla `001` (`DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`, 2026-09-15): non un endpoint runtime nostro, ma la generazione del contratto/documentazione che dice agli sviluppatori esterni come strutturare il proprio endpoint di discovery |

## Coverage Per Sezione Proposta

| Sezione proposta | Owner principale | Copertura | Note |
|---|---|---|---|
| §0 Sintesi | Constitution, 001-009 | Coperta | Principi e ambito complessivo |
| §1 Principio Architetturale | Constitution, 001, 002 | Coperta | Confini GEBAN/servizio/documentale |
| §2 Flusso Di Progettazione Del Modello | 002, 003 | Coperta | Workflow builder e pubblicazione |
| §3 Flusso GEBAN - Servizio Modelli | 001, 004, 005 | Coperta | Catalogo -> campi -> generazione -> riferimento |
| §4 Categorizzazione Interna | 001, 002 | Coperta | Tipo, categoria, tipologia, modello |
| §5 Campi Richiesti E Contratto Dati | 001, 003 | Coperta | Contratto dati e JSON schema |
| §6 Placeholder E Sezioni | 003, 004 | Coperta | Sezioni e risoluzione placeholder |
| §7 Proprietario Dei Dati | Constitution, 001, 004, 006 | Coperta | Ownership dati e snapshot |
| §8 Schema Dati Proposto | 002, 003, 004, 005, 006, 009 | Coperta | Entita' distribuite per responsabilita' |
| §9 API Esposte Verso GEBAN | 001, 004, 005 | Coperta | Catalogo, validazione, generazione, download |
| §10 API Interne Del Builder Modelli | 002, 003 | Coperta | API amministrative builder |
| §11 Frontend Del Servizio | 007 | Coperta | Builder e consultazione generazioni |
| §12 Sicurezza, Autenticazione E Autorizzazione | 006 | Coperta | Spec dedicata |
| §13 Storage PDF | 004, 005 | Coperta | Generazione + conservazione/riferimento |
| §14 Idempotenza | 005 | Coperta | Chiave, retry, conflict |
| §15 Predisposizione Per AI, Documentazione Assistita E MCP | 008, 006, 009 | Coperta | AI/MCP, sicurezza AI e documentazione pubblicabile |
| §16 Piano Di Sviluppo | 009 + tutte | Coperta | Usato come input per plan/tasks successivi; `009` governa anche navigazione documentale, API readiness e riuso PA |
| §17 Decisioni Da Confermare | 009 + spec collegate | Coperta | Decisioni distribuite come open decisions |

## Regola Di Blocco Delle Decisioni Aperte

Le decisioni aperte tracciate in `specs/009-fondamenta-mock-test-qualita/spec.md`
(sezione "Decision Ownership") e, quando popolato dalla User Story 3 della `009`, in
`docs/decision-register.yaml`, seguono una regola di blocco esplicita (FR-007, FR-018,
`quality-readiness-contract.yaml` sezione `open_decisions` e gate
`minimum_quality_gates.before_implementation`):

- ogni decisione aperta deve avere `owner_spec`, `impacted_specs`, `status` e
  `blocking_phase` (o `fase_bloccante`); non puo' restare senza owner o senza fase.
- una decisione in stato `APERTA` o `ASSUNTA_PROVVISORIA` con `fase_bloccante` diversa
  da `NESSUNA` **non puo'** entrare come assunzione silenziosa nei task implementativi
  della parte impattata: il piano/i task devono esplicitare l'assunzione provvisoria
  oppure rinviare (sospendere) le attivita' bloccate finche' la decisione non e'
  `CONFERMATA` o `SOSPESA` con rischio tracciato.
- quando una decisione passa a `CONFERMATA`, le spec elencate in `impacted_specs`
  devono essere aggiornate di conseguenza (non basta chiuderla nella spec che la
  possiede).
- `SEC-006-001` (token tecnico `geban-backend` verso `gemodo-backend`) e
  `SEC-006-002` (nessuna separazione revisore/approvatore nella prima release) sono
  gia' `CONFERMATA` (2026-07-29, spec `006`) e non bloccano piu' alcuna fase.

## Gate Trasversali Documentazione E Riuso

- Ogni API pubblica o di integrazione deve avere OpenAPI versionato prima
  dell'implementazione runtime.
- Swagger UI e ReDoc, o equivalenti, devono essere disponibili in locale/test dalla stessa
  sorgente OpenAPI.
- Ogni API deve avere esempi JSON pubblicabili di successo e di errore funzionale, senza
  token, secret, dati personali reali o URL ambientali sensibili.
- La documentazione navigabile deve permettere di raggiungere proposta, costituzione,
  feature attiva, stato spec, blocchi, decisioni, vincoli, contratti API e quickstart.
- Prima della pubblicazione open source/PA devono essere tracciati licenza, setup,
  sviluppo, produzione, architettura, configurazione, sicurezza, contributi, segnalazione
  vulnerabilita', test, release e changelog.

## Stato Plan/Tasks Delle Spec Operative (verificato 2026-07-31)

`001-catalogo-contratto-geban` ha `spec.md`, `plan.md`, OpenAPI, `data-model.md`,
`quickstart.md` e `tasks.md` aggiornati al 2026-07-31. L'implementazione runtime e'
completa per i 73 task: catalogo, contratto dati, validazione payload e protezione JWT
Keycloak minima sono disponibili nel backend.

`002-builder-modelli` ha `spec.md`, `plan.md`, `data-model.md`, OpenAPI e `tasks.md`
aggiornati al 2026-07-31. Il readiness gate per `TASKS` e' verde dopo la conferma di
`DEC-002-STATI-MODELLO`; la feature puo' partire da `T001`, ma il codice runtime deve
riusare le fondamenta condivise della `001` quando implementate.

`003-sezioni-placeholder-versionamento` ha `spec.md`, `plan.md`, `data-model.md`, OpenAPI
e `tasks.md` aggiornati al 2026-07-31. Il readiness gate per `TASKS` e' verde dopo la
conferma di `DEC-003-FORMATO-VISUALE-MODELLO`; la feature puo' partire da `T001` dopo le
fondamenta runtime di `001` e `002`.

Stato implementazione task: `001` completata (73/73), `002` non implementata (0/64),
`003` non implementata (0/69). Prima di avviare l'implementazione applicativa oltre la
`003`:

1. implementare la `002` seguendo `specs/002-builder-modelli/tasks.md`, riusando dominio
   catalogo e sicurezza comune;
2. implementare la `003` seguendo `specs/003-sezioni-placeholder-versionamento/tasks.md`,
   riusando ciclo vita versione, sicurezza builder e contratto campi;
3. verificare con `backend/app/quality/readiness_gate.py` che nessuna decisione critica
   blocchi ancora la fase `TASKS` per la spec target prima di generare nuovi task
   implementativi (FR-018).

Questo evita di implementare codice applicativo contro un contratto dati o un modello
di autorizzazione gia' superato dalle decisioni successive.

## Ordine Suggerito Di Approfondimento

1. `001-catalogo-contratto-geban`
2. `002-builder-modelli`
3. `003-sezioni-placeholder-versionamento`
4. `006-sicurezza-autorizzazioni-audit`
5. `004-generazione-documenti-pdf`
6. `005-storage-idempotenza-consultazione`
7. `007-frontend-builder-consultazione`
8. `009-fondamenta-mock-test-qualita`
9. `008-ai-mcp-readiness`

L'ordine mette prima il flusso GEBAN e il dominio configurabile, poi sicurezza e
generazione, quindi frontend, test e predisposizione AI.
