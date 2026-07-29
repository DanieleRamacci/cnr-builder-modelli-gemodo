"""Validation helper for the controlled, versioned document model.

Rejects everything the visual builder must never allow the user to author directly
(spec 009, FR-036..FR-038; edge cases in ``spec.md``): free HTML, free CSS, scripts,
block types/positions outside the controlled vocabulary, tables without structured
columns, and placeholders that are not declared by the model itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.quality.errors import ContrattoNonValidoError
from app.quality.manifest_loader import load_yaml
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
}


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
