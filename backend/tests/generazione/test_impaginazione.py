"""Dove comincia ogni pagina, misurato dal renderer mentre scrive (012 T080).

L'editor disegna il confine dei fogli dove lo dice il renderer: qui si
verifica sul PDF vero che pagina, blocco e riga annotati corrispondano a cio'
che il PDF contiene.
"""

from __future__ import annotations

from io import BytesIO

import pytest

from pypdf import PdfReader

from app.documentale.schemas import BloccoDocumento
from app.generazione.renderer import InizioPagina, _interlinea, render_documento


def paragrafo(ordine: int, testo: str, tipo: str = "PARAGRAFO") -> BloccoDocumento:
    return BloccoDocumento.model_validate({
        "id": f"p{ordine}", "tipo": tipo, "posizionamento": "BODY", "ordine": ordine,
        "allineamento": "GIUSTIFICATO", "frammenti": [{"testo": testo}],
    })


def elenco(ordine: int, voci: list[str]) -> BloccoDocumento:
    return BloccoDocumento.model_validate({
        "id": f"e{ordine}", "tipo": "ELENCO", "posizionamento": "BODY", "ordine": ordine,
        "elementi": [
            {"livello": 0, "marcatore": "NUMERICO", "frammenti": [{"testo": testo}]} for testo in voci
        ],
    })


def misura(blocchi: list[BloccoDocumento]) -> tuple[list[InizioPagina], PdfReader]:
    inizi: list[InizioPagina] = []
    pdf = render_documento(titolo="Impaginazione", blocchi=blocchi, inizi_pagina=inizi)
    return inizi, PdfReader(BytesIO(pdf))


def dove(inizio: InizioPagina) -> tuple[int, int | None, int | None, int]:
    return inizio.pagina, inizio.ordine, inizio.voce, inizio.riga


def prima_riga(lettore: PdfReader, pagina: int) -> str:
    return lettore.pages[pagina - 1].extract_text().strip().splitlines()[0]


def test_una_pagina_per_ogni_inizio_annotato_e_il_blocco_e_quello_in_cima():
    # Capoversi di una riga: ogni pagina nuova comincia con un capoverso intero.
    blocchi = [paragrafo(i, f"Capoverso numero {i} del documento.") for i in range(120)]
    inizi, lettore = misura(blocchi)

    assert len(lettore.pages) == len(inizi) + 1 >= 3
    assert [inizio.pagina for inizio in inizi] == list(range(2, len(lettore.pages) + 1))
    for inizio in inizi:
        assert inizio.riga == 0
        assert prima_riga(lettore, inizio.pagina) == f"Capoverso numero {inizio.ordine} del documento."


def capienza_prima_pagina() -> int:
    """Quanti capoversi di una riga stanno sulla prima pagina, chiesto al renderer."""
    inizi, _ = misura([paragrafo(i, f"Riga {i}.") for i in range(120)])
    return inizi[0].ordine or 0


def test_un_capoverso_che_attraversa_il_confine_dice_quante_righe_restano_sopra():
    # Il capoverso lungo comincia tre righe sopra il fondo della prima pagina.
    riempitivo = [paragrafo(i, f"Riga {i}.") for i in range(capienza_prima_pagina() - 3)]
    parole = " ".join(f"parola{n:03d}" for n in range(400))
    lungo = len(riempitivo)
    inizi, lettore = misura([*riempitivo, paragrafo(lungo, parole)])

    spezzato = next(inizio for inizio in inizi if inizio.ordine == lungo)
    assert spezzato.riga > 0
    # La pagina nuova comincia a meta' del capoverso, alla riga annotata.
    in_cima = prima_riga(lettore, spezzato.pagina).split()[0]
    pagina_prima = lettore.pages[spezzato.pagina - 2].extract_text()
    righe_sopra = [riga for riga in pagina_prima.splitlines() if "parola" in riga]
    assert len(righe_sopra) == spezzato.riga
    assert in_cima.startswith("parola") and in_cima not in pagina_prima


