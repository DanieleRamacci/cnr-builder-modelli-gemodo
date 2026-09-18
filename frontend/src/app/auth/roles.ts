import type Keycloak from 'keycloak-js';

/**
 * UI-only enablement (spec.md FR-008/FR-023): hides/disables actions the backend
 * would reject anyway. The backend is always the authority - see
 * require_admin/require_modelli_gestore in backend/app/common/security.py.
 */
export function hasClientRole(keycloak: Keycloak, clientId: string, role: string): boolean {
  const roles = keycloak.tokenParsed?.resource_access?.[clientId]?.roles;
  return Array.isArray(roles) && roles.includes(role);
}
