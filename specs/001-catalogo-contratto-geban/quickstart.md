# Quickstart - Catalogo Modelli E Contratto Dati GEBAN

Questa guida descrive gli scenari minimi per validare la feature `001` dopo
l'implementazione backend.

## Prerequisiti

- Backend avviato in ambiente locale:

```bash
cd backend
uv sync
export GEMODO_USE_MOCK_PRINCIPAL=true
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

- Database migrato (baseline `009` + migration proprie di questa feature, inclusa la
  `0007` che allinea la nomenclatura ai codici confermati dal team GEBAN il 2026-09-14).
- Seed demo con:
  - tipo documento `BANDO_CONCORSO`;
  - profili professionali `RICERCATORE`, `TECNOLOGO`, `FUNZIONARIO_AMMINISTRAZIONE`,
    `COLLABORATORE_TECNICO_ER`, `COLLABORATORE_AMMINISTRAZIONE`, `OPERATORE_TECNICO`,
    `OPERATORE_AMMINISTRAZIONE`;
  - tipologie/procedure bando GEBAN/SOL `TDPNRR`, `CD`, `DIR`, `TD`, `CP`, `RS`, `CATP`,
    `TI`, `SDIP`, `MOB` con codice SOL interno configurato in
    `infra/local/postgres/seed-demo-catalog.yaml` (i codici non ancora associati a una
    procedura SOL reale usano il placeholder `DA_CONFIGURARE_IN_SOL`);
  - albero di classificazione tipo documento -> tipologia/procedura bando -> profilo;
  - una versione modello `PUBBLICATO` per ogni combinazione tipologia/profilo
    configurata, tutte basate sullo stesso modello temporaneo;
  - una versione modello `BOZZA` con `modello_versione_id` pubblico `2`;
  - campi richiesti demo `codice_bando`, `titolo_it`, `descrizione_ridotta_it`,
    `sede_prescelta_it`, `numero_posti`, piu' `titolo_en` con `lingua: EN` per lo
    Scenario 8.
- Autenticazione Keycloak configurata secondo `specs/006-sicurezza-autorizzazioni-audit/keycloak-jwt.md`
  o principal mock abilitato esplicitamente solo in profili locali/test
  (`GEMODO_USE_MOCK_PRINCIPAL=true`).
- Token Bearer tecnico GEBAN per le prove operative:
  - catalogo/campi: ruolo `DOCUMENTI_VIEWER` o `DOCUMENTI_GENERATORE`;
  - validazione payload: ruolo `DOCUMENTI_GENERATORE`;
  - audience `gemodo-backend`, client `geban-backend`.

Combinazioni demo pubblicate:

| Tipologia | Profilo | `modello_versione_id` |
|---|---|---|
| TD | COLLABORATORE_TECNICO_ER | 1 |
| CP | COLLABORATORE_TECNICO_ER | 3 |
| CP | OPERATORE_TECNICO | 4 |
| CP | RICERCATORE | 5 |
| CP | TECNOLOGO | 6 |
| CP | FUNZIONARIO_AMMINISTRAZIONE | 7 |
| TD | OPERATORE_TECNICO | 8 |
| TD | RICERCATORE | 9 |
| TD | TECNOLOGO | 10 |
| TI | COLLABORATORE_TECNICO_ER | 11 |
| TI | OPERATORE_TECNICO | 12 |
| TI | RICERCATORE | 13 |
| TI | TECNOLOGO | 14 |
| TI | FUNZIONARIO_AMMINISTRAZIONE | 15 |
| RS | RICERCATORE | 16 |
| RS | TECNOLOGO | 17 |
| MOB | COLLABORATORE_TECNICO_ER | 18 |
| MOB | OPERATORE_TECNICO | 19 |
| MOB | RICERCATORE | 20 |
| MOB | TECNOLOGO | 21 |
| MOB | FUNZIONARIO_AMMINISTRAZIONE | 22 |

Le combinazioni tipologia/profilo non elencate sopra (es. `TDPNRR`, `CD`, `DIR`, `CATP`,
`SDIP`, o le categorie `COLLABORATORE_AMMINISTRAZIONE`/`OPERATORE_AMMINISTRAZIONE`) sono
codici validi nel catalogo ma non hanno ancora un modello demo pubblicato: una ricerca
catalogo su quei valori risponde 200 con `modelli: []`, non un errore.

## Scenario 0 - Accesso non autenticato

Inviare una richiesta catalogo senza header `Authorization: Bearer ...`.

Risultato atteso:

- risposta 401;
- codice errore `ACCESSO_NON_AUTENTICATO`.

Inviare una richiesta con token valido ma senza ruolo richiesto o con client diverso da
`geban-backend`.

Risultato atteso:

- risposta 403;
- codice errore `ACCESSO_NON_AUTORIZZATO`.

## Scenario 1 - Catalogo operativo

Richiesta:

```http
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=COLLABORATORE_TECNICO_ER&codice_tipologia=TD&modalita=OPERATIVA
```

Risultato atteso:

- risposta 200;
- solo versioni `PUBBLICATO`;
- ogni elemento contiene `modello_versione_id`;
- nessun modello in bozza, revisione, archiviato o sospeso.

## Scenario 2 - Contratto dati

Richiesta:

```http
GET /api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti
```

Esempio locale:

```bash
curl -s http://localhost:8000/api/v1/catalogo/modelli/1/campi-richiesti
```

Risultato atteso:

- risposta 200;
- campi ordinati;
- ogni campo contiene codice, etichetta, tipo, obbligatorieta' e ordine;
- lo schema non ammette campi extra in validazione.

## Scenario 3 - Payload valido

Richiesta:

```http
POST /api/v1/documenti/valida
Content-Type: application/json
```

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "modello_versione_id": 1,
  "dati": {
    "codice_bando": "BANDO-12345",
    "titolo_it": "Bando demo",
    "sede_prescelta_it": "Roma",
    "numero_posti": 2
  }
}
```

