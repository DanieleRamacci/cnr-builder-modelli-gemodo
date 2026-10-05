"""Il documento generato diventa una riga del registro delle generazioni (013 T003).

Fino a qui `documento_generato` era l'archivio dei PDF: un file per chiave
(sistema + `external_context_id` + versione del modello), e la stessa chiave con
dati diversi era un conflitto. GEBAN usa come chiave quella del bando e lo
rigenera a ogni correzione: dalla seconda generazione riceveva 409.

GEMODO ora genera e consegna senza conservare il file, e registra ogni chiamata:

- via il vincolo di unicita' della chiave: la stessa chiave si ripete;
- `DATI_NON_VALIDI` e' un esito del registro, come `COMPLETATO` e `FALLITO`;
- `percorso_file` non si scrive piu' (resta per le righe gia' esistenti);
- chi ha chiesto la generazione: client e ruoli, oltre al soggetto;
- indici per cercare una generazione dall'impronta del PDF (la verifica), per
  chiave e per data.

Le righe esistenti restano tutte.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_documento_generato_chiave_idempotente", "documento_generato", type_="unique")
    op.drop_constraint("ck_documento_generato_stato", "documento_generato", type_="check")
    op.drop_constraint("ck_documento_generato_stato_coerente", "documento_generato", type_="check")
    op.create_check_constraint(
        "ck_documento_generato_stato", "documento_generato",
        "stato IN ('COMPLETATO', 'FALLITO', 'DATI_NON_VALIDI')",
    )
    # Il file non e' piu' una condizione del COMPLETATO: lo sono l'impronta e la
    # dimensione del PDF consegnato.
    op.create_check_constraint(
        "ck_documento_generato_stato_coerente", "documento_generato",
        "(stato = 'COMPLETATO' AND hash_file IS NOT NULL AND dimensione_byte IS NOT NULL "
        "AND errore_messaggio IS NULL) "
        "OR (stato IN ('FALLITO', 'DATI_NON_VALIDI') AND hash_file IS NULL "
        "AND percorso_file IS NULL AND errore_messaggio IS NOT NULL)",
    )
    op.add_column("documento_generato", sa.Column("client_id", sa.String(255), nullable=True))
    op.add_column("documento_generato", sa.Column("ruoli", JSONB, nullable=True))
    op.create_index("ix_documento_generato_hash_file", "documento_generato", ["hash_file"])
    op.create_index(
        "ix_documento_generato_chiave", "documento_generato",
        ["sistema_richiedente", "external_context_id", "modello_versione_id"],
    )
    op.create_index("ix_documento_generato_created_at", "documento_generato", ["created_at"])


def downgrade() -> None:
    # Torna l'archivio a chiave unica: possibile solo se ogni chiave ha una riga
    # e nessuna riga e' DATI_NON_VALIDI. Con piu' generazioni per chiave il
    # vincolo di unicita' fallisce, e va bene cosi': non si cancellano registri.
    op.drop_index("ix_documento_generato_created_at", table_name="documento_generato")
    op.drop_index("ix_documento_generato_chiave", table_name="documento_generato")
    op.drop_index("ix_documento_generato_hash_file", table_name="documento_generato")
    op.drop_column("documento_generato", "ruoli")
    op.drop_column("documento_generato", "client_id")
    op.drop_constraint("ck_documento_generato_stato_coerente", "documento_generato", type_="check")
    op.drop_constraint("ck_documento_generato_stato", "documento_generato", type_="check")
    op.create_check_constraint(
        "ck_documento_generato_stato", "documento_generato", "stato IN ('COMPLETATO', 'FALLITO')",
    )
    op.create_check_constraint(
        "ck_documento_generato_stato_coerente", "documento_generato",
        "(stato = 'COMPLETATO' AND hash_file IS NOT NULL AND percorso_file IS NOT NULL "
        "AND dimensione_byte IS NOT NULL AND errore_messaggio IS NULL) "
        "OR (stato = 'FALLITO' AND hash_file IS NULL AND percorso_file IS NULL AND errore_messaggio IS NOT NULL)",
    )
    op.create_unique_constraint(
        "uq_documento_generato_chiave_idempotente", "documento_generato",
        ["sistema_richiedente", "external_context_id", "modello_versione_id"],
    )
