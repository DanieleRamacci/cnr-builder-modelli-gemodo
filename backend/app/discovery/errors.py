"""Functional discovery failures, independent of the external server's errors."""

from app.common.errors import DomainError, ErrorCode


class DiscoveryError(DomainError):
    pass


def risposta_non_valida() -> DiscoveryError:
    return DiscoveryError(
        ErrorCode.DISCOVERY_NON_CONFORME, "La risposta discovery non rispetta il contratto",
        status_code=502,
    )
