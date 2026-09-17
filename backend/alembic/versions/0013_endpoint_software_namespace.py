"""Software-owned endpoints and scoped document codes; legacy history is inert."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("endpoint_integrazione", "endpoint_integrazione_storico")
    op.create_table(
        "endpoint_integrazione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("integrazione_id", sa.Uuid(), sa.ForeignKey("integrazione.id"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="5000"),
        sa.Column("stato", sa.String(32), nullable=False, server_default="DEFINITO"),
        sa.Column("revisione_verificata", sa.Integer(), nullable=True),
        sa.Column("versione_contratto_verificata", sa.String(64), nullable=True),
        sa.Column("tentativo_id", sa.Uuid(), nullable=True),
        sa.Column("tentativo_scadenza", sa.DateTime(timezone=True), nullable=True),
        sa.Column("esito_ultimo_test", JSONB(none_as_null=True), nullable=True),
        sa.Column("data_ultimo_test", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_endpoint_software"),
        sa.UniqueConstraint("integrazione_id", name="uq_endpoint_integrazione_software"),
        sa.CheckConstraint("stato IN ('DEFINITO', 'CONNESSO', 'ERRORE')", name="ck_endpoint_software_stato"),
        sa.CheckConstraint("timeout_ms BETWEEN 1000 AND 10000", name="ck_endpoint_software_timeout"),
        sa.CheckConstraint("revisione_verificata IS NULL OR revisione_verificata > 0", name="ck_endpoint_software_revisione"),
        sa.CheckConstraint("esito_ultimo_test IS NULL OR jsonb_typeof(esito_ultimo_test) = 'object'", name="ck_endpoint_software_esito"),
        sa.CheckConstraint("stato = 'DEFINITO' OR (revisione_verificata IS NOT NULL AND versione_contratto_verificata IS NOT NULL AND data_ultimo_test IS NOT NULL AND esito_ultimo_test IS NOT NULL)", name="ck_endpoint_software_verificato"),
        sa.CheckConstraint("(tentativo_id IS NULL) = (tentativo_scadenza IS NULL)", name="ck_endpoint_software_tentativo"),
    )
    op.drop_constraint("tipo_documento_codice_key", "tipo_documento", type_="unique")
    op.create_unique_constraint("uq_tipo_documento_integrazione_codice", "tipo_documento", ["integrazione_id", "codice"])
    op.create_index("uq_tipo_documento_legacy_codice", "tipo_documento", ["codice"], unique=True, postgresql_where=sa.text("integrazione_id IS NULL"))


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM endpoint_integrazione)
               OR EXISTS (SELECT 1 FROM tipo_documento GROUP BY codice HAVING count(*) > 1)
            THEN
                RAISE EXCEPTION 'Downgrade bloccato: endpoint software o codici duplicati';
            END IF;
        END $$;
    """)
    op.drop_index("uq_tipo_documento_legacy_codice", table_name="tipo_documento")
    op.drop_constraint("uq_tipo_documento_integrazione_codice", "tipo_documento", type_="unique")
    op.create_unique_constraint("tipo_documento_codice_key", "tipo_documento", ["codice"])
    op.drop_table("endpoint_integrazione")
    op.rename_table("endpoint_integrazione_storico", "endpoint_integrazione")
