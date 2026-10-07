# Tasks: Generazione senza archivio, registro e verifica

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

**Primo passo fatto il 2026-10-05** (sblocca GEBAN): migrazione `0029`,
generazione senza archivio ne' conflitti, registro di ogni chiamata, download
tolto, lettura per riferimento solo admin; contratti 004 0.4.0 e 005 0.2.0,
`docs/api-per-geban.md`, catalogo errori (T002 e T016 in parte). Verifica: 560
test backend su Postgres reale; e2e su stack reale con lo stesso bando generato
tre volte con la stessa chiave (tre PDF, tre righe di registro, download 404).

**Registro attivita' fatto il 2026-10-05** (T010-T013): migrazione `0030`
(`evento_attivita` e `username` su tutti i registri), validazioni e accessi
negati registrati senza mai fermare l'azione, `GET /api/v1/admin/attivita` e
`.csv` solo admin, pagina "Registro attivita'" nel menu degli amministratori.
Gli eventi senza username (prima della 0030) lo prendono da un altro evento
dello stesso soggetto. Verifica: 565 test backend, 198 frontend, e2e su stack
reale (l'admin trova le tre generazioni del bando col nome dell'utente).
Manca il contratto OpenAPI delle API admin (parte di T002).

**Decisione 2026-10-06**: si chiude prima la parte che sblocca GEBAN
(rigenerazione senza conflitto, registro, riferimento e contratti aggiornati).
La verifica amministrativa di PDF e dati non si implementa in questo incremento:
resta una spec successiva, insieme alla sua pagina e ai relativi e2e. Il
riferimento nei metadati del PDF rimane in scope perche' prepara quella verifica
senza esporre nuove API.

## Phase 1: Decisione e contratti

- [x] T001 Nota nelle Clarifications di `005` (FR-005/007/012 e conservazione
      superati da 013) e di `004` (FR-018); decisione nel
      `docs/decision-register.yaml`.
- [x] T002 Contratto 004: niente 409, riferimento nuovo a ogni chiamata,
      riferimento nei metadati. Contratto 005: via il download, lettura per
      riferimento solo admin. Contratto admin nuovo solo per il registro
      attivita' gia' implementato. **Rinviato a spec futura**: contratto admin
      per verifica PDF e verifica dati. Test di contratto.
      *Completato 2026-10-06*: pubblicati contratti 004/005 gia' aggiornati
      alla 013 e nuovo
      `contracts/registro-attivita-admin.openapi.yaml`; registrato in
      `PUBLISHED_CONTRACTS` come `/docs/registro-attivita-admin`. Verifica:
      `tests/generazione/test_contracts.py` e `tests/contract/test_docs_index.py`.

## Phase 2: US1 - Rigenerare con la stessa chiave (P1)

- [x] T003 Migrazione: via il vincolo di unicita' della chiave e il vincolo che
      richiede il file; esito `DATI_NON_VALIDI`; client e ruoli; indice
      sull'impronta del PDF. Righe esistenti intatte. Test della migrazione su
      Postgres reale.
- [x] T004 `genera`: niente ricerca della generazione precedente, niente file;
      registra ogni chiamata (anche dati non validi) e consegna il PDF solo a
      riga registrata (FR-006). Test: stessa chiave e dati diversi due volte,
      stessi dati due volte, dati non validi, registro non scrivibile -> errore
      e nessun PDF.
- [x] T005 Riferimento nei metadati del PDF. Test: si estrae dal PDF ricevuto.
      *Fatto 2026-10-06*: il riferimento viene generato prima della resa,
      scritto in subject/keywords del PDF e usato per la riga del registro e
      per `X-Riferimento-Documentale`. Verifica:
      `tests/generazione/test_generazione_e_storage.py::test_generazione_consegna_il_pdf_e_lo_registra_senza_conservarlo`.
- [x] T006 Via `archivio.py` dal flusso, `gemodo_storage_dir`, i codici
      d'errore non piu' usati; test esistenti dell'idempotenza capovolti.

## Phase 3: US2/US3 - Verifica (P1/P2) - RINVIATA

- [ ] T007 **RINVIATO a spec futura**: API admin "verifica PDF": impronta del
      file caricato, generazione corrispondente o "non corrisponde". Test: PDF
      ricevuto si', un byte cambiato no, PDF estraneo no, non admin 403.
- [ ] T008 **RINVIATO a spec futura**: API admin "verifica dati": riferimento +
      dati, corrispondono o no; ordine dei campi indifferente. Test.
- [x] T009 `GET /documenti/{riferimento}` solo admin, download tolto. Test.

## Phase 4: US4 - Registro attivita' (P2)

- [x] T010 Tabella degli eventi nuovi e scrittore best-effort: sessione propria,
      errori nel log applicativo, dettaglio troncato. Test: database che
      rifiuta la scrittura -> l'azione riesce lo stesso.
- [x] T011 Eventi: validazioni, verifiche, accessi negati (401/403, minimo
      indispensabile). Test.
- [x] T012 API admin del registro: unione di eventi nuovi, audit di modelli,
      configurazione, integrazioni e registro generazioni; filtri, paginazione,
      CSV. Test, compreso 403 per i non admin.

## Phase 5: Frontend admin

- [x] T013 Pagina "Registro attivita'": filtri, elenco, dettaglio, esportazione.
- [ ] T014 **RINVIATO a spec futura**: pagina "Verifica documento": carica PDF;
      verifica dati.
- [ ] T015 e2e su stack reale: generazione ripetuta con la stessa chiave,
      registro attivita' (admin si', altri no), riferimento nuovo a ogni
      chiamata e download assente. **Fuori da questo incremento**: verifica del
      PDF ricevuto/alterato e verifica dati, coperte dalla spec futura.

## Phase 6: Documentazione e consegna

- [ ] T016 `docs/api-per-geban.md` sezioni 5 e 6, catalogo errori,
      `docs/quality-coverage-matrix.yaml`; testo dell'avviso per GEBAN. La
      documentazione deve dire esplicitamente che la verifica PDF/dati e' una
      funzione amministrativa futura, non disponibile in questo rilascio.
- [ ] T017 Suite completa backend e frontend, build di produzione; avviso
      sulla migrazione prima del deploy.
