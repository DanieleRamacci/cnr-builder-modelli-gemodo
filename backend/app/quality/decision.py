"""DecisioneAperta validation and state transitions (spec 009, User Story 3).

FR-006, FR-007, FR-017, FR-018: every open decision must carry an owner and a
blocking phase, and a critical decision must never become a silent assumption in the
implementation tasks of the parts it impacts.
"""

from __future__ import annotations

from app.quality.errors import ContrattoNonValidoError, DecisioneBloccanteError
from app.quality.schemas import DecisioneAperta, FaseBloccante, StatoDecisione

# data-model.md - DecisioneAperta state transitions.
TRANSIZIONI_AMMESSE: dict[StatoDecisione, set[StatoDecisione]] = {
    StatoDecisione.APERTA: {StatoDecisione.ASSUNTA_PROVVISORIA, StatoDecisione.CONFERMATA},
    StatoDecisione.ASSUNTA_PROVVISORIA: {StatoDecisione.CONFERMATA, StatoDecisione.SOSPESA},
    StatoDecisione.SOSPESA: {StatoDecisione.ASSUNTA_PROVVISORIA, StatoDecisione.CONFERMATA},
    StatoDecisione.CONFERMATA: set(),
}

# Ordine delle fasi Spec Kit usato per confrontare una fase bloccante con la fase che si
# sta tentando di avviare.
ORDINE_FASI: list[FaseBloccante] = [
    FaseBloccante.SPEC,
    FaseBloccante.PLAN,
    FaseBloccante.TASKS,
    FaseBloccante.IMPLEMENTAZIONE,
]


def validate_transizione(stato_attuale: StatoDecisione, nuovo_stato: StatoDecisione) -> None:
    """Raise if ``nuovo_stato`` is not a state-machine-legal transition from ``stato_attuale``."""

    if nuovo_stato == stato_attuale:
        return
    ammessi = TRANSIZIONI_AMMESSE.get(stato_attuale, set())
    if nuovo_stato not in ammessi:
        raise ContrattoNonValidoError(
            "transizione-decisione",
            [f"transizione non ammessa: {stato_attuale.value} -> {nuovo_stato.value}"],
        )


def validate_decisione(decisione: DecisioneAperta) -> None:
    """Structural rules every open decision entry must satisfy (data-model.md):

    "ogni decisione di §17 deve avere owner e assunzione provvisoria o stato
    confermato" - so unless a decision is CONFERMATA, it MUST carry an explicit
    ``assunzione_provvisoria`` (even a "nessuna assunzione proposta" statement is
    valid: the point is that the absence of an assumption is recorded, not silently
    omitted).
    """

    violazioni: list[str] = []
    if not decisione.owner_spec:
        violazioni.append("owner_spec mancante")
    if decisione.stato != StatoDecisione.CONFERMATA and not decisione.assunzione_provvisoria:
        violazioni.append(
            f"decisione non CONFERMATA (stato {decisione.stato.value}) richiede 'assunzione_provvisoria' esplicita"
        )
    if decisione.stato in (StatoDecisione.ASSUNTA_PROVVISORIA, StatoDecisione.SOSPESA) and not decisione.impatto:
        violazioni.append(f"stato {decisione.stato.value} richiede 'impatto' esplicito")
    if violazioni:
        raise ContrattoNonValidoError(decisione.id, violazioni)


def blocca_fase(decisione: DecisioneAperta, fase_richiesta: FaseBloccante) -> bool:
    """True if this decision blocks starting ``fase_richiesta`` (FR-018).

    A decision blocks a phase when: it declares a ``fase_bloccante`` other than
    NESSUNA; that phase has been reached or passed by ``fase_richiesta``; and the
    decision is not ``CONFERMATA`` nor explicitly ``SOSPESA`` with a documented
    ``impatto`` (an explicit suspension with tracked risk is an accepted way to
    proceed, per quality-readiness-contract.yaml's ``before_implementation`` gate - it
    is the opposite of a silent assumption).
    """

    if decisione.fase_bloccante == FaseBloccante.NESSUNA:
        return False
    if decisione.stato == StatoDecisione.CONFERMATA:
        return False
    if decisione.stato == StatoDecisione.SOSPESA and decisione.impatto:
        return False
    if decisione.fase_bloccante not in ORDINE_FASI or fase_richiesta not in ORDINE_FASI:
        return False
    return ORDINE_FASI.index(decisione.fase_bloccante) <= ORDINE_FASI.index(fase_richiesta)


def assert_non_bloccante_per_fase(decisione: DecisioneAperta, fase_richiesta: FaseBloccante) -> None:
    """Raise DecisioneBloccanteError if ``decisione`` blocks ``fase_richiesta``."""

    if blocca_fase(decisione, fase_richiesta):
        raise DecisioneBloccanteError(
            decisione.id,
            fase_richiesta.value,
            f"decisione '{decisione.titolo}' in stato {decisione.stato.value} blocca la fase "
            f"{decisione.fase_bloccante.value}",
        )
