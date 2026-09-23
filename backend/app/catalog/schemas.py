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


class LinguaModello(StrEnum):
    IT = "IT"
    EN = "EN"


class TipoCampo(StrEnum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ModelloCatalogoSchema(BaseModel):
    modello_id: int = Field(..., ge=1)
    modello_versione_id: int = Field(..., ge=1)
    codice: str
    descrizione: str
    variante: str = "STANDARD"
    # 011 DEC-011-CONTRATTO-GEBAN-ADDITIVO. `lingua` diventa nullable: e' una
    # modifica schema-breaking ma behavior-safe, perche' `search_modelli` impone
    # `tipo_documento`, quindi GEBAN non riceve mai una risposta mista, e tutti
    # i tipi documento che consuma oggi dichiarano la lingua con policy
    # obbligatoria. Il null compare solo per tipi che ancora non esistono.
    # Un valore sentinella tipo "N/A" e' stato scartato: conserverebbe
    # l'obbligatorieta' formale al prezzo di un dato falso nella risposta.
    lingua: LinguaModello | None = None
    livello_professionale: str | None = None
    # L'insieme completo. `lingua` e `livello_professionale` sopra ne sono una
    # proiezione, non un'informazione diversa: GEBAN puo' migrare quando vuole.
    dimensioni: dict[str, str] = Field(default_factory=dict)
    versione: int
    stato: str = "PUBBLICATO"
    data_inizio_validita: date | None = None
    data_fine_validita: date | None = None
    pubblicato_at: datetime | None = None
    edizioni_derivate: list[ModelloCatalogoSchema] = Field(default_factory=list)


class ModelloSearchResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tipo_documento": "BANDO_CONCORSO",
                "profilo": "COLLABORATORE_TECNICO_ER",
                "codice_tipologia": "TD",
                "modalita": "OPERATIVA",
                "fallback_applicato": False,
                "livello_richiesto": "VI",
                "livello_risolto": "VI",
                "modelli": [
                    {
                        "modello_id": 1,
                        "modello_versione_id": 1,
                        "codice": "demo-bando-concorso-standard-v1",
                        "descrizione": "demo-bando-concorso-standard-v1",
                        "variante": "STANDARD",
                        "lingua": "IT",
                        "livello_professionale": "VI",
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
    fallback_applicato: bool = False
    # 011 FR-010: con piu' dimensioni che ammettono il generico, il booleano da
    # solo non dice piu' cosa e' successo. `livello_richiesto`/`livello_risolto`
    # restano come caso particolare, per non rompere GEBAN.
    dimensioni_rilassate: list[str] = Field(default_factory=list)
    livello_richiesto: str | None = None
    livello_risolto: str | None = None
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
