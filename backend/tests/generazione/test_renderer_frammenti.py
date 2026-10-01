"""La resa dei frammenti nel PDF (012 T012-T018).

Il PDF si legge con un parser vero (`tests/support/pdf.py`): il testo per
cio' che dice, la variante di font per l'enfasi con cui lo dice.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.documentale.schemas import BloccoDocumento
from app.generazione.renderer import render_documento, sostituisci_placeholder
from tests.support.pdf import estrai_testo, estrai_font_e_testo


def blocco(**campi) -> BloccoDocumento:
    return BloccoDocumento.model_validate({"id": "b", "tipo": "PARAGRAFO", "posizionamento": "BODY", **campi})


def rendi(*blocchi: BloccoDocumento) -> bytes:
    return render_documento(titolo="Prova", blocchi=list(blocchi))


def test_sc006_i_caratteri_tipografici_italiani_arrivano_invariati():
    """Prima della 012 questo paragrafo non produceva un PDF sbagliato: non ne produceva nessuno.

    Il core font sollevava `FPDFUnicodeEncodingException` alla prima virgoletta
    curva, e la generazione registrava un documento FALLITO (research.md R1).
    """
    testo = "Il “Riordino” – cioè l’art. 4 — è più così: À È É Ì Ò Ù, € 1.000, § 3, «nota»."
    assert testo in estrai_testo(rendi(blocco(frammenti=[{"testo": testo}])))


def test_l_enfasi_di_ogni_frammento_diventa_la_sua_variante_di_font():
    pdf = rendi(blocco(allineamento="GIUSTIFICATO", frammenti=[
        {"testo": "VISTO", "grassetto": True},
        {"testo": " il decreto recante "},
        {"testo": "Riordino del CNR", "corsivo": True},
        {"testo": " e ", "grassetto": True, "corsivo": True},
    ]))
    font_di = {}
    for font, pezzo in estrai_font_e_testo(pdf):
        for parola in pezzo.split():
            font_di.setdefault(parola, font)
    assert font_di["VISTO"] == "TitilliumWebBold"
    assert font_di["decreto"] == "TitilliumWeb"
    assert font_di["Riordino"] == "TitilliumWebItalic"
    assert font_di["e"] == "TitilliumWebBoldItalic"
    # Un paragrafo solo: l'enfasi non lo spezza in righe separate.
    assert "VISTO il decreto recante Riordino del CNR e" in estrai_testo(pdf)


def test_un_segnaposto_in_un_frammento_in_grassetto_produce_un_valore_in_grassetto():
    """US1 scenario 3, FR-005: il valore eredita l'enfasi e il paragrafo resta intero."""
    blocchi = sostituisci_placeholder([blocco(
        frammenti=[
            {"testo": "I posti messi a concorso sono "},
            {"testo": "{{numero_posti}}", "grassetto": True},
            {"testo": " presso la sede di Roma."},
        ],
        placeholder_usati=["numero_posti"],
    )], {"numero_posti": 7})
    pdf = rendi(*blocchi)

    assert "I posti messi a concorso sono 7 presso la sede di Roma." in estrai_testo(pdf)
    assert ("TitilliumWebBold", "7") in [(f, t.strip()) for f, t in estrai_font_e_testo(pdf)]


def test_un_segnaposto_dentro_una_voce_di_elenco_viene_sostituito():
    [elenco] = sostituisci_placeholder([blocco(
        tipo="ELENCO", elementi=[{"frammenti": [{"testo": "sede: {{sede}}"}]}],
        placeholder_usati=["sede"],
    )], {"sede": "Pisa"})
    assert elenco.elementi[0].frammenti[0].testo == "sede: Pisa"


def test_lo_stile_h1_scritto_dall_editor_arriva_nel_pdf():
    """T016: prima l'editor mostrava un titolo e il PDF un paragrafo qualunque."""
    pdf = rendi(blocco(stile="H1", frammenti=[{"testo": "Art. 1 - Oggetto"}]))
    assert ("TitilliumWebBold", "Art. 1 - Oggetto") in [(f, t.strip()) for f, t in estrai_font_e_testo(pdf)]


def test_l_allineamento_dichiarato_prevale_su_quello_del_posizionamento():
    """T015: un paragrafo nel BODY, che di suo andrebbe a sinistra, si centra se lo dichiara."""
    def ascissa(pdf: bytes, cerca: str) -> float:
        posizioni = []

        def visita(testo, _cm, tm, _font, _dimensione):
            if cerca in testo:
                posizioni.append(tm[4])

        PdfReader(BytesIO(pdf)).pages[0].extract_text(visitor_text=visita)
        return posizioni[0]

    sinistra = ascissa(rendi(blocco(frammenti=[{"testo": "centrami"}])), "centrami")
    centro = ascissa(rendi(blocco(allineamento="CENTRO", frammenti=[{"testo": "centrami"}])), "centrami")
    assert centro > sinistra + 50


def test_un_elenco_si_rende_con_tutte_le_sue_voci():
    pdf = rendi(blocco(tipo="ELENCO", elementi=[
        {"livello": 0, "frammenti": [{"testo": "Roma"}]},
        {"livello": 1, "marcatore": "ALFABETICO", "frammenti": [{"testo": "Area della Ricerca"}]},
    ]))
    assert "Roma Area della Ricerca" in estrai_testo(pdf)
