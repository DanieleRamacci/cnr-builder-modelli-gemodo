# Project Map - GEBAN Builder Modelli GEMODO

Questo documento collega la proposta sorgente alle specifiche Spec Kit.
La regola di lavoro e': nessuna sezione della proposta deve restare senza owner.

## Fonti

- Documento sorgente: `PROPOSTA-servizio-gestione-modelli-bando.md`
- Costituzione: `.specify/memory/constitution.md`

## Spec Inventory

| Spec | Area | Stato | Fonte proposta | Note |
|---|---|---|---|---|
| `001-catalogo-contratto-geban` | Catalogo modelli, contratto dati, validazione payload verso GEBAN | Draft specificata | §3, §4, §5, §9.1-§9.5 | Prima spec operativa; attiva in `.specify/feature.json` |
| `002-builder-modelli` | Builder backend per tipi, categorie, modelli, versioni e pubblicazione | Draft di copertura | §2, §4, §8.2-§8.6, §10, §16.3 | Da chiarire stati definitivi |
| `003-sezioni-placeholder-versionamento` | Sezioni, placeholder, JSON schema e versionamento contenuti | Draft di copertura | §5.5, §6, §8.7-§8.9, §16.3 | Da chiarire formato contenuto e campi complessi |
| `004-generazione-documenti-pdf` | Generazione documenti, rendering, PDF bozza/ufficiale | Draft di copertura | §9.6, §13, §16.5 | Si ferma alla generazione e metadati documento |
| `005-storage-idempotenza-consultazione` | Storage documentale, idempotenza, download e stato generazione | Draft di copertura | §9.7-§9.8, §13, §14, §11.2 | Da confermare storage definitivo |
| `006-sicurezza-autorizzazioni-audit` | Keycloak, ruoli, autorizzazioni, audit sicurezza | Draft di copertura | §12, §8.11, §15.3 | Spec dedicata per non diluire sicurezza nelle altre |
| `007-frontend-builder-consultazione` | Frontend builder e consultazione generazioni | Draft di copertura | §11, §16.6 | Dipende da API builder e generazioni |
| `008-ai-mcp-readiness` | Predisposizione AI, MCP, documentazione AI-ready | Draft di copertura | §15 | Non prerequisito del primo rilascio |
| `009-fondamenta-mock-test-qualita` | Fondamenta tecniche, mock, test e qualita' | Draft di copertura | §16.1, §16.2, §16.7, §17 | Raccoglie setup e criteri cross-cutting |

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
| §15 Predisposizione Per AI, Documentazione Assistita E MCP | 008, 006 | Coperta | AI/MCP e sicurezza AI |
| §16 Piano Di Sviluppo | 009 + tutte | Coperta | Usato come input per plan/tasks successivi |
| §17 Decisioni Da Confermare | 009 + spec collegate | Coperta | Decisioni distribuite come open decisions |

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

