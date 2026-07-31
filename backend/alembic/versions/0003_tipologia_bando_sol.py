"""add GEBAN/SOL typology registry

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tipologia_bando_sol",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("codice", sa.String(32), nullable=False, unique=True),
        sa.Column("codice_sol", sa.String(128), nullable=False),
        sa.Column("descrizione", sa.String(255), nullable=False),
        sa.Column("attiva", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE tipo_documento ADD COLUMN IF NOT EXISTS tipologia_bando_sol_id uuid")
    op.execute("ALTER TABLE modello_documento ADD COLUMN IF NOT EXISTS tipologia_bando_sol_id uuid")
    op.create_foreign_key(
        "fk_tipo_documento_tipologia_bando_sol",
        "tipo_documento",
        "tipologia_bando_sol",
        ["tipologia_bando_sol_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_modello_documento_tipologia_bando_sol",
        "modello_documento",
        "tipologia_bando_sol",
        ["tipologia_bando_sol_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_modello_documento_tipologia_bando_sol", "modello_documento", type_="foreignkey")
    op.drop_constraint("fk_tipo_documento_tipologia_bando_sol", "tipo_documento", type_="foreignkey")
    op.execute("ALTER TABLE modello_documento DROP COLUMN IF EXISTS tipologia_bando_sol_id")
    op.execute("ALTER TABLE tipo_documento DROP COLUMN IF EXISTS tipologia_bando_sol_id")
    op.drop_table("tipologia_bando_sol")
