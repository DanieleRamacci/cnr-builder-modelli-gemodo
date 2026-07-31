"""Stable API error envelope and exception mapping."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(StrEnum):
    CAMPO_OBBLIGATORIO = "CAMPO_OBBLIGATORIO"
    TIPO_NON_VALIDO = "TIPO_NON_VALIDO"
    CAMPO_NON_AMMESSO = "CAMPO_NON_AMMESSO"
    CAMPO_INGLESE_MANCANTE = "CAMPO_INGLESE_MANCANTE"
    CONTESTO_NON_VALIDO = "CONTESTO_NON_VALIDO"
    TIPOLOGIA_SOL_NON_VALIDA = "TIPOLOGIA_SOL_NON_VALIDA"
    MODELLO_NON_TROVATO = "MODELLO_NON_TROVATO"
    MODELLO_VERSIONE_NON_TROVATO = "MODELLO_VERSIONE_NON_TROVATO"
    MODELLO_VERSIONE_NON_PUBBLICATO = "MODELLO_VERSIONE_NON_PUBBLICATO"
    ACCESSO_NON_AUTENTICATO = "ACCESSO_NON_AUTENTICATO"
    ACCESSO_NON_AUTORIZZATO = "ACCESSO_NON_AUTORIZZATO"


class ErrorResponse(BaseModel):
    codice: str = Field(..., description="Codice errore stabile")
    messaggio: str = Field(..., description="Messaggio funzionale pubblico")
    dettagli: list[dict[str, Any]] | None = None


class ApiError(Exception):
    def __init__(
        self,
        codice: ErrorCode | str,
        messaggio: str,
        *,
        status_code: int = 400,
        dettagli: list[dict[str, Any]] | None = None,
    ) -> None:
        self.codice = str(codice)
        self.messaggio = messaggio
        self.status_code = status_code
        self.dettagli = dettagli
        super().__init__(messaggio)


class DomainError(ApiError):
    """Base class for functional domain errors returned through the public envelope."""


class CatalogError(DomainError):
    pass


class PayloadValidationDomainError(DomainError):
    pass


class AuthenticationError(ApiError):
    def __init__(self, messaggio: str = "Token Bearer mancante o non valido") -> None:
        super().__init__(ErrorCode.ACCESSO_NON_AUTENTICATO, messaggio, status_code=401)


class AuthorizationError(ApiError):
    def __init__(self, messaggio: str = "Operazione non autorizzata") -> None:
        super().__init__(ErrorCode.ACCESSO_NON_AUTORIZZATO, messaggio, status_code=403)


def error_response(error: ApiError) -> JSONResponse:
    payload = ErrorResponse(codice=error.codice, messaggio=error.messaggio, dettagli=error.dettagli)
    return JSONResponse(status_code=error.status_code, content=payload.model_dump(exclude_none=True))


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc)


async def request_validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    dettagli = [{"campo": ".".join(str(part) for part in error["loc"]), "messaggio": error["msg"]} for error in exc.errors()]
    return error_response(
        ApiError(
            ErrorCode.CONTESTO_NON_VALIDO,
            "Richiesta non coerente con il contratto API",
            status_code=400,
            dettagli=dettagli,
        )
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return error_response(ApiError(ErrorCode.CONTESTO_NON_VALIDO, "Risorsa non trovata", status_code=404))
    return error_response(ApiError(ErrorCode.CONTESTO_NON_VALIDO, str(exc.detail), status_code=exc.status_code))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
