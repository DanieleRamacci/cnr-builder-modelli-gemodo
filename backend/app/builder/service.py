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
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.builder import repository as builder_repository
from app.builder.audit import registra_evento
from app.builder.schemas import CampoVersioneRequest, CreaModelloRequest
from app.catalog import repository as catalog_repository
from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.configurazione import repository as configurazione_repository
from app.common.errors import BuilderDomainError, DomainError, ErrorCode
from app.common.security import PrincipalGEMODO, verify_scrittura_su_contesto, contesti_con_permesso, ROLE_GEMODO_MODELLI_GESTORE
from app.db.session import get_db
from app.discovery.configuration import discovery_per_tipo
from app.discovery.port import PortaDiscovery
from app.discovery.schemas import CatalogoDiscovery

TRANSIZIONI_VALIDE: dict[str, set[str]] = {
    "BOZZA": {"IN_REVISIONE"},
    "IN_REVISIONE": {"BOZZA", "APPROVATO"},
    "APPROVATO": {"PUBBLICATO"},
    "PUBBLICATO": {"ARCHIVIATO", "SOSPESO"},
    "SOSPESO": {"ARCHIVIATO"},
    "ARCHIVIATO": set(),
}


class BuilderService:
    def __init__(self, db: Session, discovery: PortaDiscovery | None = None) -> None:
        self.db = db
        self.discovery = discovery

    def contesti(self, principal: PrincipalGEMODO) -> list[str]:
        return sorted(contesti_con_permesso(principal, ROLE_GEMODO_MODELLI_GESTORE,
                                           dict(principal.ruoli_contesto)))

    def lista(self, principal: PrincipalGEMODO, codice_contesto: str, *, offset: int, limit: int):
        verify_scrittura_su_contesto(principal, codice_contesto)
        return builder_repository.lista_modelli(self.db, codice_contesto, offset=offset, limit=limit)

    def _catalogo(self, codice: str, *, aggiornato: bool = False, tipo: TipoDocumento | None = None) -> CatalogoDiscovery:
        tipo = tipo if tipo is not None else self._resolve_tipo_documento(codice)
        porta = self.discovery if self.discovery is not None else discovery_per_tipo(self.db, tipo)
        return porta.catalogo_discovery(codice, forza_aggiornamento=aggiornato)

    def struttura_disponibile(self, principal: PrincipalGEMODO, codice_tipo_documento: str) -> CatalogoDiscovery:
        tipo = self._resolve_tipo_documento(codice_tipo_documento)
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)
        return self._catalogo(codice_tipo_documento)

    def crea_modello(self, principal: PrincipalGEMODO, request: CreaModelloRequest) -> ModelloDocumento:
        if request.integrazione_id is None:
            tipo = self._resolve_tipo_documento(request.codice_tipo_documento)
        else:
            source = configurazione_repository.integrazione(self.db, request.integrazione_id)
            if source is None:
                raise DomainError("RISORSA_NON_TROVATA", "Risorsa non disponibile", status_code=404)
            verify_scrittura_su_contesto(principal, source.codice_contesto)
            # Persist only the document type identity, never the external tree.
            self.db.execute(insert(TipoDocumento).values(
                id=uuid.uuid4(), codice=request.codice_tipo_documento,
                nome=request.codice_tipo_documento, codice_contesto=source.codice_contesto,
                integrazione_id=source.id, stato="ATTIVA", spec_owner="specs/002-builder-modelli",
            ).on_conflict_do_nothing(constraint="uq_tipo_documento_integrazione_codice"))
            tipo = self.db.scalar(select(TipoDocumento).where(
                TipoDocumento.integrazione_id == source.id,
                TipoDocumento.codice == request.codice_tipo_documento,
            ))
        verify_scrittura_su_contesto(principal, tipo.codice_contesto)

        indice = self._catalogo(request.codice_tipo_documento, aggiornato=True, tipo=tipo).indice_percorsi()

        def riferimenti(percorso: tuple[str, ...]) -> tuple[str, str | None]:
            nodi = [indice[percorso[:i]] for i in range(1, len(percorso) + 1)]
            categoria = next((n.codice for n in reversed(nodi) if n.tipo_livello == "profilo"), percorso[-1])
            tipologia = next((n.codice for n in nodi if n.tipo_livello == "tipologia"), None)
            return categoria, tipologia

        if request.percorso_categorizzazione is not None:
            percorso = tuple(request.percorso_categorizzazione)
            foglia = indice.get(percorso)
            if foglia is None or foglia.campi is None:
                raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Percorso non disponibile o non foglia", status_code=404)
            categoria, tipologia = riferimenti(percorso)
            if ((request.codice_categoria is not None and request.codice_categoria != categoria)
                or (request.codice_tipologia is not None and request.codice_tipologia != tipologia)):
                raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Codici incoerenti con il percorso scelto", status_code=400)
        else:
            candidati = [p for p, n in indice.items() if n.campi is not None
                         and riferimenti(p)[0] == request.codice_categoria
                         and (request.codice_tipologia is None or riferimenti(p)[1] == request.codice_tipologia)]
            if len(candidati) != 1:
                raise BuilderDomainError(
                    ErrorCode.CONTESTO_NON_VALIDO,
                    "Selezione ambigua: indicare il percorso completo" if candidati else "Categoria/tipologia non disponibile",
                    status_code=400 if candidati else 404,
                )
            percorso = candidati[0]
            categoria, tipologia = riferimenti(percorso)

        modello = builder_repository.crea_modello(
            self.db,
            codice=request.codice,
            nome=request.nome,
            tipo_documento_id=tipo.id,
            codice_categoria=categoria,
            codice_tipologia=tipologia,
            percorso_categorizzazione=list(percorso),
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

        self.db.execute(select(TipoDocumento.id).where(TipoDocumento.id == modello.tipo_documento_id).with_for_update())
        self.db.refresh(modello)
        if modello.stato == "ELIMINATO":
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        foglia = self._catalogo(modello.tipo_documento.codice, aggiornato=True, tipo=modello.tipo_documento).indice_percorsi().get(
            tuple(modello.percorso_categorizzazione)
        )
        if foglia is None or foglia.campi is None:
            raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Il ramo del modello non e' piu' disponibile", status_code=404)
        chiavi = [(campo.codice, campo.lingua) for campo in campi_richiesti]
        if len(set(chiavi)) != len(chiavi):
            raise BuilderDomainError(ErrorCode.CAMPO_NON_AMMESSO, "Campi duplicati nella versione", status_code=400)
        disponibili = {
            (campo.codice, campo.lingua): campo
            for campo in foglia.campi
        }
        campi_modello: list[ModelloCampoRichiesto] = []
        for richiesto in campi_richiesti:
            chiave = (richiesto.codice, richiesto.lingua)
            sorgente = disponibili.get(chiave)
            if sorgente is None:
                raise BuilderDomainError(
                    ErrorCode.CAMPO_NON_AMMESSO,
                    f"Campo '{richiesto.codice}' ({richiesto.lingua}) non presente nel ramo discovery selezionato",
                    status_code=404,
                )
            campi_modello.append(
                ModelloCampoRichiesto(
                    id=uuid.uuid4(),
                    codice=sorgente.codice,
                    etichetta=sorgente.etichetta,
                    tipo_dato=sorgente.tipo,
                    descrizione=sorgente.descrizione,
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

    def transizione(self, principal: PrincipalGEMODO, versione_id: uuid.UUID, nuovo_stato: str, *, modello_id: uuid.UUID | None = None) -> ModelloDocumentoVersione:
        versione = builder_repository.get_versione(self.db, versione_id)
        if versione is None or (modello_id is not None and versione.modello_documento_id != modello_id):
            raise BuilderDomainError(ErrorCode.MODELLO_VERSIONE_NON_TROVATO, "Versione non trovata", status_code=404)
        modello = builder_repository.get_modello(self.db, versione.modello_documento_id)
        if modello is None:
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)

        # Serialize state changes, including replacement publication, per document type.
        self.db.execute(select(TipoDocumento.id).where(
            TipoDocumento.id == modello.tipo_documento_id,
        ).with_for_update())
        self.db.refresh(versione)
        self.db.refresh(modello)
        if modello.stato == "ELIMINATO":
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)

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
                percorso_categorizzazione=modello.percorso_categorizzazione,
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

    def elimina(self, principal: PrincipalGEMODO, modello_id: uuid.UUID) -> None:
        modello = builder_repository.get_modello(self.db, modello_id)
        if modello is None:
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        verify_scrittura_su_contesto(principal, modello.tipo_documento.codice_contesto)
        self.db.execute(select(TipoDocumento.id).where(TipoDocumento.id == modello.tipo_documento_id).with_for_update())
        self.db.refresh(modello)
        if modello.stato == "ELIMINATO":
            raise BuilderDomainError(ErrorCode.MODELLO_NON_TROVATO, "Modello non trovato", status_code=404)
        modello.stato = "ELIMINATO"
        for versione in modello.versioni:
            self.db.refresh(versione)
            if versione.stato == "PUBBLICATO":
                builder_repository.transizione_stato(self.db, versione, nuovo_stato="ARCHIVIATO")
        registra_evento(self.db, tipo_evento="MODELLO_ELIMINATO", principal=principal,
                       modello_documento_id=modello.id, modello_versione_id=None,
                       payload_minimo={"codice": modello.codice})
        self.db.commit()

    def _resolve_tipo_documento(self, codice_tipo_documento: str):
        tipo = catalog_repository.get_tipo_documento_by_codice(self.db, codice_tipo_documento)
        if tipo is None:
            raise BuilderDomainError(ErrorCode.CONTESTO_NON_VALIDO, "Tipo documento non trovato", status_code=404)
        return tipo


def get_builder_service(db: Session = Depends(get_db)) -> BuilderService:
    return BuilderService(db)
