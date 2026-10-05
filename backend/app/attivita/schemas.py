from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventoAttivitaResponse(BaseModel):
    quando: datetime
    categoria: str
    azione: str
    esito: str
    soggetto: str | None = None
    username: str | None = None
    client_id: str | None = None
    contesto: str | None = None
    oggetto_tipo: str | None = None
    oggetto_id: str | None = None
    oggetto_nome: str | None = None
    dettaglio: dict[str, Any]


class RegistroAttivitaResponse(BaseModel):
    eventi: list[EventoAttivitaResponse]
    # C'e' almeno un'altra pagina: si chiede con `salto` + `limite`.
    altri: bool
