"""Cornice di pagina a maschere e logo caricato (012 T065, T066).

La forma del 2026-10-01 mattina (`logo_ref`, `intestazione` e `pie_pagina`
come liste di frammenti, `numerazione_pagine`) diventa due parti indipendenti,
ciascuna con la propria maschera:

    {"logo_ref": "logo-ente", "intestazione": [...], "pie_pagina": [...], "numerazione_pagine": true}
      ->
    {"intestazione": {"maschera": "LOGO_CENTRO_TESTO_SOTTO", "con_logo": true, "testo": [...]},
     "pie_pagina": {"maschera": "TESTO_SINISTRA_NUMERO_DESTRA", "testo": [...], "numerazione_pagine": true}}

Un'intestazione vuota e senza logo sparisce, cosi' come un pie' di pagina senza
testo e senza numero. Il logo non sta piu' nel JSON ma in
`tipo_documento.logo_cornice`, un'immagine caricata dall'interfaccia: il file
fisso `logo-ente.png` sul server non c'era mai stato, quindi non c'e' nulla da
copiare.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None

_tipi = sa.table("tipo_documento", sa.column("id", sa.Uuid()), sa.column("cornice_pagina", JSONB()))


def _a_maschere(vecchia: dict) -> dict | None:
    forma_vecchia = (
        "logo_ref" in vecchia
        or "numerazione_pagine" in vecchia
        or isinstance(vecchia.get("intestazione"), list)
    )
    if not forma_vecchia:
        return vecchia
    testa = vecchia.get("intestazione") or []
    piede = vecchia.get("pie_pagina") or []
    con_logo = vecchia.get("logo_ref") is not None
    numerazione = vecchia.get("numerazione_pagine", True)
    nuova = {
        "intestazione": (
            {"maschera": "LOGO_CENTRO_TESTO_SOTTO", "con_logo": con_logo, "testo": testa}
            if testa or con_logo else None
        ),
        "pie_pagina": (
            {"maschera": "TESTO_SINISTRA_NUMERO_DESTRA", "testo": piede, "numerazione_pagine": numerazione}
            if piede or numerazione else None
        ),
    }
    return nuova if nuova["intestazione"] or nuova["pie_pagina"] else None


def _a_liste(nuova: dict) -> dict | None:
    testa = nuova.get("intestazione") or {}
    piede = nuova.get("pie_pagina") or {}
    return {
        "logo_ref": "logo-ente" if testa.get("con_logo") else None,
        "intestazione": testa.get("testo", []),
        "pie_pagina": piede.get("testo", []),
        "numerazione_pagine": bool(piede.get("numerazione_pagine", False)),
    }


def _converti(conversione) -> None:
    connessione = op.get_bind()
    for riga in connessione.execute(sa.select(_tipi.c.id, _tipi.c.cornice_pagina)).all():
        if riga.cornice_pagina is None:
            continue
        connessione.execute(
            _tipi.update().where(_tipi.c.id == riga.id).values(cornice_pagina=conversione(riga.cornice_pagina))
        )


def upgrade() -> None:
    op.add_column("tipo_documento", sa.Column("logo_cornice", sa.LargeBinary(), nullable=True))
    _converti(_a_maschere)


def downgrade() -> None:
    _converti(_a_liste)
    op.drop_column("tipo_documento", "logo_cornice")
