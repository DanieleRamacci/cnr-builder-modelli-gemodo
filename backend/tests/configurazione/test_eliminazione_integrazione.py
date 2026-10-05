"""Cancellare un'integrazione registrata: 010 T103 e T106.

Il caso da cui nasce: un'integrazione "test" registrata per sbaglio in test
online, che dall'interfaccia non c'era modo di togliere (DELETE rispondeva 405,
e anche dal database l'audit e l'endpoint lo impedivano). Il refuso si
corregge cancellando e ricreando, non rinominando: codice e contesto sono
identita'.

Tre livelli: senza modelli si cancella sempre, con i tipi documento e i
modelli gia' eliminati a seguire; con modelli vivi si rifiuta dicendo quali;
con modelli che hanno generato documenti si rifiuta, perche' quei documenti
restano agli atti. In ogni caso l'audit sopravvive.

PostgreSQL reale, via HTTP.
"""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.catalog.models import ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.common.security import PrincipalGEMODO, require_principal
from app.configurazione.models import AuditEventoConfigurazione, AuditEventoIntegrazione, EndpointIntegrazione, Integrazione
from app.main import app
from app.storage.models import DocumentoGenerato
from tests.configurazione.test_integrazioni_admin import admin_client, crea  # noqa: F401 (fixture)
from tests.support.postgres import postgres_database_url  # noqa: F401 (fixture)


def _url(integrazione_id: str) -> str:
    return f"/api/v1/configurazione/integrazioni/{integrazione_id}"


def _tipo(engine, integrazione: dict) -> uuid.UUID:
    """Un tipo documento dell'integrazione, con un evento di audit della configurazione."""
    tipo_id = uuid.uuid4()
    with Session(engine) as db:
        db.add(TipoDocumento(
            id=tipo_id, codice=f"TIPO_{tipo_id.hex[:8]}", nome="Tipo di prova", stato="ATTIVA",
            spec_owner="specs/010-configurazione-cataloghi-integrazioni",
            codice_contesto=integrazione["codice_contesto"], integrazione_id=uuid.UUID(integrazione["id"]),
        ))
        db.flush()
        db.add(AuditEventoConfigurazione(
            tipo_documento_id=tipo_id, tipo_evento="POLICY_SALVATA", soggetto_id="admin-test",
            client_id="gemodo-frontend", payload_minimo={"codice": "prova"},
        ))
        db.commit()
    return tipo_id


def _modello(engine, tipo_id: uuid.UUID, *, stato: str, con_documento: bool = False) -> uuid.UUID:
    """Un modello con una versione; se richiesto, un documento generato da quella versione."""
    modello_id, versione_id = uuid.uuid4(), uuid.uuid4()
    with Session(engine) as db:
        db.add(ModelloDocumento(
            id=modello_id, tipo_documento_id=tipo_id, codice_categoria="RICERCATORE",
            codice_tipologia="TD", percorso_categorizzazione=["TD", "RICERCATORE"],
            codice=f"modello-{modello_id.hex[:12]}", nome="Modello di prova",
            variante="STANDARD", dimensioni={"lingua": "IT"}, stato=stato,
        ))
        db.flush()
        db.add(ModelloDocumentoVersione(
            id=versione_id, modello_documento_id=modello_id, versione=1, stato="ARCHIVIATO",
            struttura_documentale={},
        ))
        db.flush()
        if con_documento:
            db.add(DocumentoGenerato(
                riferimento=f"doc-{versione_id.hex[:16]}", sistema_richiedente="GEBAN",
                external_context_id=uuid.uuid4().hex, modello_versione_id=versione_id,
                stato="FALLITO", hash_dati="0" * 64, nome_file="prova.pdf",
                errore_messaggio="prova", creato_da="test",
            ))
        db.commit()
    return modello_id


def _esiste(engine, modello, chiave) -> bool:
    with Session(engine) as db:
        return db.get(modello, chiave) is not None


@pytest.mark.integration
def test_senza_tipi_si_cancella_anche_se_ha_un_endpoint(admin_client):
    client, engine = admin_client
    codice, creata = crea(client)
    integrazione_id = uuid.UUID(creata["id"])
    with Session(engine) as db:
        db.add(EndpointIntegrazione(integrazione_id=integrazione_id, url="https://esempio.test/discovery"))
        db.commit()

    risposta = client.delete(_url(creata["id"]))

    assert risposta.status_code == 204, risposta.text
    assert client.get(_url(creata["id"])).status_code == 404
    assert codice not in [i["codice"] for i in client.get("/api/v1/configurazione/integrazioni").json()]
    with Session(engine) as db:
        assert db.scalar(sa.select(sa.func.count()).select_from(EndpointIntegrazione)
                         .where(EndpointIntegrazione.integrazione_id == integrazione_id)) == 0
        eventi = {
            e.tipo_evento: e.payload_minimo
            for e in db.scalars(sa.select(AuditEventoIntegrazione)
                                .where(AuditEventoIntegrazione.integrazione_id == integrazione_id))
        }
    # La storia resta, con l'identificativo che la tiene insieme e il codice in chiaro.
    assert "INTEGRAZIONE_CREATA" in eventi
    assert eventi["INTEGRAZIONE_CANCELLATA"]["codice"] == codice
    assert eventi["INTEGRAZIONE_CANCELLATA"]["codice_contesto"] == creata["codice_contesto"]


