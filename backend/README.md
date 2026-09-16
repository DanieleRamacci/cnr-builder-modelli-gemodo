# GEMODO Backend

Servizio FastAPI di Gestione Modelli e Generazione Documenti per GEBAN. Per
contesto di progetto, stato delle feature e deploy, vedi il `README.md` alla
radice del repository.

## Avvio locale

```bash
cd backend
uv sync

uv run gemodo-quality verifica-ambiente      # healthcheck reali dell'ambiente locale
uv run pytest                                 # suite di test reale
uv run uvicorn app.main:app --reload          # backend su http://localhost:8000
# http://localhost:8000/docs/geban-catalog    -> Swagger UI del contratto 001
# http://localhost:8000/redoc/geban-catalog   -> ReDoc dello stesso contratto
```
