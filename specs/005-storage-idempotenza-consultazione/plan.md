# Piano - Storage, Idempotenza E Consultazione (Incremento MVP FR-019/020)

Feature attiva: **005**, scope ridotto al minimo necessario per rendere reale
il PDF di test di `004` (vedi
[ADR 0002](../../docs/adr/0002-integrazioni-contesti-modelli-test.md) e
`specs/010-configurazione-cataloghi-integrazioni/mvp-integrazione-modello-pdf-test.md`).
FR-013 (anomalia file-prodotto-ma-riferimento-non-salvato), FR-015 (audit
dedicato oltre l'esistente) e la piena FR-011 (normalizzazione avanzata per
idempotenza) restano fuori da questo incremento.

## Obiettivo

Dare a 004 un servizio reale di persistenza: un riferimento documentale
stabile, uno stato consultabile, un download autorizzato e un'idempotenza di
base (stessa chiave + stessi dati -> stesso documento; stessa chiave + dati
diversi -> conflitto), secondo FR-001..007, FR-009, FR-010, FR-014, FR-016,
FR-019, FR-020.

## Scope

- **Dentro**: tabella `documento_generato` (chiave idempotente =
  `sistema_richiedente` + `external_context_id` + `modello_versione_id`,
  FR-005); storage fisico filesystem locale (assunzione esplicita della spec:
  "GEMODO MUST comunque disporre di uno storage/copia di lavoro propria...
  anche minima, es. filesystem locale"); stato (`COMPLETATO`/`FALLITO`)
  consultabile via `GET /api/v1/documenti/{riferimento}`; download via
  `GET /api/v1/documenti/{riferimento}/download`, autorizzato con gli stessi
  ruoli di lettura gia' usati da `001` (`DOCUMENTI_VIEWER`/
  `DOCUMENTI_GENERATORE` - FR-014, in attesa dell'irrigidimento per-contesto
  gia' tracciato in T087 di 010 e non ancora chiuso, vedi Assunzioni).
- **Fuori**: backend S3/object storage (l'assunzione della spec lo rinvia a
  decisione futura), retry HTTP espliciti oltre all'idempotenza sulla stessa
  chiave, audit dedicato oltre l'evento gia' registrato da 004 in fase di
  generazione, rigenerazione volontaria con revisione esplicita (FR-012:
  oggi una richiesta con la stessa chiave e dati diversi e' semplicemente un
  conflitto, senza un meccanismo di "nuova revisione" dedicato).

## Approccio Tecnico

- Nuovo modulo `backend/app/storage/` (owner 005): `models.py`
  (`DocumentoGenerato`), migration, `repository.py`, `archivio.py`
  (persistenza filesystem: root configurabile via `GEMODO_STORAGE_DIR`,
  default `<repo>/data/documenti-generati`, cartella esclusa da git),
  `api.py` (stato + download), `schemas.py`.
- Idempotenza: `hash_dati` = SHA-256 di `dati` normalizzato (chiavi ordinate,
  separatori compatti) confrontato a parita' di chiave; stesso hash -> replay
  del documento esistente (FR-006); hash diverso -> 409 (FR-007). Confronto
  fatto sui dati di INPUT, non sul file prodotto (FR-011, versione minima:
  normalizzazione dell'ordine delle chiavi, non ancora normalizzazione
  semantica profonda dei valori).
- Riferimento documentale: stringa opaca (`uuid4().hex`), mai il path fisico
  o l'id interno della riga (FR-009).
- Vincolo di unicita' DB sulla chiave idempotente, cosi' una race fra due
  richieste concorrenti con la stessa chiave viene arbitrata dal database
  (una vince, l'altra osserva il record appena creato), non dall'
  applicazione.

## Dipendenze

- 004 chiama questo modulo per generare il riferimento e salvare il file;
  004 non scrive mai direttamente su disco.
- 006: ruoli/JWT esistenti riusati senza modifiche in questo incremento.

## Non Fatto In Questo Incremento

Backend di storage diverso dal filesystem locale, retry/idempotenza su
trasporto HTTP (distinta dall'idempotenza sulla chiave funzionale qui
implementata), audit granulare di ogni consultazione/download oltre
l'autorizzazione stessa, rigenerazione volontaria con revisione esplicita,
enforcement per-contesto sulla lettura (tracciato altrove, non introdotto qui
per non anticipare un cambio di autorizzazione non ancora deciso in dettaglio).
