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

- Database migrato (baseline `009` + migration proprie di questa feature).
- Seed demo con:
  - tipo documento `BANDO_CONCORSO`;
  - categoria `DEMO`;
  - tipologie GEBAN/SOL TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB con codice SOL
    (`infra/local/postgres/seed-demo-catalog.yaml` della `009`);
  - una versione modello `PUBBLICATO` con `modello_versione_id` pubblico `1`;
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
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&categoria=DEMO&codice_tipologia=TI&modalita=OPERATIVA
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

## Scenario 4 - Campo obbligatorio mancante

Rimuovere `numero_posti`.

Risultato atteso:

- `valido` = `false`;
- errore con `campo` = `numero_posti`;
- codice errore `CAMPO_OBBLIGATORIO`.

## Scenario 5 - Campo extra non ammesso

Aggiungere un campo non dichiarato, ad esempio `campo_extra`.

Risultato atteso:

- `valido` = `false`;
- errore con `campo` = `campo_extra`;
- codice errore `CAMPO_NON_AMMESSO`.

## Scenario 6 - Versione non pubblicata

Usare un `modello_versione_id` non pubblicato o archiviato.

Risultato atteso:

- validazione non consentita;
- errore funzionale `MODELLO_VERSIONE_NON_PUBBLICATO` o equivalente.

## Scenario 7 - Tipologia GEBAN/SOL non valida (FR-020)

Richiesta:

```http
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&categoria=DEMO&codice_tipologia=XX_NON_VALIDA&modalita=OPERATIVA
```

Risultato atteso:

- risposta di errore funzionale, non un elenco vuoto;
- codice errore `TIPOLOGIA_SOL_NON_VALIDA`;
- le tipologie ammesse nel perimetro iniziale sono TDPNRR, CD, DIR, TD, CP, RS, CATP,
  TI, SDIP, MOB (vedi `infra/local/postgres/seed-demo-catalog.yaml` della `009`).

## Scenario 8 - Campo inglese mancante con `bando_inglese: true` (FR-021, FR-022)

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
