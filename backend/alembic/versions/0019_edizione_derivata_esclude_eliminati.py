"""Free the (source model, language) slot when a derived edition is deleted.

``0017`` created ``uq_modello_derivato_padre_lingua`` as a plain unique constraint
over ``(derivato_da_modello_id, lingua)``. Deletion of a model is logical, so a
deleted edition kept occupying its slot forever while the application layer
(``builder/repository.py:get_edizione_derivata``) already excluded ``ELIMINATO``.
The two disagreed: the application check passed, the INSERT violated the
constraint, and the unhandled IntegrityError surfaced as HTTP 500 (002 FR-018).

This replaces it with a partial unique index carrying the same intent as the
query, so the slot is genuinely freed. Concurrency is still possible between two
simultaneous requests; the service translates that residual violation into a
functional 409.
"""

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

INDICE = "uq_modello_derivato_padre_lingua"


def upgrade():
    op.drop_constraint(INDICE, "modello_documento", type_="unique")
    op.execute(
        f"CREATE UNIQUE INDEX {INDICE} ON modello_documento "
        "(derivato_da_modello_id, lingua) WHERE stato <> 'ELIMINATO'"
    )


def downgrade():
    # Un duplicato fra righe eliminate renderebbe impossibile ricreare il vincolo
    # totale: si scartano quelle righe prima di tornare indietro.
    op.execute(
        "DELETE FROM modello_documento a USING modello_documento b "
        "WHERE a.stato = 'ELIMINATO' AND a.derivato_da_modello_id IS NOT NULL "
        "AND a.derivato_da_modello_id = b.derivato_da_modello_id "
        "AND a.lingua = b.lingua AND a.id <> b.id AND a.created_at < b.created_at"
    )
    op.execute(f"DROP INDEX {INDICE}")
    op.create_unique_constraint(
        INDICE, "modello_documento", ["derivato_da_modello_id", "lingua"]
    )
