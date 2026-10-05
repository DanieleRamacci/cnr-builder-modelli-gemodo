"""Il profilo di accesso delle integrazioni, letto dal database (001 T089).

Traduce ruoli e client di ogni integrazione negli stessi oggetti che prima
arrivavano da `infra/local/integration-profiles.local.yaml`, cosi' che la
regola di autorizzazione (`permessi_da_ruoli_esterni`) resti una sola e
quella gia' provata. Si legge a ogni richiesta: una revoca vale subito.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.configurazione.models import ClientIntegrazione, Integrazione, RuoloIntegrazione
from app.quality.schemas import (
    ClientApplicativo,
    ExternalRoleMapping,
    PermessoOperativo,
    ProfiloDiIntegrazione,
    StatoClientApplicativo,
    StatoProfiloIntegrazione,
    SistemaRichiedente,
)

AUDIENCE_GEMODO = "gemodo-backend"


def sistemi_dal_database(db: Session) -> tuple[SistemaRichiedente, ...]:
    """Un sistema richiedente per ogni integrazione che ha almeno un ruolo o un client."""
    ruoli: dict = {}
    for ruolo in db.scalars(select(RuoloIntegrazione).order_by(RuoloIntegrazione.ruolo)):
        ruoli.setdefault(ruolo.integrazione_id, []).append(ruolo)
    client: dict = {}
    for voce in db.scalars(select(ClientIntegrazione).order_by(ClientIntegrazione.client_id)):
        client.setdefault(voce.integrazione_id, []).append(voce.client_id)
    con_accessi = set(ruoli) | set(client)
    if not con_accessi:
        return ()
    integrazioni = db.scalars(select(Integrazione).where(Integrazione.id.in_(con_accessi)))
    return tuple(_sistema(i, ruoli.get(i.id, []), client.get(i.id, [])) for i in integrazioni)


def _sistema(integrazione: Integrazione, ruoli: list[RuoloIntegrazione], client: list[str]) -> SistemaRichiedente:
    contesto = integrazione.codice_contesto
    return SistemaRichiedente(
        codice=integrazione.codice,
        nome=integrazione.nome,
        spec_owner="specs/001-catalogo-contratto-geban",
        client_applicativi=[
            ClientApplicativo(
                client_id=client_id,
                audience_attesa=AUDIENCE_GEMODO,
                token_contexts=[contesto],
                sistemi_abilitati=[integrazione.codice],
                stato=StatoClientApplicativo.ATTIVO,
            )
            for client_id in client
        ],
        profili_integrazione=[
            ProfiloDiIntegrazione(
                codice=f"{integrazione.codice}_ACCESSI",
                sistema_richiedente=integrazione.codice,
                versione="db",
                stato=StatoProfiloIntegrazione.ATTIVO,
                client_ammessi=client,
                permessi_operativi=list(PermessoOperativo),
                role_mappings=[
                    ExternalRoleMapping(
                        token_context=contesto,
                        external_role=f"{ruolo.ruolo}#{contesto}",
                        internal_permissions=list(ruolo.permessi),
                    )
                    for ruolo in ruoli
                ],
            )
        ],
    )
