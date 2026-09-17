"""Abstract discovery port (Ports & Adapters, DEC-002-PORTS-ADAPTERS-DISCOVERY).

The builder (002) and the configuration admin interface (010) ask this port
"what's available for this tipo documento", never a concrete source directly.
AdapterHTTP fetches an explicitly configured external URL.
Registration and selection of the adapter remain the configuration service's job.
"""

from __future__ import annotations

from typing import Protocol

from app.discovery.schemas import CatalogoDiscovery, MappaDiscovery


class PortaDiscovery(Protocol):
    def mappa_discovery(self, forza_aggiornamento: bool = False) -> MappaDiscovery: ...

    def catalogo_discovery(
        self, codice_tipo_documento: str, forza_aggiornamento: bool = False
    ) -> CatalogoDiscovery: ...
