"""Profilo di accesso delle integrazioni, nel database: 001 T088-T092.

Il caso da cui nasce: un contesto registrato dall'interfaccia (`test`) non
dava permessi a nessuno, perche' chi-puo'-fare-cosa stava in un file che
mappava solo `#geban`, e cambiarlo voleva un nuovo deploy.

Qui la fonte e' il database e i test lo usano davvero: la variabile che
indica il file di prova (tests/conftest.py) viene tolta. Token firmati veri,
PostgreSQL reale, API via HTTP.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.common.security import (
    ROLE_GEMODO_MODELLI_GESTORE,
    decode_principal_from_token,
    permessi_nel_contesto,
)
from app.configurazione.models import AuditEventoIntegrazione
from app.core.settings import get_settings
from app.db.session import get_db
from app.main import app
from app.quality.integration_profile import load_sistemi_richiedenti, permessi_da_ruoli_esterni
from tests.configurazione.test_integrazioni_admin import admin_client, crea  # noqa: F401 (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401 (fixture)
from tests.support.security import JwtTestKeys, signed_token

PROFILI_DI_PROVA = Path(__file__).resolve().parents[3] / "infra/local/integration-profiles.local.yaml"

# La mappatura GEBAN che la migrazione 0028 copia dal file di prova.
GEBAN = {
    "ruoli": [
        {"ruolo": "ROLE_COORDINATOR", "permessi": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"]},
        {"ruolo": "ROLE_GESTORE", "permessi": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"]},
        {"ruolo": "ROLE_MANAGER", "permessi": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER", "GEMODO_MODELLI_GESTORE"]},
        {"ruolo": "ROLE_USER", "permessi": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"]},
    ],
    "client": ["geri-angular-public"],
}


@pytest.fixture
def dal_database(monkeypatch):
    """La fonte di un ambiente: il database, nessun file."""
    monkeypatch.delenv("GEMODO_INTEGRATION_PROFILES_PATH", raising=False)


def _url(integrazione_id: str) -> str:
    return f"/api/v1/configurazione/integrazioni/{integrazione_id}/accessi"


def _contesto() -> str:
    return "ctx" + uuid.uuid4().hex[:10]


def _registra(client, contesto: str, accessi: dict | None = None) -> dict:
    risposta = client.post("/api/v1/configurazione/integrazioni", json={
        "codice": "SW_" + uuid.uuid4().hex[:12], "nome": "Prova accessi", "codice_contesto": contesto,
    })
    assert risposta.status_code == 201, risposta.text
    integrazione = risposta.json()
    if accessi is not None:
        impostati = client.put(_url(integrazione["id"]), json=accessi)
        assert impostati.status_code == 200, impostati.text
    return integrazione


def _principal(engine, keys: JwtTestKeys, *, client_id: str, contesti: dict[str, list[str]]):
    token = signed_token(keys, audience=None, client_id=client_id, roles=None, contexts=contesti)
    with Session(engine) as db:
        return decode_principal_from_token(token, settings=get_settings(), signing_key=keys.public_pem, db=db)


@pytest.mark.integration
def test_un_integrazione_nuova_nasce_senza_ruoli(admin_client, dal_database):
    client, _ = admin_client
    integrazione = _registra(client, _contesto())

    accessi = client.get(_url(integrazione["id"])).json()

    assert accessi["ruoli"] == [] and accessi["client"] == []
    assert accessi["codice_contesto"] == integrazione["codice_contesto"]
    assert {p["codice"] for p in accessi["permessi_disponibili"]} == {
        "DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE", "GEMODO_MODELLI_GESTORE",
    }
    assert all(p["descrizione"] for p in accessi["permessi_disponibili"])


@pytest.mark.integration
def test_un_contesto_registrato_apre_il_builder_senza_deploy(admin_client, dal_database):
    """Il caso `test`: ROLE_MANAGER mappato da interfaccia, e il token ACE basta."""
    client, engine = admin_client
    contesto = _contesto()
    _registra(client, contesto, {
        "ruoli": [{"ruolo": "ROLE_MANAGER", "permessi": ["GEMODO_MODELLI_GESTORE", "DOCUMENTI_VIEWER"]}],
        "client": [],
    })
    keys = JwtTestKeys()

    principal = _principal(engine, keys, client_id="gemodo-frontend",
                           contesti={contesto: [f"ROLE_MANAGER#{contesto}"]})

    assert permessi_nel_contesto(principal, contesto) == {"GEMODO_MODELLI_GESTORE", "DOCUMENTI_VIEWER"}
    assert ROLE_GEMODO_MODELLI_GESTORE in principal.ruoli


@pytest.mark.integration
def test_un_contesto_non_registrato_non_apre_nulla(admin_client, dal_database):
    client, engine = admin_client
    registrato = _contesto()
    _registra(client, registrato, {"ruoli": [{"ruolo": "ROLE_MANAGER", "permessi": ["DOCUMENTI_VIEWER"]}],
                                   "client": []})
    estraneo = _contesto()

    principal = _principal(engine, JwtTestKeys(), client_id="gemodo-frontend",
                           contesti={estraneo: [f"ROLE_MANAGER#{estraneo}"]})

    assert permessi_nel_contesto(principal, estraneo) == set()
    assert principal.ruoli == ()


@pytest.mark.integration
def test_i_contesti_non_si_mescolano(admin_client, dal_database):
    """Il ruolo di un contesto non vale in un altro, anche nello stesso token."""
    client, engine = admin_client
    a, b = _contesto(), _contesto()
    _registra(client, a, {"ruoli": [{"ruolo": "ROLE_MANAGER", "permessi": ["GEMODO_MODELLI_GESTORE"]}],
                          "client": []})
    _registra(client, b, {"ruoli": [{"ruolo": "ROLE_USER", "permessi": ["DOCUMENTI_VIEWER"]}],
                          "client": []})

    principal = _principal(engine, JwtTestKeys(), client_id="gemodo-frontend",
                           contesti={a: [f"ROLE_USER#{a}"], b: [f"ROLE_MANAGER#{b}"]})

    assert permessi_nel_contesto(principal, a) == set(), "ROLE_USER non e' mappato in a"
    assert permessi_nel_contesto(principal, b) == set(), "ROLE_MANAGER non e' mappato in b"


@pytest.mark.integration
def test_una_revoca_vale_alla_richiesta_successiva(admin_client, dal_database):
    client, engine = admin_client
    contesto = _contesto()
    integrazione = _registra(client, contesto, {
        "ruoli": [{"ruolo": "ROLE_MANAGER", "permessi": ["GEMODO_MODELLI_GESTORE"]}], "client": [],
    })
    keys = JwtTestKeys()
    contesti = {contesto: [f"ROLE_MANAGER#{contesto}"]}
    assert permessi_nel_contesto(
        _principal(engine, keys, client_id="gemodo-frontend", contesti=contesti), contesto
    ) == {"GEMODO_MODELLI_GESTORE"}

    assert client.put(_url(integrazione["id"]), json={"ruoli": [], "client": []}).status_code == 200

    assert permessi_nel_contesto(
        _principal(engine, keys, client_id="gemodo-frontend", contesti=contesti), contesto
    ) == set()


@pytest.mark.integration
def test_un_client_tecnico_vale_solo_se_registrato(admin_client, dal_database):
    client, engine = admin_client
    contesto = _contesto()
    integrazione = _registra(client, contesto, {
        "ruoli": [{"ruolo": "ROLE_USER", "permessi": ["DOCUMENTI_GENERATORE"]}], "client": [],
    })
    contesti = {contesto: [f"ROLE_USER#{contesto}"]}
    keys = JwtTestKeys()
    with pytest.raises(Exception, match="Client non autorizzato"):
        _principal(engine, keys, client_id="client-tecnico-prova", contesti=contesti)

    client.put(_url(integrazione["id"]), json={
        "ruoli": [{"ruolo": "ROLE_USER", "permessi": ["DOCUMENTI_GENERATORE"]}],
        "client": ["client-tecnico-prova"],
    })

    principal = _principal(engine, keys, client_id="client-tecnico-prova", contesti=contesti)
    assert permessi_nel_contesto(principal, contesto) == {"DOCUMENTI_GENERATORE"}


@pytest.mark.integration
@pytest.mark.parametrize("client_id", ["gemodo-frontend", "geri-angular-public"])
@pytest.mark.parametrize("ruolo", ["ROLE_MANAGER", "ROLE_GESTORE", "ROLE_COORDINATOR", "ROLE_USER", "ROLE_IGNOTO"])
def test_geban_dal_database_ha_gli_stessi_permessi_del_file(admin_client, dal_database, client_id, ruolo):
    """Dopo il passaggio GEBAN deve poter fare esattamente cio' che faceva prima."""
    client, engine = admin_client
    contesto = _contesto()
    _registra(client, contesto, GEBAN)
    sistemi_file = load_sistemi_richiedenti(PROFILI_DI_PROVA)
    interattivo = client_id in get_settings().gemodo_allowed_interactive_clients

    attesi = permessi_da_ruoli_esterni(
        sistemi_file, client_id=client_id, context_roles={"geban": (f"{ruolo}#geban",)},
        interactive_client=interattivo,
    )
    principal = _principal(engine, JwtTestKeys(), client_id=client_id,
                           contesti={contesto: [f"{ruolo}#{contesto}"]})

    assert permessi_nel_contesto(principal, contesto) == attesi


