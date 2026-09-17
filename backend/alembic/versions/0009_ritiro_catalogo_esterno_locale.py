"""Retire the external local catalog, preserving GEMODO model contracts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("modello_documento", sa.Column("codice_categoria", sa.String(128)))
    op.add_column("modello_documento", sa.Column("codice_tipologia", sa.String(128)))
    op.add_column("modello_documento", sa.Column("percorso_categorizzazione", postgresql.JSONB()))
    op.execute("""
        UPDATE modello_documento m
        SET codice_categoria = c.codice,
            codice_tipologia = t.codice,
            percorso_categorizzazione = jsonb_build_array(t.codice, c.codice)
        FROM categoria_documento c, tipologia_bando_sol t
        WHERE m.categoria_documento_id = c.id AND m.tipologia_bando_sol_id = t.id
    """)
    op.execute("""
        UPDATE modello_documento m
        SET codice_categoria = c.codice,
            percorso_categorizzazione = jsonb_build_array(c.codice)
        FROM categoria_documento c
        WHERE m.categoria_documento_id = c.id AND m.tipologia_bando_sol_id IS NULL
    """)
    op.alter_column("modello_documento", "codice_categoria", nullable=False)
    op.alter_column("modello_documento", "percorso_categorizzazione", nullable=False)
    op.drop_column("modello_documento", "categoria_documento_id")
    op.drop_column("modello_documento", "tipologia_bando_sol_id")
    op.drop_column("tipo_documento", "tipologia_bando_sol_id")
    op.drop_table("classificazione_catalogo")
    op.drop_table("tipologia_bando")
    op.drop_table("categoria_documento")
    op.drop_table("tipologia_bando_sol")
    op.drop_table("registro_contratti_dati")


def downgrade() -> None:
    raise RuntimeError("Catalogo esterno eliminato: rollback richiede ripristino del backup pre-0009")
