from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.catalog.models import Base


class Integrazione(Base):
    __tablename__ = "integrazione"
    __table_args__ = (
        UniqueConstraint("codice", name="uq_integrazione_codice"),
        UniqueConstraint("id", "codice_contesto", name="uq_integrazione_id_contesto"),
        CheckConstraint("length(btrim(codice)) > 0 AND length(btrim(nome)) > 0 AND length(btrim(codice_contesto)) > 0", name="ck_integrazione_identita"),
        CheckConstraint("revisione > 0", name="ck_integrazione_revisione"),
        CheckConstraint("modalita = 'SINGOLO_ENDPOINT'", name="ck_integrazione_modalita"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codice: Mapped[str] = mapped_column(String(100), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    codice_contesto: Mapped[str] = mapped_column(String(64), nullable=False)
    modalita: Mapped[str] = mapped_column(String(32), nullable=False, default="SINGOLO_ENDPOINT", server_default="SINGOLO_ENDPOINT")
    revisione: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEventoIntegrazione(Base):
    __tablename__ = "audit_evento_integrazione"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(payload_minimo) = 'object'", name="ck_audit_integrazione_payload"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integrazione_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("integrazione.id"), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(64), nullable=False)
    soggetto_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_minimo: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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
        ForeignKeyConstraint(
            ["definizione_struttura_id", "tipo_documento_id"],
            ["definizione_struttura.id", "definizione_struttura.tipo_documento_id"],
            name="fk_schema_definizione",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False)
    versione: Mapped[int] = mapped_column(Integer, nullable=False)
    contenuto: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generato_il: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    generato_da: Mapped[str] = mapped_column(String(255), nullable=False)
    definizione_struttura_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )


class EndpointIntegrazione(Base):
    __tablename__ = "endpoint_integrazione"
    __table_args__ = (
        UniqueConstraint("integrazione_id", name="uq_endpoint_integrazione_software"),
        CheckConstraint("stato IN ('DEFINITO', 'CONNESSO', 'ERRORE')", name="ck_endpoint_software_stato"),
        CheckConstraint("timeout_ms BETWEEN 1000 AND 10000", name="ck_endpoint_software_timeout"),
        CheckConstraint("revisione_verificata IS NULL OR revisione_verificata > 0", name="ck_endpoint_software_revisione"),
        CheckConstraint("esito_ultimo_test IS NULL OR jsonb_typeof(esito_ultimo_test) = 'object'", name="ck_endpoint_software_esito"),
        CheckConstraint("stato = 'DEFINITO' OR (revisione_verificata IS NOT NULL AND versione_contratto_verificata IS NOT NULL AND data_ultimo_test IS NOT NULL AND esito_ultimo_test IS NOT NULL)", name="ck_endpoint_software_verificato"),
        CheckConstraint("(tentativo_id IS NULL) = (tentativo_scadenza IS NULL)", name="ck_endpoint_software_tentativo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integrazione_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("integrazione.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=5000, server_default="5000")
    stato: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFINITO", server_default="DEFINITO")
    revisione_verificata: Mapped[int | None] = mapped_column(Integer, nullable=True)
    versione_contratto_verificata: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tentativo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tentativo_scadenza: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    esito_ultimo_test: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    data_ultimo_test: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DefinizioneStruttura(Base):
    __tablename__ = "definizione_struttura"
    __table_args__ = (
        UniqueConstraint("tipo_documento_id", "versione", name="uq_definizione_tipo_versione"),
        UniqueConstraint("id", "tipo_documento_id", name="uq_definizione_id_tipo"),
        CheckConstraint("versione > 0", name="ck_definizione_versione"),
        CheckConstraint("jsonb_typeof(contenuto) = 'object'", name="ck_definizione_contenuto"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False)
    versione: Mapped[int] = mapped_column(Integer, nullable=False)
    contenuto: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuditEventoConfigurazione(Base):
    __tablename__ = "audit_evento_configurazione"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tipo_documento.id"), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(64), nullable=False)
    soggetto_id: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_minimo: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
