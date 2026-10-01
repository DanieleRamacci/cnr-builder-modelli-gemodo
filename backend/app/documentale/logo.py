"""Il logo della cornice di pagina: cosa si accetta e come si conserva (012 T066)."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.common.errors import DomainError, ErrorCode

DIMENSIONE_MASSIMA = 1024 * 1024
LATO_MASSIMO = 4000
FORMATI = {"PNG", "JPEG"}


def ricodifica_logo(contenuto: bytes) -> bytes:
    """Il logo come PNG nuovo, o un rifiuto che dice perche'.

    L'immagine si apre, si verifica e si ridisegna: del file ricevuto non si
    conserva nulla se non i pixel. Cosi' metadati, contenuti accodati o un file
    che si finge immagine non arrivano al PDF.
    """
    if len(contenuto) > DIMENSIONE_MASSIMA:
        raise _rifiuto(f"il logo supera 1 MB ({len(contenuto) // 1024} KB)")
    try:
        with Image.open(BytesIO(contenuto)) as immagine:
            formato = immagine.format
            immagine.verify()
        with Image.open(BytesIO(contenuto)) as immagine:
            if formato not in FORMATI:
                raise _rifiuto(f"formato {formato} non ammesso: PNG o JPEG")
            if max(immagine.size) > LATO_MASSIMO:
                raise _rifiuto(f"immagine troppo grande: al massimo {LATO_MASSIMO} pixel per lato")
            pulita = immagine.convert("RGBA")
    except (UnidentifiedImageError, OSError, SyntaxError) as errore:
        raise _rifiuto("il file non e' un'immagine PNG o JPEG leggibile") from errore
    uscita = BytesIO()
    pulita.save(uscita, format="PNG", optimize=True)
    return uscita.getvalue()


def _rifiuto(motivo: str) -> DomainError:
    return DomainError(
        ErrorCode.MODELLO_DOCUMENTALE_NON_VALIDO,
        "Logo non valido",
        status_code=422,
        dettagli=[{"violazione": motivo}],
    )
