# Project Map - GEBAN Builder Modelli GEMODO

Questo documento collega la proposta sorgente alle specifiche Spec Kit.
La regola di lavoro e': nessuna sezione della proposta deve restare senza owner.

## Fonti

- Documento sorgente: `PROPOSTA-servizio-gestione-modelli-bando.md`
- Costituzione: `.specify/memory/constitution.md`

## Spec Inventory

Decisione MVP corrente:

T079/T080 implementati: migration 0012/0013 per registro software, audit,
endpoint software e namespace scoped; archivio precedente inerte, senza ORM.
Associazione legacy esplicita/auditata, codici ambigui rifiutati. AdapterHTTP
valida e mette in cache RAM tutta la mappa multi-tipo per sorgente/revisione.
Nuova API onboarding e resolver registrato restano T081-T084, non operativi.
Test solo su PostgreSQL temporaneo e server HTTP locale.

Aggiornamento 2026-09-17 (T081/T082/T083): API admin
`/api/v1/configurazione/integrazioni` (CRUD + verifica sincrona) operativa;
il resolver del builder legge ora solo integrazioni `CONNESSO` dal registro
(`TipoDocumento.integrazione_id`), `GEMODO_DISCOVERY_ENDPOINTS` rimosso senza
fallback. Letture manager `/api/v1/builder/integrazioni*` operative
(autorizzazione per singolo contesto, verificata prima di ogni chiamata HTTP).
Contratto `integrazioni-api.openapi.yaml` pubblicato (Swagger/ReDoc). Resta
T084 (prove avversarie SSRF/rebinding/concorrenza). Suite non-e2e: 256
passati, 12 esclusi.

Aggiornamento 2026-09-17 (bis) - MVP end-to-end reale: implementato lo scope
FR-019/020 di `004`/`005` (`specs/004-generazione-documenti-pdf/plan.md`,
`specs/005-storage-idempotenza-consultazione/plan.md`), non pianificato in
precedenza. `POST /documenti/genera` non e' piu' simulato: produce un PDF di
test reale (`backend/app/generazione/`, `fpdf2`) e lo persiste con
riferimento/stato/download/idempotenza reali (`backend/app/storage/`,
filesystem locale, migration `0014`). `POST /documenti/genera` storico di
`001` ritirato (`geban-catalog-api.openapi.yaml` 0.6.0). Dimostrato end-to-end
in `test_flusso_completo_creazione_pubblicazione_e_generazione_documento`:
integrazione connessa (010) -> modello dalla foglia live (002) -> pubblicato
-> generazione reale (004) -> download reale (005). **Non chiuso**:
l'autorizzazione per-contesto su queste API di consumo (001 FR-034..038, 006
FR-014..017, gia' tracciata in T087) non e' ancora implementata - riusano i
ruoli globali esistenti, adatto a sviluppo/test non a uso operativo. Suite
non-e2e: 270 passati, 12 esclusi.

[ADR 0002](adr/0002-integrazioni-contesti-modelli-test.md) e
[flusso e owner](../specs/010-configurazione-cataloghi-integrazioni/mvp-integrazione-modello-pdf-test.md).
Integrazioni software create manualmente, contesto JWT e singolo endpoint
multi-tipo; manager naviga discovery autorizzato e crea modello di test,
PDF semplice non ufficiale senza editor visuale. Target ancora da sviluppare
nei task Phase 12 della 010 e nelle spec owner: la descrizione runtime sotto
non implica che registro software, frontend o PDF siano gia' disponibili.

Aggiornamento corrente 2026-09-17, prevalente sulle evidenze storiche della
tabella: feature attiva 010, FR-016/T061-T066 dismettono il catalogo esterno
locale. AdapterLocale e API di classificazione eliminati; migration 0009
rimuove cinque tabelle preservando modelli GEMODO, versioni, contratti e audit.
Backend builder collegato a discovery HTTP con URL esplicita per tipo
(`GEMODO_DISCOVERY_ENDPOINTS`), senza fallback locale. Onboarding US1-US4,
firme e runner restano aperti. Suite finale non-e2e: 206 passati, 12 esclusi.
Configurazione e backup: `specs/010-configurazione-cataloghi-integrazioni/incremento-discovery.md`.

