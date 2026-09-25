"""Dimensioni generiche del modello (011): il caso `CONTRATTI`, end-to-end.

Copre i task T013, T014, T020, T021, T024, T025, T026, T037, T038 e T039 di
`specs/011-dimensioni-generiche-modello/tasks.md`, cioe' gli Independent Test
degli Scenari 1, 2, 3, 4 e 7 del quickstart.

L'albero con `area_geografica` **non e' una fixture inventata qui**: viene letto
da `infra/local/discovery-mock/discovery.json` (T001), lo stesso file che il mock
nginx serve in locale, e restituito da un server HTTP reale. Senza questo
vincolo si verificherebbe la fixture invece del meccanismo, che e' esattamente
cio' che la spec chiede di evitare.

I test girano su PostgreSQL reale e passano dalle API HTTP: nessuna logica
simulata.
"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.catalog.models import TipoDocumento
from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    _crea_modello,
    _crea_versione,
    _pubblica_fino_in_fondo,
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
    policy_url,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

ALBERO_MOCK = Path(__file__).resolve().parents[3] / "infra" / "local" / "discovery-mock" / "discovery.json"

TIPO = "CONTRATTI"
PERCORSO = ["COLLABORAZIONE", "PRESTAZIONE_OCCASIONALE"]
CAMPI_CONTRATTO = [
    {"codice": "oggetto_contratto", "lingua": "IT"},
    {"codice": "compenso", "lingua": "IT"},
]
# La lettura resta sul builder; la scrittura passa dall'endpoint unico di
# `configurazione`, l'unico che vede l'albero dell'integrazione.
POLICY_READ_URL = f"/api/v1/builder/tipi-documento/{TIPO}/policy-dimensioni"


@pytest.fixture()
def albero_contratti(catalogo_esterno, integrazione_connessa, db_engine):
    """Serve `CONTRATTI` dal mock live, e ripulisce il tipo documento creato.

    `CONTRATTI` non esiste nel database di partenza: lo crea il builder alla
    prima richiesta, associandolo all'integrazione di test
    (`_tipo_per_integrazione`). La cancellazione in coda cade a cascata su
    modelli e versioni.
    """
    albero = json.loads(ALBERO_MOCK.read_text(encoding="utf-8"))
    assert TIPO in albero, f"T001: il mock live deve dichiarare '{TIPO}'"
    foglia = albero[TIPO]["nodi"][0]["figli"][0]
    assert "lingue_possibili" not in foglia and "livelli_possibili" not in foglia, (
        "T001: la foglia CONTRATTI non deve dichiarare lingua ne' livello, "
        "altrimenti non e' il caso portante della spec"
    )
    catalogo_esterno[1]["/discovery"][1][TIPO] = deepcopy(albero[TIPO])
    try:
        yield catalogo_esterno[1]["/discovery"][1][TIPO]
    finally:
        with Session(db_engine) as db:
            db.execute(sa.delete(TipoDocumento).where(TipoDocumento.codice == TIPO))
            db.commit()


def _crea_contratto(
    client: TestClient, integrazione_id, *, dimensioni: dict[str, str] | None = None, **extra,
):
    payload: dict = {
        "codice_tipo_documento": TIPO,
        "integrazione_id": str(integrazione_id),
        "percorso_categorizzazione": PERCORSO,
    }
    if dimensioni is not None:
        payload["dimensioni"] = dimensioni
    payload.update(extra)
    return client.post("/api/v1/builder/modelli", json=payload)


def _dimensioni_su_db(db_engine, modello_id: str) -> dict:
    with Session(db_engine) as db:
        return db.scalar(
            sa.text("SELECT dimensioni FROM modello_documento WHERE id = :id"), {"id": modello_id}
        )


def _pubblica(client: TestClient, modello: dict) -> dict:
    versione = _crea_versione(client, modello["id"], CAMPI_CONTRATTO)
    return _pubblica_fino_in_fondo(client, modello["id"], versione["id"])


# --------------------------------------------------------------------------
# US1 - registrare il valore di una dimensione qualsiasi
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_due_modelli_differiscono_solo_per_una_dimensione_mai_vista(
    builder_client, db_engine, albero_contratti, integrazione_connessa,
):
    """T013: `area_geografica` distingue due modelli come lo faceva la lingua."""
    nord = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"})
    centro = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "CENTRO"})
    assert nord.status_code == 201, nord.text
    assert centro.status_code == 201, centro.text
    nord, centro = nord.json(), centro.json()

    assert nord["codice"] != centro["codice"]
    assert nord["nome"] != centro["nome"]
    # FR-003: il valore grezzo entra nell'identita', senza nomi umani cablati.
    assert "nord" in nord["codice"] and "centro" in centro["codice"]
    assert "NORD" in nord["nome"] and "CENTRO" in centro["nome"]

    for modello, valore in ((nord, "NORD"), (centro, "CENTRO")):
        letto = builder_client.get(f"/api/v1/builder/modelli/{modello['id']}")
        assert letto.status_code == 200, letto.text
        assert letto.json()["dimensioni"] == {"area_geografica": valore}
        assert _dimensioni_su_db(db_engine, modello["id"]) == {"area_geografica": valore}


@pytest.mark.integration
def test_una_dimensione_sparita_dall_albero_non_rende_illeggibili_i_modelli(
    builder_client, db_engine, albero_contratti, integrazione_connessa,
):
    """T014, Scenario 7: il disallineamento e' segnalato senza cancellare il passato."""
    modello = _crea_contratto(
        builder_client, integrazione_connessa, dimensioni={"area_geografica": "SUD"},
    ).json()

    del albero_contratti["nodi"][0]["figli"][0]["area_geografica"]

    letto = builder_client.get(f"/api/v1/builder/modelli/{modello['id']}")
    assert letto.status_code == 200, letto.text
    assert letto.json()["dimensioni"] == {"area_geografica": "SUD"}
    assert letto.json()["dimensioni_non_disponibili"] == ["area_geografica"]

    elenco = builder_client.get("/api/v1/builder/modelli", params={"codice_contesto": "geban"})
    assert elenco.status_code == 200, elenco.text
    assert modello["id"] in {item["id"] for item in elenco.json()}


