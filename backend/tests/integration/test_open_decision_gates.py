"""Integration tests: blocking critical decisions before implementation readiness.

Exercises the real ``app.quality.readiness_gate`` logic, first with small synthetic
decision sets (deterministic, so the assertions do not depend on the ever-evolving
real register), then against the real ``docs/decision-register.yaml`` for facts that
are stable regardless of how other decisions evolve (FR-018).
"""

from __future__ import annotations

import pytest

from app.quality.errors import DecisioneBloccanteError
from app.quality.readiness_gate import load_decision_register, valuta_readiness
from app.quality.schemas import DecisioneAperta, FaseBloccante, StatoDecisione

pytestmark = pytest.mark.integration


def _decisione(**overrides) -> DecisioneAperta:
    base = {
        "id": "DEC-TEST",
        "titolo": "decisione di test",
        "owner_spec": "specs/001-catalogo-contratto-geban",
        "spec_interessate": ["specs/001-catalogo-contratto-geban"],
        "stato": StatoDecisione.APERTA,
        "assunzione_provvisoria": "nessuna assunzione proposta",
        "impatto": "impatto di test",
        "fase_bloccante": FaseBloccante.TASKS,
    }
    base.update(overrides)
    return DecisioneAperta.model_validate(base)


def test_open_decision_blocks_the_phase_it_declares_and_later_phases():
    decisione = _decisione(fase_bloccante=FaseBloccante.PLAN)

    for fase in (FaseBloccante.PLAN, FaseBloccante.TASKS, FaseBloccante.IMPLEMENTAZIONE):
        esito = valuta_readiness([decisione], fase_richiesta=fase)
        assert esito.pronto is False
        assert decisione in esito.blocchi


def test_open_decision_does_not_block_an_earlier_phase():
    decisione = _decisione(fase_bloccante=FaseBloccante.IMPLEMENTAZIONE)

    esito = valuta_readiness([decisione], fase_richiesta=FaseBloccante.PLAN)

    assert esito.pronto is True
    assert esito.blocchi == []


def test_confirmed_decision_never_blocks_any_phase():
    decisione = _decisione(stato=StatoDecisione.CONFERMATA, assunzione_provvisoria=None)

    for fase in (FaseBloccante.SPEC, FaseBloccante.PLAN, FaseBloccante.TASKS, FaseBloccante.IMPLEMENTAZIONE):
        esito = valuta_readiness([decisione], fase_richiesta=fase)
        assert esito.pronto is True


def test_explicitly_suspended_decision_with_documented_impact_does_not_block():
    decisione = _decisione(stato=StatoDecisione.SOSPESA, impatto="rischio residuo tracciato esplicitamente")

    esito = valuta_readiness([decisione], fase_richiesta=FaseBloccante.IMPLEMENTAZIONE)

    assert esito.pronto is True


def test_decision_without_a_blocking_phase_never_blocks():
    decisione = _decisione(fase_bloccante=FaseBloccante.NESSUNA)

    esito = valuta_readiness([decisione], fase_richiesta=FaseBloccante.IMPLEMENTAZIONE)

    assert esito.pronto is True


def test_spec_target_filters_to_relevant_decisions_only():
    decisione_001 = _decisione(id="DEC-A", owner_spec="specs/001-catalogo-contratto-geban")
    decisione_002 = _decisione(
        id="DEC-B", owner_spec="specs/002-builder-modelli", spec_interessate=["specs/002-builder-modelli"]
    )

    esito = valuta_readiness(
        [decisione_001, decisione_002],
        fase_richiesta=FaseBloccante.TASKS,
        spec_target="specs/002-builder-modelli",
    )

    assert [d.id for d in esito.blocchi] == ["DEC-B"]


def test_solleva_se_bloccato_raises_decisione_bloccante_error_when_not_ready():
    decisione = _decisione()
    esito = valuta_readiness([decisione], fase_richiesta=FaseBloccante.TASKS)

    with pytest.raises(DecisioneBloccanteError):
        esito.solleva_se_bloccato()


def test_solleva_se_bloccato_does_not_raise_when_ready():
    decisione = _decisione(stato=StatoDecisione.CONFERMATA, assunzione_provvisoria=None)
    esito = valuta_readiness([decisione], fase_richiesta=FaseBloccante.TASKS)

    esito.solleva_se_bloccato()  # must not raise


# ---------------------------------------------------------------------------
# Fatti stabili sul registro reale (veri indipendentemente da quali altre decisioni
# vengano risolte in futuro, perche' derivano da decisioni gia' CONFERMATA).
# ---------------------------------------------------------------------------


@pytest.fixture()
def real_decisions(repo_root):
    return load_decision_register(repo_root / "docs" / "decision-register.yaml")


def test_confirmed_security_decisions_never_block_spec_006(real_decisions):
    for fase in (FaseBloccante.PLAN, FaseBloccante.TASKS, FaseBloccante.IMPLEMENTAZIONE):
        esito = valuta_readiness(
            real_decisions, fase_richiesta=fase, spec_target="specs/006-sicurezza-autorizzazioni-audit"
        )
        bloccanti_sicurezza = {"SEC-006-001", "SEC-006-002"} & {d.id for d in esito.blocchi}
        assert bloccanti_sicurezza == set()
