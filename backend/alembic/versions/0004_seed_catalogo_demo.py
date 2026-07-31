"""seed demo catalog from infra manifest

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence, Union
import json
import uuid

import sqlalchemy as sa
import yaml
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
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


def _sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def _jsonb_literal(value: dict[str, Any] | None) -> str:
    if value is None:
        return "NULL"
    return _sql_literal(json.dumps(value)) + "::jsonb"


def upgrade() -> None:
    catalogo = _load_catalogo()
    tipo_ids: dict[str, uuid.UUID] = {}
    categoria_ids: dict[tuple[str, str], uuid.UUID] = {}
    tipologia_ids: dict[str, uuid.UUID] = {}

    tipo_table = sa.table(
        "tipo_documento",
        sa.column("id", sa.Uuid()),
        sa.column("codice", sa.String()),
        sa.column("nome", sa.String()),
        sa.column("stato", sa.String()),
        sa.column("spec_owner", sa.String()),
    )
    categoria_table = sa.table(
        "categoria_documento",
        sa.column("id", sa.Uuid()),
        sa.column("tipo_documento_id", sa.Uuid()),
        sa.column("codice", sa.String()),
        sa.column("nome", sa.String()),
        sa.column("stato", sa.String()),
    )
    tipologia_table = sa.table(
        "tipologia_bando_sol",
        sa.column("id", sa.Uuid()),
        sa.column("codice", sa.String()),
        sa.column("codice_sol", sa.String()),
        sa.column("descrizione", sa.String()),
        sa.column("attiva", sa.Boolean()),
    )
    modello_table = sa.table(
        "modello_documento",
        sa.column("id", sa.Uuid()),
        sa.column("public_id", sa.BigInteger()),
        sa.column("tipo_documento_id", sa.Uuid()),
        sa.column("categoria_documento_id", sa.Uuid()),
        sa.column("tipologia_bando_sol_id", sa.Uuid()),
        sa.column("codice", sa.String()),
        sa.column("nome", sa.String()),
        sa.column("stato", sa.String()),
        sa.column("variante", sa.String()),
    )
    for item in catalogo.get("tipi_documento", []):
        tipo_id = _uuid(f"tipo:{item['codice']}")
        tipo_ids[item["codice"]] = tipo_id
        op.bulk_insert(
            tipo_table,
            [
                {
                    "id": tipo_id,
                    "codice": item["codice"],
                    "nome": item["nome"],
                    "stato": "ATTIVA",
                    "spec_owner": item.get("spec_owner", "specs/001-catalogo-contratto-geban"),
                }
            ],
        )

    for item in catalogo.get("categorie", []):
        categoria_id = _uuid(f"categoria:{item['tipo_documento']}:{item['codice']}")
        categoria_ids[(item["tipo_documento"], item["codice"])] = categoria_id
        op.bulk_insert(
            categoria_table,
            [
                {
                    "id": categoria_id,
                    "tipo_documento_id": tipo_ids[item["tipo_documento"]],
                    "codice": item["codice"],
                    "nome": item["nome"],
                    "stato": "ATTIVA",
                }
            ],
        )

    for item in catalogo.get("tipologie_sol", []):
        tipologia_id = _uuid(f"tipologia-sol:{item['codice']}")
        tipologia_ids[item["codice"]] = tipologia_id
        op.bulk_insert(
            tipologia_table,
            [
                {
                    "id": tipologia_id,
                    "codice": item["codice"],
                    "codice_sol": item["codice_sol"],
                    "descrizione": item["nome"],
                    "attiva": True,
                }
            ],
        )

    for index, item in enumerate(catalogo.get("modelli", []), start=1):
        codice_modello = item["modello_versione_id"]
        modello_id = _uuid(f"modello:{codice_modello}")
        versione_id = _uuid(f"versione:{codice_modello}")
        op.bulk_insert(
            modello_table,
            [
                {
                    "id": modello_id,
                    "public_id": index,
                    "tipo_documento_id": tipo_ids[item["tipo_documento"]],
                    "categoria_documento_id": categoria_ids[(item["tipo_documento"], item["categoria"])],
                    "tipologia_bando_sol_id": tipologia_ids.get(item.get("codice_tipologia")),
                    "codice": codice_modello,
                    "nome": codice_modello,
                    "stato": "ATTIVA",
                    "variante": "STANDARD",
                }
            ],
        )
        struttura = json.dumps({"ref": item.get("formato_documentale_ref")}).replace("'", "''")
        published_at = "'2026-07-31T10:00:00+00:00'" if item["stato"] == "PUBBLICATO" else "NULL"
        op.execute(
            "INSERT INTO modello_versione "
            "(id, public_id, modello_documento_id, versione, stato, formato_documentale, struttura_documentale, "
            "pubblicato_il, pubblicato_at) "
            f"VALUES ('{versione_id}', {index}, '{modello_id}', 1, '{item['stato']}', "
            f"'GEMODO_DOCUMENT_V1', '{struttura}'::jsonb, {published_at}, {published_at})"
        )
        if item["stato"] == "PUBBLICATO":
            campi = [
                ("codice_bando", "Codice bando", "Identificativo funzionale del bando", "string", True, "IT", 1, {"minLength": 1}),
                ("titolo_it", "Titolo", "Titolo italiano del bando", "string", True, "IT", 2, {"minLength": 1}),
                ("descrizione_ridotta_it", "Descrizione ridotta", "Sintesi italiana del bando", "string", False, "IT", 3, None),
                ("sede_prescelta_it", "Sede", "Sede associata alla procedura", "string", True, "IT", 4, {"minLength": 1}),
                ("numero_posti", "Numero posti", "Numero dei posti previsti", "number", True, "IT", 5, {"minimum": 1}),
                ("titolo_en", "Title", "Titolo inglese del bando", "string", True, "EN", 6, {"minLength": 1}),
            ]
            for codice, etichetta, descrizione, tipo_dato, obbligatorio, lingua, ordine, validazione in campi:
                field_id = _uuid(f"campo:{codice_modello}:{codice}:{lingua}")
                op.execute(
                    "INSERT INTO campo_modello "
                    "(id, modello_versione_id, codice, etichetta, descrizione, tipo_dato, obbligatorio, "
                    "lingua, ordine, validazione) "
                    f"VALUES ('{field_id}', '{versione_id}', {_sql_literal(codice)}, {_sql_literal(etichetta)}, "
                    f"{_sql_literal(descrizione)}, {_sql_literal(tipo_dato)}, {'TRUE' if obbligatorio else 'FALSE'}, "
                    f"{_sql_literal(lingua)}, {ordine}, {_jsonb_literal(validazione)})"
                )


def downgrade() -> None:
    catalogo = _load_catalogo()
    version_ids = [_uuid(f"versione:{item['modello_versione_id']}") for item in catalogo.get("modelli", [])]
    model_ids = [_uuid(f"modello:{item['modello_versione_id']}") for item in catalogo.get("modelli", [])]
    category_ids = [
        _uuid(f"categoria:{item['tipo_documento']}:{item['codice']}") for item in catalogo.get("categorie", [])
    ]
    tipo_ids = [_uuid(f"tipo:{item['codice']}") for item in catalogo.get("tipi_documento", [])]
    tipologia_ids = [_uuid(f"tipologia-sol:{item['codice']}") for item in catalogo.get("tipologie_sol", [])]

    bind = op.get_bind()
    for table, ids in [
        ("modello_versione", version_ids),
        ("modello_documento", model_ids),
        ("categoria_documento", category_ids),
        ("tipo_documento", tipo_ids),
        ("tipologia_bando_sol", tipologia_ids),
    ]:
        for row_id in ids:
            bind.execute(sa.text(f"DELETE FROM {table} WHERE id = :id"), {"id": row_id})
