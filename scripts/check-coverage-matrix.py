#!/usr/bin/env python3
"""Cancello di coerenza fra requisiti delle spec e matrice di copertura.

Nasce dalla riconciliazione del 2026-09-22: le spec `007` e `010` erano le piu'
sviluppate del progetto e non avevano una sola riga in
`docs/quality-coverage-matrix.yaml`. Tutti i difetti trovati in quella sessione
(avvisi statici presentati come dati reali, dimensioni hardcoded, percorsi
legacy ancora raggiungibili) erano in quelle due spec; nessuno nelle spec gia'
coperte dalla matrice.

Funziona **a cricchetto**, non a soglia assoluta. Pretendere subito una riga per
ognuno dei ~200 requisiti gia' scritti farebbe fallire la build il primo giorno,
e un cancello che fallisce sempre viene disattivato. Quindi:

- i requisiti oggi scoperti sono congelati in `coverage-baseline.yaml`;
- un requisito **nuovo** senza copertura fa fallire la build;
- un requisito che esce dalla baseline non puo' rientrarci: la baseline puo'
  solo restringersi, e lo script dice di quanto.

Fallisce sempre, senza deroghe, su: identificativi duplicati e `contract_ref`
che punta a un file inesistente (l'ancora `#NOME` e' ammessa). Sono errori di
integrita', non debito.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MATRICE = ROOT / "docs" / "quality-coverage-matrix.yaml"
BASELINE = ROOT / "docs" / "coverage-baseline.yaml"
SPECS = ROOT / "specs"


def requisiti_dichiarati(spec_md: Path) -> set[str]:
    testo = spec_md.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"^- \*\*(FR-\d+)\*\*", testo, flags=re.MULTILINE))


def scoperti_attuali() -> set[tuple[str, str]]:
    righe = yaml.safe_load(MATRICE.read_text(encoding="utf-8"))["coverage"]
    coperti = {
        (riga["spec_owner"].rstrip("/").split("/")[-1], riga["requirement_id"]) for riga in righe
    }
    scoperti: set[tuple[str, str]] = set()
    for directory in sorted(SPECS.iterdir()):
        spec_md = directory / "spec.md"
        if not directory.is_dir() or not spec_md.exists():
            continue
        for fr in requisiti_dichiarati(spec_md):
            if (directory.name, fr) not in coperti:
                scoperti.add((directory.name, fr))
    return scoperti


def carica_baseline() -> set[tuple[str, str]]:
    if not BASELINE.exists():
        return set()
    dati = yaml.safe_load(BASELINE.read_text(encoding="utf-8")) or {}
    return {
        (spec, fr)
        for spec, requisiti in (dati.get("scoperti") or {}).items()
        for fr in (requisiti or [])
    }


def scrivi_baseline(scoperti: set[tuple[str, str]]) -> None:
    per_spec: dict[str, list[str]] = {}
    for spec, fr in sorted(scoperti):
        per_spec.setdefault(spec, []).append(fr)
    intestazione = (
        "# Requisiti senza riga in docs/quality-coverage-matrix.yaml, congelati\n"
        "# al 2026-09-22 da scripts/check-coverage-matrix.py.\n"
        "#\n"
        "# Questo file e' un cricchetto: puo' solo restringersi. Quando si copre un\n"
        "# requisito lo si toglie da qui; lo script rifiuta di vederlo ricomparire.\n"
        "# Un requisito nuovo NON va aggiunto qui: va coperto.\n"
        "#\n"
        "# Rigenerare con: python scripts/check-coverage-matrix.py --aggiorna-baseline\n"
        "# (solo per restringere, mai per assorbire un buco nuovo).\n\n"
    )
    BASELINE.write_text(
        intestazione + yaml.safe_dump({"scoperti": per_spec}, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    righe = yaml.safe_load(MATRICE.read_text(encoding="utf-8"))["coverage"]
    bloccanti: list[str] = []

    identificativi = [riga["id"] for riga in righe]
    for duplicato in sorted({i for i in identificativi if identificativi.count(i) > 1}):
        bloccanti.append(f"id duplicato nella matrice: {duplicato}")

    for riga in righe:
        percorso = riga["contract_ref"].split("#", 1)[0]
        if not (ROOT / percorso).exists():
            bloccanti.append(f"{riga['id']}: contract_ref inesistente -> {percorso}")

    scoperti = scoperti_attuali()

    if "--aggiorna-baseline" in argv:
        precedente = carica_baseline()
        cresciuta = scoperti - precedente
        if cresciuta and "--forza" not in argv:
            print("Rifiuto di allargare la baseline. Requisiti nuovi da coprire:\n")
            for spec, fr in sorted(cresciuta):
                print(f"  - {spec}: {fr}")
            return 1
        scrivi_baseline(scoperti)
        print(f"Baseline aggiornata: {len(scoperti)} requisiti scoperti (erano {len(precedente)}).")
        return 0

    baseline = carica_baseline()
    nuovi = sorted(scoperti - baseline)
    risolti = sorted(baseline - scoperti)

    for spec, fr in nuovi:
        bloccanti.append(f"{spec}: {fr} non ha riga di copertura e non e' nella baseline")

    if bloccanti:
        print("Matrice di copertura incoerente:\n")
        for violazione in bloccanti:
            print(f"  - {violazione}")
        print(f"\n{len(bloccanti)} violazioni. Vedi {MATRICE.relative_to(ROOT)}.")
        return 1

    print(f"Matrice coerente: {len(righe)} righe, {len(scoperti)} requisiti ancora scoperti (baseline {len(baseline)}).")
    if risolti:
        print(f"{len(risolti)} requisiti sono usciti dalla baseline: rigenerala con --aggiorna-baseline.")
        for spec, fr in risolti:
            print(f"  + {spec}: {fr}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
