from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import DocumentoGenerato


def by_riferimento(db: Session, riferimento: str) -> DocumentoGenerato | None:
    return db.scalar(select(DocumentoGenerato).where(DocumentoGenerato.riferimento == riferimento))