Il frontend builder non e' ancora implementato. Decisione confermata
2026-09-17: Angular con [Design Angular Kit](https://github.com/italia/design-angular-kit),
da pianificare nella spec 007; Swagger/ReDoc e pagina di test sono strumenti
di documentazione API, non l'interfaccia del builder.

Ripresa backend amministrativo 010: migration 0010/0011 per esempi,
revisioni, schemi, endpoint e audit; API di definizione, generazione/export
e lettura dashboard con `GEMODO_ADMIN`, senza catalogo esterno persistente.
Swagger/ReDoc: `/docs/configurazione-cataloghi`, `/redoc/configurazione-cataloghi`.
Suite finale non-e2e: 221 passati, 12 e2e esclusi, nessuno saltato; 15 mirati.
Registrazione/verifica endpoint US3 e risoluzione live dei riferimenti attributo
restano aperte. Review esterna e hash/runner rinviati dall'utente; quality gate
non superato per questi incrementi. Dettagli: `specs/010-configurazione-cataloghi-integrazioni/definizione-export.md`.

| Spec | Area | Stato | Fonte proposta | Note |
|---|---|---|---|---|
| `001-catalogo-contratto-geban` | Catalogo modelli, contratto dati, validazione payload verso GEBAN | Primo incremento implementato (2026-07-31), 73/73 task completati; nomenclatura categorie/tipologie riallineata a GEBAN (2026-09-14, migration `0007`); secondo incremento (FR-025..FR-031: perimetro per-profilo, proprieta' via `codice_contesto` vs Applicazione consumatrice — entita' Ufficio rimossa il 2026-09-15, `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO` — registro contratti dati, generalizzazione `TipologiaDocumento`) con decisioni `CONFERMATA`; migration `0008` (2026-09-16, reale su Postgres) aggiunge `tipo_documento.codice_contesto` e `registro_contratti_dati` (T085/T087 parziale — sistema_richiedente/profilo_integrazione restano su YAML, T088-T092 non fatti); gate readiness verde per PLAN, TASKS bloccato solo da `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI`; T080 (generalizzazione tipologia) ancora da fare; suite `pytest -m "not e2e"` verde (147 test) | §3, §4, §5, §9.1-§9.5 | Prima spec operativa; espone catalogo, contratto campi, validazione payload e protezione JWT Keycloak minima. UUID resta chiave interna DB, mentre `public_id` intero stabile e' esposto a GEBAN come `modello_versione_id`. L'allow-list per-profilo (`categorie_ammessi`/`tipologie_ammessi`) e i `contratti_dati_ammessi` non sono ancora applicati dalle API reali (solo dal fixture di test mock-GEBAN) — bloccante prima di andare in produzione con generazione reale per GEBAN; direzione confermata, implementazione da pianificare in `plan.md` |
| `002-builder-modelli` | Builder backend per tipi, categorie, modelli, versioni e pubblicazione | Spec/plan/tasks aggiornati (2026-07-31, riallineati 2026-09-15 al pivot ADR 0001/contesto); prima verticale reale implementata (2026-09-16, non segue 1:1 i 64 task granulari — vedi nota in `tasks.md`): creazione modello/versione, catena completa di pubblicazione con auto-archiviazione, autorizzazione scoped per contesto, tutto verificato su Postgres reale (7 test in `backend/tests/builder/`); mancano ancora modifica/derivazione di versioni pubblicate, route archivia/sospendi dedicate, vincolo DB anti-doppia-pubblicazione, contratto OpenAPI | §2, §4, §8.2-§8.6, §10, §16.3 | Stati definitivi confermati: `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO`, `SOSPESO`; `GEMODO_MODELLI_GESTORE` puo' approvare/pubblicare nel primo rilascio. La `002` espone API builder protette da Keycloak (autorizzazione scoped per `codice_contesto`, non piu' Ufficio) e riusa il dominio catalogo condiviso della `001`, senza duplicare tabelle. Dopo pubblicazione, `/documenti/valida` e `/documenti/genera` della `001` funzionano contro i nuovi modelli senza modifiche — provato end-to-end |
| `003-sezioni-placeholder-versionamento` | Sezioni proprie della versione modello, placeholder, JSON schema e contenuti strutturati | Pianificata; spec/plan/tasks aggiornati (2026-07-31), 0/69 task implementati; readiness gate `TASKS` verde | §5.5, §6, §8.7-§8.9, §16.3 | Formato visuale confermato: editor controllato, non HTML libero; modello `GEMODO_DOCUMENT_V1` con blocchi ammessi, posizionamenti controllati, asset versionati, stili consentiti e placeholder validati. La `003` estende API builder protette da Keycloak e alimenta il renderer della `004` |
| `004-generazione-documenti-pdf` | Generazione documenti, rendering, PDF bozza/ufficiale | Draft di copertura | §9.6, §13, §16.5 | Si ferma alla generazione e metadati documento; bando multiplo, ribando e bando inglese integrale chiariti in `009` il 2026-07-28; resta da chiarire confine con stampa/pubblicazione SOL |
| `005-storage-idempotenza-consultazione` | Storage documentale, idempotenza, download e stato generazione | Draft di copertura | §9.7-§9.8, §13, §14, §11.2 | Da confermare storage definitivo; ribando chiarito in `009` come nuovo bando collegato al precedente; resta da chiarire nuova pubblicazione/riferimento documentale verso sistemi esterni |
| `006-sicurezza-autorizzazioni-audit` | Keycloak, ruoli, autorizzazioni, audit sicurezza | Implementazione ACE/context roles completata localmente (2026-09-14), tasks 23/23 completati; suite `pytest -m "not e2e"` verde; quality review esterno bloccato da login reviewer | §12, §8.11, §12.9 | `keycloak-jwt.md`; decisioni confermate/estese: GEBAN puo' chiamare GEMODO con token ACE utente dal realm `cnr`, client censito (es. `geri-angular-public`), audience obbligatoria `gemodo-backend` e ruoli in `contexts.geban.roles`; GEMODO normalizza ruoli diretti `resource_access.gemodo-backend.roles` e ruoli ACE/GEBAN tramite mapping configurato in `infra/local/integration-profiles.local.yaml`. `geban-backend` resta doppio tecnico per test/CI; solo `ROLE_MANAGER#geban` deriva `GEMODO_MODELLI_GESTORE`, mentre `ROLE_GESTORE#geban`, `ROLE_MANAGER#geban`, `ROLE_COORDINATOR#geban` e `ROLE_USER#geban` derivano permessi di generazione/consultazione documenti |
| `007-frontend-builder-consultazione` | Frontend builder e consultazione generazioni | Draft integrata | §11, §16.6 | Dipende da API builder e generazioni |
| `008-ai-mcp-readiness` | Predisposizione AI, MCP, documentazione AI-ready | Draft integrata | §15 | Non prerequisito del primo rilascio |
| `009-fondamenta-mock-test-qualita` | Fondamenta tecniche, mock, test, qualita', documentazione API e readiness riuso PA | Implementata (Fase 1-5, T001-T058); Polish in corso | §16.1, §16.2, §16.7, §17 | Ambiente locale, mock GEBAN, registro decisioni (28 voci) e matrice di copertura reali e testati (109 test pytest); raccoglie setup, criteri cross-cutting, ownership decisioni, OpenAPI/Swagger/ReDoc, portale documentazione e vincoli open source/PA |
| `010-configurazione-cataloghi-integrazioni` | Interfaccia di amministrazione per definire tipi documento/tipologie/profili/campi, generare il contratto di discovery per un sistema esterno e registrarne l'endpoint | **Feature attiva**; spec/plan/research/data-model/tasks scritti (2026-09-15); chiarimento 2026-09-16: il contratto di discovery vincola la forma comune, non i valori reali; T003/T004 soddisfatti da migration `001`/`0008`; T009/T010 (`PortaDiscovery`+`AdapterLocale`, forma ridotta senza `attributi_profilo`) implementati e verificati su Postgres reale il 2026-09-16; resto (T001-T002/T005-T008/T011-T052) non fatto; readiness gate `PLAN` verde, `TASKS` bloccato da `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI` (esplicitato in `tasks.md`, non silenziato) | n/d (nata da `docs/adr/0001-ownership-dati-esterni-e-onboarding-contesti.md`, non dalla `PROPOSTA` originale) | Nuova spec nata dal cambio di paradigma su ownership dei dati esterni (referenziare non copiare, `DEC-001-OWNERSHIP-DATI-ESTERNI`); sostituisce, per questo incremento, il percorso file+deploy previsto da `DEC-001-CONFIG-PROFILO-GEBAN`. Primo caso d'uso reale: GEBAN/`BANDO_CONCORSO`, esempio in `docs/adr/0001-esempio-discovery-geban.json`. Eroga anche il sostituto funzionale delle tre API di classificazione GEBAN-facing ritirate dalla `001` (`DEC-001-RITIRO-ENDPOINT-CLASSIFICAZIONE`, 2026-09-15): non un endpoint runtime nostro, ma la generazione del contratto/documentazione che dice agli sviluppatori esterni come strutturare la forma del proprio endpoint di discovery |

