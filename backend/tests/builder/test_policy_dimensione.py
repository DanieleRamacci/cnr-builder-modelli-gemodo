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
    policy_url,
)
from tests.discovery.conftest import discovery_server  # noqa: F401  (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401  (fixture)

# La lettura resta disponibile dal builder (serve al form, non richiede admin);
# la scrittura passa dall'endpoint unico di `configurazione`, che e' dove arriva
# l'albero e si puo' verificare che la dimensione sia dichiarata.
POLICY_READ_URL = "/api/v1/builder/tipi-documento/BANDO_CONCORSO/policy-dimensioni"

# Le policy sono persistite e il database di test e' condiviso: senza ripristino
# un test lascerebbe `livello` obbligatorio e farebbe fallire gli altri.
DEFAULT = {"lingua": False, "livello_professionale": True}


@pytest.fixture(autouse=True)
def ripristina_policy(builder_client, db_engine, integrazione_connessa):
    yield
    with Session(db_engine) as db:
        db.execute(
            sa.text("DELETE FROM policy_dimensione WHERE tipo_documento_id = :id"),
            {"id": _tipo_id(db_engine)},
        )
        db.commit()
    for nome, generico in DEFAULT.items():
        builder_client.put(
            policy_url(integrazione_connessa),
            json={"nome_dimensione": nome, "consente_valore_generico": generico,
                  "conferma_impatto": True},
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
def test_policy_is_unique_per_type_and_dimension_name(builder_client, db_engine, catalogo_esterno, integrazione_connessa):
    """Una riga sola per nome, anche se il nome ricompare su piu' foglie."""
    client = builder_client
    prima = client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "livello_professionale", "consente_valore_generico": False, "conferma_impatto": True})
    assert prima.status_code in {200, 201}, prima.text

    seconda = client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "livello_professionale", "consente_valore_generico": True})
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
    builder_client, catalogo_esterno,
    integrazione_connessa,
):
    """La lingua resta obbligatoria, ma ora perche' lo dice la policy.

    Dichiararla generica viene rifiutato in modo esplicito: `modello_documento.lingua`
    e' NOT NULL con vincolo IT/EN ed e' esposta non nullabile nel catalogo verso
    GEBAN, quindi accettare la policy e poi salvare 'IT' sarebbe una bugia
    silenziosa. Serve prima una modifica di schema e contratto in `001`.
    """
    client = builder_client
    client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "lingua", "consente_valore_generico": False, "conferma_impatto": True})
    rifiutato = _crea(client, lingua=None)
    assert rifiutato.status_code == 400, rifiutato.text
    assert rifiutato.json()["codice"] == "DIMENSIONE_RICHIEDE_VALORE"

    # 011 DEC-011-POLICY-LINGUA-ALL-ADMIN: dichiarare la lingua generica non e'
    # piu' rifiutato. Il divieto esisteva perche' la colonna era NOT NULL e il
    # contratto la esponeva obbligatoria, quindi accettare e poi salvare 'IT'
    # sarebbe stata una bugia silenziosa; ora la colonna non c'e' e il contratto
    # ammette il null. La protezione e' passata all'avviso in schermata.
    generico = client.put(
        policy_url(integrazione_connessa), json={"nome_dimensione": "lingua", "consente_valore_generico": True}
    )
    assert generico.status_code == 200, generico.text
    assert _crea(client, lingua=None).status_code == 201


@pytest.mark.integration
def test_policy_can_make_the_level_mandatory_too(builder_client, catalogo_esterno, integrazione_connessa):
    """La stessa regola vale per il livello: oggi generico, per policy esplicito."""
    client = builder_client
    client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "livello_professionale", "consente_valore_generico": True})
    assert _crea(client, livello=None).status_code == 201

    client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "livello_professionale", "consente_valore_generico": False, "conferma_impatto": True})
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

    risposta = client.get(POLICY_READ_URL)
    assert risposta.status_code == 200, risposta.text
    corpo = risposta.json()
    non_configurate = {d["nome_dimensione"] for d in corpo["dimensioni_non_configurate"]}
    assert {"lingua", "livello_professionale"} <= non_configurate, corpo


@pytest.mark.integration
def test_policies_are_readable_by_the_manager_and_listed_per_type(builder_client, catalogo_esterno, integrazione_connessa):
    client = builder_client
    client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "lingua", "consente_valore_generico": False, "conferma_impatto": True})
    client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "livello_professionale", "consente_valore_generico": True})
    corpo = client.get(POLICY_READ_URL).json()
    per_nome = {p["nome_dimensione"]: p["consente_valore_generico"] for p in corpo["policy"]}
    assert per_nome["lingua"] is False
    assert per_nome["livello_professionale"] is True


def _pubblica_generico(client, lingua=None):
    """Un modello pubblicato che non valorizza la lingua, come quando il generico era ammesso."""
    creato = _crea(client, lingua=lingua)
    assert creato.status_code == 201, creato.text
    modello = creato.json()
    versione = client.post(
        f"/api/v1/builder/modelli/{modello['id']}/versioni",
        json={"campi": [{"codice": "codice_bando", "lingua": "IT"},
                        {"codice": "titolo_it", "lingua": "IT"}]},
    )
    assert versione.status_code == 201, versione.text
    vid = versione.json()["id"]
    for azione in ("invia-revisione", "approva", "pubblica"):
        r = client.post(f"/api/v1/builder/modelli/{modello['id']}/versioni/{vid}/{azione}")
        assert r.status_code == 200, r.text
    return modello, r.json()["public_id"]


