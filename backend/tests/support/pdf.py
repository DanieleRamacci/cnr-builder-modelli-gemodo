"""Lettura del testo di un PDF prodotto da GEMODO, per le asserzioni dei test.

Dalla 012 il renderer incorpora un font TrueType: il testo nel file e' codificato
come indici di glifo e non compare piu' in chiaro nei byte. Un `b"..." in pdf`
non troverebbe nulla, e un `b"..." not in pdf` passerebbe sempre senza
verificare niente. Qui il testo si estrae con un parser PDF vero.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def estrai_testo(contenuto: bytes) -> str:
    """Il testo di tutte le pagine, con gli spazi bianchi ridotti a uno.

    La normalizzazione serve alla giustificazione: distribuendo lo spazio sulla
    riga, l'estrazione restituisce spazi multipli e a capo dove il lettore vede
    una parola dopo l'altra.
    """
    lettore = PdfReader(BytesIO(contenuto))
    return " ".join(" ".join(pagina.extract_text() for pagina in lettore.pages).split())


def estrai_font_e_testo(contenuto: bytes) -> list[tuple[str, str]]:
    """Coppie (font, testo) nell'ordine in cui il PDF le scrive.

    Serve a verificare l'enfasi: il grassetto non e' un attributo del testo
    estratto ma la variante di font con cui e' scritto.
    """
    lettore = PdfReader(BytesIO(contenuto))
    pezzi: list[tuple[str, str]] = []

    def visita(testo, _cm, _tm, font, _dimensione):
        if testo and font is not None:
            pezzi.append((str(font["/BaseFont"]).split("+")[-1], testo))

    for pagina in lettore.pages:
        pagina.extract_text(visitor_text=visita)
    return pezzi
