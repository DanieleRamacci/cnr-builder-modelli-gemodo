"""Metadati di compatibilita' della versione modello (010 FR-014, T055).

Due collocazioni, perche' i dati hanno tempi di vita diversi:

- **immutabile, sulla versione**: `firma_algoritmo`, `firma_contratto` e
  `contratto_firmato` nascono quando la versione e' creata e non cambiano piu'.
  Descrivono il ramo **com'era** quando il modello e' stato costruito.
- **mutevole, in tabella propria**: l'esito del confronto viene riscritto a
  ogni ciclo del runner. Tenerlo sulla riga della versione avrebbe significato
  aggiornare una versione pubblicata a ogni giro, contro il criterio della
  spec - "il controllo conserva data e motivo senza modificare il contenuto
  pubblicato" - e avrebbe confuso due cose che la 010 tiene distinte: lo stato
  di pubblicazione e l'esito di compatibilita'.

`contratto_firmato` non e' una copia del catalogo (FR-014 lo vieta): contiene
solo cio' che serve a **spiegare** un confronto e che non e' gia' altrove -
i valori ammessi delle dipendenze usate e l'insieme dei campi obbligatori del
ramo al momento della firma. Codici, tipi e obbligatorieta' dei campi scelti
restano in `campo_modello`, il percorso in `modello_documento`.

Le colonne sono nullable: le versioni gia' pubblicate non hanno una firma e non
se ne puo' inventare una, perche' l'albero di allora non e' piu' osservabile.
Restano senza, e il confronto le riporta `NON_VERIFICABILE` finche' non sono
ripubblicate - che e' l'informazione vera, non un allineamento presunto.

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

ESITI = ("ALLINEATO", "COMPATIBILE_CON_VARIAZIONI", "DA_AGGIORNARE", "NON_VERIFICABILE")


def upgrade() -> None:
    op.add_column("modello_versione", sa.Column("firma_algoritmo", sa.String(32), nullable=True))
    op.add_column("modello_versione", sa.Column("firma_contratto", sa.String(64), nullable=True))
    op.add_column(
        "modello_versione",
        sa.Column("contratto_firmato", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # Una firma senza l'algoritmo che l'ha prodotta non e' confrontabile: quando
    # l'algoritmo cambia versione, la vecchia firma va ricalcolata, non riusata.
    op.create_check_constraint(
        "ck_modello_versione_firma_completa",
        "modello_versione",
        "(firma_algoritmo IS NULL) = (firma_contratto IS NULL)",
    )

    op.create_table(
        "esito_compatibilita_versione",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "modello_versione_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("modello_versione.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("esito", sa.String(32), nullable=False),
        sa.Column("verificato_at", sa.DateTime(timezone=True), nullable=False),
        # Le differenze che hanno prodotto l'esito, gia' nella forma che la
        # dashboard mostra: il motivo deve sopravvivere al ciclo che l'ha visto.
        sa.Column(
            "differenze",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("firma_osservata", sa.String(64), nullable=True),
        sa.CheckConstraint(
            "esito IN " + str(ESITI), name="ck_esito_compatibilita_valore",
        ),
        # Una riga per versione: e' l'ultimo esito, non uno storico. Lo storico
        # delle verifiche vive sull'integrazione (T093), dove la domanda e'
        # "questa sorgente come si e' comportata nel tempo".
        sa.UniqueConstraint("modello_versione_id", name="uq_esito_compatibilita_versione"),
    )


def downgrade() -> None:
    op.drop_table("esito_compatibilita_versione")
    op.drop_constraint("ck_modello_versione_firma_completa", "modello_versione", type_="check")
    op.drop_column("modello_versione", "contratto_firmato")
    op.drop_column("modello_versione", "firma_contratto")
    op.drop_column("modello_versione", "firma_algoritmo")
