# PostgreSQL locale

Servizio `postgres` dell'ambiente locale GEMODO (`infra/local/compose.yaml`).

- Immagine `postgres:16-alpine`, porta `5432`, database/utente/password configurabili via
  `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (default `gemodo`/`gemodo`/`gemodo`).
- Le migrations sono gestite con Alembic in `backend/alembic/` (vedi
  `backend/alembic/README.md` per la ownership dello schema iniziale).
- Il seed demo catalogo (`infra/local/postgres/seed-demo-catalog.yaml`) contiene solo dati
  marcati `DEMO`, ripetibili e privi di dati reali o sensibili (FR-010, FR-011).

## Healthcheck

`pg_isready -U ${POSTGRES_USER}`, usato sia da Docker Compose sia dalla verifica ambiente
(`VerificaAmbiente`) per distinguere un database non disponibile (prerequisito mancante) da
un errore applicativo nelle migrations o nel seed.
