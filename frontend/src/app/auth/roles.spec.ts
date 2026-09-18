import type Keycloak from 'keycloak-js';

import { hasClientRole } from './roles';

function withTokenParsed(
  resourceAccess: Record<string, { roles: string[] }> | undefined,
): Keycloak {
  return {
    tokenParsed: resourceAccess ? { resource_access: resourceAccess } : undefined,
  } as Keycloak;
}

describe('hasClientRole', () => {
  it('finds a role granted on the given client', () => {
    const kc = withTokenParsed({
      'gemodo-backend': { roles: ['GEMODO_ADMIN', 'DOCUMENTI_VIEWER'] },
    });
    expect(hasClientRole(kc, 'gemodo-backend', 'GEMODO_ADMIN')).toBe(true);
  });

  it('returns false when the role is missing', () => {
    const kc = withTokenParsed({ 'gemodo-backend': { roles: ['DOCUMENTI_VIEWER'] } });
    expect(hasClientRole(kc, 'gemodo-backend', 'GEMODO_ADMIN')).toBe(false);
  });

  it('returns false when there is no token yet', () => {
    const kc = withTokenParsed(undefined);
    expect(hasClientRole(kc, 'gemodo-backend', 'GEMODO_ADMIN')).toBe(false);
  });

  it("never falls back to another client's roles", () => {
    const kc = withTokenParsed({ 'geban-backend': { roles: ['GEMODO_ADMIN'] } });
    expect(hasClientRole(kc, 'gemodo-backend', 'GEMODO_ADMIN')).toBe(false);
  });
});
