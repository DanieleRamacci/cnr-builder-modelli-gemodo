"""Repository helpers for the builder admin domain (model/version creation and workflow)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.catalog.models import ModelloCampoRichiesto, ModelloDocumento, ModelloDocumentoVersione, TipoDocumento


def lista_modelli(db: Session, codice_contesto: str, *, offset: int, limit: int):
    return list(db.scalars(select(ModelloDocumento)
        .join(TipoDocumento, ModelloDocumento.tipo_documento_id == TipoDocumento.id)
        .where(TipoDocumento.codice_contesto == codice_contesto, ModelloDocumento.stato != "ELIMINATO")
        .options(joinedload(ModelloDocumento.tipo_documento), selectinload(ModelloDocumento.versioni))
        .order_by(ModelloDocumento.created_at.desc(), ModelloDocumento.id)
        .offset(offset).limit(limit)))


def _prossimo_public_id(db: Session, model) -> int:
    massimo = db.scalar(select(func.max(model.public_id)))
    return (massimo or 0) + 1


def crea_modello(
    db: Session,
    *,
    modello_id: uuid.UUID,
    codice: str,
    nome: str,
    tipo_documento_id: uuid.UUID,
    codice_categoria: str,
    codice_tipologia: str | None,
    percorso_categorizzazione: list[str],
    variante: str,
    lingua: str,
    livello_professionale: str | None,
) -> ModelloDocumento:
    modello = ModelloDocumento(
        id=modello_id,
        public_id=_prossimo_public_id(db, ModelloDocumento),
        tipo_documento_id=tipo_documento_id,
        codice_categoria=codice_categoria,
        codice_tipologia=codice_tipologia,
        percorso_categorizzazione=percorso_categorizzazione,
        codice=codice,
        nome=nome,
        variante=variante,
        lingua=lingua,
        livello_professionale=livello_professionale,
        stato="ATTIVA",
    )
    db.add(modello)
    db.flush()
    return modello


def get_modello(db: Session, modello_id: uuid.UUID) -> ModelloDocumento | None:
    stmt = (
        select(ModelloDocumento)
        .options(
            joinedload(ModelloDocumento.tipo_documento),
        )
        .where(ModelloDocumento.id == modello_id, ModelloDocumento.stato != "ELIMINATO")
    )
    return db.scalar(stmt)


def crea_versione(
    db: Session,
    *,
    modello_documento_id: uuid.UUID,
    campi: list[ModelloCampoRichiesto],
) -> ModelloDocumentoVersione:
    numero_versione = (
        db.scalar(
            select(func.max(ModelloDocumentoVersione.versione)).where(
                ModelloDocumentoVersione.modello_documento_id == modello_documento_id
            )
        )
        or 0
    ) + 1
    versione = ModelloDocumentoVersione(
        id=uuid.uuid4(),
        public_id=_prossimo_public_id(db, ModelloDocumentoVersione),
        modello_documento_id=modello_documento_id,
        versione=numero_versione,
        stato="BOZZA",
        formato_documentale="GEMODO_DOCUMENT_V1",
        struttura_documentale={},
    )
    db.add(versione)
    db.flush()
    for campo in campi:
        campo.modello_versione_id = versione.id
        db.add(campo)
    db.flush()
    return versione


def get_versione(db: Session, versione_id: uuid.UUID) -> ModelloDocumentoVersione | None:
    stmt = (
        select(ModelloDocumentoVersione)
        .options(joinedload(ModelloDocumentoVersione.modello))
        .where(ModelloDocumentoVersione.id == versione_id)
    )
    return db.scalar(stmt)


def get_versione_pubblicata_corrente(
    db: Session,
    *,
    tipo_documento_id: uuid.UUID,
    percorso_categorizzazione: list[str],
    variante: str,
    lingua: str,
    livello_professionale: str | None,
    escludi_versione_id: uuid.UUID,
) -> ModelloDocumentoVersione | None:
    stmt = (
        select(ModelloDocumentoVersione)
        .join(ModelloDocumento, ModelloDocumentoVersione.modello_documento_id == ModelloDocumento.id)
        .where(
            ModelloDocumento.tipo_documento_id == tipo_documento_id,
            ModelloDocumento.percorso_categorizzazione == percorso_categorizzazione,
            ModelloDocumento.variante == variante,
            ModelloDocumento.lingua == lingua,
            ModelloDocumento.livello_professionale == livello_professionale,
            ModelloDocumentoVersione.stato == "PUBBLICATO",
            ModelloDocumentoVersione.id != escludi_versione_id,
        )
    )
    return db.scalar(stmt)


def transizione_stato(
    db: Session,
    versione: ModelloDocumentoVersione,
    *,
    nuovo_stato: str,
) -> ModelloDocumentoVersione:
    versione.stato = nuovo_stato
    versione.updated_at = datetime.now(timezone.utc)
    if nuovo_stato == "PUBBLICATO":
        versione.pubblicato_at = datetime.now(timezone.utc)
        versione.pubblicato_il = datetime.now(timezone.utc)
    db.add(versione)
    db.flush()
    return versione
