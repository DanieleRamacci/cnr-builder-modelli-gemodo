"""SQLAlchemy models for catalog and data-contract entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TipoDocumento(Base):
    __tablename__ = "tipo_documento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codice: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="BOZZA")
    spec_owner: Mapped[str] = mapped_column(String(128), nullable=False)
    tipologia_bando_sol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipologia_bando_sol.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    categorie: Mapped[list[CategoriaDocumento]] = relationship(back_populates="tipo_documento")
    modelli: Mapped[list[ModelloDocumento]] = relationship(back_populates="tipo_documento")


class CategoriaDocumento(Base):
    __tablename__ = "categoria_documento"
    __table_args__ = (UniqueConstraint("tipo_documento_id", "codice", name="uq_categoria_documento_tipo_codice"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False
    )
    codice: Mapped[str] = mapped_column(String(64), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="ATTIVA")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tipo_documento: Mapped[TipoDocumento] = relationship(back_populates="categorie")
    modelli: Mapped[list[ModelloDocumento]] = relationship(back_populates="categoria_documento")


class TipologiaBandoSOL(Base):
    __tablename__ = "tipologia_bando_sol"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codice: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    codice_sol: Mapped[str] = mapped_column(String(128), nullable=False)
    descrizione: Mapped[str] = mapped_column(String(255), nullable=False)
    attiva: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    modelli: Mapped[list[ModelloDocumento]] = relationship(back_populates="tipologia_bando_sol")


class ModelloDocumento(Base):
    __tablename__ = "modello_documento"
    __table_args__ = (UniqueConstraint("tipo_documento_id", "codice", name="uq_modello_documento_tipo_codice"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False
    )
    categoria_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categoria_documento.id", ondelete="CASCADE"), nullable=False
    )
    tipologia_bando_sol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tipologia_bando_sol.id", ondelete="SET NULL"), nullable=True
    )
    public_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    codice: Mapped[str] = mapped_column(String(128), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    variante: Mapped[str] = mapped_column(String(64), nullable=False, default="STANDARD")
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="BOZZA")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tipo_documento: Mapped[TipoDocumento] = relationship(back_populates="modelli")
    categoria_documento: Mapped[CategoriaDocumento] = relationship(back_populates="modelli")
    tipologia_bando_sol: Mapped[TipologiaBandoSOL | None] = relationship(back_populates="modelli")
    versioni: Mapped[list[ModelloDocumentoVersione]] = relationship(back_populates="modello")


class ModelloDocumentoVersione(Base):
    __tablename__ = "modello_versione"
    __table_args__ = (
        UniqueConstraint("modello_documento_id", "versione", name="uq_modello_versione_documento_versione"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    modello_documento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_documento.id", ondelete="CASCADE"), nullable=False
    )
    versione: Mapped[int] = mapped_column(Integer, nullable=False)
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="BOZZA")
    formato_documentale: Mapped[str] = mapped_column(String(64), nullable=False, default="GEMODO_DOCUMENT_V1")
    struttura_documentale: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    data_inizio_validita: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_fine_validita: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pubblicato_il: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pubblicato_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    modello: Mapped[ModelloDocumento] = relationship(back_populates="versioni")
    campi: Mapped[list[ModelloCampoRichiesto]] = relationship(back_populates="versione_modello")


class ModelloCampoRichiesto(Base):
    __tablename__ = "campo_modello"
    __table_args__ = (
        UniqueConstraint("modello_versione_id", "codice", "lingua", name="uq_campo_modello_versione_codice_lingua"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    modello_versione_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("modello_versione.id", ondelete="CASCADE"), nullable=False
    )
    codice: Mapped[str] = mapped_column(String(128), nullable=False)
    etichetta: Mapped[str] = mapped_column(String(255), nullable=False)
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_dato: Mapped[str] = mapped_column(String(32), nullable=False)
    obbligatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lingua: Mapped[str] = mapped_column(String(8), nullable=False, default="IT")
    ordine: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    formato: Mapped[str | None] = mapped_column(String(64), nullable=True)
    valore_default: Mapped[str | None] = mapped_column(Text, nullable=True)
    opzioni: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validazione: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    versione_modello: Mapped[ModelloDocumentoVersione] = relationship(back_populates="campi")
