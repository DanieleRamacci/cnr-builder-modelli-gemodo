# Quickstart - Catalogo Modelli E Contratto Dati GEBAN

Questa guida descrive gli scenari minimi per validare la feature dopo
l'implementazione. I comandi concreti saranno definiti quando il progetto backend esiste.

## Prerequisiti

- Backend avviato in ambiente locale (scheletro FastAPI/Alembic gia' creato dalla
  `009` in `backend/`, vedi `specs/009-fondamenta-mock-test-qualita/quickstart.md`).
- Database migrato (baseline `009` + migration proprie di questa feature).
- Seed demo con:
  - tipo documento `BANDO_CONCORSO`;
  - categoria `CTER`;
  - tipologie GEBAN/SOL TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB con codice SOL
    (`infra/local/postgres/seed-demo-catalog.yaml` della `009`);
  - almeno due varianti modello pubblicate;
  - campi richiesti demo `PROFILO`, `LIVELLO`, `NUM_POSTI`, `SEDI`, piu' almeno un
    campo `lingua: EN` obbligatorio (es. `TITOLO_EN`) per lo Scenario 8.
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
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&categoria=CTER&codice_tipologia=TI&modalita=OPERATIVA
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
  "modello_versione_id": 27,
  "dati": {
    "PROFILO": "Collaboratore Tecnico Enti di Ricerca",
    "LIVELLO": "VI",
    "NUM_POSTI": 2,
    "SEDI": []
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

Rimuovere `NUM_POSTI`.

Risultato atteso:

- `valido` = `false`;
- errore con `campo` = `NUM_POSTI`;
- codice errore `CAMPO_OBBLIGATORIO`.

## Scenario 5 - Campo extra non ammesso

Aggiungere un campo non dichiarato, ad esempio `CAMPO_EXTRA`.

Risultato atteso:

- `valido` = `false`;
- errore con `campo` = `CAMPO_EXTRA`;
- codice errore `CAMPO_NON_AMMESSO`.

## Scenario 6 - Versione non pubblicata

Usare un `modello_versione_id` non pubblicato o archiviato.

Risultato atteso:

- validazione non consentita;
- errore funzionale `MODELLO_VERSIONE_NON_PUBBLICATO` o equivalente.

## Scenario 7 - Tipologia GEBAN/SOL non valida (FR-020)

Richiesta:

```http
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&categoria=CTER&codice_tipologia=XX_NON_VALIDA&modalita=OPERATIVA
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
  "modello_versione_id": 27,
  "bando_inglese": true,
  "dati": {
    "PROFILO": "Collaboratore Tecnico Enti di Ricerca",
    "LIVELLO": "VI",
    "NUM_POSTI": 2,
    "SEDI": []
  }
}
```

Il modello demo dichiara almeno un campo con `lingua: EN` e `obbligatorio: true` (es.
`TITOLO_EN`), assente dal payload sopra.

Risultato atteso:

- `valido` = `false`;
- un errore per ciascun campo inglese obbligatorio mancante, con codice
  `CAMPO_INGLESE_MANCANTE`;
- ripetendo la stessa richiesta con `bando_inglese: false` (o assente) e senza i
  campi inglesi, la validazione MUST considerare quei campi facoltativi e non
  generare `CAMPO_INGLESE_MANCANTE`.
