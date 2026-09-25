"""Nota di variante e unicita' dello slot di categorizzazione (002 FR-019).

`variante` esisteva gia' come colonna ma era cablata a `STANDARD` in
`crea_modello`: due modelli sulla stessa categorizzazione nascevano identici e,
alla pubblicazione, il secondo archiviava il primo in silenzio
(`get_versione_pubblicata_corrente` filtra proprio su quella chiave). Qui si
aggiunge cio' che mancava per distinguerli davvero:

- `nota`: il testo che scrive il gestore per dire **in cosa** differisce la
  variante. E' distinta da `nome`, che resta generato e non modificabile.
- due indici unici parziali sullo slot `(tipo, percorso, dimensioni)`: uno sul
  codice di variante, uno sulla nota. Il controllo applicativo da solo non
  basta - due creazioni simultanee lo attraversano entrambe - ed e' lo stesso
  motivo per cui `0019` rese unico l'indice sulle edizioni derivate.

**Backfill, non fallimento**: un database gia' usato puo' contenere piu'
modelli `STANDARD` sullo stesso slot, creati quando nulla lo vietava. Creare
l'indice e basta lo farebbe fallire lasciando la migration a meta'. Qui i
duplicati vengono numerati per data di creazione: il piu' vecchio resta
`STANDARD`, gli altri diventano `VARIANTE_1`, `VARIANTE_2`... con una nota che
dice apertamente che l'ha scritta la migrazione, cosi' chi la legge in
interfaccia sa che va rivista e non la scambia per una scelta del gestore.
I modelli eliminati restano fuori da tutto, come per gli altri indici parziali.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

_NOTA_BACKFILL = "Variante numerata automaticamente alla migrazione 0023: verificare la descrizione"


def upgrade() -> None:
    op.add_column("modello_documento", sa.Column("nota", sa.String(length=500), nullable=True))

    # Numerazione dei duplicati preesistenti. `row_number` parte da 1 sul piu'
    # vecchio, che resta STANDARD; dal secondo in poi diventa VARIANTE_n.
    op.execute(
        sa.text(
            """
            WITH numerati AS (
                SELECT id,
                       row_number() OVER (
                           PARTITION BY tipo_documento_id, percorso_categorizzazione, dimensioni, variante
                           ORDER BY created_at, id
                       ) AS posizione
                  FROM modello_documento
                 WHERE stato <> 'ELIMINATO'
            )
            UPDATE modello_documento AS m
               SET variante = 'VARIANTE_' || (numerati.posizione - 1),
                   nota = COALESCE(m.nota, :nota)
              FROM numerati
             WHERE m.id = numerati.id
               AND numerati.posizione > 1
            """
        ).bindparams(nota=_NOTA_BACKFILL)
    )

    op.create_index(
        "uq_modello_slot_variante",
        "modello_documento",
        ["tipo_documento_id", "percorso_categorizzazione", "dimensioni", "variante"],
        unique=True,
        postgresql_where=sa.text("stato <> 'ELIMINATO'"),
    )
    # La nota e' l'etichetta che l'utente legge: due varianti dello stesso slot
    # con la stessa nota sarebbero indistinguibili proprio dove serve (T033).
    op.create_index(
        "uq_modello_slot_nota",
        "modello_documento",
        ["tipo_documento_id", "percorso_categorizzazione", "dimensioni", "nota"],
        unique=True,
        postgresql_where=sa.text("stato <> 'ELIMINATO' AND nota IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_modello_slot_nota", table_name="modello_documento")
    op.drop_index("uq_modello_slot_variante", table_name="modello_documento")
    op.drop_column("modello_documento", "nota")
