"""FastAPI application entrypoint for the GEMODO backend.

This module wires the minimal application shell required by feature
``009-fondamenta-mock-test-qualita``: an ASGI app with interactive API
documentation (Swagger UI / ReDoc) generated from the same OpenAPI source,
and a health endpoint used by the local environment verification.

Domain routers (catalog, builder, generation, storage, security) belong to
their own spec-owned features and are mounted here only once those features
implement them.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.catalog.api import router as catalog_router
from app.common.errors import install_error_handlers
from app.quality.openapi_docs import router as openapi_docs_router
from app.validation.api import router as validation_router

app = FastAPI(
    title="GEMODO - Gestione Modelli e Generazione Documenti",
    description=(
        "Servizio di gestione modelli documentali e generazione documenti per GEBAN. "
        "Documentazione interattiva generata dalla stessa sorgente OpenAPI (Swagger UI, ReDoc)."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Swagger UI / ReDoc per ogni contratto OpenAPI versionato di spec (GET /docs/{spec_id},
# GET /redoc/{spec_id}), generati dalla stessa sorgente committata (FR-041).
app.include_router(openapi_docs_router)
app.include_router(catalog_router)
app.include_router(validation_router)
install_error_handlers(app)


@app.get("/health", tags=["quality"])
def health() -> dict[str, str]:
    """Liveness endpoint used by the local environment verification (VerificaAmbiente)."""

    return {"status": "ok"}
