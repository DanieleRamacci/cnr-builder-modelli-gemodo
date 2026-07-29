"""Readiness gate: fails when a critical open decision would become a silent assumption.

FR-018: decisions critical for implementation or integration MUST be closed
(``CONFERMATA``) or explicitly suspended (``SOSPESA`` with a documented ``impatto``)
before implementation tasks are generated for the part they impact. This module
evaluates the real decision register (``docs/decision-register.yaml``) against a
target phase and (optionally) a target spec, and reports every decision that would
still be blocking - it never silently lets an unresolved critical decision pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.quality.decision import blocca_fase
from app.quality.errors import DecisioneBloccanteError
from app.quality.manifest_loader import load_yaml
from app.quality.schemas import DecisioneAperta, FaseBloccante


def load_decision_register(path: Path) -> list[DecisioneAperta]:
    """Load ``docs/decision-register.yaml``."""

    data = load_yaml(path)
    return [DecisioneAperta.model_validate(item) for item in data.get("decisions", [])]


@dataclass
class EsitoReadinessGate:
    fase_richiesta: FaseBloccante
    spec_target: str | None
    blocchi: list[DecisioneAperta] = field(default_factory=list)

    @property
    def pronto(self) -> bool:
        return not self.blocchi

    def solleva_se_bloccato(self) -> None:
        if not self.blocchi:
            return
        dettagli = "; ".join(f"{d.id} ({d.titolo})" for d in self.blocchi)
        raise DecisioneBloccanteError(
            ",".join(d.id for d in self.blocchi),
            self.fase_richiesta.value,
            f"decisioni critiche non risolte per {self.spec_target or 'tutte le spec'}: {dettagli}",
        )


def valuta_readiness(
    decisioni: list[DecisioneAperta],
    *,
    fase_richiesta: FaseBloccante,
    spec_target: str | None = None,
) -> EsitoReadinessGate:
    """Evaluate whether ``fase_richiesta`` can start for ``spec_target``.

    ``spec_target`` filters to decisions whose ``owner_spec`` or ``spec_interessate``
    include it; pass ``None`` to evaluate every registered decision regardless of spec.
    """

    blocchi: list[DecisioneAperta] = []
    for decisione in decisioni:
        if spec_target is not None:
            rilevante = decisione.owner_spec == spec_target or spec_target in decisione.spec_interessate
            if not rilevante:
                continue
        if blocca_fase(decisione, fase_richiesta):
            blocchi.append(decisione)
    return EsitoReadinessGate(fase_richiesta=fase_richiesta, spec_target=spec_target, blocchi=blocchi)
