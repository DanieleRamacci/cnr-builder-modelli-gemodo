"""VerificaAmbiente service: runs healthchecks and classifies PASS / PARTIAL / FAIL.

FR-008 requires the verification to distinguish a missing prerequisite (service not
configured / not reachable) from an application error (service reachable but answering
with an error) - see ``app.quality.errors.PrerequisitoMancanteError``. The actual
probing mechanism (HTTP call, ``pg_isready``, OIDC discovery request, ...) is injected
as a mapping of service name -> :data:`HealthCheck` callable, so this module never
hardcodes how to reach a particular piece of infrastructure and can be exercised with
real or fake probes alike without mocking the classification logic itself.

Classification rule (data-model.md):

- ``PASS``: every ``obbligatorio`` service is UP (optional services may still fail and
  are reported, but do not lower a PASS result).
- ``PARTIAL``: at least one ``obbligatorio`` service is UP, but not all of them.
- ``FAIL``: no ``obbligatorio`` service is UP.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable
from uuid import uuid4

from app.quality.schemas import AmbienteLocale, EsitoVerifica, ProblemaVerifica, VerificaAmbiente


class EsitoHealthcheck(str, Enum):
    UP = "UP"
    PREREQUISITO_MANCANTE = "PREREQUISITO_MANCANTE"
    ERRORE_APPLICATIVO = "ERRORE_APPLICATIVO"


@dataclass(frozen=True)
class HealthCheckOutcome:
    esito: EsitoHealthcheck
    dettaglio: str = ""


HealthCheck = Callable[[], HealthCheckOutcome]


def healthcheck_up(dettaglio: str = "ok") -> HealthCheckOutcome:
    return HealthCheckOutcome(EsitoHealthcheck.UP, dettaglio)


def healthcheck_prerequisito_mancante(dettaglio: str) -> HealthCheckOutcome:
    return HealthCheckOutcome(EsitoHealthcheck.PREREQUISITO_MANCANTE, dettaglio)


def healthcheck_errore_applicativo(dettaglio: str) -> HealthCheckOutcome:
    return HealthCheckOutcome(EsitoHealthcheck.ERRORE_APPLICATIVO, dettaglio)


_TIPO_PROBLEMA = {
    EsitoHealthcheck.PREREQUISITO_MANCANTE: "prerequisito_mancante",
    EsitoHealthcheck.ERRORE_APPLICATIVO: "errore_applicativo",
}


def verifica_ambiente(
    ambiente: AmbienteLocale,
    checks: dict[str, HealthCheck],
) -> VerificaAmbiente:
    """Run the configured healthchecks against an environment and classify the result."""

    problemi: list[ProblemaVerifica] = []
    servizi_verificati: list[str] = []
    obbligatori_totali = 0
    obbligatori_up = 0

    for servizio in ambiente.servizi:
        servizi_verificati.append(servizio.nome)
        check = checks.get(servizio.nome)
        if check is None:
            outcome = healthcheck_prerequisito_mancante("nessun healthcheck configurato per questo servizio")
        else:
            outcome = check()

        if servizio.obbligatorio:
            obbligatori_totali += 1
            if outcome.esito == EsitoHealthcheck.UP:
                obbligatori_up += 1

        if outcome.esito != EsitoHealthcheck.UP:
            problemi.append(
                ProblemaVerifica(
                    servizio=servizio.nome,
                    tipo=_TIPO_PROBLEMA[outcome.esito],
                    dettaglio=outcome.dettaglio,
                )
            )

    if obbligatori_totali == 0 or obbligatori_up == obbligatori_totali:
        esito = EsitoVerifica.PASS_
    elif obbligatori_up > 0:
        esito = EsitoVerifica.PARTIAL
    else:
        esito = EsitoVerifica.FAIL

    return VerificaAmbiente(
        id=f"verifica-{ambiente.id}-{uuid4().hex[:8]}",
        ambiente_id=ambiente.id,
        timestamp=datetime.now(timezone.utc),
        servizi_verificati=servizi_verificati,
        esito=esito,
        problemi=problemi,
    )
