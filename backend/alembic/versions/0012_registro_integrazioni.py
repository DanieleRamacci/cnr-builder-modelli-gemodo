"""Empty software registry and explicit ownership, without external catalog data."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integrazione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("codice", sa.String(100), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("codice_contesto", sa.String(64), nullable=False),
        sa.Column("modalita", sa.String(32), nullable=False, server_default="SINGOLO_ENDPOINT"),
        sa.Column("revisione", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("codice", name="uq_integrazione_codice"),
        sa.UniqueConstraint("id", "codice_contesto", name="uq_integrazione_id_contesto"),
        sa.CheckConstraint("length(btrim(codice)) > 0 AND length(btrim(nome)) > 0 AND length(btrim(codice_contesto)) > 0", name="ck_integrazione_identita"),
        sa.CheckConstraint("revisione > 0", name="ck_integrazione_revisione"),
        sa.CheckConstraint("modalita = 'SINGOLO_ENDPOINT'", name="ck_integrazione_modalita"),
    )
    op.create_table(
        "audit_evento_integrazione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("integrazione_id", sa.Uuid(), sa.ForeignKey("integrazione.id"), nullable=False),
        sa.Column("tipo_evento", sa.String(64), nullable=False),
        sa.Column("soggetto_id", sa.String(255), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("payload_minimo", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("jsonb_typeof(payload_minimo) = 'object'", name="ck_audit_integrazione_payload"),
    )
    op.add_column("tipo_documento", sa.Column("integrazione_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_tipo_integrazione_contesto", "tipo_documento", "integrazione",
        ["integrazione_id", "codice_contesto"], ["id", "codice_contesto"],
    )


def downgrade() -> None:
    # Refuse destructive rollback even when emitted as an offline SQL script.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM integrazione)
               OR EXISTS (SELECT 1 FROM audit_evento_integrazione)
               OR EXISTS (SELECT 1 FROM tipo_documento WHERE integrazione_id IS NOT NULL)
            THEN
                RAISE EXCEPTION 'Downgrade bloccato: registro integrazioni non vuoto';
            END IF;
        END $$;
    """)
    op.drop_constraint("fk_tipo_integrazione_contesto", "tipo_documento", type_="foreignkey")
    op.drop_column("tipo_documento", "integrazione_id")
    op.drop_table("audit_evento_integrazione")
    op.drop_table("integrazione")
