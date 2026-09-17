"""Pure PDF rendering (004, MVP FR-019/020 slice).

No file I/O, no DB, no HTTP - a title and an ordered list of label/value pairs
in, PDF bytes out. Always marked TEST/non-official (ADR 0002: this increment
has no "official" generation path at all).
"""

from __future__ import annotations

from fpdf import FPDF

_MARCA_TEST = "DOCUMENTO DI TEST - NON UFFICIALE"


def render_pdf(*, titolo: str, righe: list[tuple[str, str]]) -> bytes:
    pdf = FPDF(format="A4")
    pdf.compress = False  # Simple, inspectable TEST output; not a size-sensitive path.
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 8, _MARCA_TEST, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, titolo)
    pdf.ln(4)

    for etichetta, valore in righe:
        pdf.set_font("Helvetica", "B", 11)
        pdf.write(7, f"{etichetta}: ")
        pdf.set_font("Helvetica", "", 11)
        pdf.write(7, str(valore))
        pdf.ln(9)

    return bytes(pdf.output())
