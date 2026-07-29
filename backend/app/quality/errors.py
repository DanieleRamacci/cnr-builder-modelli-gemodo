"""Shared quality error types for the feature 009 readiness gate.

Each error corresponds to one of the failure categories the foundation feature must be
able to distinguish (spec `009-fondamenta-mock-test-qualita`, FR-008, FR-011, FR-018):

- ``PrerequisitoMancanteError``: a required local service/dependency is unavailable.
  This is *not* an application bug - it must be reported separately from it.
- ``ContrattoNonValidoError``: a manifest does not satisfy the quality-readiness
  contract (or another versioned contract) it is validated against.
- ``SeedSensibileError``: a demo seed is marked as containing real or sensitive data.
- ``DecisioneBloccanteError``: a critical open decision blocks the requested
  planning/implementation phase for the part it impacts.
"""

from __future__ import annotations


class QualityError(Exception):
    """Base class for all feature-009 quality-readiness errors."""


class PrerequisitoMancanteError(QualityError):
    """A required local service or dependency is not available."""

    def __init__(self, servizio: str, dettaglio: str) -> None:
        self.servizio = servizio
        self.dettaglio = dettaglio
        super().__init__(f"prerequisito mancante: {servizio} - {dettaglio}")


class ContrattoNonValidoError(QualityError):
    """A manifest does not satisfy the contract it is validated against."""

    def __init__(self, contratto: str, violazioni: list[str]) -> None:
        self.contratto = contratto
        self.violazioni = list(violazioni)
        joined = "; ".join(self.violazioni) if self.violazioni else "nessun dettaglio"
        super().__init__(f"contratto non valido: {contratto} - {joined}")


class SeedSensibileError(QualityError):
    """A demo seed is marked as containing real or sensitive data."""

    def __init__(self, seed_id: str, motivo: str) -> None:
        self.seed_id = seed_id
        self.motivo = motivo
        super().__init__(f"seed sensibile: {seed_id} - {motivo}")


class DecisioneBloccanteError(QualityError):
    """A critical open decision blocks the requested phase for an impacted part."""

    def __init__(self, decisione_id: str, fase: str, motivo: str) -> None:
        self.decisione_id = decisione_id
        self.fase = fase
        self.motivo = motivo
        super().__init__(f"decisione bloccante: {decisione_id} (fase {fase}) - {motivo}")
