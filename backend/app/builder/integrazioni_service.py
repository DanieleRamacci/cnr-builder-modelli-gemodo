"""Manager reads over registered integrations (T083, contract T078).

Owner sequence per ADR 0002: 010 owns the integration/endpoint/verification registry,
002 owns "who may browse/select through it". A manager only ever sees integrations
that are both CONNESSO and authorized for one of their token contexts (never the
admin's URL, timeout or error details); the context check always runs before any
live HTTP read.
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.builder.schemas import IntegrazioneVisibile
from app.common.errors import DomainError
from app.common.security import ROLE_GEMODO_MODELLI_GESTORE, PrincipalGEMODO, contesti_con_permesso
from app.configurazione import repository as configurazione_repository
from app.configurazione.models import EndpointIntegrazione, Integrazione
from app.db.session import get_db
from app.discovery.adapter_http import AdapterHTTP
from app.discovery.errors import DiscoveryError
from app.discovery.schemas import CatalogoDiscovery, MappaDiscovery


class IntegrazioniManagerService:
    def __init__(self, db: Session):
        self.db = db

    def _connessa_autorizzata(
        self, integrazione_id: uuid.UUID, principal: PrincipalGEMODO
    ) -> tuple[Integrazione, EndpointIntegrazione]:
        source = configurazione_repository.integrazione(self.db, integrazione_id)
        if source is None or not contesti_con_permesso(principal, ROLE_GEMODO_MODELLI_GESTORE, (source.codice_contesto,)):
            # Same response whether the integration does not exist or the caller
            # simply cannot see it: existence of another context's integration is
            # never leaked to an unauthorized caller.
            raise DomainError("RISORSA_NON_TROVATA", "Risorsa non disponibile", status_code=404)
        endpoint = configurazione_repository.endpoint(self.db, source.id)
        if endpoint is None or endpoint.stato != "CONNESSO":
            raise DomainError("INTEGRAZIONE_NON_CONNESSA", "Integrazione non connessa", status_code=409)
        return source, endpoint

    @staticmethod
    def _adapter(integrazione_id: uuid.UUID, endpoint: EndpointIntegrazione) -> AdapterHTTP:
        return AdapterHTTP(
            endpoint.url, timeout_seconds=endpoint.timeout_ms / 1000,
            cache_scope=f"integrazione:{integrazione_id}:revisione:{endpoint.revisione_verificata}",
        )

    @staticmethod
    def _mappa(adapter: AdapterHTTP) -> MappaDiscovery:
        try:
            return adapter.mappa_discovery()
        except DiscoveryError as exc:
            # These new routes map every transport/conformance failure to 502 and an
            # expired budget to 504 (integrazioni-policy.md); the legacy adapter's own
            # 503 "non disponibile" semantics stay untouched for its existing callers.
            if exc.status_code == 503:
                raise DiscoveryError(exc.codice, exc.messaggio, status_code=502) from exc
            raise

    def lista(self, principal: PrincipalGEMODO) -> list[IntegrazioneVisibile]:
        connesse = configurazione_repository.integrazioni_connesse(self.db)
        contesti = contesti_con_permesso(
            principal, ROLE_GEMODO_MODELLI_GESTORE, {source.codice_contesto for source, _ in connesse},
        )
        return [
            IntegrazioneVisibile(id=source.id, codice=source.codice, nome=source.nome, codice_contesto=source.codice_contesto)
            for source, _ in connesse if source.codice_contesto in contesti
        ]

    def tipi_documento(self, integrazione_id: uuid.UUID, principal: PrincipalGEMODO) -> list[str]:
        _, endpoint = self._connessa_autorizzata(integrazione_id, principal)
        mappa = self._mappa(self._adapter(integrazione_id, endpoint))
        return sorted(mappa.cataloghi)

    def struttura(self, integrazione_id: uuid.UUID, codice: str, principal: PrincipalGEMODO) -> CatalogoDiscovery:
        _, endpoint = self._connessa_autorizzata(integrazione_id, principal)
        mappa = self._mappa(self._adapter(integrazione_id, endpoint))
        catalogo = mappa.cataloghi.get(codice)
        if catalogo is None:
            raise DomainError("RISORSA_NON_TROVATA", "Tipo documento non disponibile per questa integrazione", status_code=404)
        return catalogo


def get_integrazioni_manager_service(db: Session = Depends(get_db)) -> IntegrazioniManagerService:
    return IntegrazioniManagerService(db)
