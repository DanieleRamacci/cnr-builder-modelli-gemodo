FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY README.md /app/README.md
COPY backend/ /app/backend/
COPY specs/ /app/specs/
COPY infra/ /app/infra/

WORKDIR /app/backend

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["sh", "-c", "until pg_isready -h postgres -p 5432; do sleep 2; done; uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
