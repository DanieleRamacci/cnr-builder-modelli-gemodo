"""Abstract discovery port (Ports & Adapters, DEC-002-PORTS-ADAPTERS-DISCOVERY).

The builder (002) and the configuration admin interface (010) ask this port
"what's available for this tipo documento", never a concrete source directly.
Two adapters implement it: AdapterLocale (self-service, reads GEMODO's own
tables - implemented here) and AdapterHTTP (integrated tipo documento, calls
a registered external discovery endpoint - not implemented yet, out of scope
for tonight's BANDO_CONCORSO flow: docs/adr/0001-esempio-discovery-geban.json
is the manual deliverable standing in for it until 010 builds it).
"""

from __future__ import annotations

from typing import Protocol

from app.discovery.schemas import CampoDisponibile, TipologiaDisponibile


class PortaDiscovery(Protocol):
    def tipologie_disponibili(self, codice_tipo_documento: str) -> list[TipologiaDisponibile]: ...

    def campi_disponibili(self, codice_tipo_documento: str) -> list[CampoDisponibile]: ...