@pytest.mark.integration
def test_chiudere_il_generico_conta_i_modelli_senza_valore_non_quelli_con(
    builder_client, catalogo_esterno, integrazione_connessa,
):
    """Il conteggio guardava l'insieme opposto a quello che il cambio tocca.

    Con un generico pubblicato, chiudere la policy annunciava
    `modelli_pubblicati_che_la_valorizzano: 0` - vero alla lettera e inutile:
    i modelli che restano senza un valore ammesso sono quelli che la dimensione
    **non** ce l'hanno. Il database di test e' condiviso, quindi si misura la
    variazione prodotta da questo modello, non un totale assoluto.
    """
    client = builder_client
    client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "lingua", "consente_valore_generico": True})

    def impatto():
        lettura = client.get(POLICY_READ_URL).json()
        voce = next(p for p in lettura["policy"] if p["nome_dimensione"] == "lingua")
        return voce["modelli_pubblicati_che_la_valorizzano"], voce["modelli_pubblicati_senza_valore"]

    con_prima, senza_prima = impatto()
    modello, _ = _pubblica_generico(client)
    con_dopo, senza_dopo = impatto()

    assert con_dopo == con_prima, "il modello generico non valorizza la lingua"
    assert senza_dopo == senza_prima + 1, "ed e' esattamente quello che il cambio lascia senza valore"

    bloccato = client.put(
        policy_url(integrazione_connessa), json={"nome_dimensione": "lingua", "consente_valore_generico": False},
    )
    assert bloccato.status_code == 409, bloccato.text
    assert bloccato.json()["codice"] == "CONFERMA_IMPATTO_RICHIESTA"
    assert modello["id"] in [d["modello_id"] for d in bloccato.json()["dettagli"]]

    confermato = client.put(
        policy_url(integrazione_connessa),
        json={"nome_dimensione": "lingua", "consente_valore_generico": False,
              "conferma_impatto": True},
    )
    assert confermato.status_code == 200, "la scelta resta dell'admin, mai un vicolo cieco"


@pytest.mark.integration
def test_un_generico_gia_pubblicato_resta_reperibile_dopo_il_giro_di_vite(
    builder_client, catalogo_esterno, integrazione_connessa,
):
    """011 FR-010 rivisto: la policy governa la creazione, non il gia' pubblicato.

    Prima il modello spariva dal catalogo per *ogni* lingua: lo stesso danno
    che FR-009 vieta quando la causa e' l'albero che cambia, con la sola
    differenza che qui la causa e' una configurazione nostra. Si confronta la
    reperibilita' prima e dopo, perche' su un catalogo condiviso il generico
    puo' gia' essere coperto da un modello piu' specifico (precedenza voluta).
    """
    client = builder_client
    client.put(policy_url(integrazione_connessa), json={"nome_dimensione": "lingua", "consente_valore_generico": True})
    _, public_id = _pubblica_generico(client)

    def trovato(lingua):
        r = client.get("/api/v1/catalogo/modelli",
                       params={"tipo_documento": "BANDO_CONCORSO", "lingua": lingua})
        assert r.status_code == 200, r.text
        return public_id in [m.get("modello_versione_id") for m in r.json().get("modelli", [])]

    prima = {lingua: trovato(lingua) for lingua in ("IT", "EN")}
    assert any(prima.values()), "il generico deve valere per almeno una lingua prima del cambio"

    client.put(policy_url(integrazione_connessa),
               json={"nome_dimensione": "lingua", "consente_valore_generico": False,
                     "conferma_impatto": True})

    dopo = {lingua: trovato(lingua) for lingua in ("IT", "EN")}
    assert dopo == prima, "chiudere la policy non puo' invalidare cio' che e' gia' pubblicato"
    # Ma da adesso il generico non si crea piu'.
    assert _crea(client, lingua=None).status_code == 400


@pytest.mark.integration
def test_la_policy_si_scrive_da_un_endpoint_solo(builder_client, catalogo_esterno, integrazione_connessa):
    """Sotto `/builder` esisteva un secondo PUT per lo stesso dato.

    Non verificava che la dimensione fosse dichiarata nell'albero e accettava
    ruoli piu' larghi: due strade per la stessa scrittura, con controlli
    diversi. La scrittura vive dove arriva l'albero dell'integrazione; qui
    resta la sola lettura, che al builder serve per costruire il form.
    """
    client = builder_client

    scomparso = client.put(
        POLICY_READ_URL, json={"nome_dimensione": "lingua", "consente_valore_generico": True},
    )
    assert scomparso.status_code == 405, scomparso.text

    assert client.get(POLICY_READ_URL).status_code == 200, "la lettura resta"

    # E l'endpoint unico rifiuta una dimensione che l'albero non dichiara,
    # controllo che quello rimosso non faceva.
    inventata = client.put(
        policy_url(integrazione_connessa),
        json={"nome_dimensione": "dimensione_mai_vista", "consente_valore_generico": True},
    )
    assert inventata.status_code == 409, inventata.text
    assert inventata.json()["codice"] == "DIMENSIONE_NON_DISPONIBILE"
