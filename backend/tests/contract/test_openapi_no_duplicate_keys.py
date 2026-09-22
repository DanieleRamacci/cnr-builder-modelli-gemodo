"""I contratti OpenAPI non devono contenere chiavi duplicate.

`yaml.safe_load` accetta un mapping con la stessa chiave due volte e tiene
silenziosamente l'ultima: un contratto puo' quindi dire una cosa diversa da
quella che si legge, senza che alcun test se ne accorga. Il bundler usato per
generare i tipi TypeScript invece si ferma, quindi la difformita' emerge solo
molto piu' tardi. Questo test la coglie subito.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

SPECS = Path(__file__).resolve().parents[3] / "specs"


class _NoDuplicatesLoader(yaml.SafeLoader):
    pass


def _mapping_senza_duplicati(loader, node, deep=False):
    viste: set = set()
    for chiave_node, _ in node.value:
        chiave = loader.construct_object(chiave_node, deep=deep)
        if chiave in viste:
            raise yaml.YAMLError(
                f"chiave duplicata {chiave!r} alla riga {chiave_node.start_mark.line + 1}"
            )
        viste.add(chiave)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_NoDuplicatesLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_senza_duplicati
)


def _contratti() -> list[Path]:
    return sorted(SPECS.glob("*/contracts/*.openapi.yaml"))


def test_ci_sono_contratti_da_verificare():
    assert _contratti(), "nessun contratto OpenAPI trovato: percorso sbagliato?"


@pytest.mark.parametrize("contratto", _contratti(), ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_contract_has_no_duplicate_keys(contratto: Path):
    try:
        yaml.load(contratto.read_text(encoding="utf-8"), Loader=_NoDuplicatesLoader)
    except yaml.YAMLError as errore:
        pytest.fail(f"{contratto.relative_to(SPECS)}: {errore}")
