"""Pure PDF rendering (004 MVP FR-019/020; 003 T018; 012 T012-T017).

No file I/O, no DB, no HTTP - content in, PDF bytes out. The only file read is
the bundled font, which is part of the code, not of the content.

Two shapes are rendered. A model **with sections** produces the composed
document: its blocks, in order, honouring type and placement (003). A model
without sections falls back to the label/value list, which is what every model
created before `003` still is.

Always marked TEST/non-official: ADR 0002 states this increment has no
"official" generation path at all, and `003` T020 requires that marking to
survive until `004` provides one. Rendering the real body does not make the
document official.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from PIL import Image

from app.documentale.schemas import (
    AllineamentoTesto,
    BloccoDocumento,
    CornicePagina,
    ElementoElenco,
    FrammentoTesto,
    TipoBloccoDocumento,
    TipoMarcatore,
)

_MARCA_ANTEPRIMA = "ANTEPRIMA DELLA BOZZA - VALORI FAC-SIMILE"

# Titillium Web (OFL), il font delle linee guida di design della PA. Non e'
# estetica: il core font usato prima e' limitato a latin-1 e una virgoletta
# curva sollevava `FPDFUnicodeEncodingException`, cioe' un documento FALLITO
# (012 research.md R1).
_FONT = "TitilliumWeb"
_CARTELLA_FONT = Path(__file__).parent / "fonts"
_VARIANTI_FONT = {
    "": "TitilliumWeb-Regular.ttf",
    "B": "TitilliumWeb-Bold.ttf",
    "I": "TitilliumWeb-Italic.ttf",
    "BI": "TitilliumWeb-BoldItalic.ttf",
}

# Il posizionamento e' una grammatica, non una coordinata. Dalla 012 un blocco
# puo' dichiarare il proprio `allineamento`; questa derivazione resta solo come
# default per i blocchi che non lo dichiarano (T015).
_ALLINEAMENTO = {
    "TOP": "C",
    "BODY": "L",
    "BOTTOM_LEFT": "L",
    "BOTTOM_RIGHT": "R",
    "BOTTOM_CENTER": "C",
    "INLINE": "L",
    "COLUMN_LEFT": "L",
    "COLUMN_RIGHT": "R",
}
_ALLINEAMENTO_ESPLICITO = {
    AllineamentoTesto.SINISTRA: "L",
    AllineamentoTesto.CENTRO: "C",
    AllineamentoTesto.DESTRA: "R",
    AllineamentoTesto.GIUSTIFICATO: "J",
}

# `stile` lo scrive l'editor (`H1`/`H2`) e fino alla 012 nessuno lo leggeva:
# l'editor mostrava un titolo e il PDF un paragrafo (FR-008, T016).
_STILI_TITOLO = {"H1": 14, "H2": 12}

_COLORE_COLLEGAMENTO = (0, 102, 204)

# Rientri di elenco, in mm, quelli predefiniti di Word: marcatore a 0,63 cm,
# testo a 1,27 cm, e ogni livello (FR-003: due) sposta entrambi di 1,27 cm.
# Il testo della voce va a capo allineato al testo, non al marcatore: e' il
# rientro sporgente dei bandi.
_RIENTRO_MARCATORE = 6.35
_RIENTRO_TESTO = 12.7
_PASSO_LIVELLO = 12.7
_DIMENSIONE_ELENCO = 11
# Il punto elenco si disegna invece di scriverlo: il carattere `•` di
# Titillium e' minuscolo, quello di Word e' un cerchio pieno di circa 1,5 mm.
# Al secondo livello Word usa un cerchio vuoto.
_RAGGIO_PUNTO = 0.75


def _marca_anteprima(pdf: FPDF) -> None:
    """Solo l'anteprima della bozza dice di esserlo: ha valori fac-simile.

    Il documento generato non porta piu' ne' il titolo del modello ne' la
    scritta "DOCUMENTO DI TEST - NON UFFICIALE" (decisione dell'utente
    2026-10-07, 003 T020): comincia dal primo blocco scritto dal gestore. Il
    titolo resta nei metadati del PDF (`_metadati`), dove non si vede.
    """
    pdf.set_font(_FONT, "B", 10)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 6, _MARCA_ANTEPRIMA, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)


# Misure della cornice, in mm (012 T068). La testata non ha un'altezza fissa:
# la si calcola da cio' che contiene, e il corpo comincia sotto.
_ALTO_TESTATA = 8
_ALTEZZA_LOGO = 16
_RIGA_TESTATA = 4.5
_MARGINE_PIEDE = 22


@dataclass(frozen=True)
class InizioPagina:
    """Dove comincia una pagina dopo la prima (012 T080).

    `ordine` e `voce` sono il blocco (e la voce d'elenco) che si sta scrivendo
    quando la pagina finisce; `riga` e' quante righe di quel blocco sono
    rimaste sulla pagina prima: 0 se il blocco comincia sulla pagina nuova.
    Senza blocco (`ordine` assente) la pagina e' cominciata fra un blocco e
    l'altro. L'editor la usa per disegnare dove finisce un foglio.

    Le misure, in mm, sono lo spazio fra il foglio che finisce e il testo
    della pagina nuova (012 T083): `libero` e' cio' che resta vuoto in fondo
    alla pagina prima (meno di una riga, o il resto della pagina dopo
    un'interruzione), `basso` la zona del pie' di pagina, `alto` quella
    dell'intestazione della pagina nuova.
    """

    pagina: int
    ordine: int | None
    voce: int | None
    riga: int
    libero: float = 0.0
    basso: float = 0.0
    alto: float = 0.0


def _righe_testata(frammenti: list[FrammentoTesto]) -> list[list[FrammentoTesto]]:
    """Le righe dell'intestazione, ciascuna con i suoi frammenti."""
    righe: list[list[FrammentoTesto]] = [[]]
    for frammento in frammenti:
        for i, pezzo in enumerate(frammento.testo.split("\n")):
            if i:
                righe.append([])
            if pezzo:
                righe[-1].append(frammento.model_copy(update={"testo": pezzo}))
    return [riga for riga in righe if riga]


class _PdfConCornice(FPDF):
    """Un PDF che disegna la cornice su **ogni** pagina (012 T044, T068).

    `header` e `footer` li chiama fpdf2 a ogni pagina nuova, comprese quelle
    aperte dall'a capo automatico in mezzo a un elenco: e' per questo che la
    cornice sta qui e non in un blocco, che comparirebbe una volta sola.
    """

    def __init__(self, cornice: CornicePagina | None, logo: bytes | None) -> None:
        super().__init__(format="A4")
        self.cornice = cornice
        self.intestazione = cornice.intestazione if cornice else None
        self.logo = logo if self.intestazione and self.intestazione.con_logo else None
        self.righe = _righe_testata(self.intestazione.testo) if self.intestazione else []
        # Dove cominciano le pagine, se chi rende lo chiede (012 T080).
        self.inizi_pagina: list[InizioPagina] | None = None
        self._segno: tuple[int, int | None] | None = None
        self._y_segno = 0.0
        self._interlinea = _interlinea(11)
        self._righe_segno = 0

    def segna(self, ordine: int, voce: int | None = None) -> None:
        """Il blocco (o la voce) che comincia ora: le pagine nuove si riferiscono a lui."""
        self._segno = (ordine, voce)
        self._y_segno = self.get_y()
        self._righe_segno = 0

    def misura_righe(self, dimensione: float) -> None:
        """Le righe del blocco segnato partono da qui, con questa interlinea."""
        self._y_segno = self.get_y()
        self._interlinea = _interlinea(dimensione)

    def add_page(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.inizi_pagina is not None and self.page > 0:
            misure = {
                "libero": max(0.0, self.page_break_trigger - self.get_y()),
                "basso": self.h - self.page_break_trigger,
                "alto": self.t_margin,
            }
            if self._segno is None:
                self.inizi_pagina.append(InizioPagina(self.page + 1, None, None, 0, **misure))
            else:
                scritte = round((self.get_y() - self._y_segno) / self._interlinea)
                self._righe_segno += max(0, scritte)
                ordine, voce = self._segno
                self.inizi_pagina.append(
                    InizioPagina(self.page + 1, ordine, voce, self._righe_segno, **misure)
                )
        super().add_page(*args, **kwargs)
        self._y_segno = self.get_y()

    def altezza_testata(self) -> float:
        """Dove comincia il corpo: sotto logo, righe e linea di separazione."""
        if self.intestazione is None or not (self.logo or self.righe):
            return 0
        altezza = _ALTO_TESTATA + (_ALTEZZA_LOGO + 2 if self.logo else 0)
        return altezza + len(self.righe) * _RIGA_TESTATA + 6

    def header(self) -> None:
        # Maschera LOGO_CENTRO_TESTO_SOTTO, la sola per ora: logo centrato,
        # righe centrate sotto, una linea a separare dal corpo.
        if not self.altezza_testata():
            return
        y = _ALTO_TESTATA
        if self.logo:
            with Image.open(BytesIO(self.logo)) as immagine:
                larghezza = _ALTEZZA_LOGO * immagine.width / immagine.height
            self.image(BytesIO(self.logo), x=(self.w - larghezza) / 2, y=y, h=_ALTEZZA_LOGO)
            y += _ALTEZZA_LOGO + 2
        for riga in self.righe:
            # L'enfasi di una riga e' quella dei suoi frammenti; se sono misti
            # la riga resta in tondo: l'intestazione si centra riga per riga.
            varianti = {_variante(f, grassetto_base=False, corsivo_base=False) for f in riga}
            self.set_font(_FONT, varianti.pop() if len(varianti) == 1 else "", 9)
            self.set_xy(self.l_margin, y)
            self.cell(0, _RIGA_TESTATA, "".join(f.testo for f in riga), align="C")
            y += _RIGA_TESTATA
        linea = y + 2
        self.set_draw_color(160, 160, 160)
        self.line(self.l_margin, linea, self.w - self.r_margin, linea)
        self.set_draw_color(0, 0, 0)
        self.set_xy(self.l_margin, self.t_margin)

    def footer(self) -> None:
        piede = self.cornice.pie_pagina if self.cornice else None
        if piede is None:
            return
        self.set_y(-14)
        for frammento in piede.testo:
            self.set_font(_FONT, _variante(frammento, grassetto_base=False, corsivo_base=False), 8)
            self.write(4, frammento.testo)
        if piede.numerazione_pagine:
            self.set_y(-14)
            self.set_font(_FONT, "", 8)
            # `{nb}` e' il totale delle pagine, che fpdf2 conosce solo alla fine.
            self.cell(0, 4, f"Pagina {self.page_no()} di {{nb}}", align="R")


def _nuovo_pdf(cornice: CornicePagina | None = None, logo: bytes | None = None) -> FPDF:
    pdf = _PdfConCornice(cornice, logo)
    pdf.compress = False  # Simple, inspectable TEST output; not a size-sensitive path.
    for variante, file in _VARIANTI_FONT.items():
        pdf.add_font(_FONT, variante, str(_CARTELLA_FONT / file))
    if pdf.altezza_testata():
        pdf.set_top_margin(pdf.altezza_testata())
    con_piede = cornice is not None and cornice.pie_pagina is not None
    pdf.set_auto_page_break(auto=True, margin=_MARGINE_PIEDE if con_piede else 15)
    pdf.add_page()
    return pdf


def _metadati(pdf: FPDF, titolo: str, riferimento_documentale: str | None = None) -> None:
    pdf.set_title(titolo)
    pdf.set_creator("GEMODO")
    if riferimento_documentale:
        pdf.set_subject(f"Riferimento documentale: {riferimento_documentale}")
        pdf.set_keywords(f"GEMODO riferimento_documentale={riferimento_documentale}")


def testo_piano(frammenti: list[FrammentoTesto]) -> str:
    """Il testo dei frammenti senza enfasi: per le rese che non la distinguono."""
    return "".join(frammento.testo for frammento in frammenti)


def _variante(frammento: FrammentoTesto, *, grassetto_base: bool, corsivo_base: bool) -> str:
    variante = ""
    if frammento.grassetto or grassetto_base:
        variante += "B"
    if frammento.corsivo or corsivo_base:
        variante += "I"
    if frammento.sottolineato:
        variante += "U"
    return variante


def _scrivi_frammenti(
    pdf: FPDF,
    frammenti: list[FrammentoTesto],
    *,
    allineamento: str,
    dimensione: float,
    grassetto_base: bool = False,
    corsivo_base: bool = False,
    rientro: float = 0,
    spazio_dopo: float = 2,
) -> None:
    """Un paragrafo con enfasi mista, anche giustificato (012 research.md R2).

    L'API a paragrafi di fpdf2 distribuisce lo spazio sulla riga anche quando
    la riga contiene pezzi con varianti di font diverse. `multi_cell` con
    `markdown=True` lo farebbe interpretando `**` nel testo, cioe' rimettendo
    una sintassi dentro il contenuto: escluso dalla spec.
    """
    if isinstance(pdf, _PdfConCornice):
        pdf.misura_righe(dimensione)
    if not "".join(frammento.testo for frammento in frammenti):
        # Un capoverso vuoto e' una riga bianca, come in Word e come
        # nell'editor: chi va a capo per spingere il testo alla pagina dopo
        # deve vederlo succedere anche nel PDF (riscontro del 2026-10-05).
        altezza = _interlinea(dimensione)
        if pdf.get_y() + altezza > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(altezza + spazio_dopo)
        return
    with pdf.text_columns(text_align=allineamento, line_height=1.35,
                          l_margin=pdf.l_margin + rientro) as colonne:
        with colonne.paragraph(bottom_margin=spazio_dopo) as paragrafo:
            for frammento in frammenti:
                variante = _variante(frammento, grassetto_base=grassetto_base, corsivo_base=corsivo_base)
                if frammento.collegamento:
                    # Cliccabile, e riconoscibile come in Word: blu e
                    # sottolineato. Il testo resta quello scritto, quindi si
                    # legge anche stampato (FR-014). Lo schema e' gia' stato
                    # verificato alla scrittura: solo http, https, mailto.
                    pdf.set_text_color(*_COLORE_COLLEGAMENTO)
                    if "U" not in variante:
                        variante += "U"
                pdf.set_font(_FONT, variante, dimensione)
                paragrafo.write(frammento.testo, link=frammento.collegamento or None)
                pdf.set_text_color(0, 0, 0)
    pdf.set_font(_FONT, "", dimensione)


def _interlinea(dimensione: float) -> float:
    """L'altezza di una riga in mm: corpo in punti per l'interlinea 1,35 dei paragrafi."""
    return dimensione * 1.35 * 25.4 / 72


def marcatori_elenchi(
    blocchi: list[BloccoDocumento], *, inizi_sezione: frozenset[int] = frozenset(),
) -> dict[int, list[str]]:
    """Il marcatore di ogni voce, per `ordine` del blocco (012 FR-015, T029).

    Il numero non e' nel contenuto: lo si calcola qui, cosi' che un comma
    inserito in mezzo rinumeri quelli che seguono. Il contatore del primo
    livello prosegue fra elenchi della stessa sezione e riparte a ogni sezione
    e a ogni `TITOLO` (research.md R3); quello del secondo riparte a ogni voce
    di primo livello. E' la stessa regola dell'editor (`numeraElenchi` in
    `modello-anteprima.component.ts`), perche' l'editor deve mostrare cio' che
    il PDF scrive (FR-008).
    """
    marcatori: dict[int, list[str]] = {}
    primo = secondo = 0
    for blocco in sorted(blocchi, key=lambda b: b.ordine):
        if blocco.ordine in inizi_sezione or blocco.tipo is TipoBloccoDocumento.TITOLO:
            primo = secondo = 0
        if blocco.tipo is not TipoBloccoDocumento.ELENCO:
            continue
        voci: list[str] = []
        for elemento in blocco.elementi:
            # Un punto elenco non consuma numeri: un elenco numerato dopo uno
            # puntato riparte da 1, come in Word.
            conta = elemento.marcatore is not TipoMarcatore.PUNTATO
            if elemento.livello == 0:
                primo += conta
                secondo = 0
                voci.append(_formatta_marcatore(elemento, primo))
            else:
                secondo += conta
                voci.append(_formatta_marcatore(elemento, secondo))
        marcatori[blocco.ordine] = voci
    return marcatori


def _formatta_marcatore(elemento: ElementoElenco, numero: int) -> str:
    if elemento.marcatore is TipoMarcatore.NUMERICO:
        return f"{numero}."
    if elemento.marcatore is TipoMarcatore.ALFABETICO:
        return f"{chr(ord('a') + (numero - 1) % 26)})"
    # Per il puntato non c'e' testo da scrivere: la resa disegna un cerchio
    # (`_rendi_voce`). Il simbolo resta come identita' del marcatore, lo stesso
    # che mostra l'editor.
    return "\u25cf" if elemento.livello == 0 else "\u25cb"


def _rendi_voce(pdf: FPDF, elemento: ElementoElenco, marcatore: str, allineamento: str) -> None:
    """Marcatore a sinistra, testo a destra con il rientro sporgente."""
    spostamento = _PASSO_LIVELLO * elemento.livello
    x_marcatore = pdf.l_margin + _RIENTRO_MARCATORE + spostamento
    altezza_riga = _interlinea(_DIMENSIONE_ELENCO)
    # Il marcatore e il testo devono stare sulla stessa pagina: se la prima
    # riga non ci sta, si va a capo pagina prima di scrivere il marcatore.
    if pdf.get_y() + altezza_riga > pdf.page_break_trigger:
        pdf.add_page()
    inizio = pdf.get_y()
    if elemento.marcatore is TipoMarcatore.PUNTATO:
        # A meta' dell'altezza delle minuscole della prima riga, come in Word.
        centro_y = inizio + altezza_riga * 0.55
        pdf.set_line_width(0.2)
        pdf.circle(x_marcatore + _RAGGIO_PUNTO, centro_y, _RAGGIO_PUNTO,
                   style="F" if elemento.livello == 0 else "D")
    else:
        pdf.set_font(_FONT, "", _DIMENSIONE_ELENCO)
        pdf.set_xy(x_marcatore, inizio)
        pdf.cell(_RIENTRO_TESTO - _RIENTRO_MARCATORE, altezza_riga, marcatore)
    pdf.set_xy(pdf.l_margin, inizio)
    _scrivi_frammenti(pdf, elemento.frammenti or [FrammentoTesto(testo="")],
                      allineamento=allineamento, dimensione=_DIMENSIONE_ELENCO,
                      rientro=_RIENTRO_TESTO + spostamento, spazio_dopo=1)


def _rendi_blocco(pdf: FPDF, blocco: BloccoDocumento, marcatori: list[str] | None = None) -> None:
    if isinstance(pdf, _PdfConCornice):
        pdf.segna(blocco.ordine)
    allineamento = (
        _ALLINEAMENTO_ESPLICITO[blocco.allineamento]
        if blocco.allineamento is not None
        else _ALLINEAMENTO.get(blocco.posizionamento.value, "L")
    )
    frammenti = blocco.frammenti

    if blocco.tipo is TipoBloccoDocumento.INTERRUZIONE_PAGINA:
        pdf.add_page()
        return

    if blocco.tipo in (TipoBloccoDocumento.TITOLO, TipoBloccoDocumento.INTESTAZIONE):
        predefinita = 13 if blocco.tipo is TipoBloccoDocumento.TITOLO else 11
        _scrivi_frammenti(pdf, frammenti, allineamento=allineamento,
                          dimensione=_STILI_TITOLO.get(blocco.stile or "", predefinita),
                          grassetto_base=True)
        return

    if blocco.tipo is TipoBloccoDocumento.TABELLA:
        # Una tabella semplice: le colonne dichiarate come intestazione, il
        # contenuto sotto. Il vocabolario ammette tabelle, non fogli di calcolo.
        if blocco.colonne:
            pdf.set_font(_FONT, "B", 10)
            pdf.multi_cell(0, 6, " | ".join(blocco.colonne), align=allineamento)
        _scrivi_frammenti(pdf, frammenti, allineamento=allineamento, dimensione=10)
        return

    if blocco.tipo is TipoBloccoDocumento.FIRMA:
        pdf.ln(6)
        _scrivi_frammenti(pdf, frammenti, allineamento=allineamento, dimensione=11)
        return

    if blocco.tipo in (TipoBloccoDocumento.FOOTER, TipoBloccoDocumento.LOGO):
        # Il logo e' un riferimento ad asset: gli asset versionati sono fuori
        # dal perimetro di questo incremento, quindi resta il suo testo.
        if not frammenti:
            frammenti = [FrammentoTesto(testo=f"[{blocco.tipo.value}: {blocco.asset_ref or 'senza asset'}]")]
        _scrivi_frammenti(pdf, frammenti, allineamento=allineamento, dimensione=9,
                          corsivo_base=True, spazio_dopo=1)
        return

    if blocco.tipo is TipoBloccoDocumento.ELENCO:
        marcatori = marcatori or marcatori_elenchi([blocco])[blocco.ordine]
        for indice, (elemento, marcatore) in enumerate(zip(blocco.elementi, marcatori, strict=True)):
            if isinstance(pdf, _PdfConCornice):
                pdf.segna(blocco.ordine, indice)
            _rendi_voce(pdf, elemento, marcatore, allineamento)
        pdf.ln(1)
        return

    if blocco.stile in _STILI_TITOLO:
        _scrivi_frammenti(pdf, frammenti, allineamento=allineamento,
                          dimensione=_STILI_TITOLO[blocco.stile], grassetto_base=True)
        return

    _scrivi_frammenti(pdf, frammenti, allineamento=allineamento, dimensione=11)


class PlaceholderSenzaValore(Exception):
    """Un segnaposto del documento non ha un valore nei dati ricevuti (003 T019).

    E' un errore funzionale, mai una stringa vuota silenziosa: un bando con un
    buco al posto del numero di posti e' peggio di un bando non generato,
    perche' sembra completo.
    """

    def __init__(self, mancanti: list[str]) -> None:
        self.mancanti = sorted(mancanti)
        super().__init__("segnaposti senza valore: " + ", ".join(self.mancanti))


def _sostituisci_nei_frammenti(
    frammenti: list[FrammentoTesto], valori: dict[str, str],
) -> list[FrammentoTesto]:
    resi: list[FrammentoTesto] = []
    for frammento in frammenti:
        testo = frammento.testo
        for nome, valore in valori.items():
            testo = testo.replace("{{" + nome + "}}", valore)
        resi.append(frammento.model_copy(update={"testo": testo}))
    return resi


def sostituisci_placeholder(
    blocchi: list[BloccoDocumento], dati: dict[str, object],
) -> list[BloccoDocumento]:
    """Rimpiazza `{{campo}}` con il valore, o fallisce dicendo quali mancano.

    La sostituzione avviene **per frammento** (012 FR-005): il valore resta
    dentro il frammento che conteneva il segnaposto, ne eredita l'enfasi e il
    paragrafo non si spezza. `placeholder_usati` dichiara quali segnaposti il
    blocco adopera, ed e' quello che la validazione in pubblicazione ha gia'
    confrontato con i campi del modello: qui si controlla che, per quel
    documento, ci sia anche il **valore**.
    """
    mancanti: set[str] = set()
    resi: list[BloccoDocumento] = []
    for blocco in blocchi:
        valori: dict[str, str] = {}
        for nome in blocco.placeholder_usati:
            if nome not in dati or dati[nome] is None:
                mancanti.add(nome)
                continue
            valori[nome] = str(dati[nome])
        resi.append(blocco.model_copy(update={
            "frammenti": _sostituisci_nei_frammenti(blocco.frammenti, valori),
            "elementi": [
                elemento.model_copy(update={
                    "frammenti": _sostituisci_nei_frammenti(elemento.frammenti, valori),
                })
                for elemento in blocco.elementi
            ],
        }))
    if mancanti:
        raise PlaceholderSenzaValore(list(mancanti))
    return resi


def render_documento(
    *,
    titolo: str,
    blocchi: list[BloccoDocumento],
    inizi_sezione: frozenset[int] = frozenset(),
    anteprima: bool = False,
    cornice: CornicePagina | None = None,
    logo: bytes | None = None,
    inizi_pagina: list[InizioPagina] | None = None,
    riferimento_documentale: str | None = None,
) -> bytes:
    """Il documento composto: i blocchi in ordine, con tipo e posizionamento (003 T018).

    `inizi_sezione` sono gli `ordine` dei blocchi che aprono una sezione: li'
    la numerazione degli elenchi riparte (012 T029). `anteprima` aggiunge la
    marcatura di anteprima (012 FR-009): e' l'unica differenza rispetto alla
    generazione, che usa questa stessa funzione (FR-008). `cornice` e' quella
    del tipo documento (FR-011): testata e pie' di pagina su ogni pagina.
    Se si passa `inizi_pagina`, vi si annota dove comincia ogni pagina dopo la
    prima (012 T080): lo stesso documento, misurato mentre lo si scrive.
    """
    pdf = _nuovo_pdf(cornice, logo)
    _metadati(pdf, titolo, riferimento_documentale)
    if isinstance(pdf, _PdfConCornice):
        pdf.inizi_pagina = inizi_pagina
    if anteprima:
        _marca_anteprima(pdf)
    marcatori = marcatori_elenchi(blocchi, inizi_sezione=inizi_sezione)
    for blocco in sorted(blocchi, key=lambda b: b.ordine):
        _rendi_blocco(pdf, blocco, marcatori.get(blocco.ordine))
    return bytes(pdf.output())


def render_pdf(
    *,
    titolo: str,
    righe: list[tuple[str, str]],
    cornice: CornicePagina | None = None,
    logo: bytes | None = None,
    riferimento_documentale: str | None = None,
) -> bytes:
    """L'elenco etichetta/valore: cio' che e' un modello senza sezioni."""
    pdf = _nuovo_pdf(cornice, logo)
    _metadati(pdf, titolo, riferimento_documentale)
    for etichetta, valore in righe:
        pdf.set_font(_FONT, "B", 11)
        pdf.write(7, f"{etichetta}: ")
        pdf.set_font(_FONT, "", 11)
        pdf.write(7, str(valore))
        pdf.ln(9)
    return bytes(pdf.output())
