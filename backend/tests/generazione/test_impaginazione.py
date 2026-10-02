"""Dove comincia ogni pagina, misurato dal renderer mentre scrive (012 T080).

L'editor disegna il confine dei fogli dove lo dice il renderer: qui si
verifica sul PDF vero che pagina, blocco e riga annotati corrispondano a cio'
che il PDF contiene.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.documentale.schemas import BloccoDocumento
from app.generazione.renderer import InizioPagina, render_documento


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

    assert inizi == [InizioPagina(pagina=2, ordine=1, voce=None, riga=0)]
    assert prima_riga(lettore, 2) == "Dopo."


def test_senza_richiesta_il_pdf_e_identico():
    blocchi = [paragrafo(i, f"Capoverso {i}.") for i in range(80)]
    assert len(PdfReader(BytesIO(render_documento(titolo="x", blocchi=blocchi))).pages) == len(
        misura(blocchi)[1].pages
    )