# --------------------------------------------------------------------------
# US2 - la policy vale per qualunque dimensione
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_la_policy_governa_una_dimensione_che_nessuno_aveva_previsto(
    builder_client, albero_contratti, integrazione_connessa,
):
    """T020, Scenario 2: obbligatoria rifiuta, generica accetta.

    La prima creazione serve anche a far nascere il tipo documento: prima che
    esista non c'e' un `tipo_documento_id` su cui registrare una policy.
    """
    primo = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"})
    assert primo.status_code == 201, primo.text

    obbligatoria = builder_client.put(
        policy_url(integrazione_connessa, TIPO), json={"nome_dimensione": "area_geografica", "consente_valore_generico": False},
    )
    assert obbligatoria.status_code in {200, 201}, obbligatoria.text

    senza_valore = _crea_contratto(builder_client, integrazione_connessa, dimensioni={})
    assert senza_valore.status_code == 400, senza_valore.text
    assert senza_valore.json()["codice"] == "DIMENSIONE_RICHIEDE_VALORE"

    generica = builder_client.put(
        policy_url(integrazione_connessa, TIPO), json={"nome_dimensione": "area_geografica", "consente_valore_generico": True},
    )
    assert generica.status_code == 200, generica.text

    ora_ammessa = _crea_contratto(builder_client, integrazione_connessa, dimensioni={})
    assert ora_ammessa.status_code == 201, ora_ammessa.text
    assert ora_ammessa.json()["dimensioni"] == {}


