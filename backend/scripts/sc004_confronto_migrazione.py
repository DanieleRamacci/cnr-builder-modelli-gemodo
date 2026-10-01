"""SC-004: la migrazione 0024 non cambia il testo di nessuna versione pubblicata (012 T011).

Va eseguito **prima** di applicare la migrazione in un ambiente che contenga
versioni pubblicate, non dopo per confermare che sia andata bene. Due fasi,
sullo stesso database:

1. ``prima``, con il codice **precedente** alla 012 e il database ancora a 0023:
   rende ogni versione pubblicata e salva il testo estratto.

       git worktree add /tmp/gemodo-pre-012 <commit-pre-012>
       PYTHONPATH=/tmp/gemodo-pre-012/backend \\
         uv run python scripts/sc004_confronto_migrazione.py prima --file sc004.json

2. ``dopo``, con il codice nuovo, dopo ``alembic upgrade head``: rende di nuovo e
   confronta coppia per coppia.

       uv run python scripts/sc004_confronto_migrazione.py dopo --file sc004.json

Si confronta il **testo estratto**, non i byte: un PDF contiene data di
produzione e identificatori che cambiano a ogni generazione, e da 012 anche un
font diverso. Gli spazi bianchi sono normalizzati per la stessa ragione.

I segnaposto ricevono un valore fac-simile fisso, lo stesso nelle due fasi:
cio' che si confronta e' il documento, non i dati di una generazione reale.

Una differenza fa uscire con codice 1 e **ferma la migrazione**: non si
corregge il confronto. Una versione che il codice vecchio non riusciva a rendere
affatto (il core font sollevava un'eccezione su una virgoletta curva, research.md
R1) non ha un "prima" con cui confrontarsi: e' elencata a parte, perche' la
decisione su di essa spetta a chi legge, non allo script.
"""

from __future__ import annotations

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import select

from app.builder.repository import composizione_documentale

try:
    from app.builder.repository import inizi_sezione
except ImportError:
    # Fase `prima`: il codice precedente alla 012 non conosce le sezioni in
    # resa, e prima della 012 non esistevano elenchi da numerare.
    inizi_sezione = None
from app.catalog.models import ModelloDocumentoVersione
from app.db.session import SessionLocal
from app.generazione.renderer import render_documento, sostituisci_placeholder

_TITOLO = "SC-004"


def _testo(pdf: bytes) -> str:
    return " ".join(" ".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages).split())


def _rendi_pubblicate() -> dict[str, dict[str, str]]:
    esiti: dict[str, dict[str, str]] = {}
    with SessionLocal() as db:
        versioni = db.scalars(
            select(ModelloDocumentoVersione).where(ModelloDocumentoVersione.stato == "PUBBLICATO")
        ).all()
        for versione in versioni:
            documento = composizione_documentale(versione)
            if not documento.blocchi:
                # Senza sezioni la resa e' l'elenco etichetta/valore, che non
                # legge i blocchi: la migrazione non la tocca.
                continue
            dati = {nome: f"VALORE-{nome}" for nome in documento.placeholder_usati}
            try:
                extra = {} if inizi_sezione is None else {"inizi_sezione": inizi_sezione(versione)}
                pdf = render_documento(
                    titolo=_TITOLO, blocchi=sostituisci_placeholder(documento.blocchi, dati), **extra,
                )
            except Exception as errore:  # noqa: BLE001 - e' proprio cio' che si vuole registrare
                esiti[str(versione.id)] = {"errore": f"{type(errore).__name__}: {errore}"}
            else:
                esiti[str(versione.id)] = {"testo": _testo(pdf)}
    return esiti


def prima(file: Path) -> int:
    esiti = _rendi_pubblicate()
    file.write_text(json.dumps(esiti, ensure_ascii=False, indent=2), encoding="utf-8")
    non_rese = [v for v, e in esiti.items() if "errore" in e]
    print(f"{len(esiti)} versioni pubblicate con sezioni, {len(non_rese)} non rese dal codice attuale -> {file}")
    return 0


def dopo(file: Path) -> int:
    attesi: dict[str, dict[str, str]] = json.loads(file.read_text(encoding="utf-8"))
    ottenuti = _rendi_pubblicate()

    differenze: list[str] = []
    non_confrontabili: list[str] = []
    for versione, atteso in attesi.items():
        ottenuto = ottenuti.get(versione)
        if ottenuto is None:
            differenze.append(f"{versione}: presente prima, assente dopo")
        elif "errore" in ottenuto:
            differenze.append(f"{versione}: dopo la migrazione non si rende piu' ({ottenuto['errore']})")
        elif "errore" in atteso:
            non_confrontabili.append(f"{versione}: prima non si rendeva ({atteso['errore']})")
        elif ottenuto["testo"] != atteso["testo"]:
            differenze.append(f"{versione}:\n  prima: {atteso['testo']}\n  dopo:  {ottenuto['testo']}")
    for versione in ottenuti.keys() - attesi.keys():
        differenze.append(f"{versione}: assente prima, presente dopo")

    confrontate = len(attesi) - len(non_confrontabili)
    print(f"{confrontate} versioni confrontate, {len(differenze)} differenze")
    for riga in non_confrontabili:
        print(f"NON CONFRONTABILE {riga}")
    for riga in differenze:
        print(f"DIFFERENZA {riga}")
    return 1 if differenze else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fase", choices=["prima", "dopo"])
    parser.add_argument("--file", type=Path, required=True)
    argomenti = parser.parse_args()
    return prima(argomenti.file) if argomenti.fase == "prima" else dopo(argomenti.file)


if __name__ == "__main__":
    sys.exit(main())
