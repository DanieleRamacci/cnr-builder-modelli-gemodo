"""Read GEMODO-owned model versions, not an external classification mirror."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.common.errors import DomainError

STATO_ATTIVO = "ATTIVA"
STATO_PUBBLICATO = "PUBBLICATO"


def get_tipo_documento_by_codice(db: Session, codice: str) -> TipoDocumento | None:
    types = list(db.scalars(select(TipoDocumento).where(TipoDocumento.codice == codice).limit(2)))
    if len(types) > 1:
        raise DomainError("SORGENTE_AMBIGUA", "Indicare l'integrazione del tipo documento", status_code=409)
    return types[0] if types else None


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _day_end(value: date) -> datetime:
    return datetime.combine(value, time.max)


def list_published_model_versions(
    db: Session,
    *,
    codice_tipo_documento: str | None = None,
    tipo_documento_id: UUID | None = None,
    codice_categoria: str | None = None,
    codice_tipologia: str | None = None,
    historical: bool = False,
    data_riferimento: date | None = None,
    pubblicato_da: date | None = None,
    pubblicato_a: date | None = None,
) -> list[ModelloDocumentoVersione]:
    stmt = (
        select(ModelloDocumentoVersione)
        .where(ModelloDocumentoVersione.stato == STATO_PUBBLICATO)
        .options(joinedload(ModelloDocumentoVersione.modello).joinedload(ModelloDocumento.tipo_documento))
        .join(ModelloDocumento, ModelloDocumentoVersione.modello_documento_id == ModelloDocumento.id)
        .where(ModelloDocumento.stato != "ELIMINATO")
        .join(TipoDocumento, ModelloDocumento.tipo_documento_id == TipoDocumento.id)
        .order_by(TipoDocumento.codice, ModelloDocumento.codice_categoria,
                  ModelloDocumento.codice, ModelloDocumentoVersione.versione)
    )
    if not historical:
        at = data_riferimento or date.today()
        stmt = stmt.where(
            ModelloDocumentoVersione.data_inizio_validita.is_(None)
            | (ModelloDocumentoVersione.data_inizio_validita <= _day_end(at)),
            ModelloDocumentoVersione.data_fine_validita.is_(None)
            | (ModelloDocumentoVersione.data_fine_validita >= _day_start(at)),
        )
    if historical and pubblicato_da is not None:
        stmt = stmt.where(ModelloDocumentoVersione.pubblicato_at >= _day_start(pubblicato_da))
    if historical and pubblicato_a is not None:
        stmt = stmt.where(ModelloDocumentoVersione.pubblicato_at <= _day_end(pubblicato_a))
    if codice_tipo_documento:
        stmt = stmt.where(TipoDocumento.codice == codice_tipo_documento)
    if tipo_documento_id is not None:
        stmt = stmt.where(TipoDocumento.id == tipo_documento_id)
    if codice_categoria:
        stmt = stmt.where(ModelloDocumento.codice_categoria == codice_categoria)
    if codice_tipologia:
        stmt = stmt.where(ModelloDocumento.codice_tipologia == codice_tipologia)
    return list(db.scalars(stmt))


def get_model_version(db: Session, modello_versione_id: UUID) -> ModelloDocumentoVersione | None:
    return db.get(ModelloDocumentoVersione, modello_versione_id)


def get_model_version_by_public_id(db: Session, modello_versione_id: int) -> ModelloDocumentoVersione | None:
    stmt = (
        select(ModelloDocumentoVersione)
        .options(joinedload(ModelloDocumentoVersione.modello).joinedload(ModelloDocumento.tipo_documento))
        .where(ModelloDocumentoVersione.public_id == modello_versione_id)
    )
    return db.scalar(stmt)


def list_required_fields(db: Session, modello_versione_id: UUID) -> list[ModelloCampoRichiesto]:
    stmt = (
        select(ModelloCampoRichiesto)
        .where(ModelloCampoRichiesto.modello_versione_id == modello_versione_id)
        .order_by(ModelloCampoRichiesto.ordine, ModelloCampoRichiesto.codice, ModelloCampoRichiesto.lingua)
    )
    return list(db.scalars(stmt))
