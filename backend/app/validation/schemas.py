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
