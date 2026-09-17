"""Owned discovery examples and integration configuration, not catalog data."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attributo_profilo",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_documento_id", sa.Uuid(), sa.ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("percorso_profilo", JSONB(), nullable=False),
        sa.Column("codice", sa.String(128), nullable=False),
        sa.Column("valori_ammessi", JSONB(), nullable=False),
        sa.Column("valore_default", JSONB(none_as_null=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tipo_documento_id", "percorso_profilo", "codice", name="uq_attributo_profilo_percorso_codice"),
        sa.CheckConstraint("jsonb_typeof(percorso_profilo) = 'array' AND jsonb_array_length(percorso_profilo) > 0", name="ck_attributo_percorso"),
        sa.CheckConstraint("jsonb_typeof(valori_ammessi) = 'array'", name="ck_attributo_valori"),
        sa.CheckConstraint("valore_default IS NULL OR valori_ammessi @> jsonb_build_array(valore_default)", name="ck_attributo_default"),
    )
    op.create_table(
        "schema_discovery_generato",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_documento_id", sa.Uuid(), sa.ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("versione", sa.Integer(), nullable=False),
        sa.Column("contenuto", JSONB(), nullable=False),
        sa.Column("generato_il", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("generato_da", sa.String(255), nullable=False),
        sa.UniqueConstraint("tipo_documento_id", "versione", name="uq_schema_discovery_tipo_versione"),
        sa.UniqueConstraint("id", "tipo_documento_id", name="uq_schema_discovery_id_tipo"),
        sa.CheckConstraint("versione > 0", name="ck_schema_discovery_versione"),
        sa.CheckConstraint("jsonb_typeof(contenuto) = 'object'", name="ck_schema_discovery_contenuto"),
    )
    op.create_table(
        "endpoint_integrazione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_documento_id", sa.Uuid(), sa.ForeignKey("tipo_documento.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="5000"),
        sa.Column("stato", sa.String(32), nullable=False, server_default="DEFINITO"),
        sa.Column("schema_discovery_generato_id_verificato", sa.Uuid(), nullable=True),
        sa.Column("esito_ultimo_test", JSONB(none_as_null=True), nullable=True),
        sa.Column("data_ultimo_test", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tipo_documento_id", name="uq_endpoint_integrazione_tipo"),
        sa.ForeignKeyConstraint(
            ["schema_discovery_generato_id_verificato", "tipo_documento_id"],
            ["schema_discovery_generato.id", "schema_discovery_generato.tipo_documento_id"],
            name="fk_endpoint_schema_tipo",
        ),
        sa.CheckConstraint("stato IN ('DEFINITO', 'CONNESSO', 'ERRORE')", name="ck_endpoint_stato"),
        sa.CheckConstraint("timeout_ms BETWEEN 1000 AND 30000", name="ck_endpoint_timeout"),
        sa.CheckConstraint("stato != 'CONNESSO' OR (schema_discovery_generato_id_verificato IS NOT NULL AND data_ultimo_test IS NOT NULL)", name="ck_endpoint_connesso_verificato"),
    )


def downgrade() -> None:
    op.drop_table("endpoint_integrazione")
    op.drop_table("schema_discovery_generato")
    op.drop_table("attributo_profilo")
