"""Builder admin API: read available structure, create models/versions, publish workflow.

Protected by GEMODO_MODELLI_GESTORE, scoped per DEC-001-CONTESTO-SOSTITUISCE-
UFFICIO (verify_scrittura_su_contesto, enforced in BuilderService, never here
directly - the target tipo documento's codice_contesto is only known after
loading it from the DB).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.builder.schemas import (
    CreaModelloRequest,
    CreaVersioneRequest,
    ModelloResponse,
    StrutturaDisponibileResponse,
    VersioneResponse,
)
from app.builder.service import BuilderService, get_builder_service
from app.catalog.models import ModelloDocumento, ModelloDocumentoVersione
from app.common.security import PrincipalGEMODO, require_principal

router = APIRouter(prefix="/api/v1/builder", tags=["builder"])


def _modello_response(modello: ModelloDocumento) -> ModelloResponse:
    return ModelloResponse(
        id=str(modello.id),
        public_id=modello.public_id,
        codice=modello.codice,
        nome=modello.nome,
        codice_tipo_documento=modello.tipo_documento.codice,
        codice_categoria=modello.codice_categoria,
        codice_tipologia=modello.codice_tipologia,
        percorso_categorizzazione=modello.percorso_categorizzazione,
        variante=modello.variante,
    )


def _versione_response(versione: ModelloDocumentoVersione) -> VersioneResponse:
    return VersioneResponse(
        id=str(versione.id),
        public_id=versione.public_id,
        modello_id=str(versione.modello_documento_id),
        numero_versione=versione.versione,
        stato=versione.stato,
        pubblicato_at=versione.pubblicato_at,
    )


@router.get("/tipi-documento/{codiceTipoDocumento}/struttura-disponibile", response_model=StrutturaDisponibileResponse, response_model_exclude_none=True)
def get_struttura_disponibile(
    codiceTipoDocumento: str,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> StrutturaDisponibileResponse:
    return service.struttura_disponibile(principal, codiceTipoDocumento)


@router.post("/modelli", response_model=ModelloResponse, status_code=201)
def crea_modello(
    request: CreaModelloRequest,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> ModelloResponse:
    modello = service.crea_modello(principal, request)
    return _modello_response(modello)


@router.post("/modelli/{modelloId}/versioni", response_model=VersioneResponse, status_code=201)
def crea_versione(
    modelloId: uuid.UUID,
    request: CreaVersioneRequest,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> VersioneResponse:
    versione = service.crea_versione(principal, modelloId, request.campi)
    return _versione_response(versione)


@router.post("/modelli/{modelloId}/versioni/{versioneId}/invia-revisione", response_model=VersioneResponse)
def invia_revisione(
    modelloId: uuid.UUID,
    versioneId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> VersioneResponse:
    return _versione_response(service.transizione(principal, versioneId, "IN_REVISIONE"))


@router.post("/modelli/{modelloId}/versioni/{versioneId}/approva", response_model=VersioneResponse)
def approva(
    modelloId: uuid.UUID,
    versioneId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> VersioneResponse:
    return _versione_response(service.transizione(principal, versioneId, "APPROVATO"))


@router.post("/modelli/{modelloId}/versioni/{versioneId}/pubblica", response_model=VersioneResponse)
def pubblica(
    modelloId: uuid.UUID,
    versioneId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> VersioneResponse:
    return _versione_response(service.transizione(principal, versioneId, "PUBBLICATO"))
