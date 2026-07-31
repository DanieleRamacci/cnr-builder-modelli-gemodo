"""Repository helpers for catalog reads."""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.catalog.models import (
    CategoriaDocumento,
    ModelloCampoRichiesto,
    ModelloDocumento,
    ModelloDocumentoVersione,
    TipoDocumento,
    TipologiaBandoSOL,
)


STATO_ATTIVO = "ATTIVA"
STATO_PUBBLICATO = "PUBBLICATO"


def list_tipi_documento(db: Session) -> list[TipoDocumento]:
    return list(db.scalars(select(TipoDocumento).order_by(TipoDocumento.codice)))


def get_tipo_documento_by_codice(db: Session, codice: str) -> TipoDocumento | None:
    return db.scalar(select(TipoDocumento).where(TipoDocumento.codice == codice))


def list_categorie_by_tipo_codice(db: Session, codice_tipo_documento: str) -> list[CategoriaDocumento]:
    stmt = (
        select(CategoriaDocumento)
        .join(TipoDocumento, CategoriaDocumento.tipo_documento_id == TipoDocumento.id)
        .where(TipoDocumento.codice == codice_tipo_documento)
        .order_by(CategoriaDocumento.codice)
    )
    return list(db.scalars(stmt))


def get_tipologia_sol_by_codice(db: Session, codice: str) -> TipologiaBandoSOL | None:
    return db.scalar(select(TipologiaBandoSOL).where(TipologiaBandoSOL.codice == codice, TipologiaBandoSOL.attiva.is_(True)))


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _day_end(value: date) -> datetime:
    return datetime.combine(value, time.max)


def _published_versions_stmt(
    *,
    historical: bool = False,
    data_riferimento: date | None = None,
    pubblicato_da: date | None = None,
    pubblicato_a: date | None = None,
) -> Select[tuple[ModelloDocumentoVersione]]:
    stmt = select(ModelloDocumentoVersione).where(ModelloDocumentoVersione.stato == STATO_PUBBLICATO)
    if not historical:
        at = data_riferimento or date.today()
        stmt = stmt.where(
            (
                ModelloDocumentoVersione.data_inizio_validita.is_(None)
                | (ModelloDocumentoVersione.data_inizio_validita <= _day_end(at))
            ),
            (
                ModelloDocumentoVersione.data_fine_validita.is_(None)
                | (ModelloDocumentoVersione.data_fine_validita >= _day_start(at))
            ),
        )
    if historical and pubblicato_da is not None:
        stmt = stmt.where(ModelloDocumentoVersione.pubblicato_at >= _day_start(pubblicato_da))
    if historical and pubblicato_a is not None:
        stmt = stmt.where(ModelloDocumentoVersione.pubblicato_at <= _day_end(pubblicato_a))
    return stmt


def list_published_model_versions(
    db: Session,
    *,
    codice_tipo_documento: str | None = None,
    codice_categoria: str | None = None,
    codice_tipologia: str | None = None,
    historical: bool = False,
    data_riferimento: date | None = None,
    pubblicato_da: date | None = None,
    pubblicato_a: date | None = None,
) -> list[ModelloDocumentoVersione]:
    stmt = (
        _published_versions_stmt(
            historical=historical,
            data_riferimento=data_riferimento,
            pubblicato_da=pubblicato_da,
            pubblicato_a=pubblicato_a,
        )
        .options(
            joinedload(ModelloDocumentoVersione.modello).joinedload(ModelloDocumento.tipo_documento),
            joinedload(ModelloDocumentoVersione.modello).joinedload(ModelloDocumento.categoria_documento),
            joinedload(ModelloDocumentoVersione.modello).joinedload(ModelloDocumento.tipologia_bando_sol),
        )
        .join(ModelloDocumento, ModelloDocumentoVersione.modello_documento_id == ModelloDocumento.id)
        .join(TipoDocumento, ModelloDocumento.tipo_documento_id == TipoDocumento.id)
        .join(CategoriaDocumento, ModelloDocumento.categoria_documento_id == CategoriaDocumento.id)
        .order_by(TipoDocumento.codice, CategoriaDocumento.codice, ModelloDocumento.codice, ModelloDocumentoVersione.versione)
    )
    if codice_tipo_documento:
        stmt = stmt.where(TipoDocumento.codice == codice_tipo_documento)
    if codice_categoria:
        stmt = stmt.where(CategoriaDocumento.codice == codice_categoria)
    if codice_tipologia:
        stmt = stmt.join(TipologiaBandoSOL, ModelloDocumento.tipologia_bando_sol_id == TipologiaBandoSOL.id).where(
            TipologiaBandoSOL.codice == codice_tipologia
        )
    return list(db.scalars(stmt))


def get_model_version(db: Session, modello_versione_id: UUID) -> ModelloDocumentoVersione | None:
    return db.get(ModelloDocumentoVersione, modello_versione_id)


def get_model_version_by_public_id(db: Session, modello_versione_id: int) -> ModelloDocumentoVersione | None:
    stmt = (
        select(ModelloDocumentoVersione)
        .options(
            joinedload(ModelloDocumentoVersione.modello).joinedload(ModelloDocumento.tipo_documento),
            joinedload(ModelloDocumentoVersione.modello).joinedload(ModelloDocumento.categoria_documento),
        )
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
