"""Pydantic schemas for the builder admin API (creation/publication of models)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.discovery.schemas import CatalogoDiscovery

StrutturaDisponibileResponse = CatalogoDiscovery
StrutturaTipoDocumentoResponse = CatalogoDiscovery


class IntegrazioneVisibile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    codice: str
    nome: str
    codice_contesto: str


class CreaModelloRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codice_tipo_documento: str = Field(min_length=1)
    integrazione_id: uuid.UUID | None = None
    percorso_categorizzazione: list[str] | None = Field(default=None, min_length=1, max_length=64)
    codice_categoria: str | None = None
    codice_tipologia: str | None = None
    lingua: Literal["IT", "EN"]
    livello_professionale: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def verifica_selezione(self) -> CreaModelloRequest:
        if self.percorso_categorizzazione is None and not self.codice_categoria:
            raise ValueError("Indicare percorso_categorizzazione oppure codice_categoria")
        if self.percorso_categorizzazione is not None and any(not codice for codice in self.percorso_categorizzazione):
            raise ValueError("Il percorso non puo' contenere codici vuoti")
        return self


class ModelloResponse(BaseModel):
    id: str
    public_id: int | None
    codice: str
    nome: str
    codice_tipo_documento: str
    codice_categoria: str
    codice_tipologia: str | None
    percorso_categorizzazione: list[str]
    variante: str
    lingua: Literal["IT", "EN"]
    livello_professionale: str | None


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


class ModelloGestioneResponse(ModelloResponse):
    codice_contesto: str
    integrazione_id: uuid.UUID | None
    created_at: datetime
    versioni: list[VersioneResponse]
