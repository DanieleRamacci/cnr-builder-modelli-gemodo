"""Registro delle generazioni (013; prima archivio dei PDF, 005).

GEMODO consegna il PDF e non lo conserva. Di ogni chiamata a `genera` resta una
riga: chi, quando, per quale chiave, da quale versione del modello, con quale
esito, e le impronte dei dati ricevuti e del PDF consegnato. La stessa chiave si
ripete quante volte serve: GEBAN rigenera il bando a ogni correzione.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.common.errors import DomainError
from app.common.security import PrincipalGEMODO
from app.db.session import get_db
from app.storage import repository
from app.storage.models import DocumentoGenerato
from app.storage.schemas import StatoDocumento


def _non_trovato() -> DomainError:
    return DomainError("DOCUMENTO_NON_TROVATO", "Documento non trovato", status_code=404)


def hash_dati(dati: dict[str, Any]) -> str:
    """L'impronta dei dati ricevuti: chiavi ordinate, cosi' l'ordine dei campi non conta."""
    normalizzato = json.dumps(dati, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(normalizzato.encode("utf-8")).hexdigest()


def _proietta(documento: DocumentoGenerato) -> StatoDocumento:
    return StatoDocumento(
        riferimento=documento.riferimento, stato=documento.stato, tipo_output=documento.tipo_output,
        sistema_richiedente=documento.sistema_richiedente,
        external_context_id=documento.external_context_id,
        nome_file=documento.nome_file, hash_dati=documento.hash_dati, hash_file=documento.hash_file,
        dimensione_byte=documento.dimensione_byte, creato_il=documento.created_at,
        creato_da=documento.creato_da, client_id=documento.client_id,
        modello_versione_id=documento.versione.public_id, errore_messaggio=documento.errore_messaggio,
    )


class StorageDocumentiService:
    def __init__(self, db: Session):
        self.db = db

    def registra(
        self, *, stato: str, sistema_richiedente: str, external_context_id: str,
        modello_versione_id: uuid.UUID, hash_richiesta: str, nome_file: str, principal: PrincipalGEMODO,
        contenuto: bytes | None = None, errore_messaggio: str | None = None,
    ) -> DocumentoGenerato:
        """Una riga per chiamata. Se non si scrive, il PDF non si consegna (013 FR-006).

        Un PDF consegnato e non registrato non si potrebbe piu' verificare: meglio
        un errore, che GEBAN ripete, di un documento senza traccia.
        """
        documento = DocumentoGenerato(
            riferimento=uuid.uuid4().hex, sistema_richiedente=sistema_richiedente,
            external_context_id=external_context_id, modello_versione_id=modello_versione_id,
            tipo_output="TEST", stato=stato, hash_dati=hash_richiesta, nome_file=nome_file,
            hash_file=hashlib.sha256(contenuto).hexdigest() if contenuto is not None else None,
            dimensione_byte=len(contenuto) if contenuto is not None else None,
            errore_messaggio=errore_messaggio, creato_da=principal.subject,
            client_id=principal.client_id, username=principal.username or None, ruoli=list(principal.ruoli),
        )
        self.db.add(documento)
        try:
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise DomainError(
                "REGISTRO_GENERAZIONI_NON_DISPONIBILE",
                "Documento non consegnato: la generazione non si e' potuta registrare. Riprovare.",
                status_code=503,
            ) from exc
        return documento

    def stato(self, riferimento: str) -> StatoDocumento:
        """Una generazione per riferimento: solo per gli amministratori (013 FR-017)."""
        documento = repository.by_riferimento(self.db, riferimento)
        if documento is None:
            raise _non_trovato()
        return _proietta(documento)


def get_storage_documenti_service(db: Session = Depends(get_db)) -> StorageDocumentiService:
    return StorageDocumentiService(db)
