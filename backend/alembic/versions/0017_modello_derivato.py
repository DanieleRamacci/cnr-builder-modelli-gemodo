"""Link a derived model directly to its source model."""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "modello_documento",
        sa.Column("derivato_da_modello_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_modello_documento_derivato_da",
        "modello_documento",
        "modello_documento",
        ["derivato_da_modello_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_modello_derivato_padre_lingua",
        "modello_documento",
        ["derivato_da_modello_id", "lingua"],
    )
    op.create_check_constraint(
        "ck_modello_derivato_non_autoreferenziale",
        "modello_documento",
        "derivato_da_modello_id IS NULL OR derivato_da_modello_id <> id",
    )


def downgrade():
    op.drop_constraint("ck_modello_derivato_non_autoreferenziale", "modello_documento", type_="check")
    op.drop_constraint("uq_modello_derivato_padre_lingua", "modello_documento", type_="unique")
    op.drop_constraint("fk_modello_documento_derivato_da", "modello_documento", type_="foreignkey")
    op.drop_column("modello_documento", "derivato_da_modello_id")
