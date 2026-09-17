import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import DocumentoGenerato


def by_chiave(
    db: Session, *, sistema_richiedente: str, external_context_id: str, modello_versione_id: uuid.UUID,
) -> DocumentoGenerato | None:
    return db.scalar(select(DocumentoGenerato).where(
        DocumentoGenerato.sistema_richiedente == sistema_richiedente,
        DocumentoGenerato.external_context_id == external_context_id,
        DocumentoGenerato.modello_versione_id == modello_versione_id,
    ))


def by_riferimento(db: Session, riferimento: str) -> DocumentoGenerato | None:
    return db.scalar(select(DocumentoGenerato).where(DocumentoGenerato.riferimento == riferimento))
