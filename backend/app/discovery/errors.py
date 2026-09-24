"""Functional discovery failures, independent of the external server's errors."""

from typing import Any

from app.common.errors import DomainError, ErrorCode


class DiscoveryError(DomainError):
    pass


def risposta_non_valida(
    motivo: str | None = None, dettagli: list[dict[str, Any]] | None = None
) -> DiscoveryError:
    """`motivo` dice in che senso la risposta e' difforme, `dettagli` dove."""
    messaggio = "La risposta discovery non rispetta il contratto"
    if motivo is not None:
        messaggio = f"{messaggio}: {motivo}"
    return DiscoveryError(
        ErrorCode.DISCOVERY_NON_CONFORME, messaggio, status_code=502, dettagli=dettagli,
    )
