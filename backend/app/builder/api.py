"""Builder admin API: read available structure, create models/versions, publish workflow.

Protected by GEMODO_MODELLI_GESTORE, scoped per DEC-001-CONTESTO-SOSTITUISCE-
UFFICIO (verify_scrittura_su_contesto, enforced in BuilderService, never here
directly - the target tipo documento's codice_contesto is only known after
loading it from the DB).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.builder.integrazioni_service import IntegrazioniManagerService, get_integrazioni_manager_service
from app.builder.schemas import (
    CreaModelloRequest,
    CreaEdizioneDerivataRequest,
    CreaVersioneRequest,
    IntegrazioneVisibile,
    ModelloResponse,
    ModelloDettaglioResponse,
    ModelloGestioneResponse,
    VersioneDettaglioResponse,
    StrutturaDisponibileResponse,
    StrutturaTipoDocumentoResponse,
    VersioneResponse,
)
from app.builder.service import BuilderService, get_builder_service
from app.catalog.models import ModelloDocumento, ModelloDocumentoVersione
from app.common.security import PrincipalGEMODO, require_principal

router = APIRouter(prefix="/api/v1/builder", tags=["builder"])


@router.get("/contesti", response_model=list[str])
def lista_contesti(principal: PrincipalGEMODO = Depends(require_principal),
                  service: BuilderService = Depends(get_builder_service)):
    return service.contesti(principal)


@router.get("/modelli", response_model=list[ModelloGestioneResponse])
def lista_modelli(
    codice_contesto: str = Query(min_length=1, max_length=64),
    offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100),
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
):
    return [_modello_gestione_response(model) for model in service.lista(
        principal, codice_contesto, offset=offset, limit=limit
    )]


@router.get("/modelli/{modelloId}", response_model=ModelloDettaglioResponse)
def dettaglio_modello(
    modelloId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
):
    """Dettaglio con il contratto dati, leggibile anche su una BOZZA (2b ridotta)."""
    modello = service.dettaglio(principal, modelloId)
    return ModelloDettaglioResponse(
        **_modello_response(modello).model_dump(),
        codice_contesto=modello.tipo_documento.codice_contesto,
        integrazione_id=modello.tipo_documento.integrazione_id,
        created_at=modello.created_at,
        versioni=[
            VersioneDettaglioResponse(
                **_versione_response(v).model_dump(),
                campi=[
                    {
                        "codice": campo.codice,
                        "etichetta": campo.etichetta,
                        "tipo": campo.tipo_dato,
                        "lingua": campo.lingua,
                        "obbligatorio": campo.obbligatorio,
                        "ordine": campo.ordine,
                        "descrizione": campo.descrizione,
                    }
                    for campo in sorted(v.campi, key=lambda c: (c.ordine, c.codice))
                ],
            )
            for v in sorted(modello.versioni, key=lambda v: v.versione, reverse=True)
        ],
    )


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
        lingua=modello.lingua,
        livello_professionale=modello.livello_professionale,
        derivato_da_modello_id=str(modello.derivato_da_modello_id) if modello.derivato_da_modello_id else None,
    )


def _modello_gestione_response(modello: ModelloDocumento) -> ModelloGestioneResponse:
    return ModelloGestioneResponse(
        **_modello_response(modello).model_dump(),
        codice_contesto=modello.tipo_documento.codice_contesto,
        integrazione_id=modello.tipo_documento.integrazione_id,
        created_at=modello.created_at,
        versioni=[_versione_response(v) for v in sorted(
            modello.versioni, key=lambda v: v.versione, reverse=True
        )],
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


@router.get("/integrazioni", response_model=list[IntegrazioneVisibile])
def lista_integrazioni_manager(
    principal: PrincipalGEMODO = Depends(require_principal),
    service: IntegrazioniManagerService = Depends(get_integrazioni_manager_service),
) -> list[IntegrazioneVisibile]:
    return service.lista(principal)


@router.get("/integrazioni/{integrazioneId}/tipi-documento", response_model=list[str])
def lista_tipi_documento_live(
    integrazioneId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: IntegrazioniManagerService = Depends(get_integrazioni_manager_service),
) -> list[str]:
    return service.tipi_documento(integrazioneId, principal)


@router.get(
    "/integrazioni/{integrazioneId}/tipi-documento/{codice}/struttura",
    response_model=StrutturaTipoDocumentoResponse,
    response_model_exclude_none=True,
)
def get_struttura_live_per_integrazione(
    integrazioneId: uuid.UUID,
    codice: str,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: IntegrazioniManagerService = Depends(get_integrazioni_manager_service),
) -> StrutturaTipoDocumentoResponse:
    return service.struttura(integrazioneId, codice, principal)


@router.post("/modelli", response_model=ModelloResponse, status_code=201)
def crea_modello(
    request: CreaModelloRequest,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> ModelloResponse:
    modello = service.crea_modello(principal, request)
    return _modello_response(modello)


@router.delete("/modelli/{modelloId}", status_code=204)
def elimina_modello(
    modelloId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
):
    service.elimina(principal, modelloId)


@router.post(
    "/modelli/{modelloId}/edizioni-derivate",
    response_model=ModelloGestioneResponse,
    status_code=201,
)
def crea_edizione_derivata(
    modelloId: uuid.UUID,
    request: CreaEdizioneDerivataRequest,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> ModelloGestioneResponse:
    return _modello_gestione_response(
        service.crea_edizione_derivata(principal, modelloId, request)
    )


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
    return _versione_response(service.transizione(principal, versioneId, "IN_REVISIONE", modello_id=modelloId))


@router.post("/modelli/{modelloId}/versioni/{versioneId}/approva", response_model=VersioneResponse)
def approva(
    modelloId: uuid.UUID,
    versioneId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> VersioneResponse:
    return _versione_response(service.transizione(principal, versioneId, "APPROVATO", modello_id=modelloId))


@router.post("/modelli/{modelloId}/versioni/{versioneId}/pubblica", response_model=VersioneResponse)
def pubblica(
    modelloId: uuid.UUID,
    versioneId: uuid.UUID,
    principal: PrincipalGEMODO = Depends(require_principal),
    service: BuilderService = Depends(get_builder_service),
) -> VersioneResponse:
    return _versione_response(service.transizione(principal, versioneId, "PUBBLICATO", modello_id=modelloId))
