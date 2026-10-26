"""Payload validation against a published model data contract."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.catalog import repository
from app.catalog.models import ModelloCampoRichiesto
from app.common.errors import ErrorCode, PayloadValidationDomainError
from app.common.security import PrincipalGEMODO, ROLE_DOCUMENTI_GENERATORE, verifica_permesso_contesto
from app.db.session import get_db
from app.validation.schemas import ErroreValidazione, ValidazioneRequest, ValidazioneResponse


class PayloadValidationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def validate_payload(self, request: ValidazioneRequest, principal: PrincipalGEMODO) -> ValidazioneResponse:
        version = repository.get_model_version_by_public_id(self.db, request.modello_versione_id)
        if version is None or not verifica_permesso_contesto(
            principal, version.modello.tipo_documento.codice_contesto, ROLE_DOCUMENTI_GENERATORE,
        ):
            # Direct-ID access: nonexistent and out-of-context are the same public
            # response (FR-037) - never reveal that a forbidden version exists.
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
            if field.obbligatorio and not value_present:
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
                continue
            if field.sotto_campi is not None:
                elementi = request.dati.get(field.codice) or []
                if field.obbligatorio and not elementi:
                    errors.append(_missing_field_error(field))
                    continue
                errors.extend(_errori_elementi(field.codice, elementi, field.sotto_campi))

        return ValidazioneResponse(valido=not errors, errori=errors)


def get_payload_validation_service(db: Session = Depends(get_db)) -> PayloadValidationService:
    return PayloadValidationService(db)


def _missing_field_error(field: ModelloCampoRichiesto) -> ErroreValidazione:
    return ErroreValidazione(
        campo=field.codice,
        codice=ErrorCode.CAMPO_OBBLIGATORIO,
        messaggio=f"Campo obbligatorio mancante: {field.codice}",
    )


_CHIAVI_ELEMENTO = ("codice", "descrizione", "campi")


def _errori_elementi(
    campo: str, elementi: list[Any], sotto_campi: list[dict[str, Any]],
) -> list[ErroreValidazione]:
    """Gli elementi di un campo ripetibile, ciascuno contro i sotto-campi della versione (014 FR-011).

    Il percorso dice quale elemento e quale sotto-campo (FR-012):
    `articolazioni[TEMA_A].campi.numero_posti`. Se l'elemento non ha un codice
    utilizzabile si indica la posizione nella lista, da 0 come nel JSON.
    """
    errori: list[ErroreValidazione] = []
    dichiarati = {sotto["codice"]: sotto for sotto in sotto_campi}
    visti: set[str] = set()
    for indice, elemento in enumerate(elementi):
        if not isinstance(elemento, dict):
            errori.append(ErroreValidazione(
                campo=f"{campo}[{indice}]", codice=ErrorCode.TIPO_NON_VALIDO,
                messaggio="Ogni elemento deve essere un oggetto con codice, descrizione e campi",
            ))
            continue
        codice = elemento.get("codice")
        if not isinstance(codice, str) or not codice.strip():
            errori.append(ErroreValidazione(
                campo=f"{campo}[{indice}].codice", codice=ErrorCode.CAMPO_OBBLIGATORIO,
                messaggio=f"Elemento {indice} di {campo} senza codice",
            ))
            dove = f"{campo}[{indice}]"
        else:
            dove = f"{campo}[{codice}]"
            if codice in visti:
                errori.append(ErroreValidazione(
                    campo=campo, codice=ErrorCode.CODICE_ELEMENTO_DUPLICATO,
                    messaggio=f"Il codice '{codice}' compare in piu' elementi di {campo}",
                ))
            visti.add(codice)
        for chiave in sorted(set(elemento) - set(_CHIAVI_ELEMENTO)):
            errori.append(ErroreValidazione(
                campo=f"{dove}.{chiave}", codice=ErrorCode.CAMPO_NON_AMMESSO,
                messaggio="Un elemento ha solo codice, descrizione e campi",
            ))
        descrizione = elemento.get("descrizione")
        if not isinstance(descrizione, str) or not descrizione.strip():
            errori.append(ErroreValidazione(
                campo=f"{dove}.descrizione", codice=ErrorCode.CAMPO_OBBLIGATORIO,
                messaggio="La descrizione identifica l'elemento nel documento: e' obbligatoria",
            ))
        valori = elemento.get("campi", {})
        if not isinstance(valori, dict):
            errori.append(ErroreValidazione(
                campo=f"{dove}.campi", codice=ErrorCode.TIPO_NON_VALIDO,
                messaggio="'campi' deve essere un oggetto codice -> valore",
            ))
            continue
        for chiave in sorted(set(valori) - set(dichiarati)):
            errori.append(ErroreValidazione(
                campo=f"{dove}.campi.{chiave}", codice=ErrorCode.CAMPO_NON_AMMESSO,
                messaggio="Sotto-campo non previsto dal contratto dati",
            ))
        for sotto in sotto_campi:
            presente = valori.get(sotto["codice"]) is not None
            if sotto["obbligatorio"] and not presente:
                errori.append(ErroreValidazione(
                    campo=f"{dove}.campi.{sotto['codice']}", codice=ErrorCode.CAMPO_OBBLIGATORIO,
                    messaggio=f"Sotto-campo obbligatorio mancante: {sotto['codice']}",
                ))
            elif presente and not _matches_type(valori[sotto["codice"]], sotto["tipo"]):
                errori.append(ErroreValidazione(
                    campo=f"{dove}.campi.{sotto['codice']}", codice=ErrorCode.TIPO_NON_VALIDO,
                    messaggio=f"Tipo non valido per il sotto-campo {sotto['codice']}",
                ))
    return errori


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
