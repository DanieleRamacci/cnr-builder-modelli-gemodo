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

export function tokenContexts(keycloak: Keycloak): string[] {
  const contexts: unknown = keycloak.tokenParsed?.['contexts'];
  return contexts && typeof contexts === 'object' && !Array.isArray(contexts)
    ? Object.keys(contexts).sort()
    : [];
}

export function hasManagerAccess(keycloak: Keycloak): boolean {
  if (hasClientRole(keycloak, 'gemodo-backend', 'GEMODO_MODELLI_GESTORE')) return true;
  const contexts = keycloak.tokenParsed?.['contexts'] as
    Record<string, { roles?: unknown }> | undefined;
  return tokenContexts(keycloak).some((code) => {
    const roles = contexts?.[code]?.roles;
    return Array.isArray(roles) && roles.includes(`ROLE_MANAGER#${code}`);
  });
}
