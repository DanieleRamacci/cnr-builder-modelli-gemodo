"""Anteprima PDF della bozza (012 US4, T034-T039).

Il cuore della storia e' FR-010: l'anteprima **non e' una generazione**. Lo si
verifica sul database vero - nessun `DocumentoGenerato`, nessun evento di
audit, nessuna chiave di idempotenza consumata - non su un mock dello storage,
che proverebbe solo che il mock non e' stato chiamato.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.storage.models import DocumentoGenerato
from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
    _crea_modello,
    _crea_versione,
    _pubblica_fino_in_fondo,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.e2e.test_documento_composto import dati_completi, sezioni_del_bando
from tests.support.pdf import estrai_font_e_testo, estrai_testo
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

PROFILI_LOCALI = Path(__file__).resolve().parents[3] / "infra/local/integration-profiles.local.yaml"


def _bozza_composta(client, codice: str) -> tuple[dict, dict]:
    modello = _crea_modello(client, codice=codice)
    versione = _crea_versione(client, modello["id"])
    composto = client.put(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/sezioni",
        json={"sezioni": sezioni_del_bando()},
    )
    assert composto.status_code == 200, composto.text
    return modello, versione


def _anteprima(client, modello: dict, versione: dict, **corpo):
    return client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/anteprima",
        json=corpo or None,
    )


def _conta(db_engine, tabella_o_modello) -> int:
    with Session(db_engine) as db:
        if isinstance(tabella_o_modello, str):
            return db.execute(text(f"SELECT count(*) FROM {tabella_o_modello}")).scalar_one()
        return db.scalar(select(func.count()).select_from(tabella_o_modello))


@pytest.mark.integration
def test_l_anteprima_e_il_pdf_della_bozza_con_valori_fac_simile(builder_client):
    modello, versione = _bozza_composta(builder_client, "anteprima-fac-simile")

    risposta = _anteprima(builder_client, modello, versione)

    assert risposta.status_code == 200, risposta.text
    assert risposta.headers["content-type"] == "application/pdf"
    assert risposta.headers["x-gemodo-anteprima"] == "true"
    assert risposta.headers["content-disposition"].startswith('inline; filename="anteprima-')
    testo = estrai_testo(risposta.content)
    # FR-009: marcata come anteprima, oltre che come documento di test.
    assert "ANTEPRIMA DELLA BOZZA" in testo
    assert "NON UFFICIALE" in testo
    # T035: ogni segnaposto diventa «etichetta», riconoscibile a colpo d'occhio.
    assert "Bando di concorso «codice_bando»" in testo
    assert "presso «sede_prescelta_it»" in testo
    assert "{{" not in testo


@pytest.mark.integration
def test_i_valori_passati_prendono_il_posto_del_fac_simile(builder_client):
    modello, versione = _bozza_composta(builder_client, "anteprima-valori")

    risposta = _anteprima(builder_client, modello, versione, valori={"numero_posti": "2"})

    assert risposta.status_code == 200, risposta.text
    testo = estrai_testo(risposta.content)
    assert "I posti messi a concorso sono 2." in testo
    assert "«codice_bando»" in testo


@pytest.mark.integration
def test_fr008_anteprima_e_documento_finale_escono_dallo_stesso_renderer(builder_client):
    """SC-003: a parita' di valori, anteprima e PDF generato hanno lo stesso corpo."""
    modello, versione = _bozza_composta(builder_client, "anteprima-uguale")
    valori = {nome: str(valore) for nome, valore in dati_completi().items()}
    anteprima = _anteprima(builder_client, modello, versione, valori=valori)
    assert anteprima.status_code == 200, anteprima.text

    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])
    generato = builder_client.post("/api/v1/documenti/genera", json={
        "sistema_richiedente": "PYTEST_E2E",
        "external_context_id": uuid.uuid4().hex[:12],
        "modello_versione_id": pubblicata["public_id"],
        "dati": dati_completi(),
    })
    assert generato.status_code == 200, generato.text

    def corpo(pdf: bytes) -> list[tuple[str, str]]:
        # Tutto cio' che segue il titolo: la marcatura di anteprima e' l'unica
        # differenza ammessa, e sta sopra.
        pezzi = [(font, testo) for font, testo in estrai_font_e_testo(pdf) if testo.strip()]
        inizio = next(i for i, (_, testo) in enumerate(pezzi) if testo.startswith("Bando di concorso BND"))
        return pezzi[inizio:]

    assert corpo(anteprima.content) == corpo(generato.content)


