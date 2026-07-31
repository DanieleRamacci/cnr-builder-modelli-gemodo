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


class ProfiloDocumentoSchema(BaseModel):
    codice: str
    descrizione: str


class ProfiloDocumentoListResponse(BaseModel):
    tipo_documento: str
    profili: list[ProfiloDocumentoSchema]


class TipologiaCatalogoSchema(BaseModel):
    codice: str
    descrizione: str
    profili: list[ProfiloDocumentoSchema]


class ClassificazioneCatalogoResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tipo_documento": "BANDO_CONCORSO",
                "tipologie": [
                    {
                        "codice": "TD",
                        "descrizione": "Tempo determinato",
                        "profili": [
                            {"codice": "CTER", "descrizione": "Collaboratore Tecnico Enti di Ricerca"}
                        ],
                    }
                ],
            }
        }
    )

    tipo_documento: str
    tipologie: list[TipologiaCatalogoSchema]


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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tipo_documento": "BANDO_CONCORSO",
                "profilo": "CTER",
                "codice_tipologia": "TD",
                "modalita": "OPERATIVA",
                "modelli": [
                    {
                        "modello_id": 1,
                        "modello_versione_id": 1,
                        "codice": "demo-bando-concorso-standard-v1",
                        "descrizione": "demo-bando-concorso-standard-v1",
                        "variante": "STANDARD",
                        "versione": 1,
                        "stato": "PUBBLICATO",
                        "data_inizio_validita": None,
                        "data_fine_validita": None,
                        "pubblicato_at": "2026-07-31T10:00:00Z",
                    }
                ],
            }
        }
    )

    tipo_documento: str
    profilo: str | None = None
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
    profilo: str | None = None
    campi: list[CampoRichiestoSchema]
    schema_: dict[str, Any] = Field(alias="schema")


CategoriaDocumentoSchema = ProfiloDocumentoSchema
CategoriaDocumentoListResponse = ProfiloDocumentoListResponse
