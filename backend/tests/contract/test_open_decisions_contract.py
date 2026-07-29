"""Contract test: decision register required fields and statuses (spec 009, US3).

Exercises the real docs/decision-register.yaml against the real validation in
app.quality.decision. No part of the validation is mocked.
"""

from __future__ import annotations

import copy

import pytest

from app.quality.decision import validate_decisione, validate_transizione
from app.quality.errors import ContrattoNonValidoError
from app.quality.manifest_loader import load_yaml
from app.quality.schemas import DecisioneAperta, FaseBloccante, StatoDecisione

pytestmark = pytest.mark.contract


@pytest.fixture()
def decision_register_path(repo_root):
    return repo_root / "docs" / "decision-register.yaml"


@pytest.fixture()
def decision_register_raw(decision_register_path):
    return load_yaml(decision_register_path)


@pytest.fixture()
def decisions(decision_register_raw):
    return [DecisioneAperta.model_validate(item) for item in decision_register_raw["decisions"]]


def test_register_has_at_least_the_27_decisions_from_proposal_section_17(decisions):
    # spec.md "Decision Ownership" lists 27 items from proposal section 17, plus
    # SEC-006-002 tracked separately elsewhere in the repository.
    assert len(decisions) >= 27


def test_every_decision_id_is_unique(decisions):
    ids = [d.id for d in decisions]
    assert len(ids) == len(set(ids))


def test_the_two_resolved_security_decisions_are_present_and_confirmed(decisions):
    by_id = {d.id: d for d in decisions}

    assert by_id["SEC-006-001"].stato == StatoDecisione.CONFERMATA
    assert by_id["SEC-006-002"].stato == StatoDecisione.CONFERMATA
    assert by_id["SEC-006-001"].fase_bloccante == FaseBloccante.NESSUNA
    assert by_id["SEC-006-002"].fase_bloccante == FaseBloccante.NESSUNA


def test_every_decision_has_an_owner_spec(decisions):
    for decisione in decisions:
        assert decisione.owner_spec, f"{decisione.id} senza owner_spec"


def test_every_real_decision_passes_validation(decisions):
    for decisione in decisions:
        validate_decisione(decisione)  # must not raise


def test_non_confirmed_decision_without_assunzione_provvisoria_is_rejected(decisions):
    non_confermata = next(d for d in decisions if d.stato != StatoDecisione.CONFERMATA)
    rotta = non_confermata.model_copy(update={"assunzione_provvisoria": None})

    with pytest.raises(ContrattoNonValidoError):
        validate_decisione(rotta)


def test_confirmed_decision_without_owner_is_rejected(decisions):
    confermata = next(d for d in decisions if d.stato == StatoDecisione.CONFERMATA)
    rotta = confermata.model_copy(update={"owner_spec": ""})

    with pytest.raises(ContrattoNonValidoError):
        validate_decisione(rotta)


@pytest.mark.parametrize(
    ("da", "verso"),
    [
        (StatoDecisione.APERTA, StatoDecisione.ASSUNTA_PROVVISORIA),
        (StatoDecisione.APERTA, StatoDecisione.CONFERMATA),
        (StatoDecisione.ASSUNTA_PROVVISORIA, StatoDecisione.CONFERMATA),
        (StatoDecisione.ASSUNTA_PROVVISORIA, StatoDecisione.SOSPESA),
        (StatoDecisione.SOSPESA, StatoDecisione.ASSUNTA_PROVVISORIA),
        (StatoDecisione.SOSPESA, StatoDecisione.CONFERMATA),
    ],
)
def test_legal_state_transitions_are_accepted(da, verso):
    validate_transizione(da, verso)  # must not raise


@pytest.mark.parametrize(
    ("da", "verso"),
    [
        (StatoDecisione.CONFERMATA, StatoDecisione.APERTA),
        (StatoDecisione.CONFERMATA, StatoDecisione.ASSUNTA_PROVVISORIA),
        (StatoDecisione.APERTA, StatoDecisione.SOSPESA),
        (StatoDecisione.SOSPESA, StatoDecisione.APERTA),
    ],
)
def test_illegal_state_transitions_are_rejected(da, verso):
    with pytest.raises(ContrattoNonValidoError):
        validate_transizione(da, verso)


def test_raw_register_has_decisions_and_no_unexpected_top_level_keys(decision_register_raw):
    assert set(decision_register_raw.keys()) == {"decisions"}


def test_a_tampered_register_entry_with_unknown_status_is_rejected(decision_register_raw):
    tampered = copy.deepcopy(decision_register_raw)
    tampered["decisions"][0]["stato"] = "NON_UNO_STATO_VALIDO"

    with pytest.raises(Exception):  # pydantic.ValidationError: malformed input, not a domain rule
        DecisioneAperta.model_validate(tampered["decisions"][0])