@pytest.mark.integration
def test_t037_fr010_l_anteprima_non_registra_nulla_e_non_consuma_l_idempotenza(builder_client, db_engine):
    modello, versione = _bozza_composta(builder_client, "anteprima-nessuna-traccia")
    documenti_prima = _conta(db_engine, DocumentoGenerato)
    eventi_prima = _conta(db_engine, "audit_evento_modello")

    for _ in range(2):
        assert _anteprima(builder_client, modello, versione).status_code == 200

    # Nessun documento generato e nessun evento: l'anteprima non lascia traccia.
    assert _conta(db_engine, DocumentoGenerato) == documenti_prima
    assert _conta(db_engine, "audit_evento_modello") == eventi_prima

    # E la prima generazione vera produce un documento nuovo: nessuna chiave di
    # idempotenza era stata consumata.
    pubblicata = _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])
    generato = builder_client.post("/api/v1/documenti/genera", json={
        "sistema_richiedente": "PYTEST_E2E",
        "external_context_id": "anteprima-idempotenza",
        "modello_versione_id": pubblicata["public_id"],
        "dati": dati_completi(),
    })
    assert generato.status_code == 200, generato.text
    assert _conta(db_engine, DocumentoGenerato) == documenti_prima + 1


@pytest.mark.integration
def test_t039_l_anteprima_si_chiede_sulle_bozze(builder_client):
    modello, versione = _bozza_composta(builder_client, "anteprima-pubblicata")
    _pubblica_fino_in_fondo(builder_client, modello["id"], versione["id"])

    risposta = _anteprima(builder_client, modello, versione)

    assert risposta.status_code == 409, risposta.text
    assert risposta.json()["codice"] == "MODELLO_VERSIONE_NON_MODIFICABILE"


@pytest.mark.integration
def test_t038_chi_sa_solo_generare_riceve_403(builder_client, monkeypatch):
    """FR-010: l'anteprima e' un'azione di chi compone, non di chi genera."""
    modello, versione = _bozza_composta(builder_client, "anteprima-generatore")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "geban-backend")
    monkeypatch.delenv("GEMODO_MOCK_CONTEXT")
    monkeypatch.delenv("GEMODO_MOCK_CONTEXT_ROLES")
    monkeypatch.setenv("GEMODO_MOCK_ROLES", "DOCUMENTI_GENERATORE")

    risposta = _anteprima(builder_client, modello, versione)

    assert risposta.status_code == 403, risposta.text


@pytest.mark.integration
def test_t038_un_gestore_di_un_altro_contesto_riceve_404(builder_client, monkeypatch, tmp_path):
    """Non si rivela l'esistenza di una versione che il chiamante non puo' vedere."""
    modello, versione = _bozza_composta(builder_client, "anteprima-altro-contesto")

    # Lo stesso manifest locale, con un contesto in piu' in cui il chiamante e'
    # davvero gestore: senza, "altro" non concederebbe alcun permesso e il caso
    # diventerebbe quello del 403.
    manifest = yaml.safe_load(PROFILI_LOCALI.read_text(encoding="utf-8"))
    geban = manifest["sistemi_richiedenti"][0]
    for client in geban["client_applicativi"]:
        if client["client_id"] == "geri-angular-public":
            client["token_contexts"] = [*client.get("token_contexts", []), "altro"]
    profilo = geban["profili_integrazione"][0]
    mapping = deepcopy(next(
        m for m in profilo["role_mappings"] if m["external_role"] == "ROLE_MANAGER#geban"
    ))
    profilo["role_mappings"].append({**mapping, "token_context": "altro", "external_role": "ROLE_MANAGER#altro"})
    percorso = tmp_path / "profili.yaml"
    percorso.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    monkeypatch.setenv("GEMODO_INTEGRATION_PROFILES_PATH", str(percorso))
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", "altro")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", "ROLE_MANAGER#altro")

    risposta = _anteprima(builder_client, modello, versione)

    assert risposta.status_code == 404, risposta.text
    assert risposta.json()["codice"] == "MODELLO_VERSIONE_NON_TROVATO"


@pytest.mark.integration
def test_un_corpo_con_campi_sconosciuti_e_rifiutato(builder_client):
    modello, versione = _bozza_composta(builder_client, "anteprima-corpo")

    risposta = _anteprima(builder_client, modello, versione, dati={"x": "y"})

    # La convenzione del servizio per un corpo non valido: 400, come ogni rotta.
    assert risposta.status_code == 400, risposta.text
    assert risposta.json()["dettagli"][0]["campo"] == "body.dati"
