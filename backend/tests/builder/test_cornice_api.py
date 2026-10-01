"""Intestazione e pie' di pagina impostati da chi gestisce i modelli (012 T065-T067, T070).

PostgreSQL reale e HTTP. Le prove che contano: il gestore del contesto, senza
essere amministratore, imposta la cornice del suo tipo documento; quello di un
altro contesto no; il logo caricato finisce nel PDF ricodificato, e un file che
non e' un'immagine non ci arriva.
"""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO

import pytest
import sqlalchemy as sa
import yaml
from PIL import Image
from pypdf import PdfReader
from sqlalchemy.orm import Session

from tests.builder.test_anteprima_api import PROFILI_LOCALI, _anteprima, _bozza_composta
from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.pdf import estrai_testo
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

CORNICE = {
    "intestazione": {
        "maschera": "LOGO_CENTRO_TESTO_SOTTO",
        "con_logo": True,
        "testo": [{"testo": "Consiglio Nazionale delle Ricerche", "grassetto": True},
                  {"testo": "\nUfficio Reclutamento del Personale"}],
    },
    "pie_pagina": {"testo": [{"testo": "Piazzale Aldo Moro 7 - Roma"}], "numerazione_pagine": True},
}


def _url(integrazione_id, codice: str = "BANDO_CONCORSO") -> str:
    return f"/api/v1/builder/integrazioni/{integrazione_id}/tipi-documento/{codice}/cornice"


def _png(colore=(0, 70, 140, 255)) -> bytes:
    uscita = BytesIO()
    Image.new("RGBA", (200, 100), colore).save(uscita, format="PNG")
    return uscita.getvalue()


@pytest.fixture(autouse=True)
def senza_cornice(db_engine):
    """Il database di test e' condiviso: la cornice di un test non resta agli altri."""
    yield
    with Session(db_engine) as db:
        db.execute(sa.text("UPDATE tipo_documento SET cornice_pagina = NULL, logo_cornice = NULL"))
        db.commit()


@pytest.fixture()
def solo_gestore(monkeypatch):
    """Chi compone i modelli nel contesto geban, senza essere amministratore."""
    monkeypatch.setenv("GEMODO_MOCK_ROLES", "DOCUMENTI_VIEWER")


@pytest.mark.integration
def test_il_gestore_del_contesto_imposta_intestazione_e_pie_di_pagina(
    builder_client, integrazione_connessa, solo_gestore,
):
    vuota = builder_client.get(_url(integrazione_connessa))
    assert vuota.status_code == 200, vuota.text
    assert vuota.json()["cornice"] is None
    assert vuota.json()["maschere_intestazione"] == ["LOGO_CENTRO_TESTO_SOTTO"]

    salvata = builder_client.put(_url(integrazione_connessa), json=CORNICE)
    assert salvata.status_code == 200, salvata.text
    letta = builder_client.get(_url(integrazione_connessa)).json()["cornice"]
    assert letta["intestazione"]["maschera"] == "LOGO_CENTRO_TESTO_SOTTO"
    assert letta["pie_pagina"]["numerazione_pagine"] is True


@pytest.mark.integration
def test_intestazione_e_pie_di_pagina_sono_indipendenti(builder_client, integrazione_connessa):
    risposta = builder_client.put(_url(integrazione_connessa), json={"pie_pagina": CORNICE["pie_pagina"]})
    assert risposta.status_code == 200, risposta.text
    assert risposta.json()["cornice"]["intestazione"] is None


@pytest.mark.integration
def test_il_gestore_di_un_altro_contesto_non_la_tocca(
    builder_client, integrazione_connessa, monkeypatch, tmp_path,
):
    manifest = yaml.safe_load(PROFILI_LOCALI.read_text(encoding="utf-8"))
    geban = manifest["sistemi_richiedenti"][0]
    for client in geban["client_applicativi"]:
        if client["client_id"] == "geri-angular-public":
            client["token_contexts"] = [*client.get("token_contexts", []), "altro"]
    profilo = geban["profili_integrazione"][0]
    mapping = deepcopy(next(m for m in profilo["role_mappings"] if m["external_role"] == "ROLE_MANAGER#geban"))
    profilo["role_mappings"].append({**mapping, "token_context": "altro", "external_role": "ROLE_MANAGER#altro"})
    percorso = tmp_path / "profili.yaml"
    percorso.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    monkeypatch.setenv("GEMODO_INTEGRATION_PROFILES_PATH", str(percorso))
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "altro")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_MANAGER#altro")
    monkeypatch.setenv("GEMODO_MOCK_ROLES", "DOCUMENTI_VIEWER")

    assert builder_client.put(_url(integrazione_connessa), json=CORNICE).status_code == 403
    assert builder_client.put(f"{_url(integrazione_connessa)}/logo", content=_png()).status_code == 403