def test_una_voce_che_non_sta_in_fondo_va_sulla_pagina_nuova_con_il_suo_indice():
    riempitivo = [paragrafo(i, f"Riga {i}.") for i in range(capienza_prima_pagina() - 5)]
    lista = len(riempitivo)
    inizi, lettore = misura([*riempitivo, elenco(lista, [f"voce {n}" for n in range(20)])])

    sulla_voce = next(inizio for inizio in inizi if inizio.ordine == lista)
    assert sulla_voce.voce is not None and sulla_voce.riga == 0
    assert prima_riga(lettore, sulla_voce.pagina).endswith(f"voce {sulla_voce.voce}")


def test_un_interruzione_di_pagina_e_annotata_sul_suo_blocco():
    interruzione = BloccoDocumento.model_validate({
        "id": "i", "tipo": "INTERRUZIONE_PAGINA", "posizionamento": "BODY", "ordine": 1,
    })
    inizi, lettore = misura([paragrafo(0, "Prima."), interruzione, paragrafo(2, "Dopo.")])

    assert [dove(inizio) for inizio in inizi] == [(2, 1, None, 0)]
    assert prima_riga(lettore, 2) == "Dopo."


def test_senza_richiesta_il_pdf_e_identico():
    blocchi = [paragrafo(i, f"Capoverso {i}.") for i in range(80)]
    assert len(PdfReader(BytesIO(render_documento(titolo="x", blocchi=blocchi))).pages) == len(
        misura(blocchi)[1].pages
    )


def vuoto(ordine: int) -> BloccoDocumento:
    return BloccoDocumento.model_validate({
        "id": f"v{ordine}", "tipo": "PARAGRAFO", "posizionamento": "BODY", "ordine": ordine,
        "frammenti": [],
    })


def test_andare_a_capo_porta_il_testo_verso_la_pagina_dopo():
    # Riscontro del 2026-10-05: un capoverso vuoto non occupava posto nel PDF,
    # quindi gli "a capo" davanti a un capoverso spezzato non lo spostavano e
    # il confine disegnato nell'editor scendeva insieme al testo.
    riempitivo = [paragrafo(i, f"Riga {i}.") for i in range(capienza_prima_pagina() - 3)]
    parole = " ".join(f"parola{n:03d}" for n in range(400))
    lungo = len(riempitivo) + 3

    def spezzato(blocchi: list[BloccoDocumento]) -> InizioPagina:
        inizi, _ = misura([*riempitivo, *blocchi, paragrafo(lungo, parole)])
        return next(inizio for inizio in inizi if inizio.ordine == lungo)

    senza = spezzato([])
    con_uno = spezzato([vuoto(lungo - 1)])
    # Un capoverso vuoto e' una riga bianca piu' lo spazio dopo il capoverso:
    # sulla pagina prima resta una riga in meno del capoverso lungo.
    assert senza.riga >= 3
    assert con_uno.riga == senza.riga - 1


def test_una_riga_vuota_in_fondo_alla_pagina_comincia_la_pagina_dopo():
    capienza = capienza_prima_pagina()
    riempitivo = [paragrafo(i, f"Riga {i}.") for i in range(capienza)]
    inizi, lettore = misura([*riempitivo, vuoto(capienza), paragrafo(capienza + 1, "Dopo.")])

    assert dove(inizi[0]) == (2, capienza, None, 0)
    assert prima_riga(lettore, 2) == "Dopo."


def test_fra_due_fogli_ci_sono_il_vuoto_in_fondo_e_i_margini_del_pdf():
    # 012 T083: l'editor disegna fra due fogli lo spazio che il PDF lascia.
    # Capoversi di una riga: in fondo resta meno di un capoverso; senza
    # cornice i margini sono quelli di fpdf (15 mm sotto, 10 mm sopra).
    inizi, _ = misura([paragrafo(i, f"Capoverso {i}.") for i in range(120)])
    for inizio in inizi:
        assert 0 <= inizio.libero < _interlinea(11) + 2
        assert inizio.basso == pytest.approx(15)
        assert inizio.alto == pytest.approx(10)


def test_dopo_un_interruzione_il_resto_della_pagina_resta_vuoto():
    interruzione = BloccoDocumento.model_validate({
        "id": "i", "tipo": "INTERRUZIONE_PAGINA", "posizionamento": "BODY", "ordine": 1,
    })
    inizi, _ = misura([paragrafo(0, "Prima."), interruzione, paragrafo(2, "Dopo.")])

    assert inizi[0].libero > 200
