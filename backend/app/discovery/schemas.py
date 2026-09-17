"""DTOs returned by the discovery port, independent of the concrete adapter.

The external tree is held in memory, never materialized as local catalog rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator, model_validator

# specs/010-configurazione-cataloghi-integrazioni/contracts/geban-discovery-endpoint.openapi.yaml (info.version)
VERSIONE_CONTRATTO_DISCOVERY = "0.4.0"


class CampoDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    codice: StrictStr = Field(min_length=1)
    etichetta: StrictStr
    tipo: Literal["string", "number", "date", "boolean", "array", "object"]
    lingua: Literal["IT", "EN"]
    obbligatorio: StrictBool
    ordine: int = Field(strict=True, ge=1)
    descrizione: StrictStr | None = None
    validazione: dict[str, Any] | None = None


def _codici_univoci(elementi: tuple, nome: str) -> None:
    codici = [elemento.codice for elemento in elementi]
    if len(set(codici)) != len(codici):
        raise ValueError(f"Codici duplicati in {nome}")


class NodoDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    codice: StrictStr = Field(min_length=1)
    descrizione: StrictStr
    tipo_livello: StrictStr | None = None
    figli: tuple[NodoDiscovery, ...] | None = None
    campi: tuple[CampoDiscovery, ...] | None = None
    livelli_possibili: tuple[StrictStr, ...] | None = None
    livello_base: StrictStr | None = None

    @model_validator(mode="before")
    @classmethod
    def normalizza_default(cls, value: Any) -> Any:
        if isinstance(value, dict) and "figli" in value and "campi" in value:
            raise ValueError("Figli e campi non possono essere entrambi presenti")
        if isinstance(value, dict) and "livelloBase" in value:
            value = dict(value)
            alias = value.pop("livelloBase")
            if "livello_base" in value and value["livello_base"] != alias:
                raise ValueError("Default del livello discordanti")
            value["livello_base"] = alias
        return value

    @model_validator(mode="after")
    def verifica_struttura(self) -> NodoDiscovery:
        if (self.figli is None) == (self.campi is None):
            raise ValueError("Il nodo deve contenere figli oppure campi")
        _codici_univoci(self.figli if self.figli is not None else self.campi, "nodo")
        if self.livello_base is not None and (
            self.livelli_possibili is None or self.livello_base not in self.livelli_possibili
        ):
            raise ValueError("Il default non appartiene ai livelli possibili")
        return self


class CatalogoDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    codice_tipo_documento: StrictStr = Field(min_length=1)
    validita: datetime
    nodi: tuple[NodoDiscovery, ...]

    @field_validator("validita", mode="before")
    @classmethod
    def verifica_formato_data(cls, value: Any) -> Any:
        if not isinstance(value, (str, datetime)):
            raise ValueError("La validita deve essere una data ISO con fuso orario")
        return value

    @model_validator(mode="after")
    def verifica_catalogo(self) -> CatalogoDiscovery:
        _codici_univoci(self.nodi, "radice")
        if self.validita.tzinfo is None or self.validita.utcoffset() is None:
            raise ValueError("La data di validita deve includere il fuso orario")
        return self

    def indice_percorsi(self) -> dict[tuple[str, ...], NodoDiscovery]:
        indice: dict[tuple[str, ...], NodoDiscovery] = {}
        stack = [((), nodo) for nodo in self.nodi]
        while stack:
            padre, nodo = stack.pop()
            percorso = padre + (nodo.codice,)
            indice[percorso] = nodo
            stack.extend((percorso, figlio) for figlio in nodo.figli or ())
        return indice


class MappaDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    cataloghi: dict[StrictStr, CatalogoDiscovery] = Field(min_length=1)

    @model_validator(mode="after")
    def verifica_identita(self) -> MappaDiscovery:
        if any(codice != catalogo.codice_tipo_documento for codice, catalogo in self.cataloghi.items()):
            raise ValueError("Codici tipo documento incoerenti")
        return self
