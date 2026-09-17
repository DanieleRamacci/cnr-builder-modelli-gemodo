"""Storage/idempotency for generated documents (005, MVP FR-019/020 slice)."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.errors import DomainError
from app.common.security import PrincipalGEMODO, ROLE_DOCUMENTI_VIEWER, verifica_permesso_contesto
from app.core.settings import Settings, get_settings
from app.db.session import get_db
from app.storage import archivio, repository
from app.storage.models import DocumentoGenerato
from app.storage.schemas import StatoDocumento


def _non_trovato() -> DomainError:
    return DomainError("DOCUMENTO_NON_TROVATO", "Documento non trovato", status_code=404)


def hash_dati(dati: dict[str, Any]) -> str:
    normalizzato = json.dumps(dati, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(normalizzato.encode("utf-8")).hexdigest()


def _in_conflitto() -> DomainError:
    return DomainError(
        "RICHIESTA_IDEMPOTENTE_IN_CONFLITTO",
        "Stessa chiave di generazione con dati diversi da una richiesta precedente",
        status_code=409,
    )


def _proietta(documento: DocumentoGenerato) -> StatoDocumento:
    return StatoDocumento(
        riferimento=documento.riferimento, stato=documento.stato, tipo_output=documento.tipo_output,
        nome_file=documento.nome_file, hash_file=documento.hash_file, dimensione_byte=documento.dimensione_byte,
        creato_il=documento.created_at, modello_versione_id=documento.versione.public_id,
        errore_messaggio=documento.errore_messaggio,
    )


class StorageDocumentiService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()

    def esistente_per_chiave(
        self, *, sistema_richiedente: str, external_context_id: str, modello_versione_id: uuid.UUID, hash_richiesta: str,
    ) -> DocumentoGenerato | None:
        """Return the prior generation for this idempotent key, or raise on a data mismatch."""

        esistente = repository.by_chiave(
            self.db, sistema_richiedente=sistema_richiedente, external_context_id=external_context_id,
            modello_versione_id=modello_versione_id,
        )
        if esistente is not None and esistente.hash_dati != hash_richiesta:
            raise _in_conflitto()
        return esistente

    def _inserisci(self, documento: DocumentoGenerato, *, chiave: dict) -> DocumentoGenerato:
        self.db.add(documento)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if getattr(exc.orig, "sqlstate", None) != "23505":
                raise
            # A concurrent request won the race on the same idempotent key; the
            # database (not application logic) arbitrated it.
            vincitore = repository.by_chiave(self.db, **chiave)
            if vincitore is not None and vincitore.hash_dati == documento.hash_dati:
                return vincitore
            raise _in_conflitto() from exc
        return documento

    def registra_successo(
        self, *, sistema_richiedente: str, external_context_id: str, modello_versione_id: uuid.UUID,
        hash_richiesta: str, nome_file: str, contenuto: bytes, creato_da: str,
    ) -> DocumentoGenerato:
        riferimento = uuid.uuid4().hex
        percorso = archivio.salva(riferimento, contenuto, self.settings)
        documento = DocumentoGenerato(
            riferimento=riferimento, sistema_richiedente=sistema_richiedente,
            external_context_id=external_context_id, modello_versione_id=modello_versione_id,
            tipo_output="TEST", stato="COMPLETATO", hash_dati=hash_richiesta, nome_file=nome_file,
            hash_file=hashlib.sha256(contenuto).hexdigest(), percorso_file=str(percorso),
            dimensione_byte=len(contenuto), creato_da=creato_da,
        )
        try:
            return self._inserisci(documento, chiave={
                "sistema_richiedente": sistema_richiedente, "external_context_id": external_context_id,
                "modello_versione_id": modello_versione_id,
            })
        except Exception:
            archivio.rimuovi(percorso)
            raise

    def registra_fallimento(
        self, *, sistema_richiedente: str, external_context_id: str, modello_versione_id: uuid.UUID,
        hash_richiesta: str, nome_file: str, errore_messaggio: str, creato_da: str,
    ) -> DocumentoGenerato:
        documento = DocumentoGenerato(
            riferimento=uuid.uuid4().hex, sistema_richiedente=sistema_richiedente,
            external_context_id=external_context_id, modello_versione_id=modello_versione_id,
            tipo_output="TEST", stato="FALLITO", hash_dati=hash_richiesta, nome_file=nome_file,
            errore_messaggio=errore_messaggio, creato_da=creato_da,
        )
        return self._inserisci(documento, chiave={
            "sistema_richiedente": sistema_richiedente, "external_context_id": external_context_id,
            "modello_versione_id": modello_versione_id,
        })

    def _risolvi_autorizzato(self, riferimento: str, principal: PrincipalGEMODO) -> DocumentoGenerato:
        documento = repository.by_riferimento(self.db, riferimento)
        if documento is None:
            raise _non_trovato()
        codice_contesto = documento.versione.modello.tipo_documento.codice_contesto
        if not verifica_permesso_contesto(principal, codice_contesto, ROLE_DOCUMENTI_VIEWER):
            # A guessed/foreign riferimento (FR-037): identical to "does not exist".
            raise _non_trovato()
        return documento

    def stato(self, riferimento: str, principal: PrincipalGEMODO) -> StatoDocumento:
        return _proietta(self._risolvi_autorizzato(riferimento, principal))

    def contenuto_per_download(self, riferimento: str, principal: PrincipalGEMODO) -> tuple[StatoDocumento, bytes]:
        documento = self._risolvi_autorizzato(riferimento, principal)
        if documento.stato != "COMPLETATO":
            raise DomainError("DOCUMENTO_NON_DISPONIBILE", "Documento non disponibile per il download", status_code=409)
        return _proietta(documento), archivio.leggi(documento.percorso_file)


def get_storage_documenti_service(db: Session = Depends(get_db)) -> StorageDocumentiService:
    return StorageDocumentiService(db)
