"""In-memory fake GEMODO client for exercising the mock-GEBAN scenario runner.

Specs 001/004/005/006 have not implemented the real GEMODO HTTP API yet (no
``tasks.md`` - see AGENTS.md), so there is nothing to call over the network. This
test-only fake stands in for that not-yet-built backend so User Story 2's
scenario-runner orchestration, idempotency and authorization *plumbing* can be
exercised end-to-end. Authorization decisions are delegated to the real
``app.quality.integration_profile.is_operazione_autorizzata`` rather than
reimplemented here, so what is actually under test is 009's own authorization logic,
not a duplicate of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.quality.integration_profile import is_operazione_autorizzata
from app.quality.mock_contract_guard import OperazionePubblica
from app.quality.schemas import PermessoOperativo, SistemaRichiedente


class GemodoErroreFunzionale(Exception):
    """Mirrors the {codice, messaggio} shape of infra/openapi/errors.md entries."""

    def __init__(self, codice: str, messaggio: str) -> None:
        self.codice = codice
        self.messaggio = messaggio
        super().__init__(f"{codice}: {messaggio}")


_PERMESSO_PER_OPERAZIONE: dict[OperazionePubblica, PermessoOperativo] = {
    OperazionePubblica.CATALOGO_MODELLI: PermessoOperativo.CATALOGO,
    OperazionePubblica.CAMPI_RICHIESTI: PermessoOperativo.CATALOGO,
    OperazionePubblica.VALIDA_PAYLOAD: PermessoOperativo.VALIDAZIONE,
    OperazionePubblica.GENERA_DOCUMENTO: PermessoOperativo.GENERAZIONE_BOZZA,
    OperazionePubblica.STATO_GENERAZIONE: PermessoOperativo.STATO,
    OperazionePubblica.DOWNLOAD_DOCUMENTO: PermessoOperativo.DOWNLOAD,
}


@dataclass
class GenerazioneRegistrata:
    dati: dict[str, Any]
    stato: str
    output: list[dict[str, str]]


@dataclass
class FakeGemodoClient:
    """Deterministic in-memory stand-in for the GEMODO public contract operations."""

    sistema: SistemaRichiedente
    profilo_codice: str
    forza_fallimento: bool = False
    _generazioni: dict[tuple[str, ...], GenerazioneRegistrata] = field(default_factory=dict)

    def esegui(self, operazione: OperazionePubblica, payload: dict[str, Any]) -> dict[str, Any]:
        self._autorizza(operazione, payload)
        metodo = getattr(self, f"_{operazione.value}")
        return metodo(payload)

    def _autorizza(self, operazione: OperazionePubblica, payload: dict[str, Any]) -> None:
        permesso = _PERMESSO_PER_OPERAZIONE[operazione]
        autorizzato = is_operazione_autorizzata(
            self.sistema,
            client_id=payload.get("client_id", ""),
            profilo_codice=self.profilo_codice,
            operazione=permesso,
            tipo_documento=payload.get("tipo_documento"),
        )
        if not autorizzato:
            raise GemodoErroreFunzionale(
                "PROFILO_INTEGRAZIONE_NON_ABILITATO",
                f"client/profilo non abilitato per l'operazione {operazione.value}",
            )

    def _catalogo_modelli(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"modelli": ["demo-bando-concorso-standard-v1"]}

    def _campi_richiesti(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"campi": ["codice_bando", "numero_posti", "titolo_it"]}

    def _valida_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        errori = list(payload.get("atteso_errori", []))
        return {"valido": not errori, "errori": errori}

    @staticmethod
    def _chiave(payload: dict[str, Any]) -> tuple[str, ...]:
        return (
            str(payload.get("sistema_richiedente")),
            str(payload.get("external_context_id")),
            str(payload.get("modello_versione_id")),
            "BOZZA",
        )

    def _genera_documento(self, payload: dict[str, Any]) -> dict[str, Any]:
        validazione = self._valida_payload(payload)
        if not validazione["valido"]:
            raise GemodoErroreFunzionale("CAMPO_OBBLIGATORIO", "payload non valido")

        chiave = self._chiave(payload)
        esistente = self._generazioni.get(chiave)
        if esistente is not None:
            if esistente.dati == payload.get("dati"):
                return {"stato": esistente.stato, "output": esistente.output, "riutilizzato": True}
            raise GemodoErroreFunzionale(
                "GENERAZIONE_CONFLITTO_IDEMPOTENTE", "chiave idempotente con dati divergenti"
            )

        if self.forza_fallimento:
            self._generazioni[chiave] = GenerazioneRegistrata(
                dati=payload.get("dati", {}), stato="FALLITA", output=[]
            )
            raise GemodoErroreFunzionale("GENERAZIONE_FALLITA", "generazione non completata")

        output = [{"tipo_output": "BOZZA", "lingua": "IT"}]
        if payload.get("bando_inglese"):
            output.append({"tipo_output": "BOZZA", "lingua": "EN"})
        registrazione = GenerazioneRegistrata(dati=payload.get("dati", {}), stato="COMPLETATA", output=output)
        self._generazioni[chiave] = registrazione
        return {"stato": registrazione.stato, "output": registrazione.output, "riutilizzato": False}

    def _stato_generazione(self, payload: dict[str, Any]) -> dict[str, Any]:
        registrazione = self._generazioni.get(self._chiave(payload))
        if registrazione is None:
            raise GemodoErroreFunzionale("MODELLO_NON_TROVATO", "generazione non trovata")
        return {"stato": registrazione.stato}

    def _download_documento(self, payload: dict[str, Any]) -> dict[str, Any]:
        registrazione = self._generazioni.get(self._chiave(payload))
        if registrazione is None or registrazione.stato != "COMPLETATA":
            raise GemodoErroreFunzionale("DOCUMENTO_NON_DISPONIBILE", "documento non disponibile")
        return {"output": registrazione.output}