## Coverage Per Sezione Proposta

| Sezione proposta | Owner principale | Copertura | Note |
|---|---|---|---|
| §0 Sintesi | Constitution, 001-009 | Coperta | Principi e ambito complessivo |
| §1 Principio Architetturale | Constitution, 001, 002 | Coperta | Confini GEBAN/servizio/documentale |
| §2 Flusso Di Progettazione Del Modello | 002, 003 | Coperta | Workflow builder e pubblicazione |
| §3 Flusso GEBAN - Servizio Modelli | 001, 004, 005 | Coperta | Catalogo -> campi -> generazione -> riferimento |
| §4 Categorizzazione Interna | 001, 002, 010 | Coperta | Tipo, categoria, tipologia, modello; `010` governa l'onboarding/configurazione e la discovery dei dati esterni |
| §5 Campi Richiesti E Contratto Dati | 001, 003, 010 | Coperta | Contratto dati e JSON schema; `010` genera la documentazione di forma per l'endpoint di discovery |
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

## Stato Plan/Tasks Delle Spec Operative (verificato 2026-09-16)

La feature attiva e' `010-configurazione-cataloghi-integrazioni`, come dichiarato in
`.specify/feature.json`. Prima di proseguire con implementazione applicativa, usare
`specs/010-configurazione-cataloghi-integrazioni/spec.md`, `plan.md`, `data-model.md`,
`research.md` e `tasks.md` come sorgente corrente.

