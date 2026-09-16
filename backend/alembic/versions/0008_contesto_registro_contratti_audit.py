"""add tipo_documento.codice_contesto, registro_contratti_dati, audit_evento_modello

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-15

DEC-001-CONTESTO-SOSTITUISCE-UFFICIO: nessuna tabella `ufficio` separata, il
contesto del token (contexts.<codice_contesto>.roles) e' l'unita' di scoping.
DEC-001-REGISTRO-CONTRATTI-DATI: registro dei campi riusabili per tipo
documento, scoped per codice_contesto ereditato dal tipo documento.
"""

from __future__ import annotations

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NAMESPACE = uuid.UUID("0b5f5d13-3b1a-4f97-b6d2-4f5c3b7df001")


def _uuid(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


# Stessi 6 campi di CAMPI_DEMO (migration 0005) + il settimo campo "livello",
# confermato 2026-09-15 (docs/adr/0001-esempio-discovery-geban.json): GEBAN
# gestisce davvero bandi per livelli diversi dello stesso profilo. Tipo
# "string" (non "enum": vocabolario tipo_dato gia' in uso e' string/number/
# date/boolean/array/object), vincolo espresso in validazione.fonte_opzioni.
REGISTRO_CAMPI_BANDO_CONCORSO = [
    {"codice": "codice_bando", "etichetta": "Codice bando", "tipo_dato": "string", "obbligatorio": True, "lingua": "IT", "ordine": 1, "validazione": {"minLength": 1}},
    {"codice": "titolo_it", "etichetta": "Titolo", "tipo_dato": "string", "obbligatorio": True, "lingua": "IT", "ordine": 2, "validazione": {"minLength": 1}},
    {"codice": "descrizione_ridotta_it", "etichetta": "Descrizione ridotta", "tipo_dato": "string", "obbligatorio": False, "lingua": "IT", "ordine": 3, "validazione": None},
    {"codice": "sede_prescelta_it", "etichetta": "Sede", "tipo_dato": "string", "obbligatorio": True, "lingua": "IT", "ordine": 4, "validazione": {"minLength": 1}},
    {"codice": "numero_posti", "etichetta": "Numero posti", "tipo_dato": "number", "obbligatorio": True, "lingua": "IT", "ordine": 5, "validazione": {"minimum": 1}},
    {"codice": "titolo_en", "etichetta": "Title", "tipo_dato": "string", "obbligatorio": True, "lingua": "EN", "ordine": 6, "validazione": {"minLength": 1}},
    {
        "codice": "livello",
        "etichetta": "Livello",
        "tipo_dato": "string",
        "obbligatorio": True,
        "lingua": "IT",
        "ordine": 7,
        "validazione": {"fonte_opzioni": "profilo.livelli_possibili", "default": "profilo.livello_base"},
    },
]


def upgrade() -> None:
    op.add_column("tipo_documento", sa.Column("codice_contesto", sa.String(length=64), nullable=True))
    op.execute("UPDATE tipo_documento SET codice_contesto = 'geban' WHERE codice = 'BANDO_CONCORSO'")
    op.alter_column("tipo_documento", "codice_contesto", nullable=False)

    op.create_table(
        "registro_contratti_dati",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_documento_id", sa.Uuid(), nullable=False),
        sa.Column("codice", sa.String(length=128), nullable=False),
        sa.Column("versione", sa.Integer(), nullable=False),
        sa.Column("campi", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("stato", sa.String(length=32), nullable=False, server_default="ATTIVO"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tipo_documento_id"], ["tipo_documento.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tipo_documento_id", "codice", name="uq_registro_contratti_tipo_codice"),
    )

    op.create_table(
        "audit_evento_modello",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_evento", sa.String(length=64), nullable=False),
        sa.Column("soggetto_id", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("ruoli", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("modello_documento_id", sa.Uuid(), nullable=False),
        sa.Column("modello_versione_id", sa.Uuid(), nullable=True),
        sa.Column("payload_minimo", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["modello_documento_id"], ["modello_documento.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["modello_versione_id"], ["modello_versione.id"], ondelete="SET NULL"),
    )

    bind = op.get_bind()
    tipo_documento_id = bind.execute(
        sa.text("SELECT id FROM tipo_documento WHERE codice = 'BANDO_CONCORSO'")
    ).scalar()
    if tipo_documento_id is not None:
        bind.execute(
            sa.text(
                """
                INSERT INTO registro_contratti_dati (id, tipo_documento_id, codice, versione, campi, stato)
                VALUES (:id, :tipo_documento_id, :codice, 1, CAST(:campi AS jsonb), 'ATTIVO')
                ON CONFLICT (tipo_documento_id, codice) DO UPDATE SET campi = EXCLUDED.campi, stato = 'ATTIVO'
                """
            ),
            {
                "id": _uuid("registro-contratti:BANDO_CONCORSO:bando-concorso-common-fields-v1"),
                "tipo_documento_id": tipo_documento_id,
                "codice": "bando-concorso-common-fields-v1",
                "campi": json.dumps(REGISTRO_CAMPI_BANDO_CONCORSO),
            },
        )


def downgrade() -> None:
    op.drop_table("audit_evento_modello")
    op.drop_table("registro_contratti_dati")
    op.drop_column("tipo_documento", "codice_contesto")
