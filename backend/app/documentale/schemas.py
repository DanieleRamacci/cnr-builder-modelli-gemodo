"""Grammatica del documento composto: blocchi, asset, pagina (003 T002).

Queste definizioni nascevano in `app/quality/schemas.py`, che descrive le
entita' della readiness di qualita' della `009`. Finche' nessuno le usava a
runtime la collocazione era indifferente; ora le sezioni di una versione
modello ne serializzano una lista, e far dipendere `catalog`/`builder` dal
modulo che verifica la qualita' del progetto avrebbe invertito il verso della
dipendenza - il dominio non dipende da chi lo ispeziona.

Sono quindi **spostate qui**, non ricopiate: `app/quality/schemas.py` le
importa da questo modulo, cosi' la `009` continua a vedere gli stessi nomi e
non esistono due definizioni che possono divergere. E' l'alternativa che
`003` T002 prevede esplicitamente quando la separazione fra moduli rende
scomodo l'import diretto.

`GEMODO_DOCUMENT_V1` e' il formato: struttura controllata, nessun HTML o CSS
libero, nessuno script. I placeholder sono validati contro i campi del modello
alla scrittura delle sezioni e alla pubblicazione (003 US2).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

FORMATO_DOCUMENTALE = "GEMODO_DOCUMENT_V1"


class DocumentaleBaseModel(BaseModel):
    """Base rigida: una chiave sconosciuta e' un errore, non un'estensione.

    Il documento e' una struttura controllata (decisione 2026-07-31): accettare
    chiavi non previste significherebbe far entrare contenuto arbitrario dalla
    porta di servizio, che e' proprio cio' che il formato esclude.
    """

    model_config = ConfigDict(extra="forbid")


class TipoBloccoDocumento(str, Enum):
    INTESTAZIONE = "INTESTAZIONE"
    LOGO = "LOGO"
    TITOLO = "TITOLO"
    PARAGRAFO = "PARAGRAFO"
    TABELLA = "TABELLA"
    COLONNE = "COLONNE"
    FIRMA = "FIRMA"
    FOOTER = "FOOTER"
    INTERRUZIONE_PAGINA = "INTERRUZIONE_PAGINA"
    ELENCO = "ELENCO"


class PosizionamentoBlocco(str, Enum):
    TOP = "TOP"
    BODY = "BODY"
    BOTTOM_LEFT = "BOTTOM_LEFT"
    BOTTOM_RIGHT = "BOTTOM_RIGHT"
    BOTTOM_CENTER = "BOTTOM_CENTER"
    INLINE = "INLINE"
    COLUMN_LEFT = "COLUMN_LEFT"
    COLUMN_RIGHT = "COLUMN_RIGHT"


class AllineamentoTesto(str, Enum):
    """Come si dispone il testo **dentro** il blocco (012 FR-004).

    Distinto da `PosizionamentoBlocco`, che dice dove sta il blocco nella
    pagina: un paragrafo nel `BODY` puo' essere giustificato o centrato, e il
    posizionamento non sa dirlo.
    """

    SINISTRA = "SINISTRA"
    CENTRO = "CENTRO"
    DESTRA = "DESTRA"
    GIUSTIFICATO = "GIUSTIFICATO"


class TipoMarcatore(str, Enum):
    NUMERICO = "NUMERICO"
    ALFABETICO = "ALFABETICO"
    PUNTATO = "PUNTATO"


class FrammentoTesto(DocumentaleBaseModel):
    """Porzione di paragrafo con la propria enfasi (012 FR-001).

    `testo` e' testo puro: il formato non definisce alcun linguaggio di
    marcatura, quindi nessun carattere vi ha significato speciale. Il markup e'
    rifiutato alla scrittura (`quality/document_model.py`), non ripulito.
    """

    testo: str
    grassetto: bool = False
    corsivo: bool = False
    sottolineato: bool = False
    collegamento: str | None = None


class ElementoElenco(DocumentaleBaseModel):
    """Una voce di elenco. Il numero mostrato non e' un campo: lo calcola la resa (FR-015)."""

    livello: int = 0
    marcatore: TipoMarcatore = TipoMarcatore.NUMERICO
    frammenti: list[FrammentoTesto] = Field(default_factory=list)


