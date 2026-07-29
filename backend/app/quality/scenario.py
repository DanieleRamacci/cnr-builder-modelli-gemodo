"""ScenarioEndToEnd loading, parsing and validation (spec 009, User Story 2).

``mock-geban/scenarios/*.yaml`` uses the public, English field names defined by
``specs/009-fondamenta-mock-test-qualita/contracts/mock-geban-scenarios.yaml`` (id,
name, type, required_contracts, expected_outcome, ...). This module translates that
manifest vocabulary into the internal :class:`~app.quality.schemas.ScenarioEndToEnd`
domain model and validates both per-scenario invariants (data-model.md) and the local
manifest's fidelity to the versioned contract it must mirror (FR-013).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.quality.errors import ContrattoNonValidoError
from app.quality.manifest_loader import load_manifest
from app.quality.schemas import PrioritaScenario, ScenarioEndToEnd, TipoScenario

# FR-013: gli scenari minimi devono coprire almeno questi sei tipi.
TIPI_MINIMI_RICHIESTI: set[TipoScenario] = {
    TipoScenario.VALIDO,
    TipoScenario.ERRORE_VALIDAZIONE,
    TipoScenario.IDEMPOTENZA,
    TipoScenario.CONFLITTO,
    TipoScenario.FALLIMENTO,
    TipoScenario.AUTORIZZAZIONE,
}

# Campi del contratto che il manifest locale non puo' far divergere (vedi
# compare_manifest_to_contract). Il manifest locale PUO' aggiungere campi extra
# (priorita, requisiti_coperti, ...) non presenti nel contratto.
CAMPI_CONTRATTUALI = ("name", "type", "required_contracts", "expected_outcome")


def _parse_scenario(raw: dict[str, Any]) -> ScenarioEndToEnd:
    return ScenarioEndToEnd(
        id=raw["id"],
        nome=raw["name"],
        priorita=PrioritaScenario(raw.get("priorita", "P1")),
        tipo=TipoScenario(raw["type"]),
        spec_coinvolte=raw.get("spec_coinvolte", []),
        requisiti_coperti=raw.get("requisiti_coperti", []),
        contratti_coinvolti=raw.get("required_contracts", []),
        expected_outcome=raw.get("expected_outcome", []),
    )


def load_scenario_manifest(path: Path) -> dict[str, Any]:
    """Load a scenario manifest (e.g. ``mock-geban/scenarios/minimum-e2e.yaml``)."""

    data = load_manifest(path)
    if "scenarios" not in data:
        raise ContrattoNonValidoError(str(path), ["il manifest deve avere la chiave 'scenarios'"])
    return data


def parse_scenarios(manifest: dict[str, Any]) -> list[ScenarioEndToEnd]:
    return [_parse_scenario(item) for item in manifest["scenarios"]]


def validate_scenario(scenario: ScenarioEndToEnd) -> None:
    """Per-scenario invariants (data-model.md ``ScenarioEndToEnd`` validation)."""

    violazioni: list[str] = []
    if not scenario.contratti_coinvolti:
        violazioni.append("nessun contratto pubblico referenziato (required_contracts vuoto)")
    if not scenario.requisiti_coperti:
        violazioni.append("nessun requisito/user story collegato (requisiti_coperti vuoto)")
    if not scenario.expected_outcome:
        violazioni.append("nessun esito atteso dichiarato (expected_outcome vuoto)")
    if violazioni:
        raise ContrattoNonValidoError(scenario.id, violazioni)


def validate_minimum_coverage(scenarios: list[ScenarioEndToEnd]) -> None:
    """FR-013: i sei tipi di scenario minimi devono essere tutti presenti."""

    tipi_presenti = {s.tipo for s in scenarios}
    mancanti = TIPI_MINIMI_RICHIESTI - tipi_presenti
    if mancanti:
        raise ContrattoNonValidoError(
            "scenari-minimi",
            [f"tipi di scenario mancanti: {', '.join(sorted(t.value for t in mancanti))}"],
        )


def compare_manifest_to_contract(manifest: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    """Return every way the local manifest drifts from the versioned contract.

    Every scenario declared in the contract must be present in the manifest with the
    same ``name``, ``type``, ``required_contracts`` and ``expected_outcome``. The
    manifest may add extra scenarios or extra fields, but must not diverge on the
    fields the contract itself defines.
    """

    violazioni: list[str] = []
    manifest_by_id = {item["id"]: item for item in manifest.get("scenarios", [])}

    for contract_scenario in contract.get("scenarios", []):
        scenario_id = contract_scenario["id"]
        manifest_scenario = manifest_by_id.get(scenario_id)
        if manifest_scenario is None:
            violazioni.append(f"scenario {scenario_id} presente nel contratto ma assente dal manifest locale")
            continue
        for campo in CAMPI_CONTRATTUALI:
            if manifest_scenario.get(campo) != contract_scenario.get(campo):
                violazioni.append(
                    f"scenario {scenario_id}: campo '{campo}' diverge dal contratto "
                    f"(manifest={manifest_scenario.get(campo)!r}, contratto={contract_scenario.get(campo)!r})"
                )

    return violazioni
