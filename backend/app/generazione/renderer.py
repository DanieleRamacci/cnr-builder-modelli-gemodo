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

from pathlib import Path

from fpdf import FPDF

from app.documentale.schemas import (
    AllineamentoTesto,
    BloccoDocumento,
    ElementoElenco,
    FrammentoTesto,
    TipoBloccoDocumento,
    TipoMarcatore,
)

_MARCA_TEST = "DOCUMENTO DI TEST - NON UFFICIALE"

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

# Rientro per livello di elenco e spazio riservato al marcatore, in mm
# (FR-003: due livelli). Il testo della voce va a capo allineato dopo il
# marcatore, non sotto di esso: e' il rientro sporgente dei bandi.
_RIENTRO_ELENCO = 8
_LARGHEZZA_MARCATORE = 7
_DIMENSIONE_ELENCO = 11


def _intestazione(pdf: FPDF, titolo: str) -> None:
    pdf.set_font(_FONT, "B", 10)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 8, _MARCA_TEST, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font(_FONT, "B", 14)
    pdf.multi_cell(0, 8, titolo)
    pdf.ln(4)


def _nuovo_pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.compress = False  # Simple, inspectable TEST output; not a size-sensitive path.
    for variante, file in _VARIANTI_FONT.items():
        pdf.add_font(_FONT, variante, str(_CARTELLA_FONT / file))
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    return pdf


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
    if not frammenti:
        return
    with pdf.text_columns(text_align=allineamento, line_height=1.35,
                          l_margin=pdf.l_margin + rientro) as colonne:
        with colonne.paragraph(bottom_margin=spazio_dopo) as paragrafo:
            for frammento in frammenti:
                pdf.set_font(_FONT, _variante(frammento, grassetto_base=grassetto_base,
                                              corsivo_base=corsivo_base), dimensione)
                paragrafo.write(frammento.testo)
    pdf.set_font(_FONT, "", dimensione)


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
            if elemento.livello == 0:
                primo += 1
                secondo = 0
                voci.append(_formatta_marcatore(elemento, primo))
            else:
                secondo += 1
                voci.append(_formatta_marcatore(elemento, secondo))
        marcatori[blocco.ordine] = voci
    return marcatori


def _formatta_marcatore(elemento: ElementoElenco, numero: int) -> str:
    if elemento.marcatore is TipoMarcatore.NUMERICO:
        return f"{numero}."
    if elemento.marcatore is TipoMarcatore.ALFABETICO:
        return f"{chr(ord('a') + (numero - 1) % 26)})"
    return "\u2022" if elemento.livello == 0 else "\u2013"


def _rendi_voce(pdf: FPDF, elemento: ElementoElenco, marcatore: str, allineamento: str) -> None:
    """Marcatore a sinistra, testo a destra con il rientro sporgente."""
    rientro = _RIENTRO_ELENCO * (elemento.livello + 1)
    altezza_riga = _DIMENSIONE_ELENCO * 1.35 * 25.4 / 72
    # Il marcatore e il testo devono stare sulla stessa pagina: se la prima
    # riga non ci sta, si va a capo pagina prima di scrivere il marcatore.
    if pdf.get_y() + altezza_riga > pdf.page_break_trigger:
        pdf.add_page()
    inizio = pdf.get_y()
    pdf.set_font(_FONT, "", _DIMENSIONE_ELENCO)
    pdf.set_xy(pdf.l_margin + rientro, inizio)
    pdf.cell(_LARGHEZZA_MARCATORE, altezza_riga, marcatore)
    pdf.set_xy(pdf.l_margin, inizio)
    _scrivi_frammenti(pdf, elemento.frammenti or [FrammentoTesto(testo="")],
                      allineamento=allineamento, dimensione=_DIMENSIONE_ELENCO,
                      rientro=rientro + _LARGHEZZA_MARCATORE, spazio_dopo=1)


def _rendi_blocco(pdf: FPDF, blocco: BloccoDocumento, marcatori: list[str] | None = None) -> None:
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
        for elemento, marcatore in zip(blocco.elementi, marcatori, strict=True):
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
    *, titolo: str, blocchi: list[BloccoDocumento], inizi_sezione: frozenset[int] = frozenset(),
) -> bytes:
    """Il documento composto: i blocchi in ordine, con tipo e posizionamento (003 T018).

    `inizi_sezione` sono gli `ordine` dei blocchi che aprono una sezione: li'
    la numerazione degli elenchi riparte (012 T029).
    """
    pdf = _nuovo_pdf()
    _intestazione(pdf, titolo)
    marcatori = marcatori_elenchi(blocchi, inizi_sezione=inizi_sezione)
    for blocco in sorted(blocchi, key=lambda b: b.ordine):
        _rendi_blocco(pdf, blocco, marcatori.get(blocco.ordine))
    return bytes(pdf.output())


def render_pdf(*, titolo: str, righe: list[tuple[str, str]]) -> bytes:
    """L'elenco etichetta/valore: cio' che e' un modello senza sezioni."""
    pdf = _nuovo_pdf()
    _intestazione(pdf, titolo)
    for etichetta, valore in righe:
        pdf.set_font(_FONT, "B", 11)
        pdf.write(7, f"{etichetta}: ")
        pdf.set_font(_FONT, "", 11)
        pdf.write(7, str(valore))
        pdf.ln(9)
    return bytes(pdf.output())
