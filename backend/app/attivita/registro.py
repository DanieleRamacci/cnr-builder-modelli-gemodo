"""Scrivere un evento senza mai fermare l'azione che lo produce (013 FR-013).

Le validazioni e gli accessi negati sono informazioni, non condizioni: se il
registro non accetta l'evento, l'azione va avanti e l'errore finisce nel log
applicativo. Per questo l'evento si scrive in una sessione e in una transazione
sue, sullo stesso database della richiesta: non puo' annullare la transazione
dell'azione, ne' esserne annullato.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.attivita.models import EventoAttivita
from app.common.security import PrincipalGEMODO

logger = logging.getLogger("gemodo.attivita")

# Un dettaglio piu' grande si sostituisce con un avviso: l'evento si scrive lo
# stesso, e il registro non cresce per un payload sbagliato.
DETTAGLIO_MASSIMO = 4_000


def _dettaglio_contenuto(dettaglio: dict[str, Any]) -> dict[str, Any]:
    try:
        testo = json.dumps(dettaglio, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return {"troncato": True, "motivo": "dettaglio non serializzabile"}
    if len(testo) <= DETTAGLIO_MASSIMO:
        return json.loads(testo)
    return {"troncato": True, "inizio": testo[:DETTAGLIO_MASSIMO]}


def registra_attivita(
    bind: Engine | Connection | None,
    *,
    categoria: str,
    azione: str,
    esito: str,
    principal: PrincipalGEMODO | None = None,
    contesto: str | None = None,
    oggetto_tipo: str | None = None,
    oggetto_id: str | None = None,
    dettaglio: dict[str, Any] | None = None,
) -> None:
    if bind is None:
        logger.warning("Evento %s/%s non registrato: database della richiesta sconosciuto", categoria, azione)
        return
    try:
        with Session(bind=bind) as sessione:
            sessione.add(EventoAttivita(
                categoria=categoria, azione=azione, esito=esito,
                soggetto=principal.subject if principal else None,
                username=(principal.username or None) if principal else None,
                client_id=principal.client_id if principal else None,
                contesto=contesto, oggetto_tipo=oggetto_tipo,
                oggetto_id=oggetto_id[:255] if oggetto_id else None,
                dettaglio=_dettaglio_contenuto(dettaglio or {}),
            ))
            sessione.commit()
    except Exception:  # noqa: BLE001 - il registro non deve mai far cadere l'azione
        logger.exception("Evento %s/%s non registrato", categoria, azione)
