"""Modello multiplo e sotto-campi dei campi ripetibili (014 T005).

Un bando con piu' articolazioni ha un modello **multiplo**, separato dal
modello singolo della stessa categorizzazione (014 FR-009f). `multiplo` entra
quindi nello slot che identifica un modello: senza, i due occuperebbero lo
stesso posto e la pubblicazione dell'uno archivierebbe l'altro.

I sotto-campi di un campo ripetibile (es. le colonne di ogni articolazione)
si salvano dentro la riga del campo, in `sotto_campi`: la versione e' una
fotografia e si legge sempre intera (research R2).

Solo schema: i modelli esistenti diventano singoli, che e' cio' che sono.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def _indici_slot(con_multiplo: bool) -> None:
    multiplo = ["multiplo"] if con_multiplo else []
    op.create_index(
        "uq_modello_slot_variante",
        "modello_documento",
        ["tipo_documento_id", "percorso_categorizzazione", "dimensioni", *multiplo, "variante"],
        unique=True,
        postgresql_where=sa.text("stato <> 'ELIMINATO'"),
    )
    op.create_index(
        "uq_modello_slot_nota",
        "modello_documento",
        ["tipo_documento_id", "percorso_categorizzazione", "dimensioni", *multiplo, "nota"],
        unique=True,
        postgresql_where=sa.text("stato <> 'ELIMINATO' AND nota IS NOT NULL"),
    )


def upgrade() -> None:
    op.add_column(
        "modello_documento",
        sa.Column("multiplo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("campo_modello", sa.Column("sotto_campi", JSONB, nullable=True))
    op.create_check_constraint(
        "ck_campo_modello_sotto_campi_lista",
        "campo_modello",
        "sotto_campi IS NULL OR jsonb_typeof(sotto_campi) = 'array'",
    )
    op.drop_index("uq_modello_slot_nota", table_name="modello_documento")
    op.drop_index("uq_modello_slot_variante", table_name="modello_documento")
    _indici_slot(con_multiplo=True)


def downgrade() -> None:
    # Tornare indietro con modelli multipli vivi rimetterebbe singolo e
    # multiplo sullo stesso slot: l'indice unico fallirebbe a meta' strada.
    # Meglio fermarsi prima e dire perche'.
    vivi = op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM modello_documento WHERE multiplo AND stato <> 'ELIMINATO'"
    ))
    if vivi:
        raise RuntimeError(
            f"Downgrade 0031 impossibile: {vivi} modelli multipli non eliminati. "
            "Eliminarli prima di tornare alla 0030."
        )
    op.drop_index("uq_modello_slot_nota", table_name="modello_documento")
    op.drop_index("uq_modello_slot_variante", table_name="modello_documento")
    _indici_slot(con_multiplo=False)
    op.drop_constraint("ck_campo_modello_sotto_campi_lista", "campo_modello", type_="check")
    op.drop_column("campo_modello", "sotto_campi")
    op.drop_column("modello_documento", "multiplo")
