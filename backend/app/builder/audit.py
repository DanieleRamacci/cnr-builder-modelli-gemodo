"""Audit trail for builder model/version creation and state transitions (FR-008)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.catalog.models import AuditEventoModello
from app.common.security import PrincipalGEMODO


def registra_evento(
    db: Session,
    *,
    tipo_evento: str,
    principal: PrincipalGEMODO,
    modello_documento_id: uuid.UUID,
    modello_versione_id: uuid.UUID | None,
    payload_minimo: dict[str, Any],
) -> AuditEventoModello:
    evento = AuditEventoModello(
        id=uuid.uuid4(),
        tipo_evento=tipo_evento,
        soggetto_id=principal.subject,
        client_id=principal.client_id,
        ruoli=list(principal.ruoli),
        modello_documento_id=modello_documento_id,
        modello_versione_id=modello_versione_id,
        payload_minimo=payload_minimo,
    )
    db.add(evento)
    db.flush()
    return evento
