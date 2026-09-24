"""Pydantic schemas for the builder admin API (creation/publication of models)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.builder.repository import NOME_LIVELLO
from app.discovery.schemas import CatalogoDiscovery

StrutturaDisponibileResponse = CatalogoDiscovery
StrutturaTipoDocumentoResponse = CatalogoDiscovery


LinguaFiltro = Literal["IT", "EN"]
StatoVersioneFiltro = Literal[
    "BOZZA", "IN_REVISIONE", "APPROVATO", "PUBBLICATO", "ARCHIVIATO", "SOSPESO"
]


class FiltriModelli(BaseModel):
    """Filtri dell'elenco modelli, applicati lato server (007 FR-028).

    Vivono qui e non nel client perche' la lista e' paginata: filtrare dopo
    `limit` restituirebbe la pagina in mano invece dell'insieme. Un campo
    assente significa "non filtrare"; per selezionare i modelli senza livello
    si usa il token esplicito `TUTTI`.
    """

    model_config = ConfigDict(extra="forbid")

    codice_tipo_documento: str | None = Field(default=None, min_length=1, max_length=128)
    integrazione_id: uuid.UUID | None = None
    codice_tipologia: str | None = Field(default=None, min_length=1, max_length=128)
    codice_categoria: str | None = Field(default=None, min_length=1, max_length=128)
    lingua: LinguaFiltro | None = None
    livello_professionale: str | None = Field(default=None, min_length=1, max_length=64)
    variante: str | None = Field(default=None, min_length=1, max_length=64)
    stato_versione: StatoVersioneFiltro | None = None
    ricerca: str | None = Field(default=None, min_length=1, max_length=200)


class VociFiltriModelli(BaseModel):
    """Valori selezionabili nei filtri dell'elenco modelli (007 FR-028).

    Ricavati dai modelli esistenti nel contesto, non dall'albero discovery:
    l'elenco modelli non dipende dal discovery e non deve iniziare a dipenderne
    per riempire delle tendine. Una voce presente qui produce sempre almeno un
    risultato.
    """

    codici_tipo_documento: list[str]
    codici_tipologia: list[str]
    codici_categoria: list[str]
    lingue: list[str]
    livelli_professionali: list[str]
    varianti: list[str]


class IntegrazioneVisibile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    codice: str
    nome: str
    codice_contesto: str


class CreaModelloRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codice_tipo_documento: str = Field(min_length=1)
    integrazione_id: uuid.UUID | None = None
    percorso_categorizzazione: list[str] | None = Field(default=None, min_length=1, max_length=64)
    codice_categoria: str | None = None
    codice_tipologia: str | None = None
    # 011: la categorizzazione arriva come mappa per nome di dimensione. Una
    # chiave assente significa dimensione non valorizzata, ed e' l'unico modo per
    # esprimerlo (FR-006); un valore vuoto e' rifiutato perche' renderebbe
    # ambigua quella distinzione.
    dimensioni: dict[str, str] = Field(default_factory=dict)
    # Campi di transizione, equivalenti alle chiavi corrispondenti della mappa.
    # Restano finche' il frontend non ha adottato `dimensioni`.
    lingua: Literal["IT", "EN"] | None = None
    livello_professionale: str | None = Field(default=None, min_length=1, max_length=64)

    def dimensioni_effettive(self) -> dict[str, str]:
        """La mappa, con i campi di transizione fusi dentro."""
        effettive = dict(self.dimensioni)
        if self.lingua is not None:
            effettive["lingua"] = self.lingua
        if self.livello_professionale is not None:
            effettive[NOME_LIVELLO] = self.livello_professionale
        return effettive

    @model_validator(mode="after")
    def verifica_selezione(self) -> CreaModelloRequest:
        if self.percorso_categorizzazione is None and not self.codice_categoria:
            raise ValueError("Indicare percorso_categorizzazione oppure codice_categoria")
        if self.percorso_categorizzazione is not None and any(not codice for codice in self.percorso_categorizzazione):
            raise ValueError("Il percorso non puo' contenere codici vuoti")
        for nome, valore in self.dimensioni.items():
            if not nome or not valore:
                raise ValueError("Nome e valore di una dimensione non possono essere vuoti")
        # Indicare lo stesso nome due volte con valori diversi e' un errore, non
        # una precedenza silenziosa: il chiamante non saprebbe quale ha vinto.
        for campo, nome in (("lingua", "lingua"), ("livello_professionale", NOME_LIVELLO)):
            valore = getattr(self, campo)
            if valore is not None and self.dimensioni.get(nome) not in (None, valore):
                raise ValueError(f"'{campo}' e dimensioni['{nome}'] indicano valori diversi")
        return self


class ModelloResponse(BaseModel):
    id: str
    public_id: int | None
    codice: str
    nome: str
    codice_tipo_documento: str
    codice_categoria: str
    codice_tipologia: str | None
    percorso_categorizzazione: list[str]
    variante: str
    # 011: l'insieme completo. `lingua` e `livello_professionale` restano come
    # proiezione per il frontend non ancora migrato, e sono ora nullable: un
    # tipo documento che non dichiara la lingua non ne ha una da esporre.
    dimensioni: dict[str, str] = Field(default_factory=dict)
    lingua: str | None = None
    livello_professionale: str | None = None
    derivato_da_modello_id: str | None = None


class CreaEdizioneDerivataRequest(BaseModel):
    """Su quale dimensione, e con quale valore, derivare l'edizione (011 FR-013).

    `lingua` resta accettata come forma di transizione: e' il caso che la
    funzione copriva da sola prima che la derivazione si generalizzasse, ed e'
    l'unico che il bando usa oggi.
    """

    model_config = ConfigDict(extra="forbid")

    nome_dimensione: str | None = Field(default=None, min_length=1, max_length=64)
    valore: str | None = Field(default=None, min_length=1, max_length=64)
    lingua: Literal["IT", "EN"] | None = None

    def dimensione_derivata(self) -> tuple[str, str]:
        if self.nome_dimensione is not None:
            return self.nome_dimensione, self.valore
        return "lingua", self.lingua

    @model_validator(mode="after")
    def verifica_selezione(self) -> CreaEdizioneDerivataRequest:
        if self.nome_dimensione is not None and self.valore is None:
            raise ValueError("Indicando 'nome_dimensione' serve anche 'valore'")
        if self.nome_dimensione is None and self.lingua is None:
            raise ValueError("Indicare 'nome_dimensione' e 'valore', oppure 'lingua'")
        if self.nome_dimensione == "lingua" and self.lingua not in (None, self.valore):
            raise ValueError("'lingua' e 'valore' indicano valori diversi")
        return self


class CampoVersioneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codice: str
    lingua: str = "IT"


class CreaVersioneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campi: list[CampoVersioneRequest]


class VersioneResponse(BaseModel):
    id: str
    public_id: int | None
    modello_id: str
    numero_versione: int
    stato: str
    pubblicato_at: datetime | None


class PolicyDimensioneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome_dimensione: str = Field(min_length=1, max_length=64)
    consente_valore_generico: bool
    # 011 DEC-011-DEFAULT-DIMENSIONE: il valore che il form preseleziona.
    # None significa "nessuna preselezione", che per una dimensione generica
    # equivale a "il default e' non valorizzarla".
    valore_default: str | None = Field(default=None, min_length=1, max_length=64)
    # Chiudere il generico lascia senza valore ammesso i modelli pubblicati che
    # non valorizzano la dimensione. Il cambio resta permesso - la scelta e'
    # dell'admin per DEC-011-POLICY-LINGUA-ALL-ADMIN, e vietarlo creerebbe un
    # vicolo cieco - ma non deve poter accadere per distrazione.
    conferma_impatto: bool = False


class PolicyDimensioneResponse(BaseModel):
    nome_dimensione: str
    consente_valore_generico: bool
    valore_default: str | None = None
    modelli_pubblicati_che_la_valorizzano: int = 0
    # Modelli pubblicati che NON la valorizzano: l'insieme che chiudere il
    # generico lascia senza valore ammesso, e quindi la conseguenza da leggere
    # prima di chiuderlo.
    modelli_pubblicati_senza_valore: int = 0


class DimensioneNonConfigurata(BaseModel):
    """Una dimensione vista sull'albero live ma priva di policy registrata.

    `NodoDiscovery` ha `extra="allow"`, quindi senza questa segnalazione una
    dimensione nuova sparirebbe in silenzio (DEC-002-POLICY).
    """

    nome_dimensione: str
    motivo: str = "Nessuna policy registrata per questa dimensione"
    modelli_pubblicati_che_la_valorizzano: int = 0


class PolicyDimensioniResponse(BaseModel):
    codice_tipo_documento: str
    policy: list[PolicyDimensioneResponse]
    dimensioni_non_configurate: list[DimensioneNonConfigurata]


class CampoVersioneResponse(BaseModel):
    """Il contratto dati della versione, come lo espone l'anteprima del builder.

    Deliberatamente identico per forma a `CampoRichiestoSchema` del catalogo, ma
    leggibile anche su una BOZZA: il catalogo risponde solo su versioni
    pubblicate.
    """

    codice: str
    etichetta: str
    tipo: str
    # Assente se la foglia discovery dichiara le lingue per se' (contratto 0.7.0):
    # il campo vale allora per tutte, e non ha una lingua propria da esporre.
    lingua: str | None = None
    obbligatorio: bool
    ordine: int
    descrizione: str | None = None


class VersioneDettaglioResponse(VersioneResponse):
    campi: list[CampoVersioneResponse]


class ModelloDettaglioResponse(ModelloResponse):
    codice_contesto: str
    integrazione_id: uuid.UUID | None
    created_at: datetime
    dimensioni_non_disponibili: list[str] = Field(default_factory=list)
    versioni: list[VersioneDettaglioResponse]


class ModelloGestioneResponse(ModelloResponse):
    codice_contesto: str
    integrazione_id: uuid.UUID | None
    created_at: datetime
    versioni: list[VersioneResponse]
