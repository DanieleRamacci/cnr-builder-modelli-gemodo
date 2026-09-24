"""La lingua del campo diventa facoltativa (contratto discovery 0.7.0).

`campo_modello.lingua` era NOT NULL con default 'IT'. E' lo stesso
dato falso che 0020 ha eliminato dal modello, un livello piu' in basso: un
albero discovery che dichiara le lingue **sulla foglia** - la forma che GEBAN
invia davvero - non attribuisce una lingua ai singoli campi, e persisterne una
implicita dice che il campo e' italiano quando il suo contratto vale per tutte
le lingue che la foglia dichiara.

Il vincolo di unicita' va ricreato con NULLS NOT DISTINCT: in PostgreSQL due
NULL non si considerano uguali, quindi la sola `nullable=True` avrebbe aperto
la porta a piu' campi con lo stesso codice e lingua assente sulla stessa
versione - esattamente il duplicato che il vincolo esiste per impedire.
NULLS NOT DISTINCT richiede PostgreSQL 15 o superiore (test: 15, deploy: 16).

ATTENZIONE - IL DOWNGRADE INVENTA UN DATO. I campi senza lingua ne ricevono
una, 'IT', perche' la colonna ricreata e' NOT NULL. Per i modelli costruiti su
un albero che non distingue i campi per lingua e' un'informazione falsa, la
stessa che questa migration elimina. Se due campi della stessa versione
condividono il codice con lingua assente, il downgrade fallisce sul vincolo
ricreato invece di scartarne uno in silenzio.

Revision ID: 0021
Revises: 0020
"""

from __future__ import annotations

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

TABELLA = "campo_modello"
VINCOLO = "uq_campo_modello_versione_codice_lingua"
COLONNE = "(modello_versione_id, codice, lingua)"


def upgrade() -> None:
    op.alter_column(TABELLA, "lingua", nullable=True, server_default=None)
    op.drop_constraint(VINCOLO, TABELLA, type_="unique")
    # Alembic non esprime NULLS NOT DISTINCT, che e' il punto di questo passo.
    op.execute(
        f"ALTER TABLE {TABELLA} ADD CONSTRAINT {VINCOLO} UNIQUE NULLS NOT DISTINCT {COLONNE}"
    )


def downgrade() -> None:
    op.execute(f"UPDATE {TABELLA} SET lingua = 'IT' WHERE lingua IS NULL")
    op.drop_constraint(VINCOLO, TABELLA, type_="unique")
    op.execute(f"ALTER TABLE {TABELLA} ADD CONSTRAINT {VINCOLO} UNIQUE {COLONNE}")
    op.alter_column(TABELLA, "lingua", nullable=False, server_default="IT")
