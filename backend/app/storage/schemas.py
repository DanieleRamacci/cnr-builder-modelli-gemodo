from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StatoDocumento(BaseModel):
    """Una riga del registro delle generazioni (013)."""

    riferimento: str
    stato: Literal["COMPLETATO", "FALLITO", "DATI_NON_VALIDI"]
    tipo_output: Literal["TEST"]
    sistema_richiedente: str
    external_context_id: str
    nome_file: str
    hash_dati: str
    hash_file: str | None
    dimensione_byte: int | None
    creato_il: datetime
    creato_da: str
    client_id: str | None = None
    modello_versione_id: int
    errore_messaggio: str | None = None
