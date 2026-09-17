from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.discovery.schemas import CampoDiscovery


Codice = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^\S+$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TipologiaInput(Input):
    codice: Codice
    descrizione: Annotated[str, Field(min_length=1, max_length=1024)]
    riferimento_esterno: str | None = None


class AttributoInput(Input):
    nome: Codice
    valori_ammessi: list[str] = Field(max_length=1024)
    valore_default: str | None = None

    @model_validator(mode="after")
    def validate_default(self):
        if len(set(self.valori_ammessi)) != len(self.valori_ammessi):
            raise ValueError("Valori ammessi duplicati")
        if self.valore_default is not None and self.valore_default not in self.valori_ammessi:
            raise ValueError("Default non presente nei valori ammessi")
        return self


class ProfiloInput(Input):
    codice: Codice
    descrizione: Annotated[str, Field(min_length=1, max_length=1024)]
    attributi: list[AttributoInput] = Field(default_factory=list, max_length=128)


class CombinazioneInput(Input):
    codice_tipologia: Codice
    codice_profilo: Codice


class CampoInput(CampoDiscovery):
    model_config = ConfigDict(extra="forbid")
    codice: Codice
    etichetta: Annotated[str, Field(min_length=1, max_length=255)]
    dipende_da_attributo_profilo: Codice | None = None


class StrutturaInput(Input):
    tipologie: list[TipologiaInput] = Field(default_factory=list, max_length=256)
    profili: list[ProfiloInput] = Field(default_factory=list, max_length=256)
    combinazioni: list[CombinazioneInput] = Field(default_factory=list, max_length=4096)
    campi: list[CampoInput] = Field(default_factory=list, max_length=4096)

    @model_validator(mode="after")
    def validate_references(self):
        groups = [[t.codice for t in self.tipologie], [p.codice for p in self.profili],
                  [c.codice for c in self.campi],
                  [(c.codice_tipologia, c.codice_profilo) for c in self.combinazioni]]
        groups.extend([[a.nome for a in p.attributi] for p in self.profili])
        if any(len(g) != len(set(g)) for g in groups):
            raise ValueError("Codici/combinazioni duplicati nella definizione")
        profili = {p.codice: p for p in self.profili}
        tipi = {t.codice for t in self.tipologie}
        for combo in self.combinazioni:
            if combo.codice_tipologia not in tipi or combo.codice_profilo not in profili:
                raise ValueError("Combinazione con tipologia/profilo inesistente")
        for campo in self.campi:
            fonte = campo.dipende_da_attributo_profilo
            if fonte is None:
                continue
            if campo.tipo != "string":
                raise ValueError("Gli attributi profilo di questo incremento richiedono un campo string")
            if any(k in (campo.validazione or {}) for k in ("enum", "default", "fonte_opzioni")):
                raise ValueError("Un campo dipendente eredita opzioni/default dal profilo")
            for profilo in self.profili:
                attributo = next((a for a in profilo.attributi if a.nome == fonte), None)
                if attributo is None or (campo.obbligatorio and not attributo.valori_ammessi):
                    raise ValueError("Attributo profilo mancante o senza opzioni obbligatorie")
        return self

    def mancanze(self) -> list[str]:
        missing = [name for name in ("tipologie", "profili", "combinazioni", "campi") if not getattr(self, name)]
        used_types = {c.codice_tipologia for c in self.combinazioni}
        used_profiles = {c.codice_profilo for c in self.combinazioni}
        if any(t.codice not in used_types for t in self.tipologie):
            missing.append("tipologie senza combinazioni")
        if any(p.codice not in used_profiles for p in self.profili):
            missing.append("profili senza combinazioni")
        return missing


class TipoDocumentoCreate(Input):
    codice: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^\S+$")]
    nome: Annotated[str, Field(min_length=1, max_length=255)]
    codice_contesto: Annotated[str, Field(min_length=1, max_length=64, pattern=r"^\S+$")]
    struttura: StrutturaInput = Field(default_factory=StrutturaInput)


class TipoDocumentoDashboard(BaseModel):
    codice: str
    nome: str
    codice_contesto: str
    stato_integrazione: str
    versione_schema_corrente: int | None
    versione_definizione: int | None
    esito_ultimo_test: dict[str, Any] | None = None
    data_ultimo_test: datetime | None = None


class SchemaResponse(BaseModel):
    codice_tipo_documento: str
    versione: int
    generato_il: datetime
    schema_documentazione: dict[str, Any] = Field(serialization_alias="schema")


class IntegrazioneCreate(Input):
    codice: Annotated[str, Field(min_length=1, max_length=100)]
    nome: Annotated[str, Field(min_length=1, max_length=200)]
    codice_contesto: Annotated[str, Field(min_length=1, max_length=64)]


class IntegrazioneUpdate(Input):
    revisione_attesa: Annotated[int, Field(ge=1)]
    nome: Annotated[str, Field(min_length=1, max_length=200)]
    url: Annotated[str, Field(min_length=1, max_length=2048)] | None
    timeout_ms: Annotated[int, Field(ge=1000, le=10000)]


class VerificaRequest(Input):
    revisione_attesa: Annotated[int, Field(ge=1)]


class ErroreVerifica(BaseModel):
    codice: str
    messaggio: str
    percorso: str | None = None


class UltimaVerifica(BaseModel):
    data: datetime
    revisione: int
    versione_contratto: str
    esito: Literal["CONFORME", "NON_CONFORME", "NON_RAGGIUNGIBILE"]
    errori: list[ErroreVerifica]


class IntegrazioneAdmin(BaseModel):
    id: uuid.UUID
    codice: str
    nome: str
    codice_contesto: str
    modalita: str
    revisione: int
    url: str | None
    timeout_ms: int
    stato: str
    ultima_verifica: UltimaVerifica | None
