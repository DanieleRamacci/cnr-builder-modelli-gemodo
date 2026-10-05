# Implementation Plan: Generazione senza archivio, registro e verifica

**Spec**: [spec.md](spec.md) | **Created**: 2026-10-05

## Summary

`genera` smette di cercare una generazione precedente e di salvare il file:
produce il PDF, scrive una riga nel registro delle generazioni (evoluzione di
`documento_generato`) e lo consegna. Due funzioni nuove per gli amministratori:
la verifica di un PDF o di un insieme di dati contro il registro, e il registro
attivita' che mostra insieme gli eventi gia' registrati e quelli nuovi.

## Robustezza dei registri: due regole diverse, di proposito

| Registro | Regola | Perche' |
|---|---|---|
| Generazioni | Nella transazione della generazione: niente riga, niente PDF (FR-006) | Un PDF consegnato e non registrato non si potrebbe mai verificare |
| Audit esistenti (modelli, configurazione, integrazioni) | Restano nella transazione della modifica, come oggi | Il contratto 010 promette "configurazione salvata con audit atomico" |
| Eventi nuovi (validazioni, verifiche, accessi negati) | Best-effort: sessione e transazione proprie, ogni errore catturato e scritto nel log applicativo, la risposta non cambia (FR-013) | Sono informazioni utili, non condizioni dell'azione |

Per gli eventi best-effort: dettaglio troncato a una dimensione massima,
scrittura dopo la risposta di dominio, nessun retry che possa accumulare
lavoro. Indici su data, soggetto, azione per tenere veloce la consultazione
senza scadenza (FR-016).

## Modifiche per area

**Backend**

- `app/generazione/service.py`: niente piu' `esistente_per_chiave` ne' risposta
  idempotente; ogni chiamata registra (anche dati non validi) e, se valida,
  genera; il riferimento va nei metadati del PDF.
- `app/storage/` (o un modulo `registro_generazioni`): niente scrittura e
  lettura del file (`archivio.py`), niente `_in_conflitto`; registrazione con
  esito, impronte e dimensione; ricerca per impronta del PDF e per riferimento.
- `app/storage/models.py` e migrazione: via `uq_documento_generato_chiave_idempotente`
  e il vincolo `ck_documento_generato_stato_coerente` che richiede il percorso;
  `percorso_file` facoltativo e non piu' scritto; esito `DATI_NON_VALIDI`
  ammesso; client e ruoli del chiamante; indice sull'impronta del PDF. Le
  righe esistenti restano.
- `app/generazione/renderer.py`: il riferimento nei metadati (soggetto o
  parole chiave del PDF).
- `app/storage/api.py`: via `download`; `GET /documenti/{riferimento}` solo
  `GEMODO_ADMIN`.
- Nuove API admin: verifica PDF (upload), verifica dati (riferimento + dati),
  registro attivita' (filtri, paginazione, CSV).
- Registro attivita': tabella nuova per gli eventi nuovi; la consultazione
  unisce questa, le tre tabelle di audit esistenti e il registro delle
  generazioni.
- Accessi negati: registrati dal gestore degli errori 401/403, best-effort.
- `app/common/errors.py`: fuori `RICHIESTA_IDEMPOTENTE_IN_CONFLITTO` e
  `DOCUMENTO_NON_DISPONIBILE`.
- `app/core/settings.py`: `gemodo_storage_dir` non serve piu'.

**Frontend**

- Area amministrazione: pagina "Registro attivita'" (filtri, elenco, dettaglio,
  esportazione) e pagina "Verifica documento" (carica PDF; verifica dati).

**Contratti e documenti**

- 004 `generazione-documenti-api.openapi.yaml`: niente 409, riferimento nuovo a
  ogni chiamata.
- 005 `storage-documenti-api.openapi.yaml`: via il download; lettura per
  riferimento solo admin.
- Nuovo contratto admin (verifica, registro attivita').
- `docs/api-per-geban.md` sezioni 5 e 6; `docs/decision-register.yaml` (nuova
  decisione che supera FR-005/007/012 della 005 e ADR 0002 per la
  conservazione); nota nelle Clarifications della 005 e della 004;
  `docs/quality-coverage-matrix.yaml`.

**Deploy**

- Nessun volume per i documenti; la migrazione e' sui dati del registro, non
  distruttiva (le righe restano): avvisare prima del deploy, perche' il backend
  migra da solo all'avvio.

**GEBAN**

- Nessuna modifica obbligatoria. Avviso: niente piu' 409, riferimento diverso a
  ogni chiamata, download tolto.

## Verifica

Test su Postgres reale per registro e migrazione; test dell'API; e2e su stack
reale: generazione ripetuta con la stessa chiave, verifica del PDF ricevuto e
di uno alterato, verifica dati, registro attivita' (admin si', altri 403),
registro attivita' non scrivibile senza effetti sulle azioni.
