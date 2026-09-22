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
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.core.settings import get_settings

REPO_ROOT = Path(__file__).resolve().parents[3]

# Registry of published OpenAPI contracts, keyed by the short id used in the doc URLs.
# Each spec adds its own entry here once it has a versioned OpenAPI contract
# (infra/openapi/README.md keeps the human-readable inventory in sync).
PUBLISHED_CONTRACTS: dict[str, Path] = {
    "configurazione-cataloghi": REPO_ROOT
    / "specs"
    / "010-configurazione-cataloghi-integrazioni"
    / "contracts"
    / "configurazione-cataloghi-api.openapi.yaml",
    "geban-catalog": REPO_ROOT
    / "specs"
    / "001-catalogo-contratto-geban"
    / "contracts"
    / "geban-catalog-api.openapi.yaml",
    "geban-discovery-endpoint": REPO_ROOT
    / "specs"
    / "010-configurazione-cataloghi-integrazioni"
    / "contracts"
    / "geban-discovery-endpoint.openapi.yaml",
    "builder-discovery": REPO_ROOT
    / "specs"
    / "010-configurazione-cataloghi-integrazioni"
    / "contracts"
    / "builder-discovery-api.openapi.yaml",
    "integrazioni": REPO_ROOT
    / "specs"
    / "010-configurazione-cataloghi-integrazioni"
    / "contracts"
    / "integrazioni-api.openapi.yaml",
    "builder-modelli": REPO_ROOT
    / "specs"
    / "002-builder-modelli"
    / "contracts"
    / "builder-modelli-api.openapi.yaml",
    "generazione-documenti": REPO_ROOT
    / "specs"
    / "004-generazione-documenti-pdf"
    / "contracts"
    / "generazione-documenti-api.openapi.yaml",
    "storage-documenti": REPO_ROOT
    / "specs"
    / "005-storage-idempotenza-consultazione"
    / "contracts"
    / "storage-documenti-api.openapi.yaml",
}

# Relative references keep their repository filename in the published contract.
PUBLISHED_CONTRACTS["geban-discovery-endpoint.openapi"] = PUBLISHED_CONTRACTS["geban-discovery-endpoint"]

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


@router.get("/docs/oauth2-redirect.html", include_in_schema=False)
def get_swagger_default_oauth2_redirect() -> HTMLResponse:
    return get_swagger_ui_oauth2_redirect_html()


# Cosa GEMODO espone a GEBAN, e cosa GEBAN deve esporre a GEMODO. L'elenco vive
# qui e non in una pagina scritta a mano perche' un contratto aggiunto sopra
# deve comparire nell'indice senza che nessuno se lo ricordi.
FLUSSO_GEBAN = [
    ("GET", "/api/v1/catalogo/modelli", "Cerca i modelli pubblicati per tipo documento, percorso, livello e lingua"),
    ("GET", "/api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti", "Il contratto dati della versione: quali campi inviare"),
    ("POST", "/api/v1/documenti/valida", "Verifica i dati senza produrre nulla"),
    ("POST", "/api/v1/documenti/genera", "Genera il documento; idempotente sulla coppia sistema + contesto esterno"),
    ("GET", "/api/v1/documenti/{riferimento}", "Stato e metadati di un documento gia' generato"),
    ("GET", "/api/v1/documenti/{riferimento}/download", "Scarica il PDF, se stato e autorizzazione lo consentono"),
]


def _voci_indice() -> list[tuple[str, str]]:
    return sorted((spec_id, path.name) for spec_id, path in PUBLISHED_CONTRACTS.items()
                  if not spec_id.endswith(".openapi"))


