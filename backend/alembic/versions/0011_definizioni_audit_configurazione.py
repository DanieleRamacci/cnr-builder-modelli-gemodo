"""Versioned owned examples and configuration audit."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "definizione_struttura",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_documento_id", sa.Uuid(), sa.ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("versione", sa.Integer(), nullable=False),
        sa.Column("contenuto", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tipo_documento_id", "versione", name="uq_definizione_tipo_versione"),
        sa.UniqueConstraint("id", "tipo_documento_id", name="uq_definizione_id_tipo"),
        sa.CheckConstraint("versione > 0", name="ck_definizione_versione"),
        sa.CheckConstraint("jsonb_typeof(contenuto) = 'object'", name="ck_definizione_contenuto"),
    )
    op.add_column("schema_discovery_generato", sa.Column("definizione_struttura_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_schema_definizione", "schema_discovery_generato", "definizione_struttura", ["definizione_struttura_id", "tipo_documento_id"], ["id", "tipo_documento_id"])
    op.create_table(
        "audit_evento_configurazione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_documento_id", sa.Uuid(), sa.ForeignKey("tipo_documento.id"), nullable=False),
        sa.Column("tipo_evento", sa.String(64), nullable=False),
        sa.Column("soggetto_id", sa.String(255), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("payload_minimo", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_evento_configurazione")
    op.drop_constraint("fk_schema_definizione", "schema_discovery_generato", type_="foreignkey")
    op.drop_column("schema_discovery_generato", "definizione_struttura_id")
    op.drop_table("definizione_struttura")
