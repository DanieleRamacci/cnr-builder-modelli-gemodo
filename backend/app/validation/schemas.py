"""Pydantic schemas for GEBAN payload validation API."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


class ValidazioneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sistema_richiedente: str
    external_context_id: str
    modello_versione_id: int
    data_riferimento: date | None = None
    bando_inglese: bool = False
    dati: dict[str, Any]


class ErroreValidazione(BaseModel):
    campo: str | None = None
    codice: str
    messaggio: str


class ValidazioneResponse(BaseModel):
    valido: bool
    errori: list[ErroreValidazione]


class GenerazioneDocumentoResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stato": "GENERAZIONE_SIMULATA",
                "messaggio": "Chiamata ricevuta correttamente: i dati sono validi.",
                "modello_versione_id": 1,
                "external_context_id": "test-context-001",
                "download_placeholder": "Qui sara' disponibile il link per scaricare il PDF generato.",
                "validazione": {"valido": True, "errori": []},
            }
        }
    )

    stato: str
    messaggio: str
    modello_versione_id: int
    external_context_id: str
    download_placeholder: str | None = None
    validazione: ValidazioneResponse