class MascheraIntestazione(str, Enum):
    """Le impaginazioni dell'intestazione che si possono scegliere (012 T065)."""

    LOGO_CENTRO_TESTO_SOTTO = "LOGO_CENTRO_TESTO_SOTTO"


class MascheraPiePagina(str, Enum):
    TESTO_SINISTRA_NUMERO_DESTRA = "TESTO_SINISTRA_NUMERO_DESTRA"


class IntestazionePagina(DocumentaleBaseModel):
    maschera: MascheraIntestazione = MascheraIntestazione.LOGO_CENTRO_TESTO_SOTTO
    # Il logo e' quello caricato per il tipo documento: qui si dice solo se usarlo.
    con_logo: bool = True
    testo: list[FrammentoTesto] = Field(default_factory=list)


class PiePagina(DocumentaleBaseModel):
    maschera: MascheraPiePagina = MascheraPiePagina.TESTO_SINISTRA_NUMERO_DESTRA
    testo: list[FrammentoTesto] = Field(default_factory=list)
    numerazione_pagine: bool = True


class CornicePagina(DocumentaleBaseModel):
    """Cio' che si ripete su **ogni** pagina (012 FR-011).

    Appartiene al tipo documento, non al modello: vale per tutti i modelli di
    quel tipo. La impostano il gestore del contesto e l'amministratore
    (chiarimento del 2026-10-01). Intestazione e pie' di pagina sono
    indipendenti: si puo' averne uno solo. Il testo usa la grammatica a
    frammenti dei blocchi, con le stesse regole: niente markup.
    """

    intestazione: IntestazionePagina | None = None
    pie_pagina: PiePagina | None = None


class BloccoDocumento(DocumentaleBaseModel):
    """Elemento visuale ammesso nel modello documentale controllato.

    Dalla 012 il testo e' una sequenza di `frammenti`, non una stringa: il
    campo `contenuto` non esiste piu' e un blocco che lo porta e' rifiutato da
    `extra="forbid"` (FR-016, una sola forma).
    """

    id: str
    tipo: TipoBloccoDocumento
    frammenti: list[FrammentoTesto] = Field(default_factory=list)
    allineamento: AllineamentoTesto | None = None
    elementi: list[ElementoElenco] = Field(default_factory=list)
    posizionamento: PosizionamentoBlocco
    ordine: int = 0
    stile: str | None = None
    placeholder_usati: list[str] = Field(default_factory=list)
    regole_layout: dict[str, str] = Field(default_factory=dict)
    asset_ref: str | None = None
    colonne: list[str] = Field(default_factory=list)


class TipoAsset(str, Enum):
    LOGO = "LOGO"
    IMMAGINE = "IMMAGINE"
    TIMBRO = "TIMBRO"
    ALTRO = "ALTRO"


class AssetDocumento(DocumentaleBaseModel):
    id: str
    tipo: TipoAsset
    versione: str | None = None
    storage_ref: str | None = None
    hash_file: str | None = None
    dimensioni_consentite: str | None = None
    spec_owner: str | None = None


class PaginaDocumento(DocumentaleBaseModel):
    size: str = "A4"
    orientamento: str = "PORTRAIT"
    margini: str = "standard-cnr"


class ModelloDocumentaleControllato(DocumentaleBaseModel):
    """Sorgente strutturata e versionata del layout/contenuto documentale."""

    id: str
    modello_versione_id: str
    formato: str = FORMATO_DOCUMENTALE
    pagina: PaginaDocumento = Field(default_factory=PaginaDocumento)
    regioni: list[str] = Field(default_factory=list)
    blocchi: list[BloccoDocumento] = Field(default_factory=list)
    asset: list[AssetDocumento] = Field(default_factory=list)
    stili_ammessi: list[str] = Field(default_factory=list)
    placeholder_usati: list[str] = Field(default_factory=list)
    spec_owner: str
    contiene_html_libero: bool = False
    contiene_css_libero: bool = False
    contiene_script: bool = False