@pytest.mark.integration
def test_una_chiave_non_dichiarata_dalla_foglia_e_rifiutata(
    builder_client, albero_contratti, integrazione_connessa,
):
    """T021, FR-006: nessun valore inventato, nemmeno la lingua."""
    inventata = _crea_contratto(
        builder_client, integrazione_connessa,
        dimensioni={"area_geografica": "NORD", "colore": "ROSSO"},
    )
    assert inventata.status_code == 400, inventata.text
    assert inventata.json()["codice"] == "DIMENSIONE_NON_DICHIARATA"

    # La lingua non gode di nessun privilegio: su una foglia che non la dichiara
    # e' una chiave sconosciuta come le altre.
    con_lingua = _crea_contratto(
        builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"}, lingua="IT",
    )
    assert con_lingua.status_code == 400, con_lingua.text
    assert con_lingua.json()["codice"] == "DIMENSIONE_NON_DICHIARATA"


# --------------------------------------------------------------------------
# US3 - distinguere e pubblicare senza collisioni
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_due_pubblicazioni_che_differiscono_per_una_dimensione_coesistono(
    builder_client, db_engine, albero_contratti, integrazione_connessa,
):
    """T024, Scenario 3: slot diversi, nessuna archiviazione reciproca."""
    nord = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"}).json()
    centro = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "CENTRO"}).json()

    versione_nord = _pubblica(builder_client, nord)
    versione_centro = _pubblica(builder_client, centro)

    assert versione_nord["stato"] == "PUBBLICATO"
    assert versione_centro["stato"] == "PUBBLICATO"
    with Session(db_engine) as db:
        stati = dict(db.execute(sa.text(
            "SELECT id::text, stato FROM modello_versione WHERE id IN (:a, :b)"
        ), {"a": versione_nord["id"], "b": versione_centro["id"]}).all())
    assert stati == {versione_nord["id"]: "PUBBLICATO", versione_centro["id"]: "PUBBLICATO"}


@pytest.mark.integration
def test_una_seconda_versione_dello_stesso_modello_archivia_ancora_la_precedente(
    builder_client, db_engine, albero_contratti, integrazione_connessa,
):
    """T025: la controprova che l'unicita' non e' stata disattivata.

    Senza questo test, T024 passerebbe anche con il controllo di slot rotto.
    """
    modello = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "SUD"}).json()
    prima = _pubblica(builder_client, modello)
    seconda = _pubblica(builder_client, modello)

    with Session(db_engine) as db:
        stati = dict(db.execute(sa.text(
            "SELECT id::text, stato FROM modello_versione WHERE id IN (:a, :b)"
        ), {"a": prima["id"], "b": seconda["id"]}).all())
    assert stati[prima["id"]] == "ARCHIVIATO"
    assert stati[seconda["id"]] == "PUBBLICATO"