Stato sintetico:

- `001`: primo incremento completato; secondo incremento parziale con
  `tipo_documento.codice_contesto` e `registro_contratti_dati` gia' migrati su Postgres
  reale; restano task aperti per enforcement reale del perimetro per-profilo e ritiro
  API di classificazione legacy (T108, dipendente da `010`).
- `002`: prima verticale reale implementata e testata su Postgres reale; i task granulari
  storici non sono piu' un indicatore 1:1 dello stato del codice, leggere sempre la nota
  iniziale in `specs/002-builder-modelli/tasks.md` prima di riprendere lavoro li'.
- `003`: pianificata e non ancora implementata; resta dopo il builder e dopo la discovery
  necessaria ai campi/placeholder.
- `006`: implementazione ACE/context roles completata localmente; quality review esterno
  ancora bloccato da login reviewer.
- `010`: attiva; T003/T004 soddisfatti dalla migration `001`/`0008`, T009/T010
  completati in forma ridotta, resto task aperto. La decisione
  `DEC-001-VERSIONING-RIFERIMENTI-ESTERNI` resta `ASSUNTA_PROVVISORIA` e blocca
  formalmente la fase `TASKS` completa; i task che non dipendono dalle soglie fini sono
  esplicitati in `tasks.md`.

Regola aggiornata FR-016: API legacy ritirate su indicazione esplicita del
product owner nella feature 010. Non reintrodurre un catalogo locale come
ponte per US1/US2; la documentazione di forma e' distinta dai dati operativi
esterni. Il precedente prerequisito US2/T108 e' superato.

## Ordine Suggerito Di Approfondimento

1. `001-catalogo-contratto-geban`
2. `002-builder-modelli`
3. `010-configurazione-cataloghi-integrazioni`
4. `003-sezioni-placeholder-versionamento`
5. `006-sicurezza-autorizzazioni-audit`
6. `004-generazione-documenti-pdf`
7. `005-storage-idempotenza-consultazione`
8. `007-frontend-builder-consultazione`
9. `009-fondamenta-mock-test-qualita`
10. `008-ai-mcp-readiness`

L'ordine mette prima il flusso GEBAN e il dominio configurabile, poi sicurezza e
generazione, quindi frontend, test e predisposizione AI.
