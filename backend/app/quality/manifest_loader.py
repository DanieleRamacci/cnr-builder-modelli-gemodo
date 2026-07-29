"""YAML manifest loading and generic, contract-driven structural validation.

The quality-readiness contract
(``specs/009-fondamenta-mock-test-qualita/contracts/quality-readiness-contract.yaml``)
declares, for every top-level section, which fields are required and which rules
apply. Rather than hard-coding those sections/fields in Python (which would silently
drift from the versioned contract), this module reads the contract itself and
validates an arbitrary manifest dict against it. This keeps the contract file the
single source of truth, per the constitution's Contract-First Integration principle.

Only rules that are mechanically checkable from their text are actually evaluated
(currently "<field> must be true|false"); everything else is recorded as an
*unchecked* (advisory) rule so callers can see which invariants are enforced in code
versus which remain process/documentation obligations. This module never claims to
have verified something it cannot mechanically check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.quality.errors import ContrattoNonValidoError


def load_yaml(path: Path) -> Any:
    """Read and parse a YAML file, raising ContrattoNonValidoError on failure."""

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContrattoNonValidoError(str(path), [f"file non leggibile: {exc}"]) from exc
    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ContrattoNonValidoError(str(path), [f"YAML non valido: {exc}"]) from exc


def load_contract(path: Path) -> dict[str, Any]:
    """Load a versioned contract file (any ``specs/*/contracts/*.yaml``).

    A contract file is recognised generically by declaring ``contract`` and
    ``version`` keys, the convention shared by every contract under
    ``specs/009-fondamenta-mock-test-qualita/contracts/``. Section-specific shapes
    (for example ``required_sections`` on the quality-readiness contract) are
    validated by dedicated functions such as :func:`validate_manifest_against_contract`.
    """

    data = load_yaml(path)
    if not isinstance(data, dict) or "contract" not in data or "version" not in data:
        raise ContrattoNonValidoError(
            str(path), ["il file non e' un contratto valido (mancano 'contract' e/o 'version')"]
        )
    return data


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a manifest that will be validated against a contract."""

    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ContrattoNonValidoError(str(path), ["il manifest deve essere una mappa YAML"])
    return data


@dataclass
class RuleEvaluation:
    """Outcome of evaluating one contract rule against a manifest section."""

    rule: str
    section: str
    checked: bool
    passed: bool
    detail: str | None = None


@dataclass
class ContractValidationResult:
    violations: list[str] = field(default_factory=list)
    rule_evaluations: list[RuleEvaluation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.violations

    def raise_if_invalid(self, contract_name: str) -> None:
        if not self.is_valid:
            raise ContrattoNonValidoError(contract_name, self.violations)

    def checked_rules(self) -> list[RuleEvaluation]:
        return [r for r in self.rule_evaluations if r.checked]


_MUST_BE_BOOL_RE = re.compile(r"^(?P<field>[a-zA-Z0-9_]+) must be (?P<value>true|false)$")


def _check_boolean_rule(rule: str, items: list[dict[str, Any]]) -> tuple[bool, str | None] | None:
    """Evaluate a "<field> must be true|false" rule against every item; None if the
    rule text does not match this mechanically-checkable pattern."""

    match = _MUST_BE_BOOL_RE.match(rule.strip())
    if not match:
        return None
    field_name = match.group("field")
    expected = match.group("value") == "true"
    failures: list[str] = []
    for idx, item in enumerate(items):
        if field_name not in item:
            continue  # presence is covered separately by the required-fields check
        actual = item[field_name]
        if actual is not expected:
            label = item.get("id", item.get("system_code", item.get("codice", f"#{idx}")))
            failures.append(f"{label}.{field_name} = {actual!r} (atteso {expected!r})")
    return (not failures, "; ".join(failures) if failures else None)


def _section_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def validate_manifest_against_contract(
    manifest: dict[str, Any], contract: dict[str, Any]
) -> ContractValidationResult:
    """Validate a manifest dict against a contract dict of the declared shape.

    A section's value may be a single mapping (e.g. ``environment``) or a list of
    mappings (e.g. ``seed_demo``); both are validated field-by-field against the
    contract's ``fields`` list for that section. The ``contract`` argument must be a
    ``required_sections``-shaped contract (currently only the quality-readiness
    contract has this shape); other contract files use their own dedicated
    validation.
    """

    if "required_sections" not in contract:
        raise ContrattoNonValidoError(
            contract.get("contract", "<sconosciuto>"),
            ["il contratto non definisce 'required_sections' e non puo' essere usato con questo validatore"],
        )

    result = ContractValidationResult()
    required_sections = contract["required_sections"]

    for section_name, section_def in required_sections.items():
        required = bool(section_def.get("required", False))
        if section_name not in manifest or manifest[section_name] is None:
            if required:
                result.violations.append(f"sezione mancante: {section_name}")
            continue

        raw_value = manifest[section_name]
        items = _section_items(raw_value)
        if raw_value not in (None, [], {}) and not items:
            result.violations.append(
                f"{section_name}: il contenuto deve essere una mappa o una lista di mappe"
            )
            continue

        fields = section_def.get("fields", [])
        for idx, item in enumerate(items):
            label = item.get("id", item.get("system_code", item.get("codice", f"#{idx}")))
            missing = [f for f in fields if f not in item]
            if missing:
                result.violations.append(
                    f"{section_name}[{label}]: campi mancanti {', '.join(missing)}"
                )

        for rule in section_def.get("rules", []):
            outcome = _check_boolean_rule(rule, items)
            if outcome is None:
                result.rule_evaluations.append(
                    RuleEvaluation(rule=rule, section=section_name, checked=False, passed=True)
                )
                continue
            passed, detail = outcome
            result.rule_evaluations.append(
                RuleEvaluation(rule=rule, section=section_name, checked=True, passed=passed, detail=detail)
            )
            if not passed:
                result.violations.append(f"{section_name} regola violata: '{rule}' ({detail})")

    return result


def validate_quality_readiness_manifest(
    manifest_path: Path, contract_path: Path
) -> ContractValidationResult:
    """Convenience wrapper: load both files and validate the manifest against the contract."""

    manifest = load_manifest(manifest_path)
    contract = load_contract(contract_path)
    return validate_manifest_against_contract(manifest, contract)
