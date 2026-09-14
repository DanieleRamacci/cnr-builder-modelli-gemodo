from __future__ import annotations

import pytest

from app.quality.integration_profile import (
    client_ids_attivi,
    load_sistemi_richiedenti,
    permessi_da_ruoli_esterni,
)

pytestmark = pytest.mark.integration


def test_real_integration_profiles_include_ace_geban_mapping(repo_root):
    sistemi = load_sistemi_richiedenti(repo_root / "infra" / "local" / "integration-profiles.local.yaml")

    assert "geri-angular-public" in client_ids_attivi(sistemi)
    assert "DOCUMENTI_GENERATORE" in permessi_da_ruoli_esterni(
        sistemi,
        client_id="geri-angular-public",
        context_roles={"geban": ("ROLE_COORDINATOR#geban",)},
    )


def test_real_integration_profiles_map_only_manager_to_builder_permission(repo_root):
    sistemi = load_sistemi_richiedenti(repo_root / "infra" / "local" / "integration-profiles.local.yaml")

    user_permissions = permessi_da_ruoli_esterni(
        sistemi,
        client_id="geri-angular-public",
        context_roles={"geban": ("ROLE_USER#geban",)},
    )
    manager_permissions = permessi_da_ruoli_esterni(
        sistemi,
        client_id="geri-angular-public",
        context_roles={"geban": ("ROLE_MANAGER#geban",)},
    )

    assert "GEMODO_MODELLI_GESTORE" not in user_permissions
    assert "GEMODO_MODELLI_GESTORE" in manager_permissions


def test_unknown_external_role_does_not_derive_permissions(repo_root):
    sistemi = load_sistemi_richiedenti(repo_root / "infra" / "local" / "integration-profiles.local.yaml")

    assert permessi_da_ruoli_esterni(
        sistemi,
        client_id="geri-angular-public",
        context_roles={"geban": ("ROLE_UNKNOWN#geban",)},
    ) == set()
