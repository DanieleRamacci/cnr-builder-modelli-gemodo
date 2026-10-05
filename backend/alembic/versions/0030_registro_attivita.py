"""Registro attivita' per gli amministratori (013 T010).

Gli eventi su modelli, configurazione e integrazioni stanno gia' nelle loro
tabelle di audit, e le generazioni nel registro delle generazioni. Mancavano le
chiamate che non cambiano niente ma dicono chi usa GEMODO: le validazioni via
API e gli accessi negati (401, 403). Vanno in `evento_attivita`, scritta a parte
e senza mai fermare l'azione che registra.

Tutti i registri prendono anche lo `username`: finora c'era solo il `sub` del
token, che a chi legge non dice niente. Le righe di prima restano senza.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

_CON_USERNAME = (
    "documento_generato", "audit_evento_modello", "audit_evento_configurazione", "audit_evento_integrazione",
)


def upgrade() -> None:
    op.create_table(
        "evento_attivita",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("categoria", sa.String(32), nullable=False),
        sa.Column("azione", sa.String(64), nullable=False),
        sa.Column("esito", sa.String(32), nullable=False),
        sa.Column("soggetto", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("client_id", sa.String(255), nullable=True),
        sa.Column("contesto", sa.String(64), nullable=True),
        sa.Column("oggetto_tipo", sa.String(64), nullable=True),
        sa.Column("oggetto_id", sa.String(255), nullable=True),
        sa.Column("dettaglio", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("jsonb_typeof(dettaglio) = 'object'", name="ck_evento_attivita_dettaglio"),
    )
    op.create_index("ix_evento_attivita_created_at", "evento_attivita", ["created_at"])
    op.create_index("ix_evento_attivita_soggetto", "evento_attivita", ["soggetto"])
    op.create_index("ix_evento_attivita_categoria", "evento_attivita", ["categoria"])
    for tabella in _CON_USERNAME:
        op.add_column(tabella, sa.Column("username", sa.String(255), nullable=True))


def downgrade() -> None:
    for tabella in _CON_USERNAME:
        op.drop_column(tabella, "username")
    op.drop_index("ix_evento_attivita_categoria", table_name="evento_attivita")
    op.drop_index("ix_evento_attivita_soggetto", table_name="evento_attivita")
    op.drop_index("ix_evento_attivita_created_at", table_name="evento_attivita")
    op.drop_table("evento_attivita")
