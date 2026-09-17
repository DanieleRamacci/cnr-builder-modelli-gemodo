from fastapi import Depends

from app.common.security import PrincipalGEMODO, ensure_roles, require_principal


ROLE_GEMODO_ADMIN = "GEMODO_ADMIN"


def require_configurazione_admin(
    principal: PrincipalGEMODO = Depends(require_principal),
) -> PrincipalGEMODO:
    return ensure_roles(principal, (ROLE_GEMODO_ADMIN,))
