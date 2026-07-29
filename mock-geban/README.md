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

## Come si esegue oggi (dry run / piano scenario)

Le spec `001`/`004`/`005`/`006` non hanno ancora `tasks.md` proprio e quindi non
espongono endpoint HTTP reali (vedi `AGENTS.md`): `scenario_runner.py` e' oggi uno
**skeleton** che risolve il piano di uno scenario contro le sole operazioni pubbliche
ammesse (`backend/app/quality/mock_contract_guard.py`), senza eseguire chiamate di
rete.

```bash
cd backend && uv sync   # una tantum
uv run python ../mock-geban/scenario_runner.py --scenario E2E-001 --payload bando-concorso-valid.json
uv run python ../mock-geban/scenario_runner.py --scenario E2E-006
```

Stampa l'elenco ordinato delle operazioni pubbliche che lo scenario percorre (es. per
`E2E-001`: `catalogo_modelli` -> `campi_richiesti` -> `valida_payload` ->
`genera_documento` -> `stato_generazione`), utile per verificare che lo scenario sia
ben formato e non referenzi scorciatoie interne, senza dipendere da un backend GEMODO
in esecuzione.

## Come si esegue end-to-end (test automatici)

`backend/tests/e2e/test_mock_geban_valid_flow.py` e
`backend/tests/e2e/test_mock_geban_error_flows.py` eseguono gli scenari per intero
tramite `esegui_scenario(...)`, iniettando un client che implementa il protocollo
`ClienteGemodo` di `scenario_runner.py`. In assenza del backend reale, i test usano
`backend/tests/support/fake_gemodo_client.py`: uno stand-in in memoria che delega le
decisioni di autorizzazione alla logica reale
`backend/app/quality/integration_profile.py` (non la duplica). Quando le spec
`001`/`004`/`005`/`006` implementeranno gli endpoint reali, uno stesso `ClienteGemodo`
HTTP potra' sostituire il fake senza cambiare `scenario_runner.py` ne' gli scenari.

```bash
cd backend
uv run pytest tests/e2e -v
uv run pytest -m e2e -v
```

## Regole

- Il mock usa solo contratti pubblici esposti da GEMODO, mai accesso diretto a builder o
  database interni (vedi `backend/app/quality/mock_contract_guard.py`).
- I payload usano solo dati demo marcati `DEMO`, mai dati reali o sensibili.
- Ogni scenario deve restare tracciabile a un requisito e a una spec owner nella matrice di
  copertura (`docs/quality-coverage-matrix.yaml`, popolata dalla User Story 3).
- Gli esiti attesi per audit sono in `infra/local/audit-expectations.yaml`.
