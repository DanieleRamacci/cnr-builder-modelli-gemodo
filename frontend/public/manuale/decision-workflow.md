# Workflow Di Aggiornamento Delle Decisioni Aperte

Questa pagina descrive come aggiornare `docs/decision-register.yaml` e come propagare
un cambio di stato alle spec interessate (spec 009, User Story 3, FR-006, FR-007,
FR-017, FR-018).

## Dove vive una decisione

- Fonte primaria: `specs/009-fondamenta-mock-test-qualita/spec.md`, sezione
  "Decision Ownership" (transcritta dalla proposta §17).
- Registro operativo: `docs/decision-register.yaml`, una riga per decisione, forma
  `DecisioneAperta` (`backend/app/quality/schemas.py`).
- Regole di validazione: `backend/app/quality/decision.py`.
- Gate di readiness: `backend/app/quality/readiness_gate.py`.

## Stati e transizioni ammesse

```text
APERTA -> ASSUNTA_PROVVISORIA
APERTA -> CONFERMATA
ASSUNTA_PROVVISORIA -> CONFERMATA
ASSUNTA_PROVVISORIA -> SOSPESA
SOSPESA -> ASSUNTA_PROVVISORIA
SOSPESA -> CONFERMATA
```

`backend/app/quality/decision.py:validate_transizione` rifiuta ogni altra transizione
(es. non si puo' tornare da `CONFERMATA` ad `APERTA`: se una decisione confermata va
rivista, si apre una nuova decisione che la sostituisce e la referenzia, non si
riporta indietro lo stato).

## Regola sull'assunzione provvisoria

Ogni decisione non `CONFERMATA` **deve** avere `assunzione_provvisoria` valorizzata,
anche quando non esiste ancora una vera assunzione: in quel caso il campo riporta
esplicitamente "nessuna assunzione proposta" e il motivo. Questo e' cio' che
distingue una decisione tracciata da un'assunzione silenziosa (FR-007): il campo deve
sempre essere leggibile, mai assente.

## Passi per aggiornare una decisione

1. **Identificare la riga** in `docs/decision-register.yaml` tramite `id` (o crearne
   una nuova se la decisione non esiste ancora - vedi convenzione id sotto).
2. **Verificare la transizione** e' ammessa (vedi sopra). In caso di dubbio eseguire:

   ```bash
   cd backend
   uv run python -c "
   from app.quality.decision import validate_transizione
   from app.quality.schemas import StatoDecisione
   validate_transizione(StatoDecisione.ASSUNTA_PROVVISORIA, StatoDecisione.CONFERMATA)
   "
   ```

3. **Aggiornare** `stato`, `assunzione_provvisoria` (se resta non confermata),
   `impatto`, `fase_bloccante` e `data_ultima_revisione` (data ISO, oggi).
4. **Se lo stato diventa `CONFERMATA`**: aggiornare *tutte* le spec elencate in
   `spec_interessate`, non solo `owner_spec` (sezione Clarifications/Decision Ownership
   di ciascuna spec impattata). Una decisione confermata ma non propagata resta un
   rischio di divergenza silenziosa quanto una decisione mai chiusa.
5. **Validare il registro**:

   ```bash
   cd backend
   uv run pytest tests/contract/test_open_decisions_contract.py -v
   ```

6. **Se la decisione blocca una fase**, verificare il gate prima di avviare quella
   fase per la spec impattata:

   ```bash
   cd backend
   uv run python -c "
   from pathlib import Path
   from app.quality.readiness_gate import load_decision_register, valuta_readiness
   from app.quality.schemas import FaseBloccante
   decisioni = load_decision_register(Path('../docs/decision-register.yaml'))
   esito = valuta_readiness(decisioni, fase_richiesta=FaseBloccante.TASKS, spec_target='specs/001-catalogo-contratto-geban')
   print('pronto:', esito.pronto, [d.id for d in esito.blocchi])
   "
   ```

   Se `esito.pronto` e' `False`, le decisioni elencate vanno chiuse (`CONFERMATA`) o
   sospese esplicitamente (`SOSPESA` con `impatto` che ne descrive il rischio residuo)
   prima di generare i task implementativi della parte impattata (FR-018).

## Convenzione id

- Decisioni di sicurezza gia' numerate nella spec 006: riusare l'id esistente
  (`SEC-006-NNN`).
- Tutte le altre: `DEC-<owner-numerico-o-codice>-<SLUG-BREVE>`, es.
  `DEC-001-PROFILO-GEBAN`. Non riusare un id gia' assegnato a un'altra decisione.

## Aggiungere una decisione nuova

Una decisione nuova (non prevista dalla proposta §17) va aggiunta con lo stesso
schema, `stato: APERTA` (o `ASSUNTA_PROVVISORIA` se esiste gia' un'ipotesi di lavoro),
e referenziata da `docs/quality-coverage-matrix.yaml` se impatta uno scenario minimo.

## Relazione con la matrice di copertura

`docs/quality-coverage-matrix.yaml` referenzia le decisioni tramite `contract_ref`
(es. `docs/decision-register.yaml#DEC-001-BANDO-MULTIPLO`). Quando una decisione
cambia stato in modo da sbloccare un requisito prima `DA_COPRIRE`, aggiornare anche la
riga corrispondente della matrice, non solo il registro decisioni.
