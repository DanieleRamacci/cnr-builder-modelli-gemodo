"""Publishes versioned OpenAPI contracts, unmodified, as Swagger UI / ReDoc.

Constitution principle II (Contract-First Integration) and spec 009 FR-041 require
Swagger UI and ReDoc in local/test environments to be generated from the *same* OpenAPI
source as the versioned contract, never a hand-maintained copy or a runtime schema that
can drift from it. This module serves each spec-owned contract file exactly as
committed (``GET /openapi/{spec_id}.yaml``) and renders Swagger UI / ReDoc against that
same URL, so the two can never diverge (see ``infra/openapi/README.md``).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, PlainTextResponse

REPO_ROOT = Path(__file__).resolve().parents[3]

# Registry of published OpenAPI contracts, keyed by the short id used in the doc URLs.
# Each spec adds its own entry here once it has a versioned OpenAPI contract
# (infra/openapi/README.md keeps the human-readable inventory in sync).
PUBLISHED_CONTRACTS: dict[str, Path] = {
    "geban-catalog": REPO_ROOT
    / "specs"
    / "001-catalogo-contratto-geban"
    / "contracts"
    / "geban-catalog-api.openapi.yaml",
}

router = APIRouter(tags=["quality"])


def _resolve(spec_id: str) -> Path:
    path = PUBLISHED_CONTRACTS.get(spec_id)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail=f"contratto OpenAPI '{spec_id}' non pubblicato")
    return path


@router.get("/openapi/{spec_id}.yaml", include_in_schema=False)
def get_openapi_source(spec_id: str) -> PlainTextResponse:
    path = _resolve(spec_id)
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="application/yaml")


@router.get("/docs/{spec_id}", include_in_schema=False)
def get_spec_swagger_ui(spec_id: str) -> HTMLResponse:
    _resolve(spec_id)
    return get_swagger_ui_html(
        openapi_url=f"/openapi/{spec_id}.yaml", title=f"GEMODO - {spec_id} - Swagger UI"
    )


@router.get("/redoc/{spec_id}", include_in_schema=False)
def get_spec_redoc(spec_id: str) -> HTMLResponse:
    _resolve(spec_id)
    return get_redoc_html(openapi_url=f"/openapi/{spec_id}.yaml", title=f"GEMODO - {spec_id} - ReDoc")
