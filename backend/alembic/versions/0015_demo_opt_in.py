"""Leave pristine installations without demo models; preserve used databases."""

import os
import uuid
from pathlib import Path

import sqlalchemy as sa
import yaml
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    if os.environ.get("GEMODO_KEEP_DEMO_MODELS") == "1":
        return
    bind = op.get_bind()
    catalog = yaml.safe_load((Path(__file__).resolve().parents[3] / "infra/local/postgres/seed-demo-catalog.yaml").read_text())["catalogo"]
    namespace = uuid.UUID("0b5f5d13-3b1a-4f97-b6d2-4f5c3b7df001")
    ids = [uuid.uuid5(namespace, f"modello:{item['modello_versione_id']}") for item in catalog["modelli"]]
    models = sa.table("modello_documento", sa.column("id", sa.Uuid()))
    used = bind.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM integrazione) OR EXISTS (SELECT 1 FROM documento_generato)"))
    if used or bind.scalar(sa.select(sa.func.count()).select_from(models).where(models.c.id.not_in(ids))):
        return
    bind.execute(sa.delete(models).where(models.c.id.in_(ids)))


def downgrade():
    pass
