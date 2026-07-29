# Mock GEBAN

Simulatore del sistema chiamante GEBAN, usato per sviluppo e verifica ripetibile dei
contratti GEMODO senza dipendere dal sistema GEBAN reale (spec
`009-fondamenta-mock-test-qualita`, User Story 2).

Il mock **non sostituisce il collaudo con GEBAN reale**: esercita solo i contratti
pubblici (catalogo, campi/schema, validazione, generazione, stato, download) con la stessa
identita' tecnica prevista per l'integrazione operativa (client `geban-backend`, profilo
`GEBAN_RECLUTAMENTO_V1`), senza scorciatoie interne su builder o database GEMODO.

Contenuto:

- `scenarios/`: manifest degli scenari end-to-end minimi (`minimum-e2e.yaml`,
  `expected-outcomes.yaml`), allineati a
  `specs/009-fondamenta-mock-test-qualita/contracts/mock-geban-scenarios.yaml`.
- `payloads/`: payload demo valido/non valido per `BANDO_CONCORSO`.
- `scenario_runner.py`: runner che esegue gli scenari contro i contratti pubblici GEMODO.

## Come si esegue

Verra' documentato in dettaglio in `specs/009-fondamenta-mock-test-qualita/quickstart.md`
(Scenario 3/4/5) man mano che i task implementativi della User Story 2 vengono completati.
In sintesi:

1. avviare l'ambiente locale (`infra/local/compose.yaml`, servizi `backend` e
   `documentale-mock` almeno);
2. eseguire `python mock-geban/scenario_runner.py --scenario E2E-001` (o l'id di uno degli
   scenari `E2E-001`..`E2E-006`) puntando `GEMODO_API_BASE_URL` al backend locale;
3. confrontare l'esito con `mock-geban/scenarios/expected-outcomes.yaml`.

## Regole

- Il mock usa solo contratti pubblici esposti da GEMODO, mai accesso diretto a builder o
  database interni (vedi `backend/app/quality/mock_contract_guard.py`).
- I payload usano solo dati demo marcati `DEMO`, mai dati reali o sensibili.
- Ogni scenario deve restare tracciabile a un requisito e a una spec owner nella matrice di
  copertura (`docs/quality-coverage-matrix.yaml`).
