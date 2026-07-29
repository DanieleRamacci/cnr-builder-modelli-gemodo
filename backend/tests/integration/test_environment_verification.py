"""Integration tests: local environment verification PASS/PARTIAL/FAIL outcomes.

Exercises the real classification logic in ``environment_verifier.verifica_ambiente``
against the real ``ambiente_locale_default()`` definition, using deterministic fake
healthcheck probes (the probes are the infrastructure boundary being replaced for a
repeatable test - the PASS/PARTIAL/FAIL decision logic itself is fully real and never
mocked). Also covers the static ``environment.py`` validation rules (FR-008,
data-model.md).
"""

from __future__ import annotations

import pytest

from app.quality.environment import (
    ambiente_locale_default,
    validate_ambiente_locale,
    validate_servizio_locale,
)
from app.quality.environment_verifier import (
    healthcheck_errore_applicativo,
    healthcheck_prerequisito_mancante,
    healthcheck_up,
    verifica_ambiente,
)
from app.quality.errors import ContrattoNonValidoError
from app.quality.schemas import CategoriaServizio, EsitoVerifica, ServizioLocale

pytestmark = pytest.mark.integration


def _all_up(*, except_for: set[str] = frozenset()) -> dict:
    ambiente = ambiente_locale_default()
    checks = {}
    for servizio in ambiente.servizi:
        if servizio.nome in except_for:
            continue
        checks[servizio.nome] = lambda: healthcheck_up()
    return checks


def test_ambiente_locale_default_is_structurally_valid():
    ambiente = ambiente_locale_default()

    validate_ambiente_locale(ambiente)  # must not raise

    nomi = {s.nome for s in ambiente.servizi}
    assert {"backend", "frontend", "postgres", "keycloak", "documentale-mock"} <= nomi


def test_ambiente_locale_default_frontend_is_optional_not_mandatory():
    ambiente = ambiente_locale_default()
    frontend = next(s for s in ambiente.servizi if s.nome == "frontend")
    assert frontend.obbligatorio is False


def test_all_services_up_including_frontend_yields_pass_with_no_problems():
    ambiente = ambiente_locale_default()
    checks = {s.nome: (lambda: healthcheck_up()) for s in ambiente.servizi}

    risultato = verifica_ambiente(ambiente, checks)

    assert risultato.esito == EsitoVerifica.PASS_
    assert risultato.problemi == []
    assert set(risultato.servizi_verificati) == {s.nome for s in ambiente.servizi}


def test_frontend_healthcheck_down_is_reported_but_does_not_block_pass():
    """Frontend is optional (no implementation yet): its failure must be visible in
    ``problemi`` but must not turn an otherwise-healthy environment into PARTIAL/FAIL."""

    ambiente = ambiente_locale_default()
    checks = {s.nome: (lambda: healthcheck_up()) for s in ambiente.servizi}
    checks["frontend"] = lambda: healthcheck_prerequisito_mancante("connection refused")

    risultato = verifica_ambiente(ambiente, checks)

    assert risultato.esito == EsitoVerifica.PASS_
    problema_frontend = next(p for p in risultato.problemi if p.servizio == "frontend")
    assert problema_frontend.tipo == "prerequisito_mancante"
    assert problema_frontend.dettaglio == "connection refused"


def test_one_mandatory_service_down_yields_partial():
    ambiente = ambiente_locale_default()
    checks = {s.nome: (lambda: healthcheck_up()) for s in ambiente.servizi}
    checks["postgres"] = lambda: healthcheck_prerequisito_mancante("non raggiungibile")

    risultato = verifica_ambiente(ambiente, checks)

    assert risultato.esito == EsitoVerifica.PARTIAL
    problema = next(p for p in risultato.problemi if p.servizio == "postgres")
    assert problema.tipo == "prerequisito_mancante"


def test_all_mandatory_services_down_yields_fail():
    ambiente = ambiente_locale_default()
    checks = {s.nome: (lambda: healthcheck_prerequisito_mancante("down")) for s in ambiente.servizi}

    risultato = verifica_ambiente(ambiente, checks)

    assert risultato.esito == EsitoVerifica.FAIL


def test_missing_healthcheck_for_a_service_is_reported_as_missing_prerequisite():
    ambiente = ambiente_locale_default()
    checks = {s.nome: (lambda: healthcheck_up()) for s in ambiente.servizi}
    del checks["keycloak"]

    risultato = verifica_ambiente(ambiente, checks)

    problema = next(p for p in risultato.problemi if p.servizio == "keycloak")
    assert problema.tipo == "prerequisito_mancante"
    assert risultato.esito == EsitoVerifica.PARTIAL


def test_application_error_is_distinguished_from_missing_prerequisite():
    """FR-008: a reachable-but-erroring service is not the same failure as an
    unreachable one."""

    ambiente = ambiente_locale_default()
    checks = {s.nome: (lambda: healthcheck_up()) for s in ambiente.servizi}
    checks["backend"] = lambda: healthcheck_errore_applicativo("HTTP 500 da /health")

    risultato = verifica_ambiente(ambiente, checks)

    problema = next(p for p in risultato.problemi if p.servizio == "backend")
    assert problema.tipo == "errore_applicativo"
    assert risultato.esito == EsitoVerifica.PARTIAL


def test_validate_ambiente_locale_rejects_environment_missing_a_minimum_service():
    ambiente = ambiente_locale_default()
    senza_postgres = ambiente.model_copy(
        update={"servizi": [s for s in ambiente.servizi if s.nome != "postgres"]}
    )

    with pytest.raises(ContrattoNonValidoError) as exc_info:
        validate_ambiente_locale(senza_postgres)

    assert any("postgres" in v for v in exc_info.value.violazioni)


def test_validate_servizio_locale_rejects_dependency_on_real_geban():
    servizio_non_ammesso = ServizioLocale(
        nome="geban",
        categoria=CategoriaServizio.APP,
        healthcheck="GET https://geban.reale.example/health",
        obbligatorio=True,
    )

    with pytest.raises(ContrattoNonValidoError) as exc_info:
        validate_servizio_locale(servizio_non_ammesso)

    assert any("GEBAN reale" in v for v in exc_info.value.violazioni)


def test_validate_servizio_locale_rejects_mandatory_service_without_healthcheck():
    servizio_senza_healthcheck = ServizioLocale(
        nome="storage-secondario",
        categoria=CategoriaServizio.STORAGE,
        healthcheck="",
        obbligatorio=True,
    )

    with pytest.raises(ContrattoNonValidoError) as exc_info:
        validate_servizio_locale(servizio_senza_healthcheck)

    assert any("senza comando/endpoint di healthcheck" in v for v in exc_info.value.violazioni)
