"""Profilo di accesso dell'integrazione: ruoli ACE e client ammessi (001 T088).

Fino a qui chi poteva fare cosa stava in un file, `infra/local/integration-
profiles.local.yaml`, copiato nell'immagine e letto una volta all'avvio. Un
contesto registrato dall'interfaccia non dava permessi a nessuno: il file
mappava solo `#geban`, e cambiarlo voleva un nuovo deploy.

Qui il profilo diventa una parte dell'integrazione, che ha gia' il contesto:

- `ruolo_integrazione`: un ruolo ACE (senza `#contesto`, che e' quello
  dell'integrazione) e i permessi GEMODO che concede, da un catalogo chiuso;
- `client_integrazione`: i client che possono chiamare GEMODO per conto
  dell'integrazione, oltre al client di login di GEMODO stesso.

Entrambe seguono l'integrazione quando la si cancella. La mappatura di GEBAN
di oggi viene copiata sulle integrazioni di contesto `geban` gia' registrate,
cosi' che dopo la migrazione GEBAN abbia esattamente i permessi di prima.
Un'integrazione registrata dopo nasce senza ruoli.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

PERMESSI = ("DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE", "GEMODO_MODELLI_GESTORE")

# La mappatura di `infra/local/integration-profiles.local.yaml` al 2026-10-05.
_GEBAN_RUOLI = {
    "ROLE_GESTORE": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"],
    "ROLE_MANAGER": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER", "GEMODO_MODELLI_GESTORE"],
    "ROLE_COORDINATOR": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"],
    "ROLE_USER": ["DOCUMENTI_GENERATORE", "DOCUMENTI_VIEWER"],
}
# Il client ACE di GEBAN. `geban-backend`, il client tecnico del file, non c'e':
# era un doppio di prova mai usato dal flusso reale (SEC-006-001 superata).
_GEBAN_CLIENT = ("geri-angular-public",)


def upgrade() -> None:
    elenco_permessi = ", ".join(f"'{p}'" for p in PERMESSI)
    op.create_table(
        "ruolo_integrazione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("integrazione_id", sa.Uuid(), sa.ForeignKey("integrazione.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ruolo", sa.String(128), nullable=False),
        sa.Column("permessi", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("integrazione_id", "ruolo", name="uq_ruolo_integrazione"),
        sa.CheckConstraint(
            "length(btrim(ruolo)) > 0 AND position('#' in ruolo) = 0", name="ck_ruolo_integrazione_nome"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(permessi) = 'array' AND jsonb_array_length(permessi) > 0 "
            f"AND permessi <@ jsonb_build_array({elenco_permessi})",
            name="ck_ruolo_integrazione_permessi",
        ),
    )
    op.create_table(
        "client_integrazione",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("integrazione_id", sa.Uuid(), sa.ForeignKey("integrazione.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("integrazione_id", "client_id", name="uq_client_integrazione"),
        sa.CheckConstraint("length(btrim(client_id)) > 0", name="ck_client_integrazione_id"),
    )

    connessione = op.get_bind()
    ruoli = sa.table("ruolo_integrazione", sa.column("id", sa.Uuid()), sa.column("integrazione_id", sa.Uuid()),
                     sa.column("ruolo", sa.String()), sa.column("permessi", JSONB()))
    client = sa.table("client_integrazione", sa.column("id", sa.Uuid()), sa.column("integrazione_id", sa.Uuid()),
                      sa.column("client_id", sa.String()))
    geban = connessione.scalars(sa.text("SELECT id FROM integrazione WHERE codice_contesto = 'geban'")).all()
    for integrazione_id in geban:
        connessione.execute(ruoli.insert(), [
            {"id": uuid.uuid4(), "integrazione_id": integrazione_id, "ruolo": ruolo, "permessi": permessi}
            for ruolo, permessi in _GEBAN_RUOLI.items()
        ])
        connessione.execute(client.insert(), [
            {"id": uuid.uuid4(), "integrazione_id": integrazione_id, "client_id": client_id}
            for client_id in _GEBAN_CLIENT
        ])


def downgrade() -> None:
    op.drop_table("client_integrazione")
    op.drop_table("ruolo_integrazione")
