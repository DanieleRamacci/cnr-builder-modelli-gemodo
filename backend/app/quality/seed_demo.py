"""SeedDemo validation: mandatory demo marker and sensitive-data guard (FR-010, FR-011).

Every demo seed must be explicitly marked as demo data and must never carry real or
sensitive data (spec 009, data-model.md ``SeedDemo`` validation rules). The seed
catalog as a whole must also include at least one publishable/usable model and at
least one unpublishable/invalid case, so mock GEBAN and tests can exercise both the
success and the functional-error path (FR-011).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.quality.errors import ContrattoNonValidoError, SeedSensibileError
from app.quality.manifest_loader import load_yaml
from app.quality.schemas import SeedDemo

MARCATURA_DEMO_RICHIESTA = "DEMO"


def validate_seed_demo(seed: SeedDemo) -> None:
    """Raise on the first violation found for a single seed entry."""

    if seed.dati_sensibili:
        raise SeedSensibileError(
            seed.id, "il seed e' marcato come contenente dati reali o sensibili (dati_sensibili=true)"
        )
    if seed.marcatura_demo.strip().upper() != MARCATURA_DEMO_RICHIESTA:
        raise ContrattoNonValidoError(
            seed.id,
            [f"marcatura_demo deve essere '{MARCATURA_DEMO_RICHIESTA}', trovato '{seed.marcatura_demo}'"],
        )


def load_seed_catalog(path: Path) -> tuple[list[SeedDemo], dict[str, Any]]:
    """Load ``infra/local/postgres/seed-demo-catalog.yaml``: (seeds, catalogo)."""

    data = load_yaml(path)
    if not isinstance(data, dict) or "seeds" not in data or "catalogo" not in data:
        raise ContrattoNonValidoError(
            str(path), ["il manifest deve avere le chiavi 'seeds' e 'catalogo'"]
        )
    seeds = [SeedDemo.model_validate(item) for item in (data["seeds"] or [])]
    catalogo = data["catalogo"] or {}
    return seeds, catalogo


def validate_seed_catalog(seeds: list[SeedDemo], catalogo: dict[str, Any]) -> None:
    """Validate every seed entry, then the FR-011 published/unpublishable coverage."""

    for seed in seeds:
        validate_seed_demo(seed)

    modelli = catalogo.get("modelli", [])
    pubblicati_utilizzabili = [m for m in modelli if m.get("utilizzabile_da_mock_geban") is True]
    non_pubblicabili = [m for m in modelli if m.get("utilizzabile_da_mock_geban") is False]

    violazioni: list[str] = []
    if not pubblicati_utilizzabili:
        violazioni.append("nessun modello pubblicato utilizzabile dal mock GEBAN (richiesto da FR-011)")
    if not non_pubblicabili:
        violazioni.append("nessun caso di modello non pubblicabile/non valido (richiesto da FR-011)")
    if violazioni:
        raise ContrattoNonValidoError("catalogo-seed-demo", violazioni)
