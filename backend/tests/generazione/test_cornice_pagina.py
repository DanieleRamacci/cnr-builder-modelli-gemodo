"""La cornice di pagina su ogni pagina (012 US3, T044, T048).

Si verifica pagina per pagina sul PDF vero: un blocco `LOGO` compare una volta
sola, la cornice deve comparire su **tutte**, comprese quelle aperte dall'a capo
automatico.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image
from pypdf import PdfReader

from app.documentale.schemas import BloccoDocumento, CornicePagina
from app.generazione import renderer
from app.generazione.renderer import render_documento
from app.quality.document_model import violazioni_cornice

CORNICE = CornicePagina.model_validate({
    "logo_ref": "logo-ente",
    "intestazione": [
        {"testo": "Consiglio Nazionale delle Ricerche", "grassetto": True},
        {"testo": "\nUfficio Reclutamento del Personale"},
    ],
    "pie_pagina": [{"testo": "Piazzale Aldo Moro 7 - 00185 Roma"}],
    "numerazione_pagine": True,
})


@pytest.fixture()
def logo_ente(tmp_path, monkeypatch):
    """Un logo di prova: quello vero lo fornisce l'ente, e non sta nel repository."""
    Image.new("RGB", (120, 60), (0, 70, 140)).save(tmp_path / "logo-ente.png")
    monkeypatch.setattr(renderer, "_CARTELLA_LOGHI", tmp_path)


def paragrafo(ordine: int, testo: str) -> BloccoDocumento:
    return BloccoDocumento.model_validate({
        "id": f"p{ordine}", "tipo": "PARAGRAFO", "posizionamento": "BODY", "ordine": ordine,
        "frammenti": [{"testo": testo}],
    })


def pagine(pdf: bytes) -> list:
    return PdfReader(BytesIO(pdf)).pages


def test_t048_almeno_tre_pagine_logo_intestazione_e_numero_su_ciascuna(logo_ente):
    lungo = "Testo del bando che riempie la pagina. " * 40
    pdf = render_documento(
        titolo="Bando",
        blocchi=[paragrafo(i, f"Capoverso {i}. {lungo}") for i in range(10)],
        cornice=CORNICE,
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


def test_t048_l_interruzione_di_pagina_e_rispettata_e_la_cornice_la_segue(logo_ente):
    pdf = render_documento(
        titolo="Bando",
        blocchi=[
            paragrafo(0, "Prima pagina."),
            BloccoDocumento.model_validate({"id": "i", "tipo": "INTERRUZIONE_PAGINA",
                                            "posizionamento": "BODY", "ordine": 1}),
            paragrafo(2, "Seconda pagina."),
        ],
        cornice=CORNICE,
    )
    prima, seconda = pagine(pdf)
    assert "Seconda pagina." in seconda.extract_text()
    assert "Seconda pagina." not in prima.extract_text()
    assert "Pagina 2 di 2" in seconda.extract_text()


def test_il_corpo_non_finisce_sotto_la_testata(logo_ente):
    """La testata ha uno spazio suo: il testo comincia sotto la linea, su ogni pagina."""
    pdf = render_documento(
        titolo="Bando", blocchi=[paragrafo(0, "Corpo del bando. " * 400)], cornice=CORNICE,
    )
    for pagina in pagine(pdf):
        altezze = []

        def visita(testo, cm, tm, _font, _dimensione, altezze=altezze):
            if "Corpo" in testo or "bando" in testo:
                altezze.append(cm[5] + tm[5])

        pagina.extract_text(visitor_text=visita)
        # In punti dal basso: la pagina A4 e' alta 842; la testata occupa i
        # primi 30 mm (85 pt). Nessuna riga del corpo sopra quel limite.
        assert altezze and max(altezze) < 842 - 30 * 72 / 25.4


def test_senza_il_file_del_logo_la_cornice_si_rende_comunque(tmp_path, monkeypatch):
    monkeypatch.setattr(renderer, "_CARTELLA_LOGHI", tmp_path)
    pdf = render_documento(titolo="Bando", blocchi=[paragrafo(0, "Testo.")], cornice=CORNICE)
    (pagina,) = pagine(pdf)
    assert len(pagina.images) == 0
    assert "Consiglio Nazionale delle Ricerche" in pagina.extract_text()
    assert "Pagina 1 di 1" in pagina.extract_text()


def test_senza_cornice_il_documento_resta_quello_di_prima():
    pdf = render_documento(titolo="Bando", blocchi=[paragrafo(0, "Testo.")])
    (pagina,) = pagine(pdf)
    assert "Pagina" not in pagina.extract_text()


def test_la_cornice_rifiuta_markup_e_troppe_righe():
    cornice = CornicePagina.model_validate({
        "intestazione": [{"testo": "<b>CNR</b>\nuno\ndue\ntre"}],
        "pie_pagina": [{"testo": "riga\naltra"}],
    })
    violazioni = violazioni_cornice(cornice)
    assert any("markup" in v for v in violazioni)
    assert any("4 righe" in v for v in violazioni)
    assert any("una sola riga" in v for v in violazioni)
