"""Gli eventi che non stanno in un altro registro: validazioni, accessi negati (013)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.catalog.models import Base


class EventoAttivita(Base):
    __tablename__ = "evento_attivita"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(dettaglio) = 'object'", name="ck_evento_attivita_dettaglio"),
        Index("ix_evento_attivita_created_at", "created_at"),
        Index("ix_evento_attivita_soggetto", "soggetto"),
        Index("ix_evento_attivita_categoria", "categoria"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    categoria: Mapped[str] = mapped_column(String(32), nullable=False)
    azione: Mapped[str] = mapped_column(String(64), nullable=False)
    esito: Mapped[str] = mapped_column(String(32), nullable=False)
    soggetto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contesto: Mapped[str | None] = mapped_column(String(64), nullable=True)
    oggetto_tipo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    oggetto_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dettaglio: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