@pytest.mark.integration
def test_fr011_cornice_e_logo_arrivano_nel_pdf_di_ogni_modello_del_tipo(
    builder_client, integrazione_connessa, solo_gestore,
):
    modello, versione = _bozza_composta(builder_client, "cornice-logo-nel-pdf")
    assert builder_client.put(_url(integrazione_connessa), json=CORNICE).status_code == 200
    caricato = builder_client.put(f"{_url(integrazione_connessa)}/logo", content=_png(),
                                  headers={"Content-Type": "image/png"})
    assert caricato.status_code == 204, caricato.text

    pdf = _anteprima(builder_client, modello, versione).content
    testo = estrai_testo(pdf)
    assert "Consiglio Nazionale delle Ricerche Ufficio Reclutamento del Personale" in testo
    assert "Piazzale Aldo Moro 7 - Roma" in testo
    assert len(PdfReader(BytesIO(pdf)).pages[0].images) == 1

    # L'editor vede la stessa cornice, con dove impostarla.
    del_modello = builder_client.get(f"/api/v1/builder/modelli/{modello['id']}/cornice").json()
    assert del_modello["logo_presente"] is True
    assert del_modello["integrazione_id"] == str(integrazione_connessa)
    assert del_modello["codice_tipo_documento"] == "BANDO_CONCORSO"


@pytest.mark.integration
def test_t066_il_logo_si_conserva_ricodificato_e_si_puo_togliere(builder_client, integrazione_connessa):
    jpeg = BytesIO()
    Image.new("RGB", (300, 150), (200, 0, 0)).save(jpeg, format="JPEG")
    assert builder_client.put(f"{_url(integrazione_connessa)}/logo", content=jpeg.getvalue()).status_code == 204

    letto = builder_client.get(f"{_url(integrazione_connessa)}/logo")
    assert letto.status_code == 200
    assert letto.headers["content-type"] == "image/png"
    with Image.open(BytesIO(letto.content)) as immagine:
        assert immagine.format == "PNG" and immagine.size == (300, 150)

    assert builder_client.delete(f"{_url(integrazione_connessa)}/logo").status_code == 204
    assert builder_client.get(f"{_url(integrazione_connessa)}/logo").status_code == 404


@pytest.mark.integration
def test_t066_un_file_che_non_e_un_immagine_o_troppo_grande_e_rifiutato(builder_client, integrazione_connessa):
    finto = builder_client.put(f"{_url(integrazione_connessa)}/logo", content=b"<svg onload=alert(1)>")
    assert finto.status_code == 422, finto.text
    assert "immagine" in finto.json()["dettagli"][0]["violazione"]

    grande = builder_client.put(f"{_url(integrazione_connessa)}/logo", content=b"\0" * (1024 * 1024 + 1))
    assert grande.status_code == 422
    assert "1 MB" in grande.json()["dettagli"][0]["violazione"]
    assert builder_client.get(_url(integrazione_connessa)).json()["logo_presente"] is False


@pytest.mark.integration
def test_markup_e_troppe_righe_sono_rifiutati(builder_client, integrazione_connessa):
    risposta = builder_client.put(_url(integrazione_connessa), json={
        "intestazione": {"testo": [{"testo": "<b>CNR</b>\nuno\ndue\ntre"}]},
    })
    assert risposta.status_code == 422, risposta.text
    violazioni = " | ".join(d["violazione"] for d in risposta.json()["dettagli"])
    assert "markup" in violazioni and "4 righe" in violazioni
    assert builder_client.get(_url(integrazione_connessa)).json()["cornice"] is None


@pytest.mark.integration
def test_tipo_documento_che_l_integrazione_non_dichiara(builder_client, integrazione_connessa):
    assert builder_client.put(_url(integrazione_connessa, "INESISTENTE"), json=CORNICE).status_code == 404
