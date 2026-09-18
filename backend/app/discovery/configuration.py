"""Resolves the discovery adapter for a tipo documento from the registered integration.

T082 (ADR 0002): the source of truth for "which URL serves this tipo documento" is the
``Integrazione``/``EndpointIntegrazione`` registry configured and verified through
``IntegrazioniService`` (T081), reached via ``TipoDocumento.integrazione_id`` - never an
environment variable. A tipo documento whose integration is not ``CONNESSO`` has no
usable discovery source; there is no local/seed fallback.

T084: ``IntegrazioniService`` only calls ``valida_destinazione_approvata`` at configure
and verify time; a URL that was approved once but later drifts out of the deployment
allowlist (e.g. an admin narrows ``GEMODO_INTEGRAZIONI_ALLOWLIST``) would otherwise keep
being dialed on every live builder read forever, since ``CONNESSO`` never expires on its
own. Re-validating here, on every resolution, closes that gap without adding an HTTP
call - it is a local DNS+parse check, not a fetch.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.catalog.models import TipoDocumento
from app.common.errors import DomainError, ErrorCode
from app.configurazione import repository as configurazione_repository
from app.core.settings import get_settings
from app.discovery.adapter_http import AdapterHTTP
from app.discovery.cache import CacheDiscovery
from app.discovery.egress import valida_destinazione_approvata
from app.discovery.errors import DiscoveryError

# Shared across requests so the TTL cache (app.discovery.cache.CacheDiscovery) actually
# avoids re-fetching on every read; entries are scoped per integration+verified revision,
# so a re-verification or reconfiguration naturally invalidates old entries instead of
# reusing them (see integrazioni-policy.md "RAM/cache per integrazione e revisione").
_CACHE_DISCOVERY_REGISTRATA = CacheDiscovery()


def discovery_per_tipo(db: Session, tipo: TipoDocumento) -> AdapterHTTP:
    if tipo.integrazione_id is None:
        raise DiscoveryError(
            ErrorCode.DISCOVERY_NON_CONFIGURATA,
            "Endpoint discovery non configurato per questo tipo documento",
            status_code=503,
        )
    endpoint = configurazione_repository.endpoint(db, tipo.integrazione_id)
    if endpoint is None or endpoint.stato != "CONNESSO":
        raise DomainError("INTEGRAZIONE_NON_CONNESSA", "Integrazione non connessa", status_code=409)
    valida_destinazione_approvata(endpoint.url, get_settings())
    return AdapterHTTP(
        endpoint.url,
        cache=_CACHE_DISCOVERY_REGISTRATA,
        timeout_seconds=endpoint.timeout_ms / 1000,
        cache_scope=f"integrazione:{tipo.integrazione_id}:revisione:{endpoint.revisione_verificata}",
    )
