# Project Map - GEBAN Builder Modelli GEMODO

Questo documento collega la proposta sorgente alle specifiche Spec Kit.
La regola di lavoro e': nessuna sezione della proposta deve restare senza owner.

## Fonti

- Documento sorgente: `PROPOSTA-servizio-gestione-modelli-bando.md`
- Costituzione: `.specify/memory/constitution.md`

## Spec Inventory

| Spec | Area | Stato | Fonte proposta | Note |
|---|---|---|---|---|
| `001-catalogo-contratto-geban` | Catalogo modelli, contratto dati, validazione payload verso GEBAN | Attiva; spec/plan/tasks aggiornati (2026-07-31), 0/73 task implementati; readiness gate `TASKS` verde | §3, §4, §5, §9.1-§9.5 | Prima spec operativa; recepisce tipologie GEBAN/SOL, lingua IT/EN, categorie e campi comuni GEBAN confermati, bando multiplo/ribando, versionamento campi/placeholder, campi complessi strutturati e protezione JWT Keycloak minima per le API operative. Profilo GEBAN versionato e API dedicate al profilo sono sospesi per il primo incremento produttivo e restano tracciati per `002`/`006` |
| `002-builder-modelli` | Builder backend per tipi, categorie, modelli, versioni e pubblicazione | Plan+tasks generati ma superati (2026-06-19), 0/59 task implementati | §2, §4, §8.2-§8.6, §10, §16.3 | Da chiarire stati definitivi; `spec.md`/`plan.md`/`tasks.md` fermi al 2026-06-19, non riflettono `SEC-006-002` ne' il modello documentale controllato chiarito in `009`. Da aggiornare e ripianificare prima di implementare |
| `003-sezioni-placeholder-versionamento` | Sezioni proprie della versione modello, placeholder, JSON schema e contenuti strutturati | Plan+tasks generati ma superati (2026-06-19), 0/48 task implementati | §5.5, §6, §8.7-§8.9, §16.3 | Sezioni non versionate autonomamente nel perimetro corrente; chiarimento in `009`: builder visuale controllato, non editor HTML, con modello documentale versionato a blocchi/layout/asset/placeholder - non ancora recepito in `plan.md`/`tasks.md` di questa spec (fermi al 2026-06-19). Da aggiornare e ripianificare prima di implementare |
| `004-generazione-documenti-pdf` | Generazione documenti, rendering, PDF bozza/ufficiale | Draft di copertura | §9.6, §13, §16.5 | Si ferma alla generazione e metadati documento; bando multiplo, ribando e bando inglese integrale chiariti in `009` il 2026-07-28; resta da chiarire confine con stampa/pubblicazione SOL |
| `005-storage-idempotenza-consultazione` | Storage documentale, idempotenza, download e stato generazione | Draft di copertura | §9.7-§9.8, §13, §14, §11.2 | Da confermare storage definitivo; ribando chiarito in `009` come nuovo bando collegato al precedente; resta da chiarire nuova pubblicazione/riferimento documentale verso sistemi esterni |
| `006-sicurezza-autorizzazioni-audit` | Keycloak, ruoli, autorizzazioni, audit sicurezza | Decisioni risolte (SEC-006-001 e SEC-006-002), plan da avviare | §12, §8.11, §12.9 | `keycloak-jwt.md`; decisioni confermate il 2026-07-29: (1) GEBAN -> GEMODO con token tecnico backend-to-backend (client credentials) e contesto/utente reale nel payload solo per audit; ruoli GEMODO come client roles su `gemodo-backend` (realm Keycloak `cnr` condiviso); (2) nessuna separazione gestore/revisore/approvatore nella prima release, la pubblicazione del gestore vale come approvazione, ruoli revisore/approvatore restano riservati e inattivi; ambiente di test reale disponibile (`sso.test.si.cnr.it`, realm `cnr`, accesso admin per il team GEMODO), produzione da richiedere al referente infrastruttura Keycloak CNR |
| `007-frontend-builder-consultazione` | Frontend builder e consultazione generazioni | Draft integrata | §11, §16.6 | Dipende da API builder e generazioni |
| `008-ai-mcp-readiness` | Predisposizione AI, MCP, documentazione AI-ready | Draft integrata | §15 | Non prerequisito del primo rilascio |
| `009-fondamenta-mock-test-qualita` | Fondamenta tecniche, mock, test, qualita', documentazione API e readiness riuso PA | Implementata (Fase 1-5, T001-T058); Polish in corso | §16.1, §16.2, §16.7, §17 | Attiva; ambiente locale, mock GEBAN, registro decisioni (28 voci) e matrice di copertura reali e testati (109 test pytest); raccoglie setup, criteri cross-cutting, ownership decisioni, OpenAPI/Swagger/ReDoc, portale documentazione e vincoli open source/PA |

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

## Stato Plan/Tasks Delle Spec Operative (verificato 2026-07-29)

`001-catalogo-contratto-geban` ha `spec.md`, `plan.md` e `tasks.md` aggiornati al
2026-07-31. Il readiness gate per `TASKS` e' verde dopo la conferma/sospensione
esplicita delle decisioni bloccanti: la feature puo' partire da `T001`, includendo
catalogo, contratto dati, validazione payload e protezione JWT Keycloak minima.

`002-builder-modelli` e `003-sezioni-placeholder-versionamento` hanno gia' `plan.md` e
`tasks.md` generati, ma entrambi risalgono alla sessione di chiarimento del 2026-06-19
(prima ancora della sessione 2026-06-22 che ha aperto il registro decisioni). Non
riflettono ancora le decisioni chiarite/confermate successivamente (2026-06-22,
2026-07-07, 2026-07-28, 2026-07-29) e tracciate in `docs/decision-register.yaml`:
tipologie GEBAN/SOL, campi comuni GEBAN, profilo GEBAN versionato, bando
multiplo/ribando, bando inglese integrale, `SEC-006-001`, `SEC-006-002`, modello
documentale controllato.

Nessun task di queste tre spec e' implementato (0/73, 0/59, 0/48). Prima di avviare
l'implementazione applicativa oltre la `001`:

1. implementare la `001` seguendo `specs/001-catalogo-contratto-geban/tasks.md`;
2. propagare nelle `spec.md` di `002` e `003` le decisioni ormai `CONFERMATA` che le
   riguardano (vedi `spec_interessate` in `docs/decision-register.yaml`);
3. rigenerare `plan.md` e `tasks.md` di `002` e `003` (`/speckit-plan` +
   `/speckit-tasks`) cosi' che riflettano lo stato attuale, non quello del 19 giugno;
4. verificare con `backend/app/quality/readiness_gate.py` che nessuna decisione
   critica blocchi ancora la fase `TASKS` per la spec target prima di generare nuovi
   task implementativi (FR-018).

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