@router.get("/docs", include_in_schema=False)
def get_docs_index() -> HTMLResponse:
    """Indice unico della documentazione API: contratti, esploratori e flusso GEBAN."""
    contratti = "\n".join(
        f"""<tr><td><code>{spec_id}</code><div class="file">{nome}</div></td>
        <td><a href="/docs/{spec_id}">Swagger UI</a></td>
        <td><a href="/redoc/{spec_id}">ReDoc</a></td>
        <td><a href="/openapi/{spec_id}.yaml">YAML</a></td></tr>"""
        for spec_id, nome in _voci_indice()
    )
    flusso = "\n".join(
        f"""<tr><td><span class="m {metodo.lower()}">{metodo}</span></td>
        <td><code>{rotta}</code></td><td>{descrizione}</td></tr>"""
        for metodo, rotta, descrizione in FLUSSO_GEBAN
    )
    return HTMLResponse(f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMODO - Documentazione API</title>
<style>
 :root {{ --blu:#0066cc; --ink:#17324d; --grigio:#5a6772; --bordo:#e3e7eb; }}
 body {{ margin:0; font-family:system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--ink); }}
 header {{ background:var(--ink); color:#fff; padding:20px 28px; }}
 header h1 {{ margin:0; font-size:22px; }}
 header p {{ margin:6px 0 0; color:rgba(255,255,255,.75); font-size:14px; }}
 main {{ max-width:960px; margin:0 auto; padding:24px 20px 48px; }}
 h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.6px; color:var(--grigio); margin-top:32px; }}
 p.nota {{ color:var(--grigio); font-size:14px; line-height:1.55; }}
 table {{ width:100%; border-collapse:collapse; font-size:14px; }}
 th {{ text-align:left; font-size:12px; text-transform:uppercase; letter-spacing:.5px;
       color:var(--grigio); border-bottom:2px solid var(--ink); padding:8px 10px; }}
 td {{ border-bottom:1px solid var(--bordo); padding:10px; vertical-align:top; }}
 code {{ font-family:ui-monospace,"Roboto Mono",monospace; font-size:12.5px; }}
 .file {{ color:var(--grigio); font-size:11.5px; }}
 a {{ color:var(--blu); }}
 .m {{ display:inline-block; min-width:48px; padding:1px 7px; border-radius:3px;
       font-size:11px; font-weight:700; color:#fff; background:var(--grigio); }}
 .m.get {{ background:#1b7a34; }} .m.post {{ background:var(--blu); }}
 @media (prefers-color-scheme: dark) {{
   body {{ background:#12181f; color:#e8edf2; }}
   td {{ border-color:#2a343f; }} .file, p.nota, th {{ color:#9aa5af; }}
   a {{ color:#6fb3ff; }} th {{ border-bottom-color:#6fb3ff; }}
 }}
</style></head><body>
<header>
  <h1>GEMODO &middot; Documentazione API</h1>
  <p>Contratti OpenAPI versionati, serviti esattamente come sono in repository.</p>
</header>
<main>
  <h2>Il flusso di GEBAN</h2>
  <p class="nota">Le rotte che un sistema esterno usa per arrivare dal catalogo al
  documento. Tutte richiedono un token Bearer di Keycloak. Il contratto completo,
  con schemi ed esempi, e' <a href="/docs/geban-catalog">geban-catalog</a> per le
  prime quattro e <a href="/docs/storage-documenti">storage-documenti</a> per le
  due di consultazione.</p>
  <table><thead><tr><th>Metodo</th><th>Rotta</th><th>A cosa serve</th></tr></thead>
  <tbody>{flusso}</tbody></table>
  <p class="nota">Nella direzione opposta, il sistema esterno deve esporre a GEMODO
  il proprio endpoint di discovery, nella forma descritta da
  <a href="/docs/geban-discovery-endpoint">geban-discovery-endpoint</a>.</p>

  <h2>Tutti i contratti pubblicati</h2>
  <table><thead><tr><th>Contratto</th><th colspan="3">Consultazione</th></tr></thead>
  <tbody>{contratti}</tbody></table>

  <h2>Altro</h2>
  <p class="nota">
    <a href="/docs/runtime">Swagger dell'applicazione viva</a> mostra lo schema
    generato a runtime, utile per provare le chiamate ma non e' il contratto.
    <a href="/redoc">ReDoc dell'applicazione viva</a>.
  </p>
</main></body></html>""")


@router.get("/docs/{spec_id}", include_in_schema=False)
def get_spec_swagger_ui(spec_id: str) -> HTMLResponse:
    _resolve(spec_id)
    settings = get_settings()
    return get_swagger_ui_html(
        openapi_url=f"/openapi/{spec_id}.yaml",
        title=f"GEMODO - {spec_id} - Swagger UI",
        oauth2_redirect_url=f"/docs/{spec_id}/oauth2-redirect",
        init_oauth={
            "clientId": settings.keycloak_frontend_client_id,
            "usePkceWithAuthorizationCodeGrant": True,
            "scopes": "openid profile email",
        },
    )


@router.get("/docs/{spec_id}/oauth2-redirect", include_in_schema=False)
def get_spec_swagger_oauth2_redirect(spec_id: str) -> HTMLResponse:
    _resolve(spec_id)
    return get_swagger_ui_oauth2_redirect_html()


@router.get("/redoc/{spec_id}", include_in_schema=False)
def get_spec_redoc(spec_id: str) -> HTMLResponse:
    _resolve(spec_id)
    return get_redoc_html(openapi_url=f"/openapi/{spec_id}.yaml", title=f"GEMODO - {spec_id} - ReDoc")
