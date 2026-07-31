"""Pydantic schemas for GEBAN catalog API responses."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModalitaCatalogo(StrEnum):
    OPERATIVA = "OPERATIVA"
    STORICO = "STORICO"


class LinguaCampo(StrEnum):
    IT = "IT"
    EN = "EN"


class TipoCampo(StrEnum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class TipoDocumentoSchema(BaseModel):
    codice: str
    descrizione: str


class TipoDocumentoListResponse(BaseModel):
    items: list[TipoDocumentoSchema]


class CategoriaDocumentoSchema(BaseModel):
    codice: str
    descrizione: str


class CategoriaDocumentoListResponse(BaseModel):
    tipo_documento: str
    categorie: list[CategoriaDocumentoSchema]


class ModelloCatalogoSchema(BaseModel):
    modello_id: int = Field(..., ge=1)
    modello_versione_id: int = Field(..., ge=1)
    codice: str
    descrizione: str
    variante: str = "STANDARD"
    versione: int
    stato: str = "PUBBLICATO"
    data_inizio_validita: date | None = None
    data_fine_validita: date | None = None
    pubblicato_at: datetime | None = None


class ModelloSearchResponse(BaseModel):
    tipo_documento: str
    categoria: str | None = None
    codice_tipologia: str | None = None
    modalita: ModalitaCatalogo = ModalitaCatalogo.OPERATIVA
    modelli: list[ModelloCatalogoSchema]


class CampoRichiestoSchema(BaseModel):
    codice: str
    etichetta: str
    tipo: TipoCampo
    lingua: LinguaCampo = LinguaCampo.IT
    obbligatorio: bool
    ordine: int
    descrizione: str | None = None
    validazione: dict[str, Any] | None = None


class CampiRichiestiResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    modello_versione_id: int = Field(..., ge=1)
    tipo_documento: str | None = None
    categoria: str | None = None
    campi: list[CampoRichiestoSchema]
    schema_: dict[str, Any] = Field(alias="schema")
