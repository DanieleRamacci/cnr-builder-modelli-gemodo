"""Il testo dei blocchi diventa una sequenza di frammenti (012 FR-016, T009).

`sezione_modello.contenuto` serializza una lista di blocchi. Fino a qui ogni
blocco portava il proprio testo in una stringa, `contenuto`; dalla 012 lo porta
in `frammenti`, ognuno con la propria enfasi. Il formato ha **una sola forma**:
vecchia e nuova non coesistono, quindi si converte tutto, versioni pubblicate
comprese.

    {"tipo": "PARAGRAFO", "contenuto": "VISTO il D.Lgs 127/2003"}
      ->
    {"tipo": "PARAGRAFO", "frammenti": [{"testo": "VISTO il D.Lgs 127/2003"}]}

`contenuto: null` diventa `frammenti: []`. Una stringa vuota diventa un
frammento vuoto e non una lista vuota, cosi' che il giro completo
upgrade/downgrade restituisca esattamente cio' che c'era.

E' una riscrittura di **codifica**, non di contenuto. La prova non e' questo
argomento ma SC-004 (tasks.md T011): prima di applicarla in un ambiente con
versioni pubblicate si confronta il testo estratto dai PDF prima e dopo.

`downgrade` concatena i `testo`: esatto per i dati prodotti da questa
migrazione, con perdita dell'enfasi per quelli scritti dopo. E' voluto:
tornare al formato vecchio *significa* perdere cio' che il formato vecchio non
sa rappresentare. Per la stessa ragione un `ELENCO`, che prima non esisteva,
torna `PARAGRAFO` con una voce per riga, e `allineamento` si perde.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_sezioni = sa.table(
    "sezione_modello",
    sa.column("id", sa.Uuid()),
    sa.column("contenuto", JSONB()),
)


def _a_frammenti(blocco: dict[str, Any]) -> dict[str, Any]:
    if "contenuto" not in blocco:
        return blocco
    nuovo = {chiave: valore for chiave, valore in blocco.items() if chiave != "contenuto"}
    testo = blocco["contenuto"]
    nuovo["frammenti"] = [] if testo is None else [{"testo": testo}]
    return nuovo


def _testo(frammenti: list[dict[str, Any]]) -> str:
    return "".join(frammento.get("testo", "") for frammento in frammenti)


def _a_contenuto(blocco: dict[str, Any]) -> dict[str, Any]:
    if "frammenti" not in blocco:
        return blocco
    vecchio = {
        chiave: valore for chiave, valore in blocco.items()
        if chiave not in ("frammenti", "allineamento", "elementi")
    }
    if blocco.get("tipo") == "ELENCO":
        vecchio["tipo"] = "PARAGRAFO"
        righe = [_testo(elemento.get("frammenti", [])) for elemento in blocco.get("elementi", [])]
        vecchio["contenuto"] = "\n".join(righe) if righe else None
    else:
        frammenti = blocco["frammenti"]
        vecchio["contenuto"] = _testo(frammenti) if frammenti else None
    return vecchio


def _converti(conversione) -> None:
    connessione = op.get_bind()
    righe = connessione.execute(sa.select(_sezioni.c.id, _sezioni.c.contenuto)).all()
    for identificativo, blocchi in righe:
        convertiti = [conversione(blocco) for blocco in blocchi or []]
        if convertiti != (blocchi or []):
            connessione.execute(
                _sezioni.update().where(_sezioni.c.id == identificativo).values(contenuto=convertiti)
            )


def upgrade() -> None:
    _converti(_a_frammenti)


def downgrade() -> None:
    _converti(_a_contenuto)