@pytest.mark.integration
def test_due_creazioni_simultanee_sulla_stessa_combinazione_non_pubblicano_due_volte(
    builder_client, db_engine, albero_contratti, integrazione_connessa,
):
    """T026, edge case della spec: due creazioni gemelle.

    **La protezione si e' spostata a monte** con 002 FR-019 (2026-09-24). Prima
    entrambe le creazioni riuscivano e il catalogo restava coerente solo a
    valle: il gemello che pubblicava per secondo archiviava la versione del
    primo. Ora la seconda creazione sulla stessa combinazione e' rifiutata,
    perche' un secondo modello sullo stesso slot deve dichiarare in cosa
    differisce. La proprieta' della spec - il catalogo non espone mai due
    versioni correnti sulla stessa combinazione - vale ancora, e per una via
    piu' netta: il modello duplicato non nasce proprio.

    `uq_modello_documento_tipo_codice` continua a non intercettarle, per la
    ragione di sempre: il `codice` termina con l'esadecimale dell'id, quindi due
    creazioni identiche producono comunque codici diversi. Quel che le blocca e'
    il lock sul tipo documento piu' l'indice parziale sullo slot.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        risposte = [
            f.result() for f in [
                pool.submit(_crea_contratto, builder_client, integrazione_connessa,
                            dimensioni={"area_geografica": "NORD"})
                for _ in range(2)
            ]
        ]
    assert sorted(r.status_code for r in risposte) == [201, 409], [r.text for r in risposte]
    rifiutata = next(r for r in risposte if r.status_code == 409)
    assert rifiutata.json()["codice"] == "MODELLO_VARIANTE_RICHIESTA"
    # Nessun 500: la corsa e' gestita, non subita.
    creato = next(r for r in risposte if r.status_code == 201).json()

    versione = _pubblica(builder_client, creato)
    with Session(db_engine) as db:
        stato = db.scalar(sa.text(
            "SELECT stato FROM modello_versione WHERE id = :id"
        ), {"id": versione["id"]})
    assert stato == "PUBBLICATO"


# --------------------------------------------------------------------------
# US5 - un tipo documento con dimensioni proprie, visto da fuori
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_un_modello_contratti_non_ha_una_lingua_implicita(
    builder_client, db_engine, albero_contratti, integrazione_connessa,
):
    """T037, Scenario 4: sul database, non solo nella risposta API."""
    modello = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"}).json()

    assert _dimensioni_su_db(db_engine, modello["id"]) == {"area_geografica": "NORD"}
    assert modello["lingua"] is None


@pytest.mark.integration
def test_il_catalogo_espone_un_tipo_senza_lingua(
    builder_client, albero_contratti, integrazione_connessa,
):
    """T038, FR-008: `lingua: null` e le dimensioni proprie del tipo."""
    modello = _crea_contratto(builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"}).json()
    _pubblica(builder_client, modello)

    risposta = builder_client.get(f"/api/v1/catalogo/modelli?tipo_documento={TIPO}")
    assert risposta.status_code == 200, risposta.text
    modelli = risposta.json()["modelli"]
    assert len(modelli) == 1, modelli
    assert modelli[0]["lingua"] is None
    assert modelli[0]["dimensioni"] == {"area_geografica": "NORD"}


@pytest.mark.integration
def test_il_catalogo_filtra_per_una_dimensione_arbitraria(
    builder_client, albero_contratti, integrazione_connessa,
):
    """T030: `dimensione[nome]` attraversa API, servizio e query JSONB."""
    nord = _crea_contratto(
        builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"},
    ).json()
    centro = _crea_contratto(
        builder_client, integrazione_connessa, dimensioni={"area_geografica": "CENTRO"},
    ).json()
    _pubblica(builder_client, nord)
    _pubblica(builder_client, centro)

    risposta = builder_client.get(
        f"/api/v1/catalogo/modelli?tipo_documento={TIPO}&dimensione[area_geografica]=CENTRO",
    )

    assert risposta.status_code == 200, risposta.text
    modelli = risposta.json()["modelli"]
    assert [item["modello_id"] for item in modelli] == [centro["public_id"]]
    assert modelli[0]["dimensioni"] == {"area_geografica": "CENTRO"}


@pytest.mark.integration
def test_edizione_derivata_rifiutata_se_la_dimensione_ammette_generico(
    builder_client, albero_contratti, integrazione_connessa,
):
    """T040: il vincolo di derivazione e' applicato anche a CONTRATTI."""
    modello = _crea_contratto(
        builder_client, integrazione_connessa, dimensioni={"area_geografica": "NORD"},
    ).json()
    policy = builder_client.put(
        policy_url(integrazione_connessa, TIPO),
        json={"nome_dimensione": "area_geografica", "consente_valore_generico": True},
    )
    assert policy.status_code == 200, policy.text

    risposta = builder_client.post(
        f"/api/v1/builder/modelli/{modello['id']}/edizioni-derivate",
        json={"nome_dimensione": "area_geografica", "valore": "CENTRO"},
    )

    assert risposta.status_code == 400, risposta.text
    assert "ammette un valore generico" in risposta.json()["messaggio"]


