"""initial schema baseline

Provisional baseline schema covering the entities FR-009 requires (tipi, categorie,
modelli, versioni, campi, sezioni, generazioni documento e audit). Column shapes are
intentionally minimal: the definitive contract for each entity belongs to its owner
spec (see backend/alembic/README.md) and several related decisions are still open
(docs/decision-register.yaml once populated by User Story 3, spec.md "Decision
Ownership"). This migration only guarantees a working, queryable starting point.

Revision ID: 0001
Revises:
Create Date: 2026-07-29
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tipo_documento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("codice", sa.String(64), nullable=False, unique=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("stato", sa.String(32), nullable=False, server_default="BOZZA"),
        sa.Column("spec_owner", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "categoria_documento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tipo_documento_id",
            sa.Uuid(),
            sa.ForeignKey("tipo_documento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codice", sa.String(64), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("stato", sa.String(32), nullable=False, server_default="ATTIVA"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tipo_documento_id", "codice", name="uq_categoria_documento_tipo_codice"),
    )

    op.create_table(
        "tipologia_bando",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "categoria_documento_id",
            sa.Uuid(),
            sa.ForeignKey("categoria_documento.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("codice", sa.String(32), nullable=False, unique=True),
        sa.Column("codice_sol", sa.String(128), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("stato", sa.String(32), nullable=False, server_default="ATTIVA"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "modello_documento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "tipo_documento_id",
            sa.Uuid(),
            sa.ForeignKey("tipo_documento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "categoria_documento_id",
            sa.Uuid(),
            sa.ForeignKey("categoria_documento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codice", sa.String(128), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("stato", sa.String(32), nullable=False, server_default="BOZZA"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tipo_documento_id", "codice", name="uq_modello_documento_tipo_codice"),
    )

    op.create_table(
        "modello_versione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "modello_documento_id",
            sa.Uuid(),
            sa.ForeignKey("modello_documento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("versione", sa.Integer(), nullable=False),
        sa.Column("stato", sa.String(32), nullable=False, server_default="BOZZA"),
        sa.Column("formato_documentale", sa.String(64), nullable=False, server_default="GEMODO_DOCUMENT_V1"),
        sa.Column("struttura_documentale", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("pubblicato_il", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("modello_documento_id", "versione", name="uq_modello_versione_documento_versione"),
    )

    op.create_table(
        "campo_modello",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "modello_versione_id",
            sa.Uuid(),
            sa.ForeignKey("modello_versione.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codice", sa.String(128), nullable=False),
        sa.Column("etichetta", sa.String(255), nullable=False),
        sa.Column("tipo_dato", sa.String(32), nullable=False),
        sa.Column("obbligatorio", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lingua", sa.String(8), nullable=False, server_default="IT"),
        sa.Column("ordine", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "modello_versione_id", "codice", "lingua", name="uq_campo_modello_versione_codice_lingua"
        ),
    )

    op.create_table(
        "sezione_modello",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "modello_versione_id",
            sa.Uuid(),
            sa.ForeignKey("modello_versione.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("codice", sa.String(128), nullable=False),
        sa.Column("ordine", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contenuto", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("modello_versione_id", "codice", name="uq_sezione_modello_versione_codice"),
    )

    op.create_table(
        "generazione_documento",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "modello_versione_id",
            sa.Uuid(),
            sa.ForeignKey("modello_versione.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sistema_richiedente", sa.String(64), nullable=False),
        sa.Column("external_context_id", sa.String(255), nullable=False),
        sa.Column("tipo_output", sa.String(32), nullable=False),
        sa.Column("stato", sa.String(32), nullable=False, server_default="IN_CORSO"),
        sa.Column("payload_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("riferimento_documento", sa.String(255), nullable=True),
        sa.Column("hash_file", sa.String(128), nullable=True),
        sa.Column("richiesto_da", sa.String(255), nullable=False),
        sa.Column("creato_il", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completato_il", sa.DateTime(timezone=True), nullable=True),
        # Idempotency key (constitution principle IV): stessa combinazione di sistema
        # richiedente, external context id, versione modello e tipo output deve
        # restituire la stessa generazione, non crearne una nuova.
        sa.UniqueConstraint(
            "sistema_richiedente",
            "external_context_id",
            "modello_versione_id",
            "tipo_output",
            name="uq_generazione_documento_chiave_idempotenza",
        ),
    )

    op.create_table(
        "evento_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_evento", sa.String(64), nullable=False),
        sa.Column("entita_tipo", sa.String(64), nullable=False),
        sa.Column("entita_id", sa.Uuid(), nullable=True),
        sa.Column("esito", sa.String(32), nullable=False),
        sa.Column("dettaglio", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attore", sa.String(255), nullable=True),
        sa.Column("creato_il", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evento_audit_entita", "evento_audit", ["entita_tipo", "entita_id"])


def downgrade() -> None:
    op.drop_index("ix_evento_audit_entita", table_name="evento_audit")
    op.drop_table("evento_audit")
    op.drop_table("generazione_documento")
    op.drop_table("sezione_modello")
    op.drop_table("campo_modello")
    op.drop_table("modello_versione")
    op.drop_table("modello_documento")
    op.drop_table("tipologia_bando")
    op.drop_table("categoria_documento")
    op.drop_table("tipo_documento")
