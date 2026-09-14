"""riallinea nomenclatura profili/tipologie GEBAN

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-14
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence, Union
import json
import uuid

import sqlalchemy as sa
import yaml
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NAMESPACE = uuid.UUID("0b5f5d13-3b1a-4f97-b6d2-4f5c3b7df001")

CAMPI_DEMO = [
    ("codice_bando", "Codice bando", "Identificativo funzionale del bando", "string", True, "IT", 1, {"minLength": 1}),
    ("titolo_it", "Titolo", "Titolo italiano del bando", "string", True, "IT", 2, {"minLength": 1}),
    ("descrizione_ridotta_it", "Descrizione ridotta", "Sintesi italiana del bando", "string", False, "IT", 3, None),
    ("sede_prescelta_it", "Sede", "Sede associata alla procedura", "string", True, "IT", 4, {"minLength": 1}),
    ("numero_posti", "Numero posti", "Numero dei posti previsti", "number", True, "IT", 5, {"minimum": 1}),
    ("titolo_en", "Title", "Titolo inglese del bando", "string", True, "EN", 6, {"minLength": 1}),
]


def _uuid(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_catalogo() -> dict[str, Any]:
    path = _repo_root() / "infra" / "local" / "postgres" / "seed-demo-catalog.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["catalogo"]


def upgrade() -> None:
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

    for item in catalogo.get("tipologie_sol", []):
        bind.execute(
            sa.text(
                """
                INSERT INTO tipologia_bando_sol (id, codice, codice_sol, descrizione, attiva)
                VALUES (:id, :codice, :codice_sol, :descrizione, TRUE)
                ON CONFLICT (codice)
                DO UPDATE SET codice_sol = EXCLUDED.codice_sol,
                              descrizione = EXCLUDED.descrizione,
                              attiva = TRUE
                """
            ),
            {
                "id": tipologia_ids[item["codice"]],
                "codice": item["codice"],
                "codice_sol": item["codice_sol"],
                "descrizione": item["nome"],
            },
        )

    configured_tipologie = [item["codice"] for item in catalogo.get("tipologie_sol", [])]
    bind.execute(
        sa.text(
            """
            UPDATE tipologia_bando_sol
            SET attiva = FALSE
            WHERE codice NOT IN :configured_tipologie
            """
        ).bindparams(sa.bindparam("configured_tipologie", expanding=True)),
        {"configured_tipologie": configured_tipologie},
    )

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

    configured_categories = [item["codice"] for item in catalogo.get("categorie", [])]
    bind.execute(
        sa.text(
            """
            UPDATE categoria_documento
            SET stato = 'INATTIVA'
            WHERE tipo_documento_id = :tipo_documento_id
              AND codice NOT IN :configured_categories
            """
        ).bindparams(sa.bindparam("configured_categories", expanding=True)),
        {
            "tipo_documento_id": tipo_ids["BANDO_CONCORSO"],
            "configured_categories": configured_categories,
        },
    )

    bind.execute(
        sa.text(
            """
            UPDATE classificazione_catalogo
            SET attiva = FALSE
            WHERE tipo_documento_id = :tipo_documento_id
            """
        ),
        {"tipo_documento_id": tipo_ids["BANDO_CONCORSO"]},
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

    for index, item in enumerate(catalogo.get("modelli", []), start=1):
        codice_modello = item["modello_versione_id"]
        modello_id = _uuid(f"modello:{codice_modello}")
        versione_id = _uuid(f"versione:{codice_modello}")
        public_id = item.get("public_id", index)
        published_at = "2026-07-31T10:00:00+00:00" if item["stato"] == "PUBBLICATO" else None

        bind.execute(
            sa.text(
                """
                INSERT INTO modello_documento
                (id, public_id, tipo_documento_id, categoria_documento_id, tipologia_bando_sol_id, codice, nome, stato, variante)
                VALUES (:id, :public_id, :tipo_documento_id, :categoria_documento_id, :tipologia_bando_sol_id,
                        :codice, :nome, 'ATTIVA', 'STANDARD')
                ON CONFLICT (id)
                DO UPDATE SET
                  public_id = EXCLUDED.public_id,
                  categoria_documento_id = EXCLUDED.categoria_documento_id,
                  tipologia_bando_sol_id = EXCLUDED.tipologia_bando_sol_id,
                  nome = EXCLUDED.nome,
                  stato = 'ATTIVA'
                """
            ),
            {
                "id": modello_id,
                "public_id": public_id,
                "tipo_documento_id": tipo_ids[item["tipo_documento"]],
                "categoria_documento_id": categoria_ids[(item["tipo_documento"], item["categoria"])],
                "tipologia_bando_sol_id": tipologia_ids.get(item.get("codice_tipologia")),
                "codice": codice_modello,
                "nome": item.get("nome", codice_modello),
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO modello_versione
                (id, public_id, modello_documento_id, versione, stato, formato_documentale, struttura_documentale,
                 pubblicato_il, pubblicato_at)
                VALUES (:id, :public_id, :modello_documento_id, 1, :stato, 'GEMODO_DOCUMENT_V1',
                        CAST(:struttura_documentale AS jsonb), :pubblicato_at, :pubblicato_at)
                ON CONFLICT (id)
                DO UPDATE SET
                  public_id = EXCLUDED.public_id,
                  stato = EXCLUDED.stato,
                  formato_documentale = EXCLUDED.formato_documentale,
                  struttura_documentale = EXCLUDED.struttura_documentale,
                  pubblicato_il = EXCLUDED.pubblicato_il,
                  pubblicato_at = EXCLUDED.pubblicato_at
                """
            ),
            {
                "id": versione_id,
                "public_id": public_id,
                "modello_documento_id": modello_id,
                "stato": item["stato"],
                "struttura_documentale": json.dumps({"ref": item.get("formato_documentale_ref")}),
                "pubblicato_at": published_at,
            },
        )

        if item["stato"] != "PUBBLICATO":
            continue

        for codice, etichetta, descrizione, tipo_dato, obbligatorio, lingua, ordine, validazione in CAMPI_DEMO:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO campo_modello
                    (id, modello_versione_id, codice, etichetta, descrizione, tipo_dato, obbligatorio,
                     lingua, ordine, validazione)
                    VALUES (:id, :modello_versione_id, :codice, :etichetta, :descrizione, :tipo_dato,
                            :obbligatorio, :lingua, :ordine, CAST(:validazione AS jsonb))
                    ON CONFLICT (modello_versione_id, codice, lingua)
                    DO UPDATE SET
                      etichetta = EXCLUDED.etichetta,
                      descrizione = EXCLUDED.descrizione,
                      tipo_dato = EXCLUDED.tipo_dato,
                      obbligatorio = EXCLUDED.obbligatorio,
                      ordine = EXCLUDED.ordine,
                      validazione = EXCLUDED.validazione
                    """
                ),
                {
                    "id": _uuid(f"campo:{codice_modello}:{codice}:{lingua}"),
                    "modello_versione_id": versione_id,
                    "codice": codice,
                    "etichetta": etichetta,
                    "descrizione": descrizione,
                    "tipo_dato": tipo_dato,
                    "obbligatorio": obbligatorio,
                    "lingua": lingua,
                    "ordine": ordine,
                    "validazione": json.dumps(validazione) if validazione is not None else None,
                },
            )


def downgrade() -> None:
    """No-op: precedente nomenclatura (CTER/FUNZIONARIO_AMMINISTRATIVO/IR) e' considerata
    superata. Un downgrade non ripristina i vecchi codici; per tornare indietro,
    ripristinare seed-demo-catalog.yaml alla revisione precedente e rieseguire una
    migration equivalente a 0006."""
