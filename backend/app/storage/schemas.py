from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StatoDocumento(BaseModel):
    riferimento: str
    stato: Literal["COMPLETATO", "FALLITO"]
    tipo_output: Literal["TEST"]
    nome_file: str
    hash_file: str | None
    dimensione_byte: int | None
    creato_il: datetime
    modello_versione_id: int
    errore_messaggio: str | None = None