@pytest.mark.integration
def test_il_codice_si_puo_registrare_di_nuovo_dopo_la_cancellazione(admin_client):
    """E' il modo di correggere un refuso: cancellare e ricreare."""
    client, _ = admin_client
    codice, creata = crea(client)
    assert client.delete(_url(creata["id"])).status_code == 204

    _, ricreata = crea(client, codice)

    assert ricreata["id"] != creata["id"]


@pytest.mark.integration
def test_tipi_e_modelli_gia_eliminati_seguono_l_integrazione(admin_client):
    client, engine = admin_client
    _, creata = crea(client)
    tipo_id = _tipo(engine, creata)
    modello_id = _modello(engine, tipo_id, stato="ELIMINATO")

    risposta = client.delete(_url(creata["id"]))

    assert risposta.status_code == 204, risposta.text
    assert not _esiste(engine, TipoDocumento, tipo_id)
    assert not _esiste(engine, ModelloDocumento, modello_id)
    with Session(engine) as db:
        audit_tipo = db.scalar(sa.select(sa.func.count()).select_from(AuditEventoConfigurazione)
                               .where(AuditEventoConfigurazione.tipo_documento_id == tipo_id))
        cancellata = db.scalar(sa.select(AuditEventoIntegrazione.payload_minimo).where(
            AuditEventoIntegrazione.integrazione_id == uuid.UUID(creata["id"]),
            AuditEventoIntegrazione.tipo_evento == "INTEGRAZIONE_CANCELLATA",
        ))
    assert audit_tipo == 1, "l'audit del tipo documento deve sopravvivergli"
    assert len(cancellata["tipi_documento"]) == 1
    assert len(cancellata["modelli_eliminati"]) == 1


@pytest.mark.integration
def test_un_modello_vivo_blocca_e_la_risposta_dice_quale(admin_client):
    client, engine = admin_client
    _, creata = crea(client)
    tipo_id = _tipo(engine, creata)
    _modello(engine, tipo_id, stato="ELIMINATO")
    vivo = _modello(engine, tipo_id, stato="BOZZA")

    risposta = client.delete(_url(creata["id"]))

    assert risposta.status_code == 409, risposta.text
    corpo = risposta.json()
    assert corpo["codice"] == "INTEGRAZIONE_HA_MODELLI"
    assert [d["codice"] for d in corpo["dettagli"]] == [f"modello-{vivo.hex[:12]}"]
    assert _esiste(engine, Integrazione, uuid.UUID(creata["id"]))
    assert _esiste(engine, TipoDocumento, tipo_id)


@pytest.mark.integration
def test_un_modello_che_ha_generato_documenti_blocca(admin_client):
    """I documenti generati restano agli atti e devono poter dire da dove vengono."""
    client, engine = admin_client
    _, creata = crea(client)
    tipo_id = _tipo(engine, creata)
    con_documento = _modello(engine, tipo_id, stato="ELIMINATO", con_documento=True)

    risposta = client.delete(_url(creata["id"]))

    assert risposta.status_code == 409, risposta.text
    assert risposta.json()["codice"] == "INTEGRAZIONE_HA_DOCUMENTI"
    assert risposta.json()["dettagli"][0]["codice"] == f"modello-{con_documento.hex[:12]}"
    assert _esiste(engine, ModelloDocumento, con_documento)
    with Session(engine) as db:
        db.execute(sa.delete(DocumentoGenerato).where(DocumentoGenerato.modello_versione_id.in_(
            sa.select(ModelloDocumentoVersione.id).where(ModelloDocumentoVersione.modello_documento_id == con_documento)
        )))
        db.commit()


@pytest.mark.integration
def test_un_integrazione_inesistente_e_404(admin_client):
    client, _ = admin_client

    assert client.delete(_url(str(uuid.uuid4()))).status_code == 404


@pytest.mark.integration
def test_solo_l_amministratore_cancella(admin_client):
    client, engine = admin_client
    _, creata = crea(client)
    app.dependency_overrides[require_principal] = lambda: PrincipalGEMODO(
        "manager", "gemodo-frontend", ("gemodo-backend",), ("GEMODO_MODELLI_GESTORE",),
        "https://sso.example.test",
    )

    assert client.delete(_url(creata["id"])).status_code == 403
    assert _esiste(engine, Integrazione, uuid.UUID(creata["id"]))
