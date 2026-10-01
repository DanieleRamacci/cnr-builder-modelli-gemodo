"""La cornice di pagina su ogni pagina (012 US3, T044, T048, T068).

Si verifica pagina per pagina sul PDF vero: un blocco compare una volta sola,
la cornice deve comparire su **tutte**, comprese quelle aperte dall'a capo
automatico.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image
from pypdf import PdfReader

from app.documentale.schemas import BloccoDocumento, CornicePagina
from app.generazione.renderer import render_documento
from app.quality.document_model import violazioni_cornice

CORNICE = CornicePagina.model_validate({
    "intestazione": {
        "maschera": "LOGO_CENTRO_TESTO_SOTTO",
        "con_logo": True,
        "testo": [
            {"testo": "Consiglio Nazionale delle Ricerche", "grassetto": True},
            {"testo": "\nUfficio Reclutamento del Personale"},
        ],
    },
    "pie_pagina": {"testo": [{"testo": "Piazzale Aldo Moro 7 - 00185 Roma"}], "numerazione_pagine": True},
})


def logo_png(larghezza: int = 240, altezza: int = 120) -> bytes:
    uscita = BytesIO()
    Image.new("RGBA", (larghezza, altezza), (0, 70, 140, 255)).save(uscita, format="PNG")
    return uscita.getvalue()


def paragrafo(ordine: int, testo: str) -> BloccoDocumento:
    return BloccoDocumento.model_validate({
        "id": f"p{ordine}", "tipo": "PARAGRAFO", "posizionamento": "BODY", "ordine": ordine,
        "frammenti": [{"testo": testo}],
    })


def pagine(pdf: bytes) -> list:
    return PdfReader(BytesIO(pdf)).pages


def ascisse(pagina, cerca: str) -> list[float]:
    trovate: list[float] = []

    def visita(testo, cm, tm, _font, _dimensione):
        if cerca in testo:
            trovate.append(cm[4] + tm[4])

    pagina.extract_text(visitor_text=visita)
    return trovate


def test_t048_almeno_tre_pagine_logo_intestazione_e_numero_su_ciascuna():
    lungo = "Testo del bando che riempie la pagina. " * 40
    pdf = render_documento(
        titolo="Bando",
        blocchi=[paragrafo(i, f"Capoverso {i}. {lungo}") for i in range(10)],
        cornice=CORNICE,
        logo=logo_png(),
    )
    lette = pagine(pdf)
    totale = len(lette)
    assert totale >= 3
    for numero, pagina in enumerate(lette, start=1):
        testo = " ".join(pagina.extract_text().split())
        assert len(pagina.images) == 1, f"logo mancante a pagina {numero}"
        assert "Consiglio Nazionale delle Ricerche" in testo
        assert "Ufficio Reclutamento del Personale" in testo
        assert "Piazzale Aldo Moro 7" in testo
        assert f"Pagina {numero} di {totale}" in testo


def test_t068_maschera_logo_al_centro_testo_sotto():
    """Il testo dell'intestazione e' centrato: comincia molto oltre il margine sinistro."""
    pdf = render_documento(titolo="Bando", blocchi=[paragrafo(0, "Corpo.")], cornice=CORNICE, logo=logo_png())
    (pagina,) = pagine(pdf)
    mm = 72 / 25.4
    (x_testata,) = ascisse(pagina, "Consiglio Nazionale")
    (x_corpo,) = ascisse(pagina, "Corpo.")
    assert x_testata > x_corpo + 30 * mm
    # Il logo e' centrato anche lui: la sua immagine sta a meta' pagina.
    immagine = pagina.images[0]
    assert immagine.image.width == 240


def test_il_corpo_comincia_sotto_la_testata_qualunque_sia_la_sua_altezza():
    for cornice, logo in [(CORNICE, logo_png()), (CORNICE, None)]:
        pdf = render_documento(titolo="Bando", blocchi=[paragrafo(0, "Corpo del bando. " * 400)],
                               cornice=cornice, logo=logo)
        for pagina in pagine(pdf):
            y_testata = []

            def visita(testo, cm, tm, _font, _dimensione, y_testata=y_testata):
                if "Ufficio Reclutamento" in testo:
                    y_testata.append(cm[5] + tm[5])

            corpo = []

            def visita_corpo(testo, cm, tm, _font, _dimensione, corpo=corpo):
                if "Corpo del bando" in testo:
                    corpo.append(cm[5] + tm[5])

            pagina.extract_text(visitor_text=visita)
            pagina.extract_text(visitor_text=visita_corpo)
            # In punti dal basso: tutto il corpo sta sotto l'ultima riga di intestazione.
            assert corpo and max(corpo) < min(y_testata) - 5


def test_solo_il_pie_di_pagina():
    """Intestazione e pie' di pagina sono indipendenti (T065)."""
    solo_piede = CornicePagina.model_validate({"pie_pagina": {"testo": [], "numerazione_pagine": True}})
    pdf = render_documento(titolo="Bando", blocchi=[paragrafo(0, "Testo.")], cornice=solo_piede)
    (pagina,) = pagine(pdf)
    assert len(pagina.images) == 0
    assert "Pagina 1 di 1" in pagina.extract_text()


def test_senza_logo_caricato_l_intestazione_resta_testo():
    pdf = render_documento(titolo="Bando", blocchi=[paragrafo(0, "Testo.")], cornice=CORNICE, logo=None)
    (pagina,) = pagine(pdf)
    assert len(pagina.images) == 0
    assert "Consiglio Nazionale delle Ricerche" in pagina.extract_text()


def test_t048_l_interruzione_di_pagina_e_rispettata_e_la_cornice_la_segue():
    pdf = render_documento(
        titolo="Bando",
        blocchi=[
            paragrafo(0, "Prima pagina."),
            BloccoDocumento.model_validate({"id": "i", "tipo": "INTERRUZIONE_PAGINA",
                                            "posizionamento": "BODY", "ordine": 1}),
            paragrafo(2, "Seconda pagina."),
        ],
        cornice=CORNICE,
        logo=logo_png(),
    )
    prima, seconda = pagine(pdf)
    assert "Seconda pagina." in seconda.extract_text()
    assert "Seconda pagina." not in prima.extract_text()
    assert "Pagina 2 di 2" in seconda.extract_text()
    assert len(seconda.images) == 1


def test_senza_cornice_il_documento_resta_quello_di_prima():
    pdf = render_documento(titolo="Bando", blocchi=[paragrafo(0, "Testo.")])
    (pagina,) = pagine(pdf)
    assert "Pagina" not in pagina.extract_text()


def test_la_cornice_rifiuta_markup_e_troppe_righe():
    cornice = CornicePagina.model_validate({
        "intestazione": {"testo": [{"testo": "<b>CNR</b>\nuno\ndue\ntre"}]},
        "pie_pagina": {"testo": [{"testo": "riga\naltra"}]},
    })
    violazioni = violazioni_cornice(cornice)
    assert any("markup" in v for v in violazioni)
    assert any("4 righe" in v for v in violazioni)
    assert any("una sola riga" in v for v in violazioni)
