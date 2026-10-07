"""La documentazione di riferimento dice cio' che il codice fa (verifica del 2026-10-07).

`docs/` e' letta da integratori, utenti e agenti come fonte: una tabella di rotte
o un esempio JSON che non corrisponde al codice e' un errore che nessuno vede
finche' non costa. Qui le parti verificabili meccanicamente sono confrontate
con il codice; se un test fallisce, si corregge la pagina nello stesso lavoro
(o il codice, se e' la pagina ad avere ragione).
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import jsonschema
import yaml
from fastapi.routing import APIRoute

from app.builder.service import TRANSIZIONI_VALIDE
from app.discovery.schemas import VERSIONE_CONTRATTO_DISCOVERY, CatalogoDiscovery, MappaDiscovery
from app.main import app
from app.quality.openapi_docs import PUBLISHED_CONTRACTS

REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "docs"
SCHEMA_080 = REPO / "specs" / "014-articolazioni-bando" / "contracts" / "discovery-0.8.0.schema.json"


def _testo(nome: str) -> str:
    return (DOCS / nome).read_text(encoding="utf-8")


def _norm(percorso: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", percorso)


def _rotte_app() -> dict[tuple[str, str], APIRoute]:
    """Metodo e percorso di ogni rotta, anche quelle escluse dallo schema runtime."""

    def cammina(rotte, prefisso=""):
        for rotta in rotte:
            if type(rotta).__name__ == "_IncludedRouter":
                yield from cammina(
                    rotta.original_router.routes, prefisso + (getattr(rotta.include_context, "prefix", "") or "")
                )
            elif isinstance(rotta, APIRoute):
                yield prefisso + rotta.path, rotta

    return {
        (metodo, percorso): rotta
        for percorso, rotta in cammina(app.routes)
        for metodo in rotta.methods - {"HEAD", "OPTIONS"}
    }


def _contratti() -> dict[str, Path]:
    return {codice: p for codice, p in PUBLISHED_CONTRACTS.items() if not codice.endswith(".openapi")}


def _operazioni_contratto() -> list[tuple[str, str, str]]:
    operazioni = []
    for codice, percorso in _contratti().items():
        documento = yaml.safe_load(percorso.read_text(encoding="utf-8"))
        for rotta, metodi in (documento.get("paths") or {}).items():
            for metodo in metodi:
                if metodo in {"get", "post", "put", "patch", "delete"}:
                    operazioni.append((metodo.upper(), _norm(rotta), codice))
    return operazioni


def _righe_rotte(testo: str) -> dict[tuple[str, str], list[str]]:
    """Le righe `| METODO | `percorso` | permesso | contratto |` del riferimento API."""
    righe = {}
    for metodo, percorso, resto in re.findall(
        r"^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \|(.*)$", testo, flags=re.M
    ):
        celle = [c.strip() for c in resto.strip().strip("|").split("|")]
        righe[(metodo, percorso)] = celle
    return righe


def test_il_riferimento_api_elenca_esattamente_le_rotte_del_backend():
    # I nomi dei parametri possono essere piu' leggibili nella pagina: conta la forma.
    documentate = {(m, _norm(p)) for m, p in _righe_rotte(_testo("riferimento-api.md"))}
    reali = {(m, _norm(p)) for m, p in _rotte_app()}
    assert sorted(reali - documentate) == [], "rotte del backend assenti da docs/riferimento-api.md"
    assert sorted(documentate - reali) == [], "rotte in docs/riferimento-api.md che il backend non ha"


def test_il_riferimento_api_indica_il_contratto_giusto_per_ogni_rotta():
    operazioni = _operazioni_contratto()
    for (metodo, percorso), celle in _righe_rotte(_testo("riferimento-api.md")).items():
        if not percorso.startswith("/api/"):
            continue
        attesi = {c for m, p, c in operazioni if m == metodo and _norm(percorso).endswith(p)}
        dichiarati = set(re.findall(r"`([a-z0-9-]+)`", celle[-1]))
        assert dichiarati == attesi, f"{metodo} {percorso}: contratti {dichiarati}, attesi {attesi or 'nessuno'}"
        if not attesi:
            assert "nessuno" in celle[-1], f"{metodo} {percorso}: senza contratto va dichiarato 'nessuno'"


def test_il_riferimento_api_elenca_i_contratti_pubblicati():
    tabella = _testo("riferimento-api.md").split("## Contratti OpenAPI", 1)[1].split("\n## ", 1)[0]
    elencati = set(re.findall(r"^\| `([a-z0-9-]+)` \|", tabella, flags=re.M))
    assert elencati == set(_contratti())


def test_i_codici_di_errore_documentati_esistono_nel_backend():
    sorgente = "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "backend" / "app").rglob("*.py"))
    sezione = _testo("riferimento-api.md").split("## Codici di errore", 1)[1].split("## Lacune note", 1)[0]
    for pagina, testo in {"riferimento-api.md": sezione, "integrazione-sistema-esterno.md": _testo(
        "integrazione-sistema-esterno.md"
    ).split("## Errori ricorrenti", 1)[1]}.items():
        codici = set(re.findall(r"^\| `([A-Z][A-Z_]+)`(?:, `([A-Z][A-Z_]+)`)? \|", testo, flags=re.M))
        for coppia in codici:
            for codice in filter(None, coppia):
                assert f'"{codice}"' in sorgente or f"{codice} =" in sorgente, f"{pagina}: {codice} non e' nel backend"


def _esempi_discovery(testo: str) -> list[dict]:
    blocchi = re.findall(r"```json\n(.*?)\n```", testo, flags=re.S)
    return [json.loads(b) for b in blocchi if '"validita"' in b and "<" not in b]


def test_gli_esempi_di_discovery_sono_validi_per_il_codice_e_per_lo_schema_080():
    schema = json.loads(SCHEMA_080.read_text(encoding="utf-8"))
    validatore = jsonschema.Draft202012Validator(schema)
    esempi = _esempi_discovery(_testo("contratto-dati.md"))
    assert esempi, "docs/contratto-dati.md deve contenere esempi di discovery completi"
    assert any(len(esempio) > 1 for esempio in esempi), "serve un esempio con piu' tipi documento nella stessa risposta"
    for esempio in esempi:
        MappaDiscovery(cataloghi={
            codice: CatalogoDiscovery(codice_tipo_documento=codice, **corpo) for codice, corpo in esempio.items()
        })
        assert list(validatore.iter_errors(esempio)) == []


def test_la_versione_attiva_del_contratto_e_quella_del_codice():
    assert f"| **{VERSIONE_CONTRATTO_DISCOVERY}** | **Attiva.**" in _testo("contratto-dati.md")


def test_gli_stati_della_versione_sono_quelli_del_ciclo_di_vita():
    stati = set(TRANSIZIONI_VALIDE) | {s for arrivi in TRANSIZIONI_VALIDE.values() for s in arrivi}
    diagramma = _testo("architettura.md").split("### Ciclo di vita di una versione", 1)[1].split("\n## ", 1)[0]
    assert set(re.findall(r"\b[A-Z_]{5,}\b", diagramma)) >= stati


def test_il_profilo_di_accesso_geban_e_quello_della_migrazione():
    spec = importlib.util.spec_from_file_location(
        "m0028", REPO / "backend" / "alembic" / "versions" / "0028_profilo_accesso_integrazione.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    righe = re.findall(r"^\| `(ROLE_\w+)` \| (.+) \|$", _testo("casi/geban.md"), flags=re.M)
    documentato = {ruolo: set(re.findall(r"`(\w+)`", permessi)) for ruolo, permessi in righe}
    assert documentato == {ruolo: set(permessi) for ruolo, permessi in modulo._GEBAN_RUOLI.items()}
    assert all(f"`{client}`" in _testo("casi/geban.md") for client in modulo._GEBAN_CLIENT)
