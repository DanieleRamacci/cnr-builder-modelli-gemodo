"""L'audit sopravvive alla cancellazione di cio' che racconta (010 T106).

Prima di questa migrazione un'integrazione non si poteva cancellare: il suo
audit, il suo endpoint e i suoi tipi documento la riferivano senza azione di
cancellazione. E l'audit dei modelli faceva il contrario, spariva a cascata
col modello: perdere la tracciabilita' per fare pulizia e' il rimedio
sbagliato.

Qui l'audit di integrazioni, tipi documento e modelli smette di essere legato
alla riga da una chiave esterna, e conserva l'identificativo: gli eventi di
un oggetto cancellato restano raggruppabili, e l'evento di cancellazione dice
a quale codice corrispondeva. Un `SET NULL` avrebbe svuotato proprio
l'identificativo, e molti payload (`VERSIONE_PUBBLICATO`: solo lo stato) non
portano altro. L'endpoint, che senza la sua integrazione non significa nulla,
la segue (`CASCADE`).

Nessun dato cambia: solo vincoli. Il `downgrade` rifiuta di procedere se
esistono eventi di righe cancellate, invece di cancellarli.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

# (tabella, colonna, tabella riferita, nome del vincolo, azione prima)
_AUDIT = (
    ("audit_evento_integrazione", "integrazione_id", "integrazione",
     "audit_evento_integrazione_integrazione_id_fkey", None),
    ("audit_evento_configurazione", "tipo_documento_id", "tipo_documento",
     "audit_evento_configurazione_tipo_documento_id_fkey", None),
    ("audit_evento_modello", "modello_documento_id", "modello_documento",
     "audit_evento_modello_modello_documento_id_fkey", "CASCADE"),
)
_ENDPOINT = ("endpoint_integrazione", "integrazione_id", "integrazione", "endpoint_integrazione_integrazione_id_fkey")


def _ricrea(tabella: str, colonna: str, riferita: str, nome: str, azione: str | None) -> None:
    op.drop_constraint(nome, tabella, type_="foreignkey")
    op.create_foreign_key(nome, tabella, riferita, [colonna], ["id"], ondelete=azione)


def upgrade() -> None:
    for tabella, _, _, nome, _ in _AUDIT:
        op.drop_constraint(nome, tabella, type_="foreignkey")
    _ricrea(*_ENDPOINT, "CASCADE")


def downgrade() -> None:
    connessione = op.get_bind()
    for tabella, colonna, riferita, _, _ in _AUDIT:
        orfani = connessione.scalar(sa.text(
            f"SELECT count(*) FROM {tabella} a WHERE NOT EXISTS "
            f"(SELECT 1 FROM {riferita} r WHERE r.id = a.{colonna})"
        ))
        if orfani:
            raise RuntimeError(
                f"{tabella}: {orfani} eventi di audit riguardano righe cancellate; "
                "il downgrade li perderebbe e non procede"
            )
    _ricrea(*_ENDPOINT, None)
    for tabella, colonna, riferita, nome, azione in _AUDIT:
        op.create_foreign_key(nome, tabella, riferita, [colonna], ["id"], ondelete=azione)
