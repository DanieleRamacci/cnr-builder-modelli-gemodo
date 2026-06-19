# Quickstart - Catalogo Modelli E Contratto Dati GEBAN

Questa guida descrive gli scenari minimi per validare la feature dopo
l'implementazione. I comandi concreti saranno definiti quando il progetto backend esiste.

## Prerequisiti

- Backend avviato in ambiente locale.
- Database migrato.
- Seed demo con:
  - tipo documento `BANDO_CONCORSO`;
  - categoria `CTER`;
  - almeno due varianti modello pubblicate;
  - campi richiesti demo `PROFILO`, `LIVELLO`, `NUM_POSTI`, `SEDI`.
- Autenticazione configurata secondo la spec sicurezza o disabilitata solo nel profilo di
  test locale.

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
