"""Read GEMODO-owned model versions, not an external classification mirror."""

from __future__ import annotations

from collections.abc import Collection
from datetime import date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento
from app.common.errors import DomainError

# 011 T054: uniformato al nome della colonna sostituita e del campo di contratto.
NOME_LIVELLO = "livello_professionale"

STATO_ATTIVO = "ATTIVA"
STATO_PUBBLICATO = "PUBBLICATO"


def get_tipo_documento_by_codice(db: Session, codice: str) -> TipoDocumento | None:
    # Only ATTIVA candidates compete for ambiguity: a BOZZA/abandoned onboarding
    # draft sharing the same codice (e.g. an incomplete admin-side definition
    # left next to the real builder-provisioned one) must never block a
    # catalog read that has exactly one real, usable source.
    types = list(
        db.scalars(
            select(TipoDocumento)
            .where(TipoDocumento.codice == codice, TipoDocumento.stato == STATO_ATTIVO)
            .limit(2)
        )
    )
    if len(types) > 1:
        raise DomainError("SORGENTE_AMBIGUA", "Indicare l'integrazione del tipo documento", status_code=409)
    return types[0] if types else None


def list_tipi_documento_attivi_by_codice(db: Session, codice: str) -> list[TipoDocumento]:
    return list(db.scalars(
        select(TipoDocumento)
        .where(TipoDocumento.codice == codice, TipoDocumento.stato == STATO_ATTIVO)
        .order_by(TipoDocumento.created_at, TipoDocumento.id)
    ))


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _day_end(value: date) -> datetime:
    return datetime.combine(value, time.max)


def list_published_model_versions(
    db: Session,
    *,
    codice_tipo_documento: str | None = None,
    tipo_documento_id: UUID | None = None,
    tipo_documento_ids: Collection[UUID] | None = None,
    codice_categoria: str | None = None,
    codice_tipologia: str | None = None,
    lingua: str | None = None,
    livello_professionale: str | None = None,
    solo_livello_generico: bool = False,
    # 011 FR-010: filtri per dimensione arbitraria. `dimensioni` richiede un
    # valore preciso, `dimensioni_generiche` richiede che la dimensione NON sia
    # valorizzata - e' cosi' che il fallback rilassa una dimensione alla volta.
    dimensioni: dict[str, str] | None = None,
    dimensioni_generiche: Collection[str] | None = None,
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
    if tipo_documento_ids is not None:
        stmt = stmt.where(TipoDocumento.id.in_(tipo_documento_ids))
    if codice_categoria:
        stmt = stmt.where(ModelloDocumento.codice_categoria == codice_categoria)
    if codice_tipologia:
        stmt = stmt.where(ModelloDocumento.codice_tipologia == codice_tipologia)
    if lingua:
        stmt = stmt.where(ModelloDocumento.dimensioni["lingua"].astext == lingua)
    if solo_livello_generico:
        # "generico" per una dimensione e' l'assenza della chiave: con le colonne
        # era `IS NULL` (011 FR-006).
        stmt = stmt.where(~ModelloDocumento.dimensioni.has_key(NOME_LIVELLO))  # noqa: W601 - operatore JSONB
    elif livello_professionale:
        stmt = stmt.where(ModelloDocumento.dimensioni[NOME_LIVELLO].astext == livello_professionale)
    for nome, valore in (dimensioni or {}).items():
        stmt = stmt.where(ModelloDocumento.dimensioni[nome].astext == valore)
    for nome in (dimensioni_generiche or ()):
        stmt = stmt.where(~ModelloDocumento.dimensioni.has_key(nome))  # noqa: W601 - operatore JSONB
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
