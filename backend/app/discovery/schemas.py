"""DTOs returned by the discovery port, independent of the concrete adapter.

Same shape whether the data comes from AdapterLocale (self-service tipo
documento, reads local tables) or AdapterHTTP (integrated tipo documento, not
implemented yet - see specs/010-configurazione-cataloghi-integrazioni). The
caller (builder, 002) never sees which adapter answered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfiloDisponibile:
    codice: str
    descrizione: str


@dataclass(frozen=True)
class TipologiaDisponibile:
    codice: str
    descrizione: str
    profili: tuple[ProfiloDisponibile, ...]


@dataclass(frozen=True)
class CampoDisponibile:
    codice: str
    etichetta: str
    tipo_dato: str
    obbligatorio: bool
    lingua: str
    ordine: int
    validazione: dict[str, Any] | None
