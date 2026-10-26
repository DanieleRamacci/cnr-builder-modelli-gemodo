"""Modello multiplo: creazione, tabella con riga ripetuta, validazione, generazione, catalogo (014).

Passa dalle API HTTP contro PostgreSQL reale, come il resto della cartella. Il
discovery e' un server HTTP di prova perche' l'integratore e' un sistema
esterno; tutto il resto e' il codice vero. Il caso e' il bando 367.501 a tempo
determinato con tre tematiche.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    CAMPI_BASE,
    _pubblica_fino_in_fondo,
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.pdf import estrai_testo
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

PERCORSO = ["TD", "RICERCATORE"]
# Un livello che il seed non occupa: il modello singolo di questi test e' lo
# STANDARD dello slot, senza nota.
LIVELLO = "IV"

ARTICOLAZIONI = {
    "codice": "articolazioni", "etichetta": "Tematiche del bando", "tipo": "array",
    "obbligatorio": False, "ordine": 7,
    "campi": [
        {"codice": "codice_bando", "etichetta": "Codice sottobando", "tipo": "string", "obbligatorio": True, "ordine": 1},
        {"codice": "numero_posti", "etichetta": "Posti", "tipo": "number", "obbligatorio": True, "ordine": 2},
        {"codice": "sede_lavoro", "etichetta": "Sede", "tipo": "string", "obbligatorio": True, "ordine": 3},
        {"codice": "comune_sede_lavoro", "etichetta": "Comune", "tipo": "string", "obbligatorio": False, "ordine": 4},
    ],
}
SOTTO = ["codice_bando", "numero_posti", "sede_lavoro", "comune_sede_lavoro"]


@pytest.fixture()
def slot_pulito(db_engine):
    """Lo slot di questi test libero prima, e i modelli creati tolti dopo.

    Come `slot_pulito` delle varianti, piu' il registro delle generazioni: un
    test che genera lascia una riga che punta alla versione, e senza toglierla
    il modello non si cancella e occuperebbe lo slot del test seguente.
    """
    slot = {"percorso": '["TD", "RICERCATORE"]', "dimensioni": f'{{"lingua": "IT", "livello_professionale": "{LIVELLO}"}}'}
    with Session(db_engine) as db:
        db.execute(sa.text(
            "UPDATE modello_documento SET stato = 'ELIMINATO'"
            " WHERE percorso_categorizzazione = CAST(:percorso AS jsonb) AND dimensioni = CAST(:dimensioni AS jsonb)"
        ), slot)
        db.commit()
        prima = set(db.scalars(sa.text("SELECT id FROM modello_documento")).all())
    yield
    with Session(db_engine) as db:
        nuovi = [i for i in db.scalars(sa.text("SELECT id FROM modello_documento")).all() if i not in prima]
        if nuovi:
            versioni = sa.text("SELECT id FROM modello_versione WHERE modello_documento_id = ANY(:ids)")
            db.execute(sa.text(f"DELETE FROM documento_generato WHERE modello_versione_id IN ({versioni.text})"),
                       {"ids": nuovi})
            db.execute(sa.text("DELETE FROM audit_evento_modello WHERE modello_documento_id = ANY(:ids)"), {"ids": nuovi})
            db.execute(sa.text("DELETE FROM modello_documento WHERE id = ANY(:ids)"), {"ids": nuovi})
            db.commit()


@pytest.fixture()
def con_articolazioni(catalogo_esterno):
    foglia = catalogo_esterno[1]["/discovery"][1]["BANDO_CONCORSO"]["nodi"][0]["figli"][0]
    foglia["campi"].append(ARTICOLAZIONI)
    return foglia


def _crea(client, *, multiplo: bool, nota: str | None = None):
    corpo = {
        "codice_tipo_documento": "BANDO_CONCORSO", "percorso_categorizzazione": PERCORSO,
        "lingua": "IT", "livello_professionale": LIVELLO, "multiplo": multiplo,
    }
    if nota:
        corpo["nota"] = nota
    return client.post("/api/v1/builder/modelli", json=corpo)


def _versione(client, modello_id: str, *, con_articolazioni: bool):
    campi = [*CAMPI_BASE, *([{"codice": "articolazioni", "lingua": "IT"}] if con_articolazioni else [])]
    return client.post(f"/api/v1/builder/modelli/{modello_id}/versioni", json={"campi": campi})


def _frammento(testo: str, **enfasi) -> dict:
    return {"testo": testo, **enfasi}


def _cella(testo: str = "", **enfasi) -> dict:
    return {"frammenti": [_frammento(testo, **enfasi)] if testo else []}


def _tabella(identificativo: str, righe: list[dict], *, ordine: int = 1) -> dict:
    segnaposti = []
    for riga in righe:
        for cella in riga["celle"]:
            for frammento in cella["frammenti"]:
                testo = frammento["testo"]
                while "{{" in testo:
                    nome = testo.split("{{", 1)[1].split("}}", 1)[0].strip()
                    if nome not in segnaposti:
                        segnaposti.append(nome)
                    testo = testo.split("}}", 1)[1]
    return {
        "id": identificativo, "tipo": "TABELLA", "posizionamento": "BODY", "ordine": ordine,
        "colonne": ["Codice", "Tematica", "Posti", "Comune"], "righe": righe, "placeholder_usati": segnaposti,
    }


RIGA_RIPETUTA = {"ripeti_per": "articolazioni", "celle": [
    _cella("{{articolazioni.campi.codice_bando}}"), _cella("{{articolazioni.descrizione}}"),
    _cella("{{articolazioni.campi.numero_posti}}", grassetto=True), _cella("{{articolazioni.campi.comune_sede_lavoro}}"),
]}
RIGA_TOTALE = {"ripeti_per": None, "celle": [_cella("Totale"), _cella(), _cella("{{numero_posti}}"), _cella()]}
PREMESSA = {
    "id": "premessa", "tipo": "PARAGRAFO", "posizionamento": "BODY", "ordine": 0,
    "frammenti": [_frammento("Bando {{codice_bando}}: i posti sono cosi' ripartiti.")],
    "placeholder_usati": ["codice_bando"],
}


def _sezioni(client, modello_id: str, versione_id: str, blocchi: list[dict]):
    return client.put(
        f"/api/v1/builder/modelli/{modello_id}/versioni/{versione_id}/sezioni",
        json={"sezioni": [{"codice": "posti", "ordine": 10, "contenuto": blocchi}]},
    )


def _violazioni(risposta) -> str:
    return " | ".join(d["violazione"] for d in risposta.json().get("dettagli") or [])


def _multiplo_pubblicato(client) -> tuple[dict, dict]:
    modello = _crea(client, multiplo=True)
    assert modello.status_code == 201, modello.text
    versione = _versione(client, modello.json()["id"], con_articolazioni=True)
    assert versione.status_code == 201, versione.text
    salvate = _sezioni(client, modello.json()["id"], versione.json()["id"],
                       [PREMESSA, _tabella("posti", [RIGA_RIPETUTA, RIGA_TOTALE])])
    assert salvate.status_code == 200, salvate.text
    pubblicata = _pubblica_fino_in_fondo(client, modello.json()["id"], versione.json()["id"])
    return modello.json(), pubblicata


DATI_367_501 = {
    "codice_bando": "367.501", "titolo_it": "Selezione CTER", "sede_prescelta_it": "Sedi diverse",
    "numero_posti": 10, "titolo_en": "CTER selection", "livello": "V",
    "articolazioni": [
        {"codice": "TEMA_A", "descrizione": "Tematica A - Chimica ambientale",
         "campi": {"codice_bando": "367.501-A", "numero_posti": 2, "sede_lavoro": "IIA", "comune_sede_lavoro": "Roma"}},
        {"codice": "TEMA_B", "descrizione": "Tematica B - Oceanografia",
         "campi": {"codice_bando": "367.501-B", "numero_posti": 5, "sede_lavoro": "ISMAR", "comune_sede_lavoro": "Napoli"}},
        {"codice": "TEMA_C", "descrizione": "Tematica C - Calcolo",
         "campi": {"codice_bando": "367.501-C", "numero_posti": 3, "sede_lavoro": "IIT"}},
    ],
}


def _richiesta(versione_pubblica: int, dati: dict) -> dict:
    return {"sistema_richiedente": "GEBAN", "external_context_id": f"367.501-{uuid.uuid4().hex[:6]}",
            "modello_versione_id": versione_pubblica, "dati": dati}


# --- US2: creazione e versione -------------------------------------------------


@pytest.mark.integration
def test_il_multiplo_si_crea_solo_dove_la_foglia_ha_campi_ripetibili(builder_client, catalogo_esterno, slot_pulito):
    rifiutato = _crea(builder_client, multiplo=True)

    assert rifiutato.status_code == 400, rifiutato.text
    assert rifiutato.json()["codice"] == "CONTESTO_NON_VALIDO"


@pytest.mark.integration
def test_singolo_e_multiplo_coesistono_pubblicati_con_identita_distinte(
    builder_client, con_articolazioni, slot_pulito, db_engine,
):
    singolo = _crea(builder_client, multiplo=False).json()
    versione_singolo = _versione(builder_client, singolo["id"], con_articolazioni=False).json()
    _pubblica_fino_in_fondo(builder_client, singolo["id"], versione_singolo["id"])

    multiplo, _ = _multiplo_pubblicato(builder_client)

    assert multiplo["multiplo"] is True and singolo["multiplo"] is False
    assert "MULTIPLO" in multiplo["codice"].upper() and "bando multiplo" in multiplo["nome"]
    assert multiplo["variante"] == "STANDARD", "il multiplo non e' una variante del singolo"
    # FR-009f: pubblicare il multiplo non archivia il singolo.
    dettaglio = builder_client.get(f"/api/v1/builder/modelli/{singolo['id']}").json()
    assert dettaglio["versioni"][0]["stato"] == "PUBBLICATO"
    # Un secondo multiplo senza nota sullo stesso slot segue la regola delle varianti.
    assert _crea(builder_client, multiplo=True).status_code == 409
    # `multiplo` non si cambia dopo: nessuna rotta lo accetta.
    with Session(db_engine) as db:
        assert db.scalar(sa.text("SELECT multiplo FROM modello_documento WHERE id = :id"),
                         {"id": singolo["id"]}) is False


@pytest.mark.integration
def test_la_versione_segue_la_regola_dei_campi_ripetibili(builder_client, con_articolazioni, slot_pulito):
    singolo = _crea(builder_client, multiplo=False).json()
    multiplo = _crea(builder_client, multiplo=True).json()

    con = _versione(builder_client, singolo["id"], con_articolazioni=True)
    assert con.status_code == 400 and con.json()["codice"] == "CAMPO_NON_AMMESSO", con.text
    senza = _versione(builder_client, multiplo["id"], con_articolazioni=False)
    assert senza.status_code == 400 and "articolazioni" in senza.json()["messaggio"], senza.text

    assert _versione(builder_client, multiplo["id"], con_articolazioni=True).status_code == 201
    campi = builder_client.get(f"/api/v1/builder/modelli/{multiplo['id']}").json()["versioni"][0]["campi"]
    articolazioni = next(c for c in campi if c["codice"] == "articolazioni")
    # FR-016c: nella foglia e' facoltativo, nel modello multiplo no.
    assert articolazioni["obbligatorio"] is True
    assert [s["codice"] for s in articolazioni["sotto_campi"]] == SOTTO
    assert all(c["sotto_campi"] is None for c in campi if c["codice"] != "articolazioni")


@pytest.mark.integration
def test_il_multiplo_nasce_dal_testo_del_singolo(builder_client, con_articolazioni, slot_pulito):
    singolo = _crea(builder_client, multiplo=False).json()
    versione = _versione(builder_client, singolo["id"], con_articolazioni=False).json()
    assert _sezioni(builder_client, singolo["id"], versione["id"], [PREMESSA]).status_code == 200

    creato = builder_client.post(f"/api/v1/builder/modelli/{singolo['id']}/multiplo")

    assert creato.status_code == 201, creato.text
    multiplo = creato.json()
    assert multiplo["multiplo"] is True
    nuova = multiplo["versioni"][0]
    sezioni = builder_client.get(
        f"/api/v1/builder/modelli/{multiplo['id']}/versioni/{nuova['id']}/sezioni"
    ).json()["sezioni"]
    assert sezioni[0]["contenuto"][0]["frammenti"][0]["testo"].startswith("Bando {{codice_bando}}")
    campi = builder_client.get(f"/api/v1/builder/modelli/{multiplo['id']}").json()["versioni"][0]["campi"]
    assert "articolazioni" in {c["codice"] for c in campi}

    di_nuovo = builder_client.post(f"/api/v1/builder/modelli/{singolo['id']}/multiplo")
    assert di_nuovo.status_code == 409 and di_nuovo.json()["codice"] == "MODELLO_VARIANTE_DUPLICATA"
    assert di_nuovo.json()["dettagli"][0]["modello_id"] == multiplo["id"]
    dal_multiplo = builder_client.post(f"/api/v1/builder/modelli/{multiplo['id']}/multiplo")
    assert dal_multiplo.status_code == 400 and dal_multiplo.json()["codice"] == "CONTESTO_NON_VALIDO"


@pytest.mark.integration
def test_varianti_ed_edizioni_derivate_del_multiplo_restano_multiple(builder_client, con_articolazioni, slot_pulito):
    multiplo, _ = _multiplo_pubblicato(builder_client)

    variante = builder_client.post(f"/api/v1/builder/modelli/{multiplo['id']}/varianti",
                                   json={"nota": "Senza prova preselettiva"})
    edizione = builder_client.post(f"/api/v1/builder/modelli/{multiplo['id']}/edizioni-derivate",
                                   json={"lingua": "EN"})

    assert variante.status_code == 201, variante.text
    assert variante.json()["multiplo"] is True
    assert edizione.status_code == 201, edizione.text
    assert edizione.json()["multiplo"] is True


# --- US2: regole del documento -------------------------------------------------


@pytest.mark.integration
def test_la_bozza_del_multiplo_si_salva_senza_tabella_ma_non_si_pubblica(builder_client, con_articolazioni, slot_pulito):
    modello = _crea(builder_client, multiplo=True).json()
    versione = _versione(builder_client, modello["id"], con_articolazioni=True).json()

    salvata = _sezioni(builder_client, modello["id"], versione["id"], [PREMESSA])
    assert salvata.status_code == 200, salvata.text

    for azione in ("invia-revisione", "approva"):
        builder_client.post(f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/{azione}")
    pubblica = builder_client.post(f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/pubblica")
    assert pubblica.status_code == 400, pubblica.text
    assert "non ha una riga di tabella ripetuta per 'articolazioni'" in _violazioni(pubblica)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("blocchi", "atteso"),
    [
        pytest.param([_tabella("t", [{"ripeti_per": "articolazioni", "celle": [
            _cella("{{numero_posti}}"), _cella(), _cella(), _cella()]}])],
            "non e' di un elemento di 'articolazioni'", id="principale-dentro-la-riga-ripetuta"),
        pytest.param([{**PREMESSA, "frammenti": [_frammento("Posti {{articolazioni.campi.numero_posti}}")],
                       "placeholder_usati": ["articolazioni.campi.numero_posti"]}],
            "sta solo in una riga di tabella ripetuta", id="elemento-fuori-dalla-tabella"),
        pytest.param([{**PREMESSA, "frammenti": [_frammento("{{articolazioni}}")],
                       "placeholder_usati": ["articolazioni"]}],
            "'articolazioni' non presente nel contratto dati", id="lista-grezza"),
        pytest.param([_tabella("t", [RIGA_RIPETUTA, RIGA_RIPETUTA])],
            "2 righe ripetute su 'articolazioni' nella stessa tabella", id="due-righe-ripetute"),
        pytest.param([_tabella("t", [{"ripeti_per": "sedi", "celle": [_cella(), _cella(), _cella(), _cella()]}])],
            "'sedi' non e' un campo ripetibile", id="campo-inesistente"),
    ],
)
def test_i_segnaposti_dei_sottobandi_stanno_solo_nella_riga_ripetuta(
    builder_client, con_articolazioni, slot_pulito, blocchi, atteso,
):
    modello = _crea(builder_client, multiplo=True).json()
    versione = _versione(builder_client, modello["id"], con_articolazioni=True).json()

    risposta = _sezioni(builder_client, modello["id"], versione["id"], blocchi)

    assert risposta.status_code == 400, risposta.text
    assert risposta.json()["codice"] == "PLACEHOLDER_NON_VALIDO"
    assert atteso in _violazioni(risposta)


@pytest.mark.integration
def test_due_tabelle_diverse_possono_ripetere_le_articolazioni(builder_client, con_articolazioni, slot_pulito):
    modello = _crea(builder_client, multiplo=True).json()
    versione = _versione(builder_client, modello["id"], con_articolazioni=True).json()

    salvata = _sezioni(builder_client, modello["id"], versione["id"], [
        _tabella("riepilogo", [RIGA_RIPETUTA], ordine=0), _tabella("sedi", [RIGA_RIPETUTA], ordine=1),
    ])

    assert salvata.status_code == 200, salvata.text


@pytest.mark.integration
def test_un_singolo_non_ha_righe_ripetute_e_una_riga_deve_avere_una_cella_per_colonna(
    builder_client, con_articolazioni, slot_pulito,
):
    singolo = _crea(builder_client, multiplo=False).json()
    versione = _versione(builder_client, singolo["id"], con_articolazioni=False).json()

    ripetuta = _sezioni(builder_client, singolo["id"], versione["id"],
                        [_tabella("t", [{"ripeti_per": "articolazioni", "celle": [_cella()] * 4}])])
    assert ripetuta.status_code == 400 and "un modello singolo non ha righe ripetute" in _violazioni(ripetuta)

    corta = _sezioni(builder_client, singolo["id"], versione["id"],
                     [_tabella("t", [{"ripeti_per": None, "celle": [_cella("solo una")]}])])
    assert corta.status_code == 422, corta.text
    assert "1 celle per 4 colonne" in _violazioni(corta)


@pytest.mark.integration
def test_l_anteprima_mostra_due_righe_d_esempio(builder_client, con_articolazioni, slot_pulito):
    modello = _crea(builder_client, multiplo=True).json()
    versione = _versione(builder_client, modello["id"], con_articolazioni=True).json()
    _sezioni(builder_client, modello["id"], versione["id"], [_tabella("posti", [RIGA_RIPETUTA, RIGA_TOTALE])])

    anteprima = builder_client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni/{versione['id']}/anteprima", json={},
    )

    assert anteprima.status_code == 200, anteprima.text
    testo = estrai_testo(anteprima.content)
    assert "Codice sottobando (1)" in testo and "Codice sottobando (2)" in testo
    assert "Tematiche del bando (1)" in testo and "Tematiche del bando (2)" in testo


# --- US3: validazione, generazione, catalogo ----------------------------------


@pytest.mark.integration
def test_il_bando_367_501_genera_un_solo_pdf_con_una_riga_per_tematica(builder_client, con_articolazioni, slot_pulito):
    _, pubblicata = _multiplo_pubblicato(builder_client)

    generazione = builder_client.post("/api/v1/documenti/genera", json=_richiesta(pubblicata["public_id"], DATI_367_501))

    assert generazione.status_code == 200, generazione.text
    assert generazione.headers["content-type"] == "application/pdf"
    testo = estrai_testo(generazione.content)
    righe = [testo.index(codice) for codice in ("367.501-A", "367.501-B", "367.501-C")]
    assert righe == sorted(righe), "le righe escono nell'ordine dei dati"
    assert "Totale 10" in testo
    assert "Roma" in testo and "Napoli" in testo
    # FR-015: nessuna rappresentazione grezza della lista.
    assert "TEMA_A" not in testo and "{'" not in testo and "[{" not in testo


@pytest.mark.integration
def test_la_validazione_degli_elementi_dice_dove_sta_l_errore(builder_client, con_articolazioni, slot_pulito):
    _, pubblicata = _multiplo_pubblicato(builder_client)
    articolazioni = [dict(a, campi=dict(a["campi"])) for a in DATI_367_501["articolazioni"]]
    del articolazioni[0]["campi"]["numero_posti"]
    articolazioni[1]["campi"]["numero_posti"] = "cinque"
    articolazioni[1]["campi"]["extra"] = 1
    articolazioni[2]["codice"] = "TEMA_A"
    articolazioni.append({"descrizione": "senza codice", "campi": {}, "sede": "x"})
    dati = {**DATI_367_501, "articolazioni": articolazioni}

    risposta = builder_client.post("/api/v1/documenti/valida", json=_richiesta(pubblicata["public_id"], dati))

    assert risposta.status_code == 200, risposta.text
    errori = {(e["campo"], e["codice"]) for e in risposta.json()["errori"]}
    assert ("articolazioni[TEMA_A].campi.numero_posti", "CAMPO_OBBLIGATORIO") in errori
    assert ("articolazioni[TEMA_B].campi.numero_posti", "TIPO_NON_VALIDO") in errori
    assert ("articolazioni[TEMA_B].campi.extra", "CAMPO_NON_AMMESSO") in errori
    assert ("articolazioni", "CODICE_ELEMENTO_DUPLICATO") in errori
    assert ("articolazioni[3].codice", "CAMPO_OBBLIGATORIO") in errori
    assert ("articolazioni[3].sede", "CAMPO_NON_AMMESSO") in errori
    assert ("articolazioni[3].campi.codice_bando", "CAMPO_OBBLIGATORIO") in errori


@pytest.mark.integration
def test_senza_articolazioni_il_multiplo_rifiuta_e_il_singolo_rifiuta_le_articolazioni(
    builder_client, con_articolazioni, slot_pulito,
):
    _, multiplo = _multiplo_pubblicato(builder_client)
    singolo = _crea(builder_client, multiplo=False).json()
    versione_singolo = _versione(builder_client, singolo["id"], con_articolazioni=False).json()
    pubblicata_singolo = _pubblica_fino_in_fondo(builder_client, singolo["id"], versione_singolo["id"])
    senza = {k: v for k, v in DATI_367_501.items() if k != "articolazioni"}

    al_multiplo = builder_client.post("/api/v1/documenti/valida", json=_richiesta(multiplo["public_id"], senza))
    al_singolo = builder_client.post("/api/v1/documenti/valida", json=_richiesta(pubblicata_singolo["public_id"], DATI_367_501))

    assert {(e["campo"], e["codice"]) for e in al_multiplo.json()["errori"]} == {("articolazioni", "CAMPO_OBBLIGATORIO")}
    assert ("articolazioni", "CAMPO_NON_AMMESSO") in {(e["campo"], e["codice"]) for e in al_singolo.json()["errori"]}
    vuota = builder_client.post("/api/v1/documenti/valida",
                                json=_richiesta(multiplo["public_id"], {**senza, "articolazioni": []}))
    assert ("articolazioni", "CAMPO_OBBLIGATORIO") in {(e["campo"], e["codice"]) for e in vuota.json()["errori"]}


@pytest.mark.integration
def test_la_versione_pubblicata_valida_con_i_sotto_campi_di_allora(builder_client, con_articolazioni, slot_pulito):
    _, pubblicata = _multiplo_pubblicato(builder_client)
    # La foglia cambia dopo la pubblicazione: un sotto-campo obbligatorio in piu'.
    con_articolazioni["campi"][-1] = {**ARTICOLAZIONI, "campi": [
        *ARTICOLAZIONI["campi"],
        {"codice": "data_presa_servizio", "etichetta": "Presa servizio", "tipo": "date", "obbligatorio": True, "ordine": 5},
    ]}

    risposta = builder_client.post("/api/v1/documenti/valida", json=_richiesta(pubblicata["public_id"], DATI_367_501))

    assert risposta.json() == {"valido": True, "errori": []}


@pytest.mark.integration
def test_il_catalogo_distingue_singolo_e_multiplo(builder_client, con_articolazioni, slot_pulito):
    singolo = _crea(builder_client, multiplo=False).json()
    versione_singolo = _versione(builder_client, singolo["id"], con_articolazioni=False).json()
    pubblicata_singolo = _pubblica_fino_in_fondo(builder_client, singolo["id"], versione_singolo["id"])
    _, pubblicata_multiplo = _multiplo_pubblicato(builder_client)
    ricerca = ("/api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&codice_tipologia=TD"
               f"&profilo=RICERCATORE&lingua=IT&livello_professionale={LIVELLO}")

    senza_filtro = builder_client.get(ricerca).json()["modelli"]
    multipli = builder_client.get(ricerca + "&multiplo=true").json()["modelli"]

    assert [m["modello_versione_id"] for m in senza_filtro] == [pubblicata_singolo["public_id"]]
    assert senza_filtro[0]["multiplo"] is False
    assert [m["modello_versione_id"] for m in multipli] == [pubblicata_multiplo["public_id"]]
    assert multipli[0]["multiplo"] is True

    campi = builder_client.get(
        f"/api/v1/catalogo/modelli/{pubblicata_multiplo['public_id']}/campi-richiesti"
    ).json()
    articolazioni = next(c for c in campi["campi"] if c["codice"] == "articolazioni")
    assert [s["codice"] for s in articolazioni["campi"]] == SOTTO
    assert all("campi" not in c for c in campi["campi"] if c["codice"] != "articolazioni")
    schema = campi["schema"]["properties"]["articolazioni"]
    assert schema["minItems"] == 1
    assert schema["items"]["required"] == ["codice", "descrizione", "campi"]
    assert schema["items"]["properties"]["campi"]["required"] == ["codice_bando", "numero_posti", "sede_lavoro"]
    assert "articolazioni" in campi["schema"]["required"]
