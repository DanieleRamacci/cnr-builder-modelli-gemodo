# Piano - Generazione Documenti PDF (Incremento MVP FR-019/020)

Feature attiva: **004**, scope volutamente ridotto al PDF di test confermato
in [ADR 0002](../../docs/adr/0002-integrazioni-contesti-modelli-test.md) e in
`specs/010-configurazione-cataloghi-integrazioni/mvp-integrazione-modello-pdf-test.md`.
FR-001..FR-018 (distinzione bozza/ufficiale, hash di conformita', motore di
sezioni/placeholder vivo) restano fuori da questo incremento: non c'e' ancora
alcuna generazione "ufficiale" nel sistema, quindi la distinzione non si pone.

## Obiettivo Di Questo Incremento

Sostituire la risposta simulata (`GENERAZIONE_SIMULATA`) di
`POST /api/v1/documenti/genera` con un vero rendering PDF, cosi' da poter
dimostrare il flusso end-to-end: integrazione connessa (010) -> modello creato
dal builder (002) -> pubblicato -> generazione reale (004) -> file scaricabile
(005).

## Scope

- **Dentro**: FR-019/FR-020. Un solo tipo di output (`TEST`), nessuna
  distinzione bozza/ufficiale (non esiste ancora un percorso "ufficiale").
  Rendering deterministico: titolo (tipo documento + variante), etichette e
  valori nell'ordine (`ModelloCampoRichiesto.ordine`) del contratto dati della
  versione pubblicata. Nessun placeholder posizionale, nessuna sezione grafica
  (quella e' l'ambito futuro di FR-011/012, dipendente da 003 - qui il
  contenuto e' una lista ordinata etichetta/valore, non un template).
- **Fuori**: hash di conformita' con il contratto (FR-008 gia' soddisfatto in
  altro modo, vedi sotto), motore sezioni/placeholder della 003, formati
  diversi da PDF, generazione "ufficiale" (FR-002).

## Approccio Tecnico

- Nuovo modulo `backend/app/generazione/` (owner 004), separato da
  `backend/app/validation/` (001): la validazione del payload resta in 001
  (`PayloadValidationService.validate_payload`, riusata qui, non duplicata);
  la produzione del documento e' responsabilita' di 004.
- Renderer: libreria `fpdf2` (pura Python, nessuna dipendenza di sistema tipo
  Cairo/Pango), scelta per restare aderenti a "PDF semplice" dell'ADR 0002
  senza introdurre un motore di template. `backend/app/generazione/renderer.py`
  espone una funzione pura (titolo, righe etichetta/valore) -> bytes PDF,
  testabile senza I/O.
- Il documento generato e' sempre etichettato `TEST` nel contenuto (titolo e
  filigrana) e nei metadati, per FR-019 e per l'assenza di un percorso
  ufficiale.
- Persistenza reale del file: vedi `specs/005-storage-idempotenza-consultazione/plan.md`.
  Questo modulo chiama il servizio di storage (005), non scrive file
  direttamente.
- Il vecchio `POST /api/v1/documenti/genera` di 001
  (`GenerazioneDocumentoResponse` in `geban-catalog-api.openapi.yaml`) viene
  ritirato (`x-implementation-status: withdrawn`, stesso pattern gia' usato in
  `010/configurazione-cataloghi-api.openapi.yaml`): lo stesso percorso HTTP e'
  ora implementato secondo il nuovo contratto
  `contracts/generazione-documenti-api.openapi.yaml`, di proprieta' di questa
  spec. FR-019 di `001` ("MUST NOT includere generazione PDF dettagliata")
  resta rispettato: il dettaglio vive qui, non in `001`.

## Dipendenze

- 002 (builder): fornisce versioni modello pubblicate con campi ordinati -
  gia' reale (vedi `backend/app/builder/`).
- 001: validazione payload - gia' reale, riusata senza modifiche.
- 005: riferimento documentale, storage, stato, download - implementata in
  questo stesso incremento (vedi il suo `plan.md`), non simulata.
- 010: il modello e' raggiungibile solo se la sua integrazione e' `CONNESSO`
  (gia' vero dal T082/T083 di 010) - non e' un nuovo requisito di 004, e'
  gia' garantito a monte.

## Non Fatto In Questo Incremento

Firma/hash di conformita' periodico (FR-008 nel senso di "verifica che il
modello sia ancora allineato al catalogo esterno", non nel senso di "hash del
file generato" - quest'ultimo e' implementato, vedi 005), audit dedicato oltre
quanto gia' previsto da 006 per le route esistenti, formati diversi da PDF,
generazione ufficiale/bozza.
