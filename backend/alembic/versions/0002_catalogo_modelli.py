"""extend catalog model columns for feature 001

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE modello_documento ADD COLUMN IF NOT EXISTS variante varchar(64) NOT NULL DEFAULT 'STANDARD'")
    op.execute("ALTER TABLE modello_documento ADD COLUMN IF NOT EXISTS public_id bigint")
    op.execute("ALTER TABLE modello_versione ADD COLUMN IF NOT EXISTS public_id bigint")
    op.execute("ALTER TABLE modello_versione ADD COLUMN IF NOT EXISTS data_inizio_validita timestamp with time zone")
    op.execute("ALTER TABLE modello_versione ADD COLUMN IF NOT EXISTS data_fine_validita timestamp with time zone")
    op.execute("ALTER TABLE modello_versione ADD COLUMN IF NOT EXISTS pubblicato_at timestamp with time zone")
    op.execute("ALTER TABLE campo_modello ADD COLUMN IF NOT EXISTS descrizione text")
    op.execute("ALTER TABLE campo_modello ADD COLUMN IF NOT EXISTS formato varchar(64)")
    op.execute("ALTER TABLE campo_modello ADD COLUMN IF NOT EXISTS valore_default text")
    op.execute("ALTER TABLE campo_modello ADD COLUMN IF NOT EXISTS opzioni jsonb")
    op.execute("ALTER TABLE campo_modello ADD COLUMN IF NOT EXISTS validazione jsonb")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_modello_versione_pubblicata_corrente "
        "ON modello_versione (modello_documento_id) WHERE stato = 'PUBBLICATO'"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_modello_documento_public_id "
        "ON modello_documento (public_id) WHERE public_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_modello_versione_public_id "
        "ON modello_versione (public_id) WHERE public_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_modello_versione_public_id")
    op.execute("DROP INDEX IF EXISTS uq_modello_documento_public_id")
    op.execute("DROP INDEX IF EXISTS uq_modello_versione_pubblicata_corrente")
    op.execute("ALTER TABLE campo_modello DROP COLUMN IF EXISTS validazione")
    op.execute("ALTER TABLE campo_modello DROP COLUMN IF EXISTS opzioni")
    op.execute("ALTER TABLE campo_modello DROP COLUMN IF EXISTS valore_default")
    op.execute("ALTER TABLE campo_modello DROP COLUMN IF EXISTS formato")
    op.execute("ALTER TABLE campo_modello DROP COLUMN IF EXISTS descrizione")
    op.execute("ALTER TABLE modello_versione DROP COLUMN IF EXISTS pubblicato_at")
    op.execute("ALTER TABLE modello_versione DROP COLUMN IF EXISTS data_fine_validita")
    op.execute("ALTER TABLE modello_versione DROP COLUMN IF EXISTS data_inizio_validita")
    op.execute("ALTER TABLE modello_versione DROP COLUMN IF EXISTS public_id")
    op.execute("ALTER TABLE modello_documento DROP COLUMN IF EXISTS public_id")
    op.execute("ALTER TABLE modello_documento DROP COLUMN IF EXISTS variante")