@pytest.mark.integration
def test_la_modifica_e_registrata_con_il_prima_e_il_dopo(admin_client, dal_database):
    client, engine = admin_client
    integrazione = _registra(client, _contesto(), {
        "ruoli": [{"ruolo": "ROLE_USER", "permessi": ["DOCUMENTI_VIEWER"]}], "client": [],
    })
    client.put(_url(integrazione["id"]), json={
        "ruoli": [{"ruolo": "ROLE_MANAGER", "permessi": ["GEMODO_MODELLI_GESTORE"]}], "client": ["geri-angular-public"],
    })

    with Session(engine) as db:
        eventi = list(db.scalars(sa.select(AuditEventoIntegrazione).where(
            AuditEventoIntegrazione.integrazione_id == uuid.UUID(integrazione["id"]),
            AuditEventoIntegrazione.tipo_evento == "ACCESSI_MODIFICATI",
        ).order_by(AuditEventoIntegrazione.created_at)))
    assert len(eventi) == 2
    ultimo = eventi[-1].payload_minimo
    assert ultimo["prima"]["ruoli"] == [{"ruolo": "ROLE_USER", "permessi": ["DOCUMENTI_VIEWER"]}]
    assert ultimo["dopo"]["ruoli"] == [{"ruolo": "ROLE_MANAGER", "permessi": ["GEMODO_MODELLI_GESTORE"]}]
    assert ultimo["dopo"]["client"] == ["geri-angular-public"]


