"""Explicit deployment configuration, until administrative onboarding is built."""

import json
import os
from functools import lru_cache

from app.common.errors import ErrorCode
from app.discovery.adapter_http import AdapterHTTP
from app.discovery.errors import DiscoveryError


@lru_cache(maxsize=32)
def _adapter(url: str) -> AdapterHTTP:
    return AdapterHTTP(url)


def discovery_per_tipo(codice: str) -> AdapterHTTP:
    try:
        endpoints = json.loads(os.environ.get("GEMODO_DISCOVERY_ENDPOINTS", "{}"))
        if not isinstance(endpoints, dict):
            raise ValueError("Configurazione non valida")
        url = endpoints.get(codice)
        if not isinstance(url, str) or not url:
            raise ValueError("Endpoint assente")
        return _adapter(url)
    except (ValueError, TypeError):
        raise DiscoveryError(
            ErrorCode.DISCOVERY_NON_CONFIGURATA,
            "Endpoint discovery non configurato per questo tipo documento",
            status_code=503,
        ) from None
