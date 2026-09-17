from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.catalog.models import Base


class AttributoProfilo(Base):
    """Attribute in the owned integration example, not in the external catalog."""

    __tablename__ = "attributo_profilo"
    __table_args__ = (
        UniqueConstraint("tipo_documento_id", "percorso_profilo", "codice", name="uq_attributo_profilo_percorso_codice"),
        CheckConstraint("jsonb_typeof(percorso_profilo) = 'array' AND jsonb_array_length(percorso_profilo) > 0", name="ck_attributo_percorso"),
        CheckConstraint("jsonb_typeof(valori_ammessi) = 'array'", name="ck_attributo_valori"),
        CheckConstraint("valore_default IS NULL OR valori_ammessi @> jsonb_build_array(valore_default)", name="ck_attributo_default"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False)
    percorso_profilo: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    codice: Mapped[str] = mapped_column(String(128), nullable=False)
    valori_ammessi: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    valore_default: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SchemaDiscoveryGenerato(Base):
    __tablename__ = "schema_discovery_generato"
    __table_args__ = (
        UniqueConstraint("tipo_documento_id", "versione", name="uq_schema_discovery_tipo_versione"),
        UniqueConstraint("id", "tipo_documento_id", name="uq_schema_discovery_id_tipo"),
        CheckConstraint("versione > 0", name="ck_schema_discovery_versione"),
        CheckConstraint("jsonb_typeof(contenuto) = 'object'", name="ck_schema_discovery_contenuto"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False)
    versione: Mapped[int] = mapped_column(Integer, nullable=False)
    contenuto: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    generato_da: Mapped[str] = mapped_column(String(255), nullable=False)


class EndpointIntegrazione(Base):
    __tablename__ = "endpoint_integrazione"
    __table_args__ = (
        UniqueConstraint("tipo_documento_id", name="uq_endpoint_integrazione_tipo"),
        ForeignKeyConstraint(
            ["schema_discovery_generato_id_verificato", "tipo_documento_id"],
            ["schema_discovery_generato.id", "schema_discovery_generato.tipo_documento_id"],
            name="fk_endpoint_schema_tipo",
        ),
        CheckConstraint("stato IN ('DEFINITO', 'CONNESSO', 'ERRORE')", name="ck_endpoint_stato"),
        CheckConstraint("timeout_ms BETWEEN 1000 AND 30000", name="ck_endpoint_timeout"),
        CheckConstraint("stato != 'CONNESSO' OR (schema_discovery_generato_id_verificato IS NOT NULL AND data_ultimo_test IS NOT NULL)", name="ck_endpoint_connesso_verificato"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=5000, server_default="5000")
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFINITO", server_default="DEFINITO")
    schema_discovery_generato_id_verificato: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    esito_ultimo_test: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    data_ultimo_test: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
