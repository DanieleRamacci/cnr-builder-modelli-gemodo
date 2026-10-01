"""La numerazione delle voci di elenco, calcolata in resa (012 FR-015, T029, T031, T032).

Il contenuto dichiara solo livello e tipo di marcatore; `1.`, `a)` li scrive
il renderer. Si verifica sul testo estratto dal PDF, non su una funzione
interna: e' il PDF che il gestore legge.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.documentale.schemas import BloccoDocumento
from app.generazione.renderer import marcatori_elenchi, render_documento
from tests.support.pdf import estrai_testo


def voce(testo: str, livello: int = 0, marcatore: str | None = None) -> dict:
    return {
        "livello": livello,
        "marcatore": marcatore or ("NUMERICO" if livello == 0 else "ALFABETICO"),
        "frammenti": [{"testo": testo}],
    }


def elenco(ordine: int, *voci: dict) -> BloccoDocumento:
    return BloccoDocumento.model_validate({
        "id": f"e{ordine}", "tipo": "ELENCO", "posizionamento": "BODY", "ordine": ordine,
        "elementi": list(voci),
    })


def paragrafo(ordine: int, testo: str, tipo: str = "PARAGRAFO") -> BloccoDocumento:
    return BloccoDocumento.model_validate({
        "id": f"p{ordine}", "tipo": tipo, "posizionamento": "BODY", "ordine": ordine,
        "frammenti": [{"testo": testo}],
    })


def resa_testo(*blocchi: BloccoDocumento, inizi: frozenset[int] = frozenset()) -> str:
    return estrai_testo(render_documento(titolo="Prova", blocchi=list(blocchi), inizi_sezione=inizi))


def test_t031_un_comma_inserito_in_mezzo_rinumera_quelli_che_seguono():
    prima = resa_testo(elenco(0, voce("primo"), voce("secondo"), voce("terzo")))
    assert "1. primo 2. secondo 3. terzo" in prima

    dopo = resa_testo(elenco(0, voce("primo"), voce("inserito"), voce("secondo"), voce("terzo")))
    assert "1. primo 2. inserito 3. secondo 4. terzo" in dopo


def test_le_lettere_ripartono_sotto_ogni_comma():
    testo = resa_testo(elenco(
        0,
        voce("Sono indetti:"), voce("Roma", 1), voce("Milano", 1),
        voce("Le domande:"), voce("in via telematica", 1),
    ))
    assert "1. Sono indetti: a) Roma b) Milano 2. Le domande: a) in via telematica" in testo


def test_la_numerazione_prosegue_fra_elenchi_della_stessa_sezione():
    """Un comma dopo un paragrafo intermedio e' il comma successivo, non di nuovo l'1."""
    testo = resa_testo(
        elenco(0, voce("primo")),
        paragrafo(1, "Testo fra i commi."),
        elenco(2, voce("secondo")),
    )
    assert "1. primo Testo fra i commi. 2. secondo" in testo


def test_la_numerazione_riparte_a_ogni_sezione_e_a_ogni_titolo():
    testo = resa_testo(
        elenco(0, voce("art1-c1"), voce("art1-c2")),
        elenco(1, voce("art2-c1")),          # apre una nuova sezione
        paragrafo(2, "Art. 3 - Domande", tipo="TITOLO"),
        elenco(3, voce("art3-c1")),
        inizi=frozenset({0, 1}),
    )
    assert "1. art1-c1 2. art1-c2 1. art2-c1" in testo
    assert "Art. 3 - Domande 1. art3-c1" in testo


def test_un_elenco_puntato_non_ha_numeri_e_disegna_i_punti():
    blocchi = [elenco(0, voce("cittadinanza", 0, "PUNTATO"), voce("eta", 1, "PUNTATO"))]
    assert marcatori_elenchi(blocchi) == {0: ["●", "○"]}
    # Il punto e' un disegno, non testo: nel testo estratto restano le voci.
    assert "cittadinanza eta" in resa_testo(*blocchi)


def test_un_elenco_numerato_dopo_uno_puntato_riparte_da_uno():
    """Visto nel PDF del 2026-10-01: i punti consumavano numeri e il comma partiva da 3."""
    testo = resa_testo(
        elenco(0, voce("primo punto", 0, "PUNTATO"), voce("secondo punto", 0, "PUNTATO")),
        elenco(1, voce("primo comma"), voce("lettera", 1)),
    )
    assert "1. primo comma a) lettera" in testo


def test_rientri_come_word_marcatore_a_0_63_cm_testo_a_1_27_cm():
    pdf = render_documento(titolo="Prova", blocchi=[
        paragrafo(0, "margine"),
        elenco(1, voce("comma"), voce("lettera", 1)),
    ])
    x = posizioni(pdf)
    mm = 72 / 25.4
    assert abs((x["1."] - x["margine"]) - 6.35 * mm) < 1
    assert abs((x["comma"] - x["margine"]) - 12.7 * mm) < 1
    # Il secondo livello sposta marcatore e testo di altri 1,27 cm.
    assert abs((x["a)"] - x["1."]) - 12.7 * mm) < 1
    assert abs((x["lettera"] - x["comma"]) - 12.7 * mm) < 1


def posizioni(pdf: bytes) -> dict[str, float]:
    """L'ascissa, in punti, del primo pezzo di testo che comincia con ciascuna parola."""
    x: dict[str, float] = {}

    def visita(testo, cm, tm, _font, _dimensione):
        parole = testo.split()
        if parole:
            x.setdefault(parole[0], cm[4] + tm[4])

    PdfReader(BytesIO(pdf)).pages[0].extract_text(visitor_text=visita)
    return x


def test_t032_un_elenco_che_attraversa_il_cambio_pagina_continua_la_numerazione():
    voci = [voce(f"comma numero {n} " + "testo del comma " * 12) for n in range(1, 41)]
    pdf = render_documento(titolo="Prova", blocchi=[elenco(0, *voci)])
    pagine = [estrai_testo_pagina(pdf, i) for i in range(len(PdfReader(BytesIO(pdf)).pages))]
    assert len(pagine) > 1
    # La prima voce della seconda pagina porta il numero che segue l'ultima
    # della prima, e il marcatore e' sulla stessa pagina del suo testo.
    seconda = pagine[1].split()
    numero = int(seconda[0].rstrip("."))
    assert seconda[1:4] == ["comma", "numero", str(numero)]
    assert f"{numero - 1}. comma numero {numero - 1}" in pagine[0]


def estrai_testo_pagina(pdf: bytes, indice: int) -> str:
    return " ".join(PdfReader(BytesIO(pdf)).pages[indice].extract_text().split())


def test_editor_e_renderer_usano_la_stessa_regola():
    """Lo stesso caso del test di componente dell'editor: deve dare gli stessi marcatori (FR-008)."""
    marcatori = marcatori_elenchi([
        elenco(0, voce("Sono indetti:"), voce("un posto a Roma", 1)),
    ])
    assert marcatori == {0: ["1.", "a)"]}
