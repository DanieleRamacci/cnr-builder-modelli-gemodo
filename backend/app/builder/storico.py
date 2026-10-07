"""Storico di un modello: chi ha fatto cosa, quando, su quale versione e da dove.

Mette insieme gli eventi di audit del modello (`audit_evento_modello`) e le
generazioni dalle sue versioni (`documento_generato`), in ordine dal piu'
recente. Non scrive nulla: legge cio' che i due registri gia' conservano.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import AuditEventoModello, ModelloDocumentoVersione
from app.storage.models import DocumentoGenerato

Canale = Literal["INTERFACCIA", "API"]

# Gli eventi che fanno nascere un modello: chi li ha registrati lo ha creato.
EVENTI_CREAZIONE = ("MODELLO_CREATO", "MODELLO_VARIANTE_CREATA", "MODELLO_DERIVATO_CREATO")

DESCRIZIONI = {
    "MODELLO_CREATO": "Modello creato",
    "MODELLO_VARIANTE_CREATA": "Variante creata",
    "MODELLO_DERIVATO_CREATO": "Edizione derivata creata",
    "MODELLO_ELIMINATO": "Modello eliminato",
    "VERSIONE_CREATA": "Versione creata",
    "SEZIONI_AGGIORNATE": "Documento modificato",
    "VERSIONE_BOZZA": "Riportata in bozza",
    "VERSIONE_IN_REVISIONE": "Inviata in revisione",
    "VERSIONE_APPROVATO": "Approvata",
    "VERSIONE_PUBBLICATO": "Pubblicata",
    "VERSIONE_SOSPESO": "Sospesa",
    "VERSIONE_ARCHIVIATO": "Archiviata",
    "VERSIONE_ARCHIVIATA": "Archiviata (sostituita da una nuova pubblicazione)",
    "DOCUMENTO_GENERATO": "Documento generato",
    "GENERAZIONE_FALLITA": "Generazione non riuscita",
    "GENERAZIONE_DATI_NON_VALIDI": "Generazione rifiutata: dati non validi",
}


class EventoStorico(BaseModel):
    quando: datetime
    utente: str
    canale: Canale
    client_id: str | None = None
    azione: str
    descrizione: str
    versione: int | None = None
    dettaglio: dict[str, Any] = {}


def creatori(db: Session, modello_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Username di chi ha creato ciascun modello (l'id del token se manca)."""
    if not modello_ids:
        return {}
    righe = db.execute(
        select(AuditEventoModello.modello_documento_id, AuditEventoModello.username, AuditEventoModello.soggetto_id)
        .where(AuditEventoModello.modello_documento_id.in_(modello_ids))
        .where(AuditEventoModello.tipo_evento.in_(EVENTI_CREAZIONE))
        .order_by(AuditEventoModello.created_at)
    )
    risultato: dict[uuid.UUID, str] = {}
    for modello_id, username, soggetto in righe:
        risultato.setdefault(modello_id, username or soggetto)
    return risultato


def _canale(client_id: str | None, interattivi: frozenset[str]) -> Canale:
    return "INTERFACCIA" if client_id in interattivi else "API"


def _descrizione_sezioni(dettaglio: dict[str, Any]) -> str:
    parti = []
    for chiave, etichetta in (("aggiunte", "aggiunte"), ("modificate", "modificate"), ("rimosse", "rimosse")):
        if dettaglio.get(chiave):
            parti.append(f"{etichetta}: {', '.join(dettaglio[chiave])}")
    if dettaglio.get("riordinate"):
        parti.append("ordine delle sezioni cambiato")
    if parti:
        return "Documento modificato - sezioni " + "; ".join(parti)
    if "aggiunte" in dettaglio:
        return "Documento salvato senza modifiche"
    return DESCRIZIONI["SEZIONI_AGGIORNATE"]


def storico_modello(db: Session, modello_id: uuid.UUID, interattivi: frozenset[str]) -> list[EventoStorico]:
    numeri = dict(db.execute(
        select(ModelloDocumentoVersione.id, ModelloDocumentoVersione.versione)
        .where(ModelloDocumentoVersione.modello_documento_id == modello_id)
    ).all())
    eventi: list[EventoStorico] = []
    for evento in db.scalars(
        select(AuditEventoModello).where(AuditEventoModello.modello_documento_id == modello_id)
    ):
        dettaglio = dict(evento.payload_minimo or {})
        descrizione = (
            _descrizione_sezioni(dettaglio) if evento.tipo_evento == "SEZIONI_AGGIORNATE"
            else DESCRIZIONI.get(evento.tipo_evento, evento.tipo_evento)
        )
        eventi.append(EventoStorico(
            quando=evento.created_at,
            utente=evento.username or evento.soggetto_id,
            canale=_canale(evento.client_id, interattivi),
            client_id=evento.client_id,
            azione=evento.tipo_evento,
            descrizione=descrizione,
            versione=numeri.get(evento.modello_versione_id),
            dettaglio=dettaglio,
        ))
    if numeri:
        for generazione in db.scalars(
            select(DocumentoGenerato).where(DocumentoGenerato.modello_versione_id.in_(list(numeri)))
        ):
            azione = {
                "COMPLETATO": "DOCUMENTO_GENERATO",
                "FALLITO": "GENERAZIONE_FALLITA",
                "DATI_NON_VALIDI": "GENERAZIONE_DATI_NON_VALIDI",
            }.get(generazione.stato, "DOCUMENTO_GENERATO")
            eventi.append(EventoStorico(
                quando=generazione.created_at,
                utente=generazione.username or generazione.creato_da,
                canale=_canale(generazione.client_id, interattivi),
                client_id=generazione.client_id,
                azione=azione,
                descrizione=f"{DESCRIZIONI[azione]} per {generazione.sistema_richiedente} "
                            f"(chiave {generazione.external_context_id})",
                versione=numeri.get(generazione.modello_versione_id),
                dettaglio={
                    "riferimento": generazione.riferimento,
                    "sistema_richiedente": generazione.sistema_richiedente,
                    "external_context_id": generazione.external_context_id,
                },
            ))
    return sorted(eventi, key=lambda e: e.quando, reverse=True)
