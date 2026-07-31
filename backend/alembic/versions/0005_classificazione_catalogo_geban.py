"""add GEBAN catalog classification tree

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-31
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence, Union
import uuid

import sqlalchemy as sa
import yaml
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NAMESPACE = uuid.UUID("0b5f5d13-3b1a-4f97-b6d2-4f5c3b7df001")


def _uuid(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_catalogo() -> dict[str, Any]:
    path = _repo_root() / "infra" / "local" / "postgres" / "seed-demo-catalog.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["catalogo"]


def upgrade() -> None:
    op.create_table(
        "classificazione_catalogo",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo_documento_id", sa.Uuid(), nullable=False),
        sa.Column("tipologia_bando_sol_id", sa.Uuid(), nullable=False),
        sa.Column("categoria_documento_id", sa.Uuid(), nullable=False),
        sa.Column("attiva", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tipo_documento_id"], ["tipo_documento.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tipologia_bando_sol_id"], ["tipologia_bando_sol.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["categoria_documento_id"], ["categoria_documento.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tipo_documento_id",
            "tipologia_bando_sol_id",
            "categoria_documento_id",
            name="uq_classificazione_catalogo_albero",
        ),
    )

    catalogo = _load_catalogo()
    bind = op.get_bind()
    tipo_ids = {item["codice"]: _uuid(f"tipo:{item['codice']}") for item in catalogo.get("tipi_documento", [])}
    categoria_ids = {
        (item["tipo_documento"], item["codice"]): _uuid(f"categoria:{item['tipo_documento']}:{item['codice']}")
        for item in catalogo.get("categorie", [])
    }
    tipologia_ids = {
        item["codice"]: _uuid(f"tipologia-sol:{item['codice']}") for item in catalogo.get("tipologie_sol", [])
    }

    for item in catalogo.get("categorie", []):
        bind.execute(
            sa.text(
                """
                INSERT INTO categoria_documento (id, tipo_documento_id, codice, nome, stato)
                VALUES (:id, :tipo_documento_id, :codice, :nome, 'ATTIVA')
                ON CONFLICT (tipo_documento_id, codice)
                DO UPDATE SET nome = EXCLUDED.nome, stato = 'ATTIVA'
                """
            ),
            {
                "id": categoria_ids[(item["tipo_documento"], item["codice"])],
                "tipo_documento_id": tipo_ids[item["tipo_documento"]],
                "codice": item["codice"],
                "nome": item["nome"],
            },
        )

    for item in catalogo.get("classificazioni", []):
        tipo_id = tipo_ids[item["tipo_documento"]]
        tipologia_id = tipologia_ids[item["codice_tipologia"]]
        for codice_categoria in item.get("categorie", []):
            categoria_id = categoria_ids[(item["tipo_documento"], codice_categoria)]
            bind.execute(
                sa.text(
                    """
                    INSERT INTO classificazione_catalogo
                    (id, tipo_documento_id, tipologia_bando_sol_id, categoria_documento_id, attiva)
                    VALUES (:id, :tipo_documento_id, :tipologia_bando_sol_id, :categoria_documento_id, TRUE)
                    ON CONFLICT (tipo_documento_id, tipologia_bando_sol_id, categoria_documento_id)
                    DO UPDATE SET attiva = TRUE
                    """
                ),
                {
                    "id": _uuid(f"classificazione:{item['tipo_documento']}:{item['codice_tipologia']}:{codice_categoria}"),
                    "tipo_documento_id": tipo_id,
                    "tipologia_bando_sol_id": tipologia_id,
                    "categoria_documento_id": categoria_id,
                },
            )

    bind.execute(
        sa.text(
            """
            UPDATE categoria_documento
            SET stato = 'INATTIVA'
            WHERE codice = 'DEMO'
              AND tipo_documento_id = :tipo_documento_id
            """
        ),
        {"tipo_documento_id": tipo_ids["BANDO_CONCORSO"]},
    )

    demo_model_id = _uuid("modello:demo-bando-concorso-standard-v1")
    invalid_model_id = _uuid("modello:demo-bando-concorso-html-libero-non-valido")
    bind.execute(
        sa.text(
            """
            UPDATE modello_documento
            SET categoria_documento_id = :categoria_id,
                tipologia_bando_sol_id = :tipologia_id
            WHERE id = :demo_model_id OR id = :invalid_model_id
            """
        ),
        {
            "categoria_id": categoria_ids[("BANDO_CONCORSO", "TECNOLOGO")],
            "tipologia_id": tipologia_ids["TD"],
            "demo_model_id": demo_model_id,
            "invalid_model_id": invalid_model_id,
        },
    )


def downgrade() -> None:
    op.drop_table("classificazione_catalogo")
