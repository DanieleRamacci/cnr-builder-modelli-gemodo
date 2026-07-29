"""Reusable SistemaRichiedente/ClientApplicativo/ProfiloDiIntegrazione fixtures.

Provides representative in-memory instances (authorized, unauthorized, suspended,
draft) used by integration-profile and mock-GEBAN authorization tests, so tests do not
need to hand-roll Pydantic objects for every edge case.
"""

from __future__ import annotations

from app.quality.schemas import (
    ClientApplicativo,
    PermessoOperativo,
    ProfiloDiIntegrazione,
    SistemaRichiedente,
    StatoClientApplicativo,
    StatoProfiloIntegrazione,
    StatoSistemaRichiedente,
)

GEBAN_CLIENT_ID = "geban-backend"
GEBAN_PROFILE_CODE = "GEBAN_RECLUTAMENTO_V1"


def client_geban_backend(stato: StatoClientApplicativo = StatoClientApplicativo.ATTIVO) -> ClientApplicativo:
    return ClientApplicativo(
        client_id=GEBAN_CLIENT_ID,
        audience_attesa="gemodo-backend",
        ruoli_claim_richiesti=["DOCUMENTI_GENERATORE"],
        sistemi_abilitati=["GEBAN"],
        stato=stato,
        gestisce_credenziali=False,
    )


def profilo_geban_attivo(
    *,
    permessi: list[PermessoOperativo] | None = None,
    tipi_documento_ammessi: list[str] | None = None,
) -> ProfiloDiIntegrazione:
    return ProfiloDiIntegrazione(
        codice=GEBAN_PROFILE_CODE,
        sistema_richiedente="GEBAN",
        versione="1",
        stato=StatoProfiloIntegrazione.ATTIVO,
        client_ammessi=[GEBAN_CLIENT_ID],
        tipi_documento_ammessi=tipi_documento_ammessi
        if tipi_documento_ammessi is not None
        else ["BANDO_CONCORSO"],
        categorie_ammessi=["DEMO"],
        tipologie_ammessi=["TDPNRR", "CD", "DIR", "TD", "CP", "RS", "CATP", "TI", "SDIP", "MOB"],
        modelli_versioni_ammessi=["demo-bando-concorso-standard-v1"],
        contratti_dati_ammessi=["bando-concorso-common-fields-v1"],
        permessi_operativi=permessi
        if permessi is not None
        else [
            PermessoOperativo.CATALOGO,
            PermessoOperativo.VALIDAZIONE,
            PermessoOperativo.GENERAZIONE_BOZZA,
            PermessoOperativo.GENERAZIONE_UFFICIALE,
            PermessoOperativo.STATO,
            PermessoOperativo.DOWNLOAD,
        ],
    )


def profilo_geban_bozza() -> ProfiloDiIntegrazione:
    return profilo_geban_attivo().model_copy(update={"stato": StatoProfiloIntegrazione.BOZZA})


def sistema_geban_attivo() -> SistemaRichiedente:
    return SistemaRichiedente(
        codice="GEBAN",
        nome="GEBAN - gestione bandi di concorso",
        stato=StatoSistemaRichiedente.ATTIVO,
        client_applicativi=[client_geban_backend()],
        profili_integrazione=[profilo_geban_attivo()],
        spec_owner="specs/001-catalogo-contratto-geban",
    )


def sistema_geban_sospeso() -> SistemaRichiedente:
    return sistema_geban_attivo().model_copy(update={"stato": StatoSistemaRichiedente.SOSPESO})


def sistema_geban_senza_client() -> SistemaRichiedente:
    return sistema_geban_attivo().model_copy(update={"client_applicativi": []})


def sistema_geban_profilo_bozza() -> SistemaRichiedente:
    return sistema_geban_attivo().model_copy(update={"profili_integrazione": [profilo_geban_bozza()]})
