/**
 * KEYCLOAK_ISSUER_URL (infra/local/keycloak/README.md, already the backend's own env
 * var) bundles server url + realm in one string, e.g.
 * "https://sso.test.si.cnr.it/auth/realms/cnr" or, on Keycloak >=17 without the legacy
 * /auth context path, "http://localhost:8081/realms/gemodo-local". keycloak-js wants
 * them split.
 */
export function parseIssuerUrl(issuerUrl: string): { url: string; realm: string } {
  const marker = '/realms/';
  const index = issuerUrl.indexOf(marker);
  if (index === -1) {
    throw new Error(`KEYCLOAK_ISSUER_URL non contiene "${marker}": ${issuerUrl}`);
  }
  return {
    url: issuerUrl.slice(0, index),
    realm: issuerUrl.slice(index + marker.length),
  };
}
