"""Builder domain service: model/version creation and publication workflow.

FR-002/FR-003/FR-014/FR-015 (specs/002-builder-modelli, riallineate 2026-09-15,
DEC-001-CONTESTO-SOSTITUISCE-UFFICIO): la struttura disponibile (tipologie,
profili, campi) si legge sempre dalla porta di discovery, mai direttamente
dalle tabelle catalogo; ogni scrittura e' autorizzata per il singolo contesto
del tipo documento target, mai sulla lista di permessi del principal gia'
appiattita su tutti i contesti del token.
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.builder import repository as builder_repository
from app.builder.audit import registra_evento
from app.builder.schemas import CampoVersioneRequest, CreaModelloRequest
from app.catalog import repository as catalog_repository
from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione
from app.common.errors import BuilderDomainError, ErrorCode
from app.common.security import PrincipalGEMODO, verify_scrittura_su_contesto
from app.db.session import get_db
from app.discovery.adapter_locale import AdapterLocale
from app.discovery.schemas import CampoDisponibile, TipologiaDisponibile

TRANSIZIONI_VALIDE: dict[str, set[str]] = {
    "BOZZA": {"IN_REVISIONE"},
    "IN_REVISIONE": {"BOZZA", "APPROVATO"},
    "APPROVATO": {"PUBBLICATO"},
    "PUBBLICATO": {"ARCHIVIATO", "SOSPESO"},
    "SOSPESO": {"ARCHIVIATO"},
    "ARCHIVIATO": set(),
}


class BuilderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.discovery = AdapterLocale(db)

    def struttura_disponibile(self, principal: PrincipalGEMODO, codice_tipo_documento: str) -> tuple[list[TipologiaDisponibile], list[CampoDisponibile]]:
        tipo = self._resolve_tipo_documento(codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)
        return (
            self.discovery.tipologie_disponibili(codice_tipo_documento),
            self.discovery.campi_disponibili(codice_tipo_documento),
        )

    def crea_modello(self, principal: PrincipalGEMODO, request: CreaModelloRequest) -> ModelloDocumento:
        tipo = self._resolve_tipo_documento(request.codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)

        tipologie = self.discovery.tipologie_disponibili(request.codice_tipo_documento)
        tipologia_scelta = None
        if request.codice_tipologia is not None:
            tipologia_scelta = next((t for t in tipologie if t.codice == request.codice_tipologia), None)
            if tipologia_scelta is None:
                raise BuilderDomainError(
                    ErrorCode.CONTESTO_NON_VALIDO,
                    "Tipologia non disponibile per questo tipo documento",
                    status_code=404,
                )
            if not any(p.codice == request.codice_categoria for p in tipologia_scelta.profili):
                raise BuilderDomainError(
                    ErrorCode.CONTESTO_NON_VALIDO,
                    "Categoria non ammessa per la tipologia scelta",
                    status_code=404,
                )

        categoria = builder_repository.get_categoria_by_codice(self.db, tipo.id, request.codice_categoria)
        if categoria is None:
            raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Categoria non trovata", status_code=404)

        tipologia_row = None
        if request.codice_tipologia is not None:
            tipologia_row = catalog_repository.get_tipologia_sol_by_codice(self.db, request.codice_tipologia)

        modello = builder_repository.crea_modello(
            self.db,
            codice=request.codice,
            nome=request.nome,
            tipo_documento_id=tipo.id,
            categoria_documento_id=categoria.id,
            tipologia_bando_sol_id=tipologia_row.id if tipologia_row else None,
            variante=request.variante,
        )
        registra_evento(
            self.db,
            tipo_evento="MODELLO_CREATO",
            principal=principal,
            modello_documento_id=modello.id,
            modello_versione_id=None,
            payload_minimo={"codice": modello.codice, "codice_tipo_documento": request.codice_tipo_documento},
        )
        self.db.commit()
        return modello

    def crea_versione(
        self, principal: PrincipalGEMODO, modello_id: uuid.UUID, campi_richiesti: list[CampoVersioneRequest]
    ) -> ModelloDocumentoVersione:
        modello = builder_repository.get_modello(self.db, modello_id)
        if modello is None:
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)

        disponibili = {
            (campo.codice, campo.lingua): campo
            for campo in self.discovery.campi_disponibili(modello.tipo_documento.codice)
        }
        campi_modello: list[ModelloCampoRichiesto] = []
        for richiesto in campi_richiesti:
            chiave = (richiesto.codice, richiesto.lingua)
            sorgente = disponibili.get(chiave)
            if sorgente is None:
                raise BuilderDomainError(
                    ErrorCode.CAMPO_NON_AMMESSO,
                    f"Campo '{richiesto.codice}' ({richiesto.lingua}) non presente nel registro contratti dati",
                    status_code=404,
                )
            campi_modello.append(
                ModelloCampoRichiesto(
                    id=uuid.uuid4(),
                    codice=sorgente.codice,
                    etichetta=sorgente.etichetta,
                    tipo_dato=sorgente.tipo_dato,
                    obbligatorio=sorgente.obbligatorio,
                    lingua=sorgente.lingua,
                    ordine=sorgente.ordine,
                    validazione=sorgente.validazione,
                )
            )

        versione = builder_repository.crea_versione(
            self.db, modello_documento_id=modello.id, campi=campi_modello
        )
        registra_evento(
            self.db,
            tipo_evento="VERSIONE_CREATA",
            principal=principal,
            modello_documento_id=modello.id,
            modello_versione_id=versione.id,
            payload_minimo={"numero_versione": versione.versione, "campi": [c.codice for c in campi_modello]},
        )
        self.db.commit()
        return versione

    def transizione(self, principal: PrincipalGEMODO, versione_id: uuid.UUID, nuovo_stato: str) -> ModelloDocumentoVersione:
        versione = builder_repository.get_versione(self.db, versione_id)
        if versione is None:
            raise BuilderDomainError(ErrorCode.MODELLO_VERSIONE_NON_TROVATO, "Versione non trovata", status_code=404)
        modello = builder_repository.get_modello(self.db, versione.modello_documento_id)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)

        ammessi = TRANSIZIONI_VALIDE.get(versione.stato, set())
        if nuovo_stato not in ammessi:
            raise BuilderDomainError(
                ErrorCode.TRANSIZIONE_STATO_NON_VALIDA,
                f"Transizione da {versione.stato} a {nuovo_stato} non valida",
                status_code=409,
            )

        if nuovo_stato == "PUBBLICATO":
            precedente = builder_repository.get_versione_pubblicata_corrente(
                self.db,
                tipo_documento_id=modello.tipo_documento_id,
                categoria_documento_id=modello.categoria_documento_id,
                tipologia_bando_sol_id=modello.tipologia_bando_sol_id,
                variante=modello.variante,
                escludi_versione_id=versione.id,
            )
            if precedente is not None:
                builder_repository.transizione_stato(self.db, precedente, nuovo_stato="ARCHIVIATO")
                registra_evento(
                    self.db,
                    tipo_evento="VERSIONE_ARCHIVIATA",
                    principal=principal,
                    modello_documento_id=modello.id,
                    modello_versione_id=precedente.id,
                    payload_minimo={"motivo": "sostituita da nuova versione corrente"},
                )

        builder_repository.transizione_stato(self.db, versione, nuovo_stato=nuovo_stato)
        registra_evento(
            self.db,
            tipo_evento=f"VERSIONE_{nuovo_stato}",
            principal=principal,
            modello_documento_id=modello.id,
            modello_versione_id=versione.id,
            payload_minimo={"stato": nuovo_stato},
        )
        self.db.commit()
        return versione

    def _resolve_tipo_documento(self, codice_tipo_documento: str):
        tipo = catalog_repository.get_tipo_documento_by_codice(self.db, codice_tipo_documento)
        if tipo is None:
            raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Tipo documento non trovato", status_code=404)
        return tipo


def get_builder_service(db: Session = Depends(get_db)) -> BuilderService:
    return BuilderService(db)
