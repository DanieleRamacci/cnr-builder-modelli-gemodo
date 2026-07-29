#!/usr/bin/env python3
"""Mock GEBAN scenario runner (skeleton).

Resolves an E2E-00X scenario (``mock-geban/scenarios/minimum-e2e.yaml``) into an
ordered list of steps against GEMODO's PUBLIC contract operations only - catalogo,
campi richiesti, validazione, generazione, stato, download - never internal builder or
database shortcuts (``mock-geban-scenarios.yaml``, ``coverage_requirements``); every
step is checked by ``app.quality.mock_contract_guard`` before being scheduled.

This is a *skeleton*: specs 001/004/005/006 have not implemented the real GEMODO HTTP
API yet (no ``tasks.md`` for those features - see AGENTS.md), so there is nothing to
call over the network yet. Without an injected client this script only resolves and
prints the execution plan (dry run). Once a real client implementing
:class:`ClienteGemodo` exists, pass it to :func:`esegui_scenario` to run the scenario
end-to-end for real.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

MOCK_GEBAN_DIR = Path(__file__).resolve().parent
REPO_ROOT = MOCK_GEBAN_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.quality.mock_contract_guard import (  # noqa: E402
    OperazionePubblica,
    assert_no_internal_shortcut,
)
from app.quality.scenario import load_scenario_manifest, parse_scenarios  # noqa: E402
from app.quality.schemas import ScenarioEndToEnd  # noqa: E402

SCENARIOS_PATH = MOCK_GEBAN_DIR / "scenarios" / "minimum-e2e.yaml"
PAYLOADS_DIR = MOCK_GEBAN_DIR / "payloads"

# Mappa dai testi liberi 'required_contracts' del contratto/manifest alle operazioni
# pubbliche GEMODO che il runner sa risolvere.
CONTRATTO_A_OPERAZIONE: dict[str, OperazionePubblica] = {
    "catalogo modelli pubblicati": OperazionePubblica.CATALOGO_MODELLI,
    "campi richiesti/schema": OperazionePubblica.CAMPI_RICHIESTI,
    "validazione payload": OperazionePubblica.VALIDA_PAYLOAD,
    "generazione documento": OperazionePubblica.GENERA_DOCUMENTO,
    "stato generazione": OperazionePubblica.STATO_GENERAZIONE,
    "download documento": OperazionePubblica.DOWNLOAD_DOCUMENTO,
}


@dataclass(frozen=True)
class PassoScenario:
    operazione: OperazionePubblica
    descrizione: str


def risolvi_passi(scenario: ScenarioEndToEnd) -> list[PassoScenario]:
    """Resolve a scenario's declared contracts into ordered public-operation steps."""

    passi: list[PassoScenario] = []
    for riferimento in scenario.contratti_coinvolti:
        assert_no_internal_shortcut(riferimento)
        operazione = CONTRATTO_A_OPERAZIONE.get(riferimento)
        if operazione is None:
            raise ValueError(f"contratto non mappato a un'operazione pubblica nota: {riferimento!r}")
        passi.append(PassoScenario(operazione=operazione, descrizione=riferimento))
    return passi


class ClienteGemodo(Protocol):
    """Boundary verso le operazioni pubbliche GEMODO.

    Nessuna implementazione reale esiste ancora in questa feature: le spec
    001/004/005/006 la forniranno quando i loro endpoint saranno implementati (vedi
    AGENTS.md - nessun codice applicativo prima del tasks.md della relativa feature).
    """

    def esegui(self, operazione: OperazionePubblica, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class RisultatoPasso:
    passo: PassoScenario
    eseguito: bool
    esito: dict[str, Any] | None = None


@dataclass
class RisultatoScenario:
    scenario_id: str
    passi: list[RisultatoPasso] = field(default_factory=list)

    @property
    def piano_eseguito(self) -> bool:
        return all(p.eseguito for p in self.passi)


def carica_payload_demo(nome_file: str) -> dict[str, Any]:
    path = PAYLOADS_DIR / nome_file
    return json.loads(path.read_text(encoding="utf-8"))


def esegui_scenario(
    scenario: ScenarioEndToEnd,
    *,
    payload: dict[str, Any] | None = None,
    client: ClienteGemodo | None = None,
) -> RisultatoScenario:
    """Resolve a scenario's steps and, if a client is provided, execute them for real.

    Without a client this only builds the execution plan (dry run): every step comes
    back with ``eseguito=False``. This is enough to verify a scenario is well-formed
    and references only public contract operations, without depending on a live
    GEMODO backend.
    """

    passi = risolvi_passi(scenario)
    risultato = RisultatoScenario(scenario_id=scenario.id)
    for passo in passi:
        if client is None:
            risultato.passi.append(RisultatoPasso(passo=passo, eseguito=False))
            continue
        esito = client.esegui(passo.operazione, payload or {})
        risultato.passi.append(RisultatoPasso(passo=passo, eseguito=True, esito=esito))
    return risultato


def _carica_scenario(scenario_id: str) -> ScenarioEndToEnd:
    manifest = load_scenario_manifest(SCENARIOS_PATH)
    scenari = {s.id: s for s in parse_scenarios(manifest)}
    scenario = scenari.get(scenario_id)
    if scenario is None:
        raise SystemExit(f"scenario sconosciuto: {scenario_id} (disponibili: {', '.join(sorted(scenari))})")
    return scenario


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", required=True, help="Scenario id, es. E2E-001")
    parser.add_argument("--payload", help="Nome file payload demo in mock-geban/payloads/ (opzionale)")
    args = parser.parse_args(argv)

    scenario = _carica_scenario(args.scenario)
    payload = carica_payload_demo(args.payload) if args.payload else None
    risultato = esegui_scenario(scenario, payload=payload, client=None)

    print(f"Piano scenario {risultato.scenario_id} (dry run, nessun client GEMODO configurato):")
    for r in risultato.passi:
        print(f"  - {r.passo.operazione.value}: {r.passo.descrizione}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
