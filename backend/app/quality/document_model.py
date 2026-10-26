"""Validation helper for the controlled, versioned document model.

Rejects everything the visual builder must never allow the user to author directly
(spec 009, FR-036..FR-038; edge cases in ``spec.md``): free HTML, free CSS, scripts,
block types/positions outside the controlled vocabulary, tables without structured
columns, and placeholders that are not declared by the model itself.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.quality.errors import ContrattoNonValidoError
from app.quality.manifest_loader import load_yaml
from app.documentale.schemas import CornicePagina, FrammentoTesto, segnaposti_nei_frammenti
from app.quality.schemas import BloccoDocumento, ModelloDocumentaleControllato, PosizionamentoBlocco, TipoBloccoDocumento

# Compatible positions per block type (data-model.md: "il posizionamento deve essere
# compatibile con tipo blocco e regione").
POSIZIONI_AMMESSE: dict[TipoBloccoDocumento, set[PosizionamentoBlocco]] = {
    TipoBloccoDocumento.LOGO: {PosizionamentoBlocco.TOP, PosizionamentoBlocco.INLINE},
    TipoBloccoDocumento.INTESTAZIONE: {PosizionamentoBlocco.TOP},
    TipoBloccoDocumento.TITOLO: {PosizionamentoBlocco.TOP, PosizionamentoBlocco.BODY},
    TipoBloccoDocumento.PARAGRAFO: {
        PosizionamentoBlocco.BODY,
        PosizionamentoBlocco.COLUMN_LEFT,
        PosizionamentoBlocco.COLUMN_RIGHT,
    },
    TipoBloccoDocumento.TABELLA: {PosizionamentoBlocco.BODY},
    TipoBloccoDocumento.COLONNE: {PosizionamentoBlocco.BODY},
    TipoBloccoDocumento.FIRMA: {
        PosizionamentoBlocco.BOTTOM_LEFT,
        PosizionamentoBlocco.BOTTOM_RIGHT,
        PosizionamentoBlocco.BOTTOM_CENTER,
    },
    TipoBloccoDocumento.FOOTER: {
        PosizionamentoBlocco.BOTTOM_LEFT,
        PosizionamentoBlocco.BOTTOM_RIGHT,
        PosizionamentoBlocco.BOTTOM_CENTER,
    },
    TipoBloccoDocumento.INTERRUZIONE_PAGINA: {PosizionamentoBlocco.BODY},
    TipoBloccoDocumento.ELENCO: {
        PosizionamentoBlocco.BODY,
        PosizionamentoBlocco.COLUMN_LEFT,
        PosizionamentoBlocco.COLUMN_RIGHT,
    },
}

# Un tag (`<b>`, `</i>`, `<a href=...>`, `<br/>`) o un commento HTML. Il `<`
# deve essere seguito subito da una lettera, `/` o `!`: "3 < 5" nel testo di un
# bando non e' markup e non va rifiutato.
_MARKUP = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(\s[^<>]*)?/?\s*>|<!--")
_SCHEMI_COLLEGAMENTO = {"http", "https", "mailto"}
_LIVELLI_ELENCO = {0, 1}
# Blocchi che non portano testo proprio: l'elenco lo porta nei suoi elementi,
# l'interruzione di pagina non ne ha.
_SENZA_FRAMMENTI = {TipoBloccoDocumento.ELENCO, TipoBloccoDocumento.INTERRUZIONE_PAGINA}


def load_document_model(path: Path) -> ModelloDocumentaleControllato:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ContrattoNonValidoError(str(path), ["il modello documentale deve essere una mappa YAML"])
    return ModelloDocumentaleControllato.model_validate(data)


def _validate_blocco(blocco: BloccoDocumento, asset_ids: set[str], violazioni: list[str]) -> None:
    ammesse = POSIZIONI_AMMESSE.get(blocco.tipo, set())
    if blocco.posizionamento not in ammesse:
        violazioni.append(
            f"blocco {blocco.id}: posizionamento {blocco.posizionamento.value} non ammesso per il tipo {blocco.tipo.value}"
        )

    if blocco.tipo == TipoBloccoDocumento.TABELLA and not blocco.colonne:
        violazioni.append(f"blocco {blocco.id}: tabella senza colonne dichiarate")

    if blocco.tipo == TipoBloccoDocumento.COLONNE and len(blocco.colonne) < 2:
        violazioni.append(f"blocco {blocco.id}: blocco colonne con meno di due colonne dichiarate")

    if blocco.asset_ref is not None and blocco.asset_ref not in asset_ids:
        violazioni.append(f"blocco {blocco.id}: asset_ref '{blocco.asset_ref}' non presente tra gli asset del modello")


def _validate_frammenti(
    dove: str, frammenti: list[FrammentoTesto], violazioni: list[str],
) -> None:
    for indice, frammento in enumerate(frammenti):
        if _MARKUP.search(frammento.testo):
            violazioni.append(f"{dove}, frammento {indice}: il testo contiene markup, non ammesso")
        if frammento.collegamento is not None and not _collegamento_ammesso(frammento.collegamento):
            violazioni.append(
                f"{dove}, frammento {indice}: collegamento con schema non ammesso "
                "(solo http, https, mailto)"
            )


def _collegamento_ammesso(collegamento: str) -> bool:
    # Un carattere di controllo o uno spazio iniziale servono solo a far
    # leggere `java\tscript:` diversamente a chi controlla e a chi apre.
    if collegamento != collegamento.strip() or any(ord(c) < 32 for c in collegamento):
        return False
    parti = urlsplit(collegamento)
    if parti.scheme.lower() not in _SCHEMI_COLLEGAMENTO:
        return False
    return parti.scheme.lower() == "mailto" or bool(parti.netloc)


def _validate_righe(dove: str, blocco: BloccoDocumento, violazioni: list[str]) -> None:
    """Le righe di una tabella: solo su TABELLA, una cella per colonna (014 R6)."""
    if not blocco.righe:
        return
    if blocco.tipo is not TipoBloccoDocumento.TABELLA:
        violazioni.append(f"{dove}: righe ammesse solo su un blocco TABELLA")
        return
    for indice, riga in enumerate(blocco.righe):
        if len(riga.celle) != len(blocco.colonne):
            violazioni.append(
                f"{dove}, riga {indice + 1}: {len(riga.celle)} celle per {len(blocco.colonne)} colonne"
            )
        for colonna, cella in enumerate(riga.celle):
            _validate_frammenti(f"{dove}, riga {indice + 1}, colonna {colonna + 1}", cella.frammenti, violazioni)


def segnaposti_elemento(campo: str, sotto_campi: set[str]) -> set[str]:
    """I segnaposti ammessi in una riga ripetuta su `campo` (014 FR-016)."""
    return {f"{campo}.codice", f"{campo}.descrizione", *(f"{campo}.campi.{s}" for s in sotto_campi)}


def violazioni_righe_ripetute(
    blocchi: list[BloccoDocumento],
    *,
    ripetibili: dict[str, set[str]],
    multiplo: bool,
    pubblicazione: bool = False,
) -> list[str]:
    """Dove possono stare i segnaposti dei campi ripetibili (014 FR-016b, FR-016h, FR-009d).

    `ripetibili` mappa il codice di ogni campo ripetibile della versione ai
    codici dei suoi sotto-campi. Il segnaposto di un elemento ha senso solo
    dentro una riga che si ripete su quel campo: fuori, non si saprebbe di
    quale elemento parla. Un segnaposto del padre dentro la riga ripetuta si
    ripeterebbe uguale su ogni riga, ed e' quasi sempre un errore di
    inserimento: va in una riga fissa.

    `pubblicazione` aggiunge cio' che vale solo per un modello finito: un
    modello multiplo deve impaginare ogni suo campo ripetibile, ma durante la
    stesura la tabella puo' non esserci ancora.
    """
    violazioni: list[str] = []
    di_elemento = {nome: campo for campo, sotto in ripetibili.items() for nome in segnaposti_elemento(campo, sotto)}
    impaginati: set[str] = set()

    def fuori_riga(dove: str, frammenti: list[FrammentoTesto]) -> None:
        for nome in segnaposti_nei_frammenti(frammenti):
            if nome in di_elemento:
                violazioni.append(
                    f"{dove}: il segnaposto '{{{{{nome}}}}}' e' di un elemento di '{di_elemento[nome]}' "
                    "e sta solo in una riga di tabella ripetuta su quel campo"
                )

    for blocco in blocchi:
        dove = f"blocco {blocco.id}"
        fuori_riga(dove, blocco.frammenti)
        for indice, elemento in enumerate(blocco.elementi):
            fuori_riga(f"{dove}, elemento {indice}", elemento.frammenti)
        ripetute_qui: dict[str, int] = {}
        for numero, riga in enumerate(blocco.righe, start=1):
            dove_riga = f"{dove}, riga {numero}"
            if riga.ripeti_per is None:
                for cella in riga.celle:
                    fuori_riga(dove_riga, cella.frammenti)
                continue
            if not multiplo:
                violazioni.append(f"{dove_riga}: un modello singolo non ha righe ripetute")
                continue
            if riga.ripeti_per not in ripetibili:
                violazioni.append(f"{dove_riga}: '{riga.ripeti_per}' non e' un campo ripetibile del modello")
                continue
            ripetute_qui[riga.ripeti_per] = ripetute_qui.get(riga.ripeti_per, 0) + 1
            impaginati.add(riga.ripeti_per)
            ammessi = segnaposti_elemento(riga.ripeti_per, ripetibili[riga.ripeti_per])
            for cella in riga.celle:
                for nome in segnaposti_nei_frammenti(cella.frammenti):
                    if nome not in ammessi:
                        violazioni.append(
                            f"{dove_riga}: il segnaposto '{{{{{nome}}}}}' non e' di un elemento di "
                            f"'{riga.ripeti_per}'; in una riga ripetuta vanno solo i suoi"
                        )
        for campo, quante in ripetute_qui.items():
            if quante > 1:
                violazioni.append(
                    f"{dove}: {quante} righe ripetute su '{campo}' nella stessa tabella, ne e' ammessa una"
                )
    if multiplo and pubblicazione:
        for campo in sorted(set(ripetibili) - impaginati):
            violazioni.append(
                f"il modello multiplo non ha una riga di tabella ripetuta per '{campo}': "
                "senza, le articolazioni non comparirebbero nel documento"
            )
    return violazioni


def violazioni_struttura_blocchi(blocchi: list[BloccoDocumento]) -> list[str]:
    """Cio' che rende un blocco non ammesso nel formato, indipendentemente dai dati (012 T007).

    Separato dalla validazione dei segnaposto perche' e' un errore diverso:
    qui il documento **non e' un documento GEMODO** (`MODELLO_DOCUMENTALE_NON_VALIDO`),
    li' e' un documento valido che cita campi che il modello non ha.

    Prima della 012 il divieto di HTML era applicato solo al booleano
    auto-dichiarato `contiene_html_libero`: nessuno guardava dentro il testo
    (research.md R6). Ogni violazione e' un **rifiuto**, mai una bonifica.
    """
    violazioni: list[str] = []
    for blocco in blocchi:
        dove = f"blocco {blocco.id}"
        _validate_frammenti(dove, blocco.frammenti, violazioni)
        _validate_righe(dove, blocco, violazioni)
        if blocco.tipo in _SENZA_FRAMMENTI and blocco.frammenti:
            violazioni.append(f"{dove}: un blocco {blocco.tipo.value} non porta frammenti propri")
        if blocco.tipo is not TipoBloccoDocumento.ELENCO:
            if blocco.elementi:
                violazioni.append(f"{dove}: elementi ammessi solo su un blocco ELENCO")
            continue
        if not blocco.elementi:
            violazioni.append(f"{dove}: elenco senza elementi")
        for indice, elemento in enumerate(blocco.elementi):
            if elemento.livello not in _LIVELLI_ELENCO:
                violazioni.append(
                    f"{dove}, elemento {indice}: livello {elemento.livello} non ammesso (solo 0 o 1)"
                )
            _validate_frammenti(f"{dove}, elemento {indice}", elemento.frammenti, violazioni)
    return violazioni


# La testata ha un'altezza fissa sopra il margine del corpo: piu' righe di
# cosi' finirebbero sopra il testo (renderer, `_ALTEZZA_TESTATA`).
RIGHE_MASSIME_INTESTAZIONE = 3


def violazioni_cornice(cornice: CornicePagina) -> list[str]:
    """Cio' che rende una cornice di pagina non ammessa (012 T042, T065).

    Le stesse regole dei blocchi per il testo, piu' i limiti che dipendono
    dalla resa: l'intestazione ha al massimo tre righe, il pie' di pagina una.
    """
    violazioni: list[str] = []
    if cornice.intestazione is not None:
        testo = cornice.intestazione.testo
        _validate_frammenti("intestazione", testo, violazioni)
        righe = "".join(f.testo for f in testo).count("\n") + 1
        if righe > RIGHE_MASSIME_INTESTAZIONE:
            violazioni.append(
                f"intestazione: {righe} righe, al massimo {RIGHE_MASSIME_INTESTAZIONE}"
            )
    if cornice.pie_pagina is not None:
        _validate_frammenti("pie' di pagina", cornice.pie_pagina.testo, violazioni)
        if "\n" in "".join(f.testo for f in cornice.pie_pagina.testo):
            violazioni.append("pie' di pagina: una sola riga")
    return violazioni


def validate_document_model(
    modello: ModelloDocumentaleControllato,
    *,
    placeholder_contratto_dati: set[str] | None = None,
) -> None:
    """Raise ContrattoNonValidoError collecting every violation found.

    ``placeholder_contratto_dati``, when provided, is the set of placeholders the
    owning data contract (spec 001/003) actually exposes; every placeholder used by the
    model must be a subset of it. When omitted, placeholders are only checked for
    internal consistency (every placeholder used by a block must be declared at model
    level in ``placeholder_usati``).
    """

    violazioni: list[str] = []

    if modello.contiene_html_libero:
        violazioni.append("il modello contiene HTML libero, non ammesso")
    if modello.contiene_css_libero:
        violazioni.append("il modello contiene CSS libero, non ammesso")
    if modello.contiene_script:
        violazioni.append("il modello contiene script, non ammessi")

    violazioni.extend(violazioni_struttura_blocchi(modello.blocchi))

    asset_ids = {asset.id for asset in modello.asset}
    stili_ammessi = set(modello.stili_ammessi)
    placeholder_dichiarati = set(modello.placeholder_usati)

    for blocco in modello.blocchi:
        _validate_blocco(blocco, asset_ids, violazioni)
        if blocco.stile is not None and stili_ammessi and blocco.stile not in stili_ammessi:
            violazioni.append(f"blocco {blocco.id}: stile '{blocco.stile}' non presente in stili_ammessi")
        for placeholder in blocco.placeholder_usati:
            if placeholder not in placeholder_dichiarati:
                violazioni.append(
                    f"blocco {blocco.id}: placeholder '{placeholder}' non dichiarato in placeholder_usati del modello"
                )

    riferimento = placeholder_contratto_dati
    if riferimento is not None:
        non_disponibili = sorted(placeholder_dichiarati - riferimento)
        for placeholder in non_disponibili:
            violazioni.append(
                f"placeholder '{placeholder}' non presente nel contratto dati del modello"
            )

    if violazioni:
        raise ContrattoNonValidoError(modello.modello_versione_id, violazioni)
