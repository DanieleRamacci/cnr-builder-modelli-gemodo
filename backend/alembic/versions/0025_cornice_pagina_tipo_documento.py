"""Cornice di pagina sul tipo documento (012 FR-011, T043).

Logo, intestazione e pie' di pagina che si ripetono su ogni pagina
appartengono al tipo documento, non al modello: si configurano una volta e
valgono per tutti i bandi di quel tipo. Colonna nullable: un tipo documento
senza cornice continua a generare il documento di prima, senza testata.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tipo_documento", sa.Column("cornice_pagina", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("tipo_documento", "cornice_pagina")
