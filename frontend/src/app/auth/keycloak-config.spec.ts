import { describe, expect, it } from 'vitest';

import { parseIssuerUrl } from './keycloak-config';

describe('parseIssuerUrl', () => {
  it('splits the production issuer URL (legacy /auth context path)', () => {
    expect(parseIssuerUrl('https://sso.test.si.cnr.it/auth/realms/cnr')).toEqual({
      url: 'https://sso.test.si.cnr.it/auth',
      realm: 'cnr',
    });
  });

  it('splits a Keycloak 25+ issuer URL without the legacy /auth context path', () => {
    expect(parseIssuerUrl('http://localhost:8081/realms/gemodo-local')).toEqual({
      url: 'http://localhost:8081',
      realm: 'gemodo-local',
    });
  });

  it('throws on a URL with no /realms/ segment instead of silently guessing', () => {
    expect(() => parseIssuerUrl('https://sso.test.si.cnr.it/not-a-realm-url')).toThrow();
  });
});
