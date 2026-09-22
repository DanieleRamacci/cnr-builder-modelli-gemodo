"""Policy per dimensione della categorizzazione (DEC-002-POLICY).

Rende configurabile cio' che era scritto a mano nel builder: `lingua` esige
sempre una scelta esplicita, `livello` ammette un generico. La tabella e'
deliberatamente separata da `definizione_struttura` (modulo configurazione,
010), che resta solo l'esempio presentazionale per il team dell'integrazione.

Revision ID: 0018
Revises: 0017
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_dimensione",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tipo_documento_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tipo_documento.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nome_dimensione", sa.String(64), nullable=False),
        sa.Column("consente_valore_generico", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("tipo_documento_id", "nome_dimensione", name="uq_policy_dimensione_tipo_nome"),
    )
    # Il comportamento non deve cambiare al primo deploy: registro per ogni tipo
    # documento esistente le due policy finora implicite nel codice.
    op.execute(
        """
        INSERT INTO policy_dimensione (id, tipo_documento_id, nome_dimensione, consente_valore_generico)
        SELECT gen_random_uuid(), t.id, d.nome, d.generico
        FROM tipo_documento t
        CROSS JOIN (VALUES ('lingua', false), ('livello', true)) AS d(nome, generico)
        ON CONFLICT ON CONSTRAINT uq_policy_dimensione_tipo_nome DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("policy_dimensione")
