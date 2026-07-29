"""MatriceCopertura validation (spec 009, User Story 3, FR-016).

Bridges scenarios, requirements, contracts and spec owners so every minimum e2e
scenario is traceable, and every ``BLOCCATO`` row points at an explicit blocker
instead of silently dropping coverage.
"""

from __future__ import annotations

from app.quality.errors import ContrattoNonValidoError
from app.quality.schemas import MatriceCopertura, StatoCopertura


def validate_riga_copertura(riga: MatriceCopertura) -> None:
    violazioni: list[str] = []
    if riga.stato == StatoCopertura.BLOCCATO and not riga.note:
        violazioni.append("stato BLOCCATO richiede 'note' che indichi la decisione o il prerequisito bloccante")
    if violazioni:
        raise ContrattoNonValidoError(riga.id, violazioni)


def validate_copertura_scenari_minimi(righe: list[MatriceCopertura], scenario_ids: set[str]) -> None:
    """Every minimum e2e scenario (E2E-001..006) must appear at least once (FR-016)."""

    coperti = {r.scenario_id for r in righe}
    mancanti = scenario_ids - coperti
    if mancanti:
        raise ContrattoNonValidoError(
            "matrice-copertura", [f"scenari minimi assenti dalla matrice: {', '.join(sorted(mancanti))}"]
        )


def riepilogo_stato(righe: list[MatriceCopertura]) -> dict[str, int]:
    """Count rows per ``stato``, useful for a quick readiness summary."""

    riepilogo: dict[str, int] = {}
    for riga in righe:
        riepilogo[riga.stato.value] = riepilogo.get(riga.stato.value, 0) + 1
    return riepilogo
