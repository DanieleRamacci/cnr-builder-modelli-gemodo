"""Payload validation against a published model data contract."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.catalog import repository
from app.catalog.models import ModelloCampoRichiesto
from app.common.errors import ErrorCode, PayloadValidationDomainError
from app.db.session import get_db
from app.validation.schemas import ErroreValidazione, ValidazioneRequest, ValidazioneResponse


class PayloadValidationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def validate_payload(self, request: ValidazioneRequest) -> ValidazioneResponse:
        version = repository.get_model_version_by_public_id(self.db, request.modello_versione_id)
        if version is None:
            raise PayloadValidationDomainError(
                ErrorCode.MODELLO_VERSIONE_NON_TROVATO,
                "Versione modello non trovata",
                status_code=404,
            )
        if version.stato != repository.STATO_PUBBLICATO:
            raise PayloadValidationDomainError(
                ErrorCode.MODELLO_VERSIONE_NON_PUBBLICATO,
                "Versione modello non pubblicata",
                status_code=409,
            )

        fields = repository.list_required_fields(self.db, version.id)
        errors: list[ErroreValidazione] = []
        allowed = {field.codice for field in fields}

        for field_name in sorted(set(request.dati) - allowed):
            errors.append(
                ErroreValidazione(
                    campo=field_name,
                    codice=ErrorCode.CAMPO_NON_AMMESSO,
                    messaggio="Campo non previsto dal contratto dati",
                )
            )

        for field in fields:
            value_present = field.codice in request.dati and request.dati[field.codice] is not None
            if _is_required(field, bando_inglese=request.bando_inglese) and not value_present:
                errors.append(_missing_field_error(field))
                continue
            if value_present and not _matches_type(request.dati[field.codice], field.tipo_dato):
                errors.append(
                    ErroreValidazione(
                        campo=field.codice,
                        codice=ErrorCode.TIPO_NON_VALIDO,
                        messaggio=f"Tipo non valido per il campo {field.codice}",
                    )
                )

        return ValidazioneResponse(valido=not errors, errori=errors)


def get_payload_validation_service(db: Session = Depends(get_db)) -> PayloadValidationService:
    return PayloadValidationService(db)


def _is_required(field: ModelloCampoRichiesto, *, bando_inglese: bool) -> bool:
    if not field.obbligatorio:
        return False
    if field.lingua == "EN":
        return bando_inglese
    return True


def _missing_field_error(field: ModelloCampoRichiesto) -> ErroreValidazione:
    if field.lingua == "EN":
        return ErroreValidazione(
            campo=field.codice,
            codice=ErrorCode.CAMPO_INGLESE_MANCANTE,
            messaggio=f"Campo inglese obbligatorio mancante: {field.codice}",
        )
    return ErroreValidazione(
        campo=field.codice,
        codice=ErrorCode.CAMPO_OBBLIGATORIO,
        messaggio=f"Campo obbligatorio mancante: {field.codice}",
    )


def _matches_type(value: Any, tipo_dato: str) -> bool:
    match tipo_dato:
        case "string":
            return isinstance(value, str)
        case "number":
            return (isinstance(value, int | float)) and not isinstance(value, bool)
        case "date":
            if not isinstance(value, str):
                return False
            try:
                date.fromisoformat(value)
            except ValueError:
                return False
            return True
        case "boolean":
            return isinstance(value, bool)
        case "array":
            return isinstance(value, list)
        case "object":
            return isinstance(value, dict)
        case _:
            return False
