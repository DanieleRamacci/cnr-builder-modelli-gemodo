"""Reusable ModelloDocumentaleControllato fixtures for document-model validation tests."""

from __future__ import annotations

from app.quality.schemas import (
    AssetDocumento,
    BloccoDocumento,
    ModelloDocumentaleControllato,
    PaginaDocumento,
    PosizionamentoBlocco,
    TipoAsset,
    TipoBloccoDocumento,
)

LOGO_ASSET_ID = "logo-cnr-demo"


def asset_logo_demo() -> AssetDocumento:
    return AssetDocumento(
        id=LOGO_ASSET_ID,
        tipo=TipoAsset.LOGO,
        nome="Logo CNR (demo)",
        versione=1,
        storage_ref="documentale-mock://assets/logo-cnr-demo-v1.png",
        hash_file="DEMO_HASH_LOGO_CNR_V1",
        dimensioni_consentite="200x60",
        spec_owner="specs/003-sezioni-placeholder-versionamento",
    )


def modello_valido() -> ModelloDocumentaleControllato:
    return ModelloDocumentaleControllato(
        id="modello-demo-test",
        modello_versione_id="demo-bando-concorso-standard-v1",
        formato="GEMODO_DOCUMENT_V1",
        pagina=PaginaDocumento(size="A4", orientamento="PORTRAIT", margini="standard-cnr"),
        regioni=["header", "body", "footer", "signature_area"],
        blocchi=[
            BloccoDocumento(
                id="header-logo",
                tipo=TipoBloccoDocumento.LOGO,
                posizionamento=PosizionamentoBlocco.TOP,
                ordine=1,
                asset_ref=LOGO_ASSET_ID,
            ),
            BloccoDocumento(
                id="titolo-bando",
                tipo=TipoBloccoDocumento.TITOLO,
                posizionamento=PosizionamentoBlocco.BODY,
                ordine=2,
                stile="title",
                placeholder_usati=["codice_bando"],
            ),
            BloccoDocumento(
                id="tabella-requisiti",
                tipo=TipoBloccoDocumento.TABELLA,
                posizionamento=PosizionamentoBlocco.BODY,
                ordine=3,
                stile="table",
                colonne=["Sede", "Requisiti", "Posti"],
            ),
            BloccoDocumento(
                id="firma-direttore",
                tipo=TipoBloccoDocumento.FIRMA,
                posizionamento=PosizionamentoBlocco.BOTTOM_RIGHT,
                ordine=4,
                stile="signature",
            ),
        ],
        asset=[asset_logo_demo()],
        stili_ammessi=["title", "table", "signature"],
        placeholder_usati=["codice_bando"],
        spec_owner="specs/003-sezioni-placeholder-versionamento",
        contiene_html_libero=False,
        contiene_css_libero=False,
        contiene_script=False,
    )


def modello_con_html_libero() -> ModelloDocumentaleControllato:
    return modello_valido().model_copy(update={"contiene_html_libero": True})


def modello_con_posizionamento_non_valido() -> ModelloDocumentaleControllato:
    modello = modello_valido()
    blocchi = list(modello.blocchi)
    blocchi[3] = blocchi[3].model_copy(update={"posizionamento": PosizionamentoBlocco.TOP})
    return modello.model_copy(update={"blocchi": blocchi})


def modello_con_tabella_senza_colonne() -> ModelloDocumentaleControllato:
    modello = modello_valido()
    blocchi = list(modello.blocchi)
    blocchi[2] = blocchi[2].model_copy(update={"colonne": []})
    return modello.model_copy(update={"blocchi": blocchi})


def modello_con_placeholder_non_dichiarato() -> ModelloDocumentaleControllato:
    modello = modello_valido()
    blocchi = list(modello.blocchi)
    blocchi[1] = blocchi[1].model_copy(update={"placeholder_usati": ["campo_non_dichiarato"]})
    return modello.model_copy(update={"blocchi": blocchi})


def modello_con_asset_ref_mancante() -> ModelloDocumentaleControllato:
    modello = modello_valido()
    blocchi = list(modello.blocchi)
    blocchi[0] = blocchi[0].model_copy(update={"asset_ref": "asset-inesistente"})
    return modello.model_copy(update={"blocchi": blocchi})
