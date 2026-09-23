"""Policy per dimensione della categorizzazione (002, DEC-002-POLICY, T065-T067).

Oggi il comportamento e' scritto a mano: la lingua esige sempre una scelta
esplicita, il livello ammette un generico che vale per tutti i valori. La policy
rende la stessa distinzione configurabile per nome di dimensione, cosi' che una
dimensione nuova aggiunta da un'integrazione non richieda una modifica al codice.

I test girano su PostgreSQL reale e passano dalle API HTTP: nessuna logica
simulata.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from tests.builder.test_builder_flow_api import (  # noqa: F401  (fixtures)
    builder_client,
    catalogo_esterno,
    db_engine,
    integrazione_connessa,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

POLICY_URL = "/api/v1/builder/tipi-documento/BANDO_CONCORSO/policy-dimensioni"

# Le policy sono persistite e il database di test e' condiviso: senza ripristino
# un test lascerebbe `livello` obbligatorio e farebbe fallire gli altri.
DEFAULT = {"lingua": False, "livello_professionale": True}


@pytest.fixture(autouse=True)
def ripristina_policy(builder_client, db_engine):
    yield
    with Session(db_engine) as db:
        db.execute(
            sa.text("DELETE FROM policy_dimensione WHERE tipo_documento_id = :id"),
            {"id": _tipo_id(db_engine)},
        )
        db.commit()
    for nome, generico in DEFAULT.items():
        builder_client.put(
            POLICY_URL, json={"nome_dimensione": nome, "consente_valore_generico": generico}
        )


def _tipo_id(db_engine) -> uuid.UUID:
    with Session(db_engine) as db:
        return db.scalar(
            sa.text("SELECT id FROM tipo_documento WHERE codice = 'BANDO_CONCORSO' LIMIT 1")
        )


def _crea(client, *, lingua="IT", livello=...):
    payload = {
        "codice_tipo_documento": "BANDO_CONCORSO",
        "codice_categoria": "RICERCATORE",
        "codice_tipologia": "TD",
    }
    payload["lingua"] = lingua
    if livello is not ...:
        payload["livello_professionale"] = livello
    return client.post("/api/v1/builder/modelli", json=payload)


@pytest.mark.integration
def test_policy_is_unique_per_type_and_dimension_name(builder_client, db_engine, catalogo_esterno):
    """Una riga sola per nome, anche se il nome ricompare su piu' foglie."""
    client = builder_client
    prima = client.put(POLICY_URL, json={"nome_dimensione": "livello_professionale", "consente_valore_generico": False})
    assert prima.status_code in {200, 201}, prima.text

    seconda = client.put(POLICY_URL, json={"nome_dimensione": "livello_professionale", "consente_valore_generico": True})
    assert seconda.status_code == 200, seconda.text
    assert seconda.json()["consente_valore_generico"] is True

    with Session(db_engine) as db:
        righe = db.scalar(
            sa.text(
                "SELECT count(*) FROM policy_dimensione "
                "WHERE tipo_documento_id = :id AND nome_dimensione = 'livello_professionale'"
            ),
            {"id": _tipo_id(db_engine)},
        )
    assert righe == 1, "la policy si aggiorna, non si duplica"


@pytest.mark.integration
def test_policy_drives_the_language_rule_and_refuses_an_unsupported_generic(
    builder_client, catalogo_esterno
):
    """La lingua resta obbligatoria, ma ora perche' lo dice la policy.

    Dichiararla generica viene rifiutato in modo esplicito: `modello_documento.lingua`
    e' NOT NULL con vincolo IT/EN ed e' esposta non nullabile nel catalogo verso
    GEBAN, quindi accettare la policy e poi salvare 'IT' sarebbe una bugia
    silenziosa. Serve prima una modifica di schema e contratto in `001`.
    """
    client = builder_client
    client.put(POLICY_URL, json={"nome_dimensione": "lingua", "consente_valore_generico": False})
    rifiutato = _crea(client, lingua=None)
    assert rifiutato.status_code == 400, rifiutato.text
    assert rifiutato.json()["codice"] == "DIMENSIONE_RICHIEDE_VALORE"

    # 011 DEC-011-POLICY-LINGUA-ALL-ADMIN: dichiarare la lingua generica non e'
    # piu' rifiutato. Il divieto esisteva perche' la colonna era NOT NULL e il
    # contratto la esponeva obbligatoria, quindi accettare e poi salvare 'IT'
    # sarebbe stata una bugia silenziosa; ora la colonna non c'e' e il contratto
    # ammette il null. La protezione e' passata all'avviso in schermata.
    generico = client.put(
        POLICY_URL, json={"nome_dimensione": "lingua", "consente_valore_generico": True}
    )
    assert generico.status_code == 200, generico.text
    assert _crea(client, lingua=None).status_code == 201


@pytest.mark.integration
def test_policy_can_make_the_level_mandatory_too(builder_client, catalogo_esterno):
    """La stessa regola vale per il livello: oggi generico, per policy esplicito."""
    client = builder_client
    client.put(POLICY_URL, json={"nome_dimensione": "livello_professionale", "consente_valore_generico": True})
    assert _crea(client, livello=None).status_code == 201

    client.put(POLICY_URL, json={"nome_dimensione": "livello_professionale", "consente_valore_generico": False})
    rifiutato = _crea(client, livello=None)
    assert rifiutato.status_code == 400, rifiutato.text
    assert rifiutato.json()["codice"] == "DIMENSIONE_RICHIEDE_VALORE"
    assert _crea(client, livello="VI").status_code == 201


@pytest.mark.integration
def test_an_unconfigured_dimension_is_signalled_not_silently_ignored(
    builder_client, db_engine, catalogo_esterno
):
    """`NodoDiscovery` ha `extra="allow"`: senza segnalazione la dimensione sparirebbe."""
    client = builder_client
    with Session(db_engine) as db:
        db.execute(
            sa.text("DELETE FROM policy_dimensione WHERE tipo_documento_id = :id"),
            {"id": _tipo_id(db_engine)},
        )
        db.commit()

    risposta = client.get(POLICY_URL)
    assert risposta.status_code == 200, risposta.text
    corpo = risposta.json()
    non_configurate = {d["nome_dimensione"] for d in corpo["dimensioni_non_configurate"]}
    assert {"lingua", "livello_professionale"} <= non_configurate, corpo


@pytest.mark.integration
def test_policies_are_readable_by_the_manager_and_listed_per_type(builder_client, catalogo_esterno):
    client = builder_client
    client.put(POLICY_URL, json={"nome_dimensione": "lingua", "consente_valore_generico": False})
    client.put(POLICY_URL, json={"nome_dimensione": "livello_professionale", "consente_valore_generico": True})
    corpo = client.get(POLICY_URL).json()
    per_nome = {p["nome_dimensione"]: p["consente_valore_generico"] for p in corpo["policy"]}
    assert per_nome["lingua"] is False
    assert per_nome["livello_professionale"] is True
