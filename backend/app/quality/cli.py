"""CLI entrypoint for the feature-009 quality readiness checks.

Usage::

    uv run gemodo-quality verifica-ambiente

Exit codes follow the VerificaAmbiente outcome so the command is usable in CI/setup
scripts: ``0`` for PASS, ``1`` for PARTIAL, ``2`` for FAIL.
"""

from __future__ import annotations

import argparse
import sys

from app.quality.environment import ambiente_locale_default, validate_ambiente_locale
from app.quality.environment_verifier import verifica_ambiente
from app.quality.errors import QualityError
from app.quality.probes import probes_ambiente_locale
from app.quality.schemas import EsitoVerifica

_EXIT_CODE = {
    EsitoVerifica.PASS_: 0,
    EsitoVerifica.PARTIAL: 1,
    EsitoVerifica.FAIL: 2,
}


def _cmd_verifica_ambiente(_: argparse.Namespace) -> int:
    ambiente = ambiente_locale_default()
    try:
        validate_ambiente_locale(ambiente)
    except QualityError as exc:
        print(f"ambiente non valido: {exc}", file=sys.stderr)
        return 2

    risultato = verifica_ambiente(ambiente, probes_ambiente_locale())

    print(f"Verifica ambiente '{risultato.ambiente_id}': {risultato.esito.value}")
    for servizio in risultato.servizi_verificati:
        problema = next((p for p in risultato.problemi if p.servizio == servizio), None)
        stato = "OK" if problema is None else f"{problema.tipo}: {problema.dettaglio}"
        print(f"  - {servizio}: {stato}")

    return _EXIT_CODE[risultato.esito]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gemodo-quality", description="Controlli di readiness qualita' per GEMODO (feature 009)."
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    verifica = subparsers.add_parser(
        "verifica-ambiente", help="Esegue le healthcheck dell'ambiente locale e classifica PASS/PARTIAL/FAIL"
    )
    verifica.set_defaults(func=_cmd_verifica_ambiente)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
