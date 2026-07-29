"""Validation helpers for requesting systems, technical clients and integration profiles.

Encodes the Keycloak/GEMODO authorization boundary (spec 009, FR-033..FR-035;
``infra/local/keycloak/authorization-boundary.local.yaml``): Keycloak is the source of
identity, technical clients, audience and coarse roles/claims; GEMODO owns fine-grained
authorization on integration profiles, document types, categories, typologies, model
versions, data contracts and operations. A valid Keycloak client identity is never
sufficient on its own - it must also resolve to an ACTIVE GEMODO integration profile
that explicitly allows the requested operation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.quality.errors import ContrattoNonValidoError, PrerequisitoMancanteError
from app.quality.manifest_loader import load_yaml
from app.quality.schemas import (
    PermessoOperativo,
    ProfiloDiIntegrazione,
    SistemaRichiedente,
    StatoProfiloIntegrazione,
    StatoSistemaRichiedente,
)


def load_sistemi_richiedenti(path: Path) -> list[SistemaRichiedente]:
    """Load and parse ``infra/local/integration-profiles.local.yaml``."""

    data = load_yaml(path)
    if not isinstance(data, dict) or "sistemi_richiedenti" not in data:
        raise ContrattoNonValidoError(
            str(path), ["il manifest deve avere una chiave 'sistemi_richiedenti'"]
        )
    raw_sistemi: list[dict[str, Any]] = data["sistemi_richiedenti"] or []
    return [SistemaRichiedente.model_validate(item) for item in raw_sistemi]


def validate_sistema_richiedente(sistema: SistemaRichiedente) -> None:
    """Every requesting system must have at least one technical client configured.

    A system without any client and without a documented blocking decision cannot be
    used operationally; this function only checks the manifest-local invariant (no
    client at all). Cross-checking against the open-decisions register is the
    responsibility of ``decision.py`` / ``readiness_gate.py``.
    """

    if not sistema.client_applicativi:
        raise PrerequisitoMancanteError(
            servizio=f"sistema-richiedente:{sistema.codice}",
            dettaglio="nessun client applicativo configurato",
        )


def validate_profilo(profilo: ProfiloDiIntegrazione) -> None:
    """An ACTIVE profile must declare a system, admitted clients and at least one operation."""

    if profilo.stato != StatoProfiloIntegrazione.ATTIVO:
        return
    violazioni: list[str] = []
    if not profilo.sistema_richiedente:
        violazioni.append("profilo attivo senza sistema_richiedente")
    if not profilo.client_ammessi:
        violazioni.append("profilo attivo senza client_ammessi")
    if not profilo.permessi_operativi:
        violazioni.append("profilo attivo senza permessi_operativi")
    if violazioni:
        raise ContrattoNonValidoError(profilo.codice, violazioni)


def _valore_ammesso(valore: str | None, ammessi: list[str]) -> bool:
    """Allow-list semantics: no value requested -> pass; value requested -> must be listed.

    An empty allow-list denies every explicit value (least-privilege default), it does
    not mean "unrestricted".
    """

    if valore is None:
        return True
    return valore in ammessi


def trova_profilo_attivo(
    sistema: SistemaRichiedente, profilo_codice: str
) -> ProfiloDiIntegrazione | None:
    for profilo in sistema.profili_integrazione:
        if profilo.codice == profilo_codice and profilo.stato == StatoProfiloIntegrazione.ATTIVO:
            return profilo
    return None


def is_operazione_autorizzata(
    sistema: SistemaRichiedente,
    *,
    client_id: str,
    profilo_codice: str,
    operazione: PermessoOperativo,
    tipo_documento: str | None = None,
    categoria: str | None = None,
    modello_versione: str | None = None,
) -> bool:
    """Decide whether an operation is authorized for a given client + profile.

    A valid Keycloak client identity (``client_id``) is a precondition, not a
    sufficient condition: the system must be ATTIVO, the client must belong to it, the
    named profile must be ATTIVO and admit that client, and the profile must
    explicitly allow the operation and (when provided) the document type, category and
    model version.
    """

    if sistema.stato != StatoSistemaRichiedente.ATTIVO:
        return False
    if client_id not in [c.client_id for c in sistema.client_applicativi]:
        return False

    profilo = trova_profilo_attivo(sistema, profilo_codice)
    if profilo is None:
        return False
    if client_id not in profilo.client_ammessi:
        return False
    if operazione not in profilo.permessi_operativi:
        return False
    if not _valore_ammesso(tipo_documento, profilo.tipi_documento_ammessi):
        return False
    if not _valore_ammesso(categoria, profilo.categorie_ammessi):
        return False
    if not _valore_ammesso(modello_versione, profilo.modelli_versioni_ammessi):
        return False
    return True
