"""Pydantic schemas for the builder admin API (creation/publication of models)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class TipologiaStrutturaSchema(BaseModel):
    codice: str
    descrizione: str
    profili: list[dict[str, str]]


class CampoStrutturaSchema(BaseModel):
    codice: str
    etichetta: str
    tipo_dato: str
    obbligatorio: bool
    lingua: str
    ordine: int
    validazione: dict[str, Any] | None = None


class StrutturaDisponibileResponse(BaseModel):
    tipo_documento: str
    tipologie: list[TipologiaStrutturaSchema]
    campi: list[CampoStrutturaSchema]


class CreaModelloRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codice: str
    nome: str
    codice_tipo_documento: str
    codice_categoria: str
    codice_tipologia: str | None = None
    variante: str = "STANDARD"


class ModelloResponse(BaseModel):
    id: str
    public_id: int | None
    codice: str
    nome: str
    codice_tipo_documento: str
    codice_categoria: str
    codice_tipologia: str | None
    variante: str


class CampoVersioneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codice: str
    lingua: str = "IT"


class CreaVersioneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campi: list[CampoVersioneRequest]


class VersioneResponse(BaseModel):
    id: str
    public_id: int | None
    modello_id: str
    numero_versione: int
    stato: str
    pubblicato_at: datetime | None
