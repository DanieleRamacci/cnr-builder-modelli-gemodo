# Tasks - Generazione Documenti PDF (Incremento MVP FR-019/020)

Scope di questo incremento: vedi `plan.md`. Solo FR-019/FR-020; FR-001..018
restano non pianificati (nessun task qui li implementa).

- [x] T001 Contratto `contracts/generazione-documenti-api.openapi.yaml`:
      `POST /api/v1/documenti/genera` reale (stato `COMPLETATO`/`FALLITO`/
      `DATI_NON_VALIDI`, riferimento documentale, nome file, hash). Ritirata
      la versione storica in `001/contracts/geban-catalog-api.openapi.yaml`
      (`deprecated: true`, `x-implementation-status: withdrawn`, versione
      0.6.0, stesso pattern di `010/configurazione-cataloghi-api.openapi.yaml`).
- [x] T002 [P] `backend/app/generazione/renderer.py`: funzione pura
      (titolo, righe etichetta/valore ordinate) -> bytes PDF via `fpdf2`;
      marcatura "DOCUMENTO DI TEST - NON UFFICIALE" sempre presente.
      `pdf.compress = False` per un output semplice e ispezionabile (non e'
      un percorso sensibile alla dimensione).
- [x] T003 `backend/app/generazione/service.py`: valida il payload (riusa
      `PayloadValidationService.validate_payload`), verifica versione
      pubblicata, richiede a 005 il riferimento idempotente, chiama il
      renderer, richiede a 005 la persistenza, ritorna la risposta pubblica.
      Nessun rendering se la validazione fallisce (FR-020). Un errore del
      renderer (edge case esplicito della spec, non ipotetico: fpdf2 puo'
      sollevare `FPDFException` su token non spezzabili) produce stato
      `FALLITO` con un messaggio sanificato, mai lo stack trace (FR-015),
      ed e' comunque consultabile via riferimento (FR-007/008 di 005).
- [x] T004 `backend/app/generazione/api.py` + `schemas.py`: espone
      `POST /api/v1/documenti/genera` (sostituisce la route storica in
      `app/validation/api.py`), stesso ruolo richiesto
      (`require_documenti_generatore`).
- [x] T005 Rimosso `generate_document_placeholder`/
      `GenerazioneDocumentoResponse` da `app/validation/` (restano solo
      `valida_payload`/`ValidazioneRequest`/`ValidazioneResponse`, di
      proprieta' 001). `app/main.py` aggiornato.
- [x] T006 [P] Test reali (Postgres reale, nessun mock del rendering salvo
      un'iniezione mirata di errore per il solo caso FALLITO) in
      `backend/tests/generazione/test_generazione_e_storage.py` (8 test) e
      nell'e2e `backend/tests/builder/test_builder_flow_api.py` (flusso
      integrazione->modello->pubblicazione->generazione->download reale):
      payload valido produce un PDF reale (`%PDF`, dimensione > 0, testo
      leggibile nei byte), payload non valido non persiste nulla, versione
      non pubblicata rifiutata, titolo/etichette riflettono modello/versione,
      idempotenza (stesso/diverso payload), concorrenza reale (4 thread,
      un solo documento), fallimento di rendering -> FALLITO senza download.
- [x] T007 [P] Aggiornato `specs/001-catalogo-contratto-geban/quickstart.md`
      (Scenario 4) e i test che assumevano `GENERAZIONE_SIMULATA`
      (`backend/tests/validation/test_validazione_payload_api.py`,
      `backend/tests/builder/test_builder_flow_api.py`).
      `pytest -m "not e2e"`: 262 passati, 12 esclusi.
