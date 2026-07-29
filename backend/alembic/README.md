# Migrations - ownership dello schema

Le migrations vivono qui (`backend/alembic/`) e sono applicate con Alembic contro
PostgreSQL. La stringa di connessione viene letta da `DATABASE_URL` (mai hardcodata),
vedi `infra/local/compose.yaml` e `infra/local/postgres/README.md` per il default
locale.

## `0001_initial_schema` - baseline provvisoria

FR-009 richiede che lo schema iniziale copra tipi, categorie, modelli, versioni, campi,
sezioni, generazioni documento e audit. La migration `0001_initial_schema.py` crea una
**baseline provvisoria** minima per queste entita':

| Tabella | Entita' | Spec owner |
|---|---|---|
| `tipo_documento` | Tipo documento (es. `BANDO_CONCORSO`) | `001-catalogo-contratto-geban` |
| `categoria_documento` | Categoria per tipo documento | `002-builder-modelli` |
| `tipologia_bando` | Tipologia SOL (TDPNRR, CD, DIR, TD, CP, RS, CATP, TI, SDIP, MOB) | `001-catalogo-contratto-geban` |
| `modello_documento` | Modello documentale | `002-builder-modelli` |
| `modello_versione` | Versione di un modello, con struttura documentale controllata | `002-builder-modelli`, `003-sezioni-placeholder-versionamento` |
| `campo_modello` | Campo/placeholder richiesto da una versione modello | `003-sezioni-placeholder-versionamento` |
| `sezione_modello` | Sezione versionata di contenuto strutturato | `003-sezioni-placeholder-versionamento` |
| `generazione_documento` | Generazione documento, con chiave di idempotenza | `004-generazione-documenti-pdf`, `005-storage-idempotenza-consultazione` |
| `evento_audit` | Evento auditabile | `006-sicurezza-autorizzazioni-audit` |

**Questa e' solo la baseline**, non il contratto dati definitivo: le colonne restano
volutamente minime (codice, nome, stato, riferimenti, timestamp). Diverse decisioni da
cui dipende la forma finale sono ancora aperte (vedi
`specs/009-fondamenta-mock-test-qualita/spec.md`, sezione "Decision Ownership", e
`docs/decision-register.yaml` una volta popolato dalla User Story 3): stati definitivi
di pubblicazione, formato dei campi complessi, profilo GEBAN versionato, mapping
placeholder/campi. Ogni spec proprietaria estende questa baseline con le proprie
migrations quando i rispettivi `plan.md`/`tasks.md` vengono generati.

`generazione_documento` ha un vincolo unique su
`(sistema_richiedente, external_context_id, modello_versione_id, tipo_output)`: e' la
chiave di idempotenza richiesta dal principio costituzionale IV (una richiesta ripetuta
con la stessa chiave e gli stessi dati deve restituire la generazione esistente).

## Comandi

```bash
cd backend
DATABASE_URL=postgresql+psycopg://gemodo:gemodo@localhost:5432/gemodo uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://gemodo:gemodo@localhost:5432/gemodo uv run alembic downgrade base
```

## Regola per nuove migrations

- Ogni migration deve restare tracciabile a una spec owner (vedi tabella sopra o quella
  aggiunta dalla nuova migration).
- Nessuna migration puo' introdurre dati reali: i dati demo restano seed separati
  (`infra/local/postgres/seed-demo-catalog.yaml`), mai valori hardcodati nella
  migration stessa.
- Le migrations sono lineari (una sola `head`); non riscrivere migrations gia'
  applicate altrove, crearne una nuova.