@pytest.mark.integration
@pytest.mark.parametrize("ruoli, client_ids", [
    ([{"ruolo": "ROLE_MANAGER#geban", "permessi": ["DOCUMENTI_VIEWER"]}], []),
    ([{"ruolo": "ROLE_MANAGER", "permessi": ["GEMODO_ADMIN"]}], []),
    ([{"ruolo": "ROLE_MANAGER", "permessi": []}], []),
    ([{"ruolo": "ROLE_X", "permessi": ["DOCUMENTI_VIEWER"]}, {"ruolo": "ROLE_X", "permessi": ["DOCUMENTI_VIEWER"]}], []),
    ([], ["geri-angular-public", "geri-angular-public"]),
])
def test_un_profilo_non_valido_e_rifiutato(admin_client, dal_database, ruoli, client_ids):
    """In particolare non si puo' concedere GEMODO_ADMIN: il catalogo e' chiuso."""
    client, _ = admin_client
    integrazione = _registra(client, _contesto())

    risposta = client.put(_url(integrazione["id"]), json={"ruoli": ruoli, "client": client_ids})

    # Una richiesta fuori schema e' 400 in tutta l'API (`CONTESTO_NON_VALIDO`);
    # 422 resta ai rifiuti di dominio, come la destinazione non approvata.
    assert risposta.status_code == 400, risposta.text
    assert risposta.json()["codice"] == "CONTESTO_NON_VALIDO"
    assert client.get(_url(integrazione["id"])).json()["ruoli"] == []


@pytest.mark.integration
def test_le_richieste_http_leggono_il_profilo_dal_database(admin_client, dal_database, monkeypatch):
    """Il percorso di ogni richiesta: `require_principal` con la sessione della richiesta."""
    client, engine = admin_client
    contesto = _contesto()
    integrazione = _registra(client, contesto, {
        "ruoli": [{"ruolo": "ROLE_MANAGER", "permessi": ["GEMODO_MODELLI_GESTORE", "DOCUMENTI_VIEWER"]}],
        "client": [],
    })
    from app.common.security import require_principal

    app.dependency_overrides.pop(require_principal)
    monkeypatch.setenv("GEMODO_USE_MOCK_PRINCIPAL", "true")
    monkeypatch.setenv("GEMODO_MOCK_CLIENT_ID", "gemodo-frontend")
    monkeypatch.setenv("GEMODO_MOCK_ROLES", "")
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT", contesto)
    monkeypatch.setenv("GEMODO_MOCK_CONTEXT_ROLES", f"ROLE_MANAGER#{contesto}")
    assert app.dependency_overrides.get(get_db) is not None

    def permessi() -> set[str]:
        profilo = client.get("/api/v1/builder/profilo")
        assert profilo.status_code == 200, profilo.text
        voce = next(c for c in profilo.json()["contesti"] if c["codice"] == contesto)
        return {p["codice"] for p in voce["permessi"]}

    assert permessi() == {"GEMODO_MODELLI_GESTORE", "DOCUMENTI_VIEWER"}
    with Session(engine) as db:
        db.execute(sa.text("DELETE FROM ruolo_integrazione WHERE integrazione_id = :id"),
                   {"id": uuid.UUID(integrazione["id"])})
        db.commit()
    assert permessi() == set()
