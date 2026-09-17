from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.validation.schemas import ValidazioneResponse


class EsitoGenerazione(BaseModel):
    stato: Literal["COMPLETATO", "FALLITO", "DATI_NON_VALIDI"]
    messaggio: str
    modello_versione_id: int
    external_context_id: str
    riferimento_documentale: str | None = None
    validazione: ValidazioneResponse