@pytest.mark.integration
def test_fallback_lingua_e_governato_dalla_policy(
    builder_client, db_engine, catalogo_esterno, integrazione_connessa,
):
    """T035: il nome `lingua` non abilita il fallback; lo abilita la policy."""
    codice_tipo = "BANDO_FALLBACK_" + uuid.uuid4().hex[:8].upper()
    catalogo_esterno[1]["/discovery"][1][codice_tipo] = deepcopy(
        catalogo_esterno[1]["/discovery"][1]["BANDO_CONCORSO"],
    )
    base = {
        "codice_tipo_documento": codice_tipo,
        "integrazione_id": str(integrazione_connessa),
        "percorso_categorizzazione": ["TD", "RICERCATORE"],
    }
    try:
        italiana = builder_client.post(
            "/api/v1/builder/modelli", json={**base, "dimensioni": {"lingua": "IT"}},
        )
        assert italiana.status_code == 201, italiana.text
        modello_it = italiana.json()
        _pubblica_fino_in_fondo(
            builder_client,
            modello_it["id"],
            _crea_versione(builder_client, modello_it["id"])["id"],
        )

        senza_fallback = builder_client.get(
            f"/api/v1/catalogo/modelli?tipo_documento={codice_tipo}&lingua=EN",
        )
        assert senza_fallback.status_code == 200, senza_fallback.text
        assert senza_fallback.json()["modelli"] == []
        assert senza_fallback.json()["fallback_applicato"] is False

        policy = builder_client.put(
            policy_url(integrazione_connessa, codice_tipo),
            json={"nome_dimensione": "lingua", "consente_valore_generico": True},
        )
        assert policy.status_code == 200, policy.text
        generico = builder_client.post(
            "/api/v1/builder/modelli", json={**base, "dimensioni": {}},
        )
        assert generico.status_code == 201, generico.text
        modello_generico = generico.json()
        _pubblica_fino_in_fondo(
            builder_client,
            modello_generico["id"],
            _crea_versione(builder_client, modello_generico["id"])["id"],
        )

        con_fallback = builder_client.get(
            f"/api/v1/catalogo/modelli?tipo_documento={codice_tipo}&lingua=EN",
        )
        assert con_fallback.status_code == 200, con_fallback.text
        assert con_fallback.json()["fallback_applicato"] is True
        assert con_fallback.json()["dimensioni_con_fallback"] == ["lingua"]
        assert [item["modello_id"] for item in con_fallback.json()["modelli"]] == [
            modello_generico["public_id"],
        ]
    finally:
        catalogo_esterno[1]["/discovery"][1].pop(codice_tipo, None)
        with Session(db_engine) as db:
            db.execute(sa.delete(TipoDocumento).where(TipoDocumento.codice == codice_tipo))
            db.commit()


@pytest.mark.integration
def test_il_bando_continua_a_esporre_la_lingua_valorizzata(
    builder_client, albero_contratti, integrazione_connessa,
):
    """T039, controprova obbligatoria: GEBAN non e' stato toccato.

    E' la proprieta' su cui poggia DEC-011-CONTRATTO-GEBAN-ADDITIVO: `lingua` e'
    nullable nello schema ma **mai nulla** nelle risposte che GEBAN riceve oggi,
    perche' `search_modelli` impone `tipo_documento` e la policy del bando
    rende la lingua obbligatoria.
    """
    modello = _crea_modello(builder_client, codice="controprova-geban", lingua="IT")
    _pubblica_fino_in_fondo(builder_client, modello["id"], _crea_versione(builder_client, modello["id"])["id"])

    risposta = builder_client.get("/api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO")
    assert risposta.status_code == 200, risposta.text
    modelli = risposta.json()["modelli"]
    assert modelli, "la controprova non prova nulla su un catalogo vuoto"
    assert all(item["lingua"] for item in modelli), [item["lingua"] for item in modelli]
