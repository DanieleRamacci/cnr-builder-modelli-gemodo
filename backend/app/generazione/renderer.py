"""Pure PDF rendering (004 MVP FR-019/020; 003 T018).

No file I/O, no DB, no HTTP - content in, PDF bytes out.

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

from fpdf import FPDF

from app.documentale.schemas import BloccoDocumento, TipoBloccoDocumento

_MARCA_TEST = "DOCUMENTO DI TEST - NON UFFICIALE"

# Il posizionamento e' una grammatica, non una coordinata: qui diventa un
# allineamento, che e' quanto il renderer di questo incremento sa esprimere.
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


def _intestazione(pdf: FPDF, titolo: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 8, _MARCA_TEST, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, titolo)
    pdf.ln(4)


def _nuovo_pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.compress = False  # Simple, inspectable TEST output; not a size-sensitive path.
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    return pdf


def _rendi_blocco(pdf: FPDF, blocco: BloccoDocumento) -> None:
    allineamento = _ALLINEAMENTO.get(blocco.posizionamento.value, "L")
    testo = blocco.contenuto or ""

    if blocco.tipo is TipoBloccoDocumento.INTERRUZIONE_PAGINA:
        pdf.add_page()
        return

    if blocco.tipo in (TipoBloccoDocumento.TITOLO, TipoBloccoDocumento.INTESTAZIONE):
        pdf.set_font("Helvetica", "B", 13 if blocco.tipo is TipoBloccoDocumento.TITOLO else 11)
        pdf.multi_cell(0, 7, testo, align=allineamento)
        pdf.ln(2)
        return

    if blocco.tipo is TipoBloccoDocumento.TABELLA:
        # Una tabella semplice: le colonne dichiarate come intestazione, il
        # contenuto sotto. Il vocabolario ammette tabelle, non fogli di calcolo.
        pdf.set_font("Helvetica", "B", 10)
        if blocco.colonne:
            pdf.multi_cell(0, 6, " | ".join(blocco.colonne), align=allineamento)
        pdf.set_font("Helvetica", "", 10)
        if testo:
            pdf.multi_cell(0, 6, testo, align=allineamento)
        pdf.ln(2)
        return

    if blocco.tipo is TipoBloccoDocumento.FIRMA:
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, testo, align=allineamento)
        pdf.ln(2)
        return

    if blocco.tipo in (TipoBloccoDocumento.FOOTER, TipoBloccoDocumento.LOGO):
        # Il logo e' un riferimento ad asset: gli asset versionati sono fuori
        # dal perimetro di questo incremento, quindi resta il suo testo.
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 6, testo or f"[{blocco.tipo.value}: {blocco.asset_ref or 'senza asset'}]",
                       align=allineamento)
        pdf.ln(1)
        return

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, testo, align=allineamento)
    pdf.ln(2)


class PlaceholderSenzaValore(Exception):
    """Un segnaposto del documento non ha un valore nei dati ricevuti (003 T019).

    E' un errore funzionale, mai una stringa vuota silenziosa: un bando con un
    buco al posto del numero di posti e' peggio di un bando non generato,
    perche' sembra completo.
    """

    def __init__(self, mancanti: list[str]) -> None:
        self.mancanti = sorted(mancanti)
        super().__init__("segnaposti senza valore: " + ", ".join(self.mancanti))


def sostituisci_placeholder(
    blocchi: list[BloccoDocumento], dati: dict[str, object],
) -> list[BloccoDocumento]:
    """Rimpiazza `{{campo}}` con il valore, o fallisce dicendo quali mancano.

    La sostituzione e' testuale sul contenuto del blocco. `placeholder_usati`
    dichiara quali segnaposti il blocco adopera, ed e' quello che la
    validazione in pubblicazione ha gia' confrontato con i campi del modello:
    qui si controlla che, per quel documento, ci sia anche il **valore**.
    """
    mancanti: set[str] = set()
    resi: list[BloccoDocumento] = []
    for blocco in blocchi:
        testo = blocco.contenuto
        for nome in blocco.placeholder_usati:
            if nome not in dati or dati[nome] is None:
                mancanti.add(nome)
                continue
            if testo is not None:
                testo = testo.replace("{{" + nome + "}}", str(dati[nome]))
        resi.append(blocco.model_copy(update={"contenuto": testo}))
    if mancanti:
        raise PlaceholderSenzaValore(list(mancanti))
    return resi


def render_documento(*, titolo: str, blocchi: list[BloccoDocumento]) -> bytes:
    """Il documento composto: i blocchi in ordine, con tipo e posizionamento (003 T018)."""
    pdf = _nuovo_pdf()
    _intestazione(pdf, titolo)
    for blocco in sorted(blocchi, key=lambda b: b.ordine):
        _rendi_blocco(pdf, blocco)
    return bytes(pdf.output())


def render_pdf(*, titolo: str, righe: list[tuple[str, str]]) -> bytes:
    """L'elenco etichetta/valore: cio' che e' un modello senza sezioni."""
    pdf = _nuovo_pdf()
    _intestazione(pdf, titolo)
    for etichetta, valore in righe:
        pdf.set_font("Helvetica", "B", 11)
        pdf.write(7, f"{etichetta}: ")
        pdf.set_font("Helvetica", "", 11)
        pdf.write(7, str(valore))
        pdf.ln(9)
    return bytes(pdf.output())
