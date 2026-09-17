"""Generated-document references for storage/idempotency (005, MVP FR-019/020 slice)."""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documento_generato",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("riferimento", sa.String(64), nullable=False),
        sa.Column("sistema_richiedente", sa.String(128), nullable=False),
        sa.Column("external_context_id", sa.String(255), nullable=False),
        sa.Column("modello_versione_id", sa.Uuid(), sa.ForeignKey("modello_versione.id"), nullable=False),
        sa.Column("tipo_output", sa.String(32), nullable=False, server_default="TEST"),
        sa.Column("stato", sa.String(16), nullable=False),
        sa.Column("hash_dati", sa.String(64), nullable=False),
        sa.Column("nome_file", sa.String(255), nullable=False),
        sa.Column("hash_file", sa.String(64), nullable=True),
        sa.Column("percorso_file", sa.String(512), nullable=True),
        sa.Column("dimensione_byte", sa.Integer(), nullable=True),
        sa.Column("errore_messaggio", sa.Text(), nullable=True),
        sa.Column("creato_da", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("riferimento", name="uq_documento_generato_riferimento"),
        sa.UniqueConstraint(
            "sistema_richiedente", "external_context_id", "modello_versione_id",
            name="uq_documento_generato_chiave_idempotente",
        ),
        sa.CheckConstraint("stato IN ('COMPLETATO', 'FALLITO')", name="ck_documento_generato_stato"),
        sa.CheckConstraint(
            "(stato = 'COMPLETATO' AND hash_file IS NOT NULL AND percorso_file IS NOT NULL "
            "AND dimensione_byte IS NOT NULL AND errore_messaggio IS NULL) "
            "OR (stato = 'FALLITO' AND hash_file IS NULL AND percorso_file IS NULL AND errore_messaggio IS NOT NULL)",
            name="ck_documento_generato_stato_coerente",
        ),
    )


def downgrade() -> None:
    op.drop_table("documento_generato")
