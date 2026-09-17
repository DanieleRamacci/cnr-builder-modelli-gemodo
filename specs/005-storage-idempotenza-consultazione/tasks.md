# Tasks - Storage, Idempotenza E Consultazione (Incremento MVP FR-019/020)

Scope di questo incremento: vedi `plan.md`. FR-011 (normalizzazione profonda),
FR-012 (revisione esplicita), FR-013/FR-015 (anomalie/audit dedicati) restano
non pianificati.

- [x] T001 Contratto `contracts/storage-documenti-api.openapi.yaml`:
      `GET /api/v1/documenti/{riferimento}` (stato/metadati) e
      `GET /api/v1/documenti/{riferimento}/download` (file), errori
      `DOCUMENTO_NON_TROVATO`/`DOCUMENTO_NON_DISPONIBILE`.
- [x] T002 Migration `0014_documento_generato` (verificata su Postgres reale
      con `alembic upgrade head`): tabella `documento_generato` (riferimento
      univoco, chiave idempotente univoca su sistema_richiedente+
      external_context_id+modello_versione_id, stato, hash_dati, hash_file,
      nome_file, percorso_file, dimensione_byte, creato_da, created_at,
      CHECK di coerenza stato/campi). Modello SQLAlchemy in
      `backend/app/storage/models.py`.
- [x] T003 [P] `backend/app/storage/archivio.py`: salva/legge bytes su
      filesystem (`GEMODO_STORAGE_DIR`, default `<repo>/data/documenti-generati`,
      escluso da git), path derivato dal riferimento generato dal server, mai
      dall'input dell'utente (niente traversal possibile).
- [x] T004 `backend/app/storage/repository.py` + `service.py`: lookup per
      chiave idempotente (stesso hash -> replay, hash diverso -> 409 anche
      in caso di race risolta dal vincolo unico DB), creazione riga (successo
      o fallimento), lookup per riferimento per stato/download.
- [x] T005 `backend/app/storage/api.py`: le due route GET, autorizzazione
      `require_documenti_viewer`; download restituisce 409
      `DOCUMENTO_NON_DISPONIBILE` per generazioni FALLITE (senza il file);
      lo stato resta consultabile in entrambi i casi.
- [x] T006 [P] Test reali (Postgres reale, file scritti/letti per davvero) in
      `backend/tests/generazione/test_generazione_e_storage.py`: idempotenza
      (stesso payload -> stesso riferimento, un solo record; payload diverso
      -> 409), download restituisce esattamente i byte salvati (`%PDF` +
      testo leggibile), riferimento inesistente -> 404 su entrambe le route,
      generazione fallita -> stato FALLITO consultabile e download 409,
      concorrenza reale sulla stessa chiave con 4 thread -> un solo
      documento (vincolo DB, non lock applicativo). `pytest -m "not e2e"`:
      270 passati, 12 esclusi.
