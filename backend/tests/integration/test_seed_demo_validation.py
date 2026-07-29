"""Integration tests: seed demo entries with real/sensitive data must be rejected.

Exercises the real seed catalog (infra/local/postgres/seed-demo-catalog.yaml) and the
real validation logic in ``app.quality.seed_demo`` (FR-010, FR-011). No seed content or
validation behaviour is mocked.
"""

from __future__ import annotations

import copy

import pytest

from app.quality.errors import ContrattoNonValidoError, SeedSensibileError
from app.quality.schemas import SeedDemo, TipoSeedDemo
from app.quality.seed_demo import load_seed_catalog, validate_seed_catalog, validate_seed_demo

pytestmark = pytest.mark.integration


@pytest.fixture()
def seed_demo_catalog_path(repo_root):
    return repo_root / "infra" / "local" / "postgres" / "seed-demo-catalog.yaml"


@pytest.fixture()
def loaded_seed_catalog(seed_demo_catalog_path):
    return load_seed_catalog(seed_demo_catalog_path)


def _make_seed(**overrides) -> SeedDemo:
    base = {
        "id": "seed-test",
        "nome": "Seed di test",
        "tipo": TipoSeedDemo.CATALOGO,
        "marcatura_demo": "DEMO",
        "spec_owner": "specs/001-catalogo-contratto-geban",
        "resettable": True,
        "dati_sensibili": False,
    }
    base.update(overrides)
    return SeedDemo.model_validate(base)


def test_real_seed_catalog_loads_and_validates_cleanly(loaded_seed_catalog):
    seeds, catalogo = loaded_seed_catalog

    validate_seed_catalog(seeds, catalogo)  # must not raise

    assert len(seeds) >= 1
    assert all(seed.dati_sensibili is False for seed in seeds)
    assert all(seed.marcatura_demo == "DEMO" for seed in seeds)


def test_real_seed_catalog_has_a_published_model_usable_by_mock_geban(loaded_seed_catalog):
    _, catalogo = loaded_seed_catalog
    modelli = catalogo["modelli"]

    assert any(m.get("utilizzabile_da_mock_geban") is True for m in modelli)


def test_real_seed_catalog_has_an_unpublishable_case(loaded_seed_catalog):
    _, catalogo = loaded_seed_catalog
    modelli = catalogo["modelli"]

    assert any(m.get("utilizzabile_da_mock_geban") is False for m in modelli)


def test_real_seed_catalog_typologies_cover_the_ten_geban_sol_codes(loaded_seed_catalog):
    _, catalogo = loaded_seed_catalog
    codici = {t["codice"] for t in catalogo["tipologie_sol"]}

    assert codici == {"TDPNRR", "CD", "DIR", "TD", "CP", "RS", "CATP", "TI", "SDIP", "MOB"}


def test_seed_with_sensitive_data_is_rejected():
    seed_sensibile = _make_seed(id="seed-sensibile", dati_sensibili=True)

    with pytest.raises(SeedSensibileError) as exc_info:
        validate_seed_demo(seed_sensibile)

    assert exc_info.value.seed_id == "seed-sensibile"


def test_seed_without_demo_marker_is_rejected():
    seed_senza_marker = _make_seed(id="seed-senza-marker", marcatura_demo="")

    with pytest.raises(ContrattoNonValidoError):
        validate_seed_demo(seed_senza_marker)


def test_seed_with_wrong_demo_marker_value_is_rejected():
    seed_marker_sbagliato = _make_seed(id="seed-marker-sbagliato", marcatura_demo="PRODUZIONE")

    with pytest.raises(ContrattoNonValidoError):
        validate_seed_demo(seed_marker_sbagliato)


def test_valid_demo_seed_passes():
    validate_seed_demo(_make_seed())  # must not raise


def test_validate_seed_catalog_rejects_any_sensitive_seed_in_the_list(loaded_seed_catalog):
    seeds, catalogo = loaded_seed_catalog
    seeds_con_uno_sensibile = list(seeds)
    seeds_con_uno_sensibile[0] = seeds_con_uno_sensibile[0].model_copy(update={"dati_sensibili": True})

    with pytest.raises(SeedSensibileError):
        validate_seed_catalog(seeds_con_uno_sensibile, catalogo)


def test_validate_seed_catalog_rejects_missing_published_model(loaded_seed_catalog):
    seeds, catalogo = loaded_seed_catalog
    catalogo_senza_pubblicato = copy.deepcopy(catalogo)
    for modello in catalogo_senza_pubblicato["modelli"]:
        modello["utilizzabile_da_mock_geban"] = False

    with pytest.raises(ContrattoNonValidoError) as exc_info:
        validate_seed_catalog(seeds, catalogo_senza_pubblicato)

    assert any("nessun modello pubblicato" in v for v in exc_info.value.violazioni)


def test_validate_seed_catalog_rejects_missing_unpublishable_case(loaded_seed_catalog):
    seeds, catalogo = loaded_seed_catalog
    catalogo_tutto_pubblicato = copy.deepcopy(catalogo)
    for modello in catalogo_tutto_pubblicato["modelli"]:
        modello["utilizzabile_da_mock_geban"] = True

    with pytest.raises(ContrattoNonValidoError) as exc_info:
        validate_seed_catalog(seeds, catalogo_tutto_pubblicato)

    assert any("nessun caso di modello non pubblicabile" in v for v in exc_info.value.violazioni)


def test_load_seed_catalog_rejects_manifest_missing_expected_keys(tmp_path):
    bad_manifest = tmp_path / "bad-seed-catalog.yaml"
    bad_manifest.write_text("solo_una_chiave_a_caso: true\n", encoding="utf-8")

    with pytest.raises(ContrattoNonValidoError):
        load_seed_catalog(bad_manifest)
