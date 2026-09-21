"""Persist the discovery language and professional-level selection on models."""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "modello_documento",
        sa.Column("lingua", sa.String(length=2), nullable=False, server_default="IT"),
    )
    op.add_column(
        "modello_documento",
        sa.Column("livello_professionale", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "ck_modello_documento_lingua",
        "modello_documento",
        "lingua IN ('IT', 'EN')",
    )


def downgrade():
    op.drop_constraint("ck_modello_documento_lingua", "modello_documento", type_="check")
    op.drop_column("modello_documento", "livello_professionale")
    op.drop_column("modello_documento", "lingua")