Risultato atteso:

```json
{
  "valido": true,
  "errori": []
}
```

## Scenario 4 - Generazione reale (PDF di test)

Ritirato dal 2026-09-17 (004 FR-019/020): `POST /documenti/genera` non e' piu'
simulato. Vedi
`specs/004-generazione-documenti-pdf/contracts/generazione-documenti-api.openapi.yaml`
per il contratto corrente.

Richiesta:

```http
POST /api/v1/documenti/genera
Content-Type: application/json
```

Usare lo stesso payload valido dello Scenario 3.

Risultato atteso:

```json
{
  "stato": "COMPLETATO",
  "messaggio": "Documento di test generato correttamente.",
  "modello_versione_id": 1,
  "external_context_id": "BANDO-12345",
  "riferimento_documentale": "<uuid opaco>",
  "validazione": {
    "valido": true,
    "errori": []
  }
}
```

Il PDF prodotto e' reale ma sempre etichettato TEST (nessun percorso
"ufficiale" in questo incremento): titolo ed etichette/valori riflettono il
contratto dati della versione modello, nell'ordine configurato. Stato e
download del documento sono descritti in
`specs/005-storage-idempotenza-consultazione/contracts/storage-documenti-api.openapi.yaml`
(`GET /documenti/{riferimento}`, `GET /documenti/{riferimento}/download`).

## Scenario 5 - Campo obbligatorio mancante

Rimuovere `numero_posti`.

Risultato atteso:

- `valido` = `false`;
- errore con `campo` = `numero_posti`;
- codice errore `CAMPO_OBBLIGATORIO`.

## Scenario 6 - Campo extra non ammesso

Aggiungere un campo non dichiarato, ad esempio `campo_extra`.

Risultato atteso:

- `valido` = `false`;
- errore con `campo` = `campo_extra`;
- codice errore `CAMPO_NON_AMMESSO`.

## Scenario 7 - Versione non pubblicata

Usare un `modello_versione_id` non pubblicato o archiviato.

Risultato atteso:

- validazione non consentita;
- errore funzionale `MODELLO_VERSIONE_NON_PUBBLICATO` o equivalente.

## Scenario 8 - Tipologia GEBAN/SOL non valida (FR-020)

Richiesta:

```http
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=COLLABORATORE_TECNICO_ER&codice_tipologia=XX_NON_VALIDA&modalita=OPERATIVA
```

Risultato atteso:

- HTTP 200 con `modelli: []` (contratto v0.4/010 FR-016);
- nessuna allowlist locale e nessun errore TIPOLOGIA_SOL_NON_VALIDA nella ricerca;
- il seed storico non e' sorgente delle tipologie disponibili nel builder.

## Scenario 9 - Campo inglese mancante con `bando_inglese: true` (FR-021, FR-022)

Richiesta:

```http
POST /api/v1/documenti/valida
Content-Type: application/json
```

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "BANDO-12345",
  "modello_versione_id": 1,
  "bando_inglese": true,
  "dati": {
    "codice_bando": "BANDO-12345",
    "titolo_it": "Bando demo",
    "sede_prescelta_it": "Roma",
    "numero_posti": 2
  }
}
```

Il modello demo dichiara almeno un campo con `lingua: EN` e `obbligatorio: true` (es.
`titolo_en`), assente dal payload sopra.

Risultato atteso:

- `valido` = `false`;
- un errore per ciascun campo inglese obbligatorio mancante, con codice
  `CAMPO_INGLESE_MANCANTE`;
- ripetendo la stessa richiesta con `bando_inglese: false` (o assente) e senza i
  campi inglesi, la validazione MUST considerare quei campi facoltativi e non
  generare `CAMPO_INGLESE_MANCANTE`.

## Verifica Test

Comando eseguito il 2026-07-31:

```bash
cd backend
uv run pytest tests/catalog tests/validation tests/common/test_api_error_response.py tests/common/test_security_jwt.py -q -rs
```

Esito mirato registrato: `28 passed`.

Suite ampia eseguita il 2026-07-31:

```bash
cd backend
uv run pytest -m "not e2e" -q -rs
```

Esito registrato: `126 passed, 12 deselected`.

Riallineamento nomenclatura GEBAN (categorie/tipologie) verificato il 2026-09-14 con
Postgres reale (migration `0001`-`0007` eseguite su un DB scratch, incluso il percorso
di aggiornamento da uno stato gia' migrato con la nomenclatura precedente):

```bash
cd backend
DATABASE_URL=postgresql+psycopg://<user>@localhost:5432/<db> uv run pytest -m "not e2e" -q
DATABASE_URL=postgresql+psycopg://<user>@localhost:5432/<db> uv run pytest -m "e2e" -q
```

Esito registrato: `140 passed, 12 deselected` (non-e2e) e `12 passed` (e2e).
