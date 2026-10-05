# Tasks: Generazione senza archivio, registro e verifica

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Decisione e contratti

- [ ] T001 Nota nelle Clarifications di `005` (FR-005/007/012 e conservazione
      superati da 013) e di `004` (FR-018); decisione nel
      `docs/decision-register.yaml`.
- [ ] T002 Contratto 004: niente 409, riferimento nuovo a ogni chiamata,
      riferimento nei metadati. Contratto 005: via il download, lettura per
      riferimento solo admin. Contratto admin nuovo: verifica PDF, verifica
      dati, registro attivita'. Test di contratto.

## Phase 2: US1 - Rigenerare con la stessa chiave (P1)

- [ ] T003 Migrazione: via il vincolo di unicita' della chiave e il vincolo che
      richiede il file; esito `DATI_NON_VALIDI`; client e ruoli; indice
      sull'impronta del PDF. Righe esistenti intatte. Test della migrazione su
      Postgres reale.
- [ ] T004 `genera`: niente ricerca della generazione precedente, niente file;
      registra ogni chiamata (anche dati non validi) e consegna il PDF solo a
      riga registrata (FR-006). Test: stessa chiave e dati diversi due volte,
      stessi dati due volte, dati non validi, registro non scrivibile -> errore
      e nessun PDF.
- [ ] T005 Riferimento nei metadati del PDF. Test: si estrae dal PDF ricevuto.
- [ ] T006 Via `archivio.py` dal flusso, `gemodo_storage_dir`, i codici
      d'errore non piu' usati; test esistenti dell'idempotenza capovolti.

## Phase 3: US2/US3 - Verifica (P1/P2)

- [ ] T007 API admin "verifica PDF": impronta del file caricato, generazione
      corrispondente o "non corrisponde". Test: PDF ricevuto si', un byte
      cambiato no, PDF estraneo no, non admin 403.
- [ ] T008 API admin "verifica dati": riferimento + dati, corrispondono o no;
      ordine dei campi indifferente. Test.
- [ ] T009 `GET /documenti/{riferimento}` solo admin, download tolto. Test.

## Phase 4: US4 - Registro attivita' (P2)

- [ ] T010 Tabella degli eventi nuovi e scrittore best-effort: sessione propria,
      errori nel log applicativo, dettaglio troncato. Test: database che
      rifiuta la scrittura -> l'azione riesce lo stesso.
- [ ] T011 Eventi: validazioni, verifiche, accessi negati (401/403, minimo
      indispensabile). Test.
- [ ] T012 API admin del registro: unione di eventi nuovi, audit di modelli,
      configurazione, integrazioni e registro generazioni; filtri, paginazione,
      CSV. Test, compreso 403 per i non admin.

## Phase 5: Frontend admin

- [ ] T013 Pagina "Registro attivita'": filtri, elenco, dettaglio, esportazione.
- [ ] T014 Pagina "Verifica documento": carica PDF; verifica dati.
- [ ] T015 e2e su stack reale: generazione ripetuta con la stessa chiave,
      verifica del PDF ricevuto e di uno alterato, verifica dati, registro
      attivita' (admin si', altri no).

## Phase 6: Documentazione e consegna

- [ ] T016 `docs/api-per-geban.md` sezioni 5 e 6, catalogo errori,
      `docs/quality-coverage-matrix.yaml`; testo dell'avviso per GEBAN.
- [ ] T017 Suite completa backend e frontend, build di produzione; avviso
      sulla migrazione prima del deploy.
