"""ORM model for generated-document references (005, MVP FR-019/020 slice)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.catalog.models import Base, ModelloDocumentoVersione


class DocumentoGenerato(Base):
    """Una chiamata a `genera` e il suo esito: il registro delle generazioni (013).

    GEMODO consegna il PDF e non lo conserva: della generazione restano chi,
    quando, per quale chiave e da quale versione del modello, e le impronte
    SHA-256 dei dati ricevuti e del PDF consegnato, che bastano a verificare un
    documento contestato. La stessa chiave si ripete: GEBAN rigenera il bando a
    ogni correzione. `percorso_file` resta solo per le righe di prima.
    """

    __tablename__ = "documento_generato"
    __table_args__ = (
        UniqueConstraint("riferimento", name="uq_documento_generato_riferimento"),
        CheckConstraint(
            "stato IN ('COMPLETATO', 'FALLITO', 'DATI_NON_VALIDI')", name="ck_documento_generato_stato",
        ),
        CheckConstraint(
            "(stato = 'COMPLETATO' AND hash_file IS NOT NULL AND dimensione_byte IS NOT NULL "
            "AND errore_messaggio IS NULL) "
            "OR (stato IN ('FALLITO', 'DATI_NON_VALIDI') AND hash_file IS NULL "
            "AND percorso_file IS NULL AND errore_messaggio IS NOT NULL)",
            name="ck_documento_generato_stato_coerente",
        ),
        Index("ix_documento_generato_hash_file", "hash_file"),
        Index("ix_documento_generato_chiave", "sistema_richiedente", "external_context_id", "modello_versione_id"),
        Index("ix_documento_generato_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    riferimento: Mapped[str] = mapped_column(String(64), nullable=False)
    sistema_richiedente: Mapped[str] = mapped_column(String(128), nullable=False)
    external_context_id: Mapped[str] = mapped_column(String(255), nullable=False)
    modello_versione_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("modello_versione.id"), nullable=False)
    tipo_output: Mapped[str] = mapped_column(String(32), nullable=False, default="TEST", server_default="TEST")
    stato: Mapped[str] = mapped_column(String(16), nullable=False)
    hash_dati: Mapped[str] = mapped_column(String(64), nullable=False)
    nome_file: Mapped[str] = mapped_column(String(255), nullable=False)
    hash_file: Mapped[str | None] = mapped_column(String(64), nullable=True)
    percorso_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    dimensione_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    errore_messaggio: Mapped[str | None] = mapped_column(Text, nullable=True)
    creato_da: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ruoli: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    versione: Mapped[ModelloDocumentoVersione] = relationship()
