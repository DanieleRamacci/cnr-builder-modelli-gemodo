"""Destination approval for admin-configured discovery endpoints (T081).

Only an explicitly allowlisted HTTPS origin resolving to a public IP is approved;
the allowlist is a deployment setting (``GEMODO_INTEGRAZIONI_ALLOWLIST``), empty by
default, per specs/010-.../contracts/integrazioni-policy.md ("default vuota, nessuna
chiamata finche' una destinazione non e' approvata"). An origin additionally listed in
``GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO`` is the deployment's explicit exception for a
private/loopback destination or an HTTP test fixture; that pairing is the "eccezione di
deployment esplicita" the policy requires, never inferred from the hostname.

This checks the resolution at approval time; it does not pin the later HTTP request's
connection to the IP verified here. That DNS-rebinding-proof connection pinning, plus
the full adversarial test matrix (redirects, cyclic HAL, rebinding), is deliberately
deferred to T084.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from app.common.errors import DomainError
from app.core.settings import Settings


def _non_approvata() -> DomainError:
    return DomainError("DESTINAZIONE_NON_APPROVATA", "Destinazione non approvata", status_code=422)


def _origine(hostname: str, scheme: str, port: int | None) -> str:
    return f"{scheme}://{hostname.lower()}" + (f":{port}" if port else "")


def _ip_pubblico(hostname: str) -> None:
    try:
        risoluzioni = socket.getaddrinfo(hostname, None)
    except OSError:
        raise _non_approvata() from None
    if not risoluzioni:
        raise _non_approvata()
    for risoluzione in risoluzioni:
        indirizzo = ipaddress.ip_address(risoluzione[4][0])
        if (
            indirizzo.is_private or indirizzo.is_loopback or indirizzo.is_link_local
            or indirizzo.is_multicast or indirizzo.is_unspecified or indirizzo.is_reserved
        ):
            raise _non_approvata()


def valida_destinazione_approvata(url: str, settings: Settings) -> None:
    parsed = urlsplit(url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise _non_approvata()
    origine = _origine(parsed.hostname, parsed.scheme, parsed.port)
    privato = origine in settings.gemodo_integrazioni_allowlist_privato
    if parsed.scheme not in ("https", "http") or (parsed.scheme == "http" and not privato):
        raise _non_approvata()
    if origine not in settings.gemodo_integrazioni_allowlist:
        raise _non_approvata()
    if not privato:
        _ip_pubblico(parsed.hostname)
