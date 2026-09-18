import { provideKeycloak } from 'keycloak-angular';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import type { EnvironmentProviders, Provider } from '@angular/core';

import { parseIssuerUrl } from './keycloak-config';
import type { RuntimeConfig } from '../runtime-config';
import { sessionInterceptor } from './session.interceptor';

/**
 * All routes in this MVP require authentication (spec.md FR-021..023): admin and
 * manager screens both, no public route exists yet - so onLoad: 'login-required'
 * (redirect immediately, no anonymous landing page) is correct here, not
 * 'check-sso'. Revisit if a public route is ever added.
 */
export function provideKeycloakAuth(config: RuntimeConfig): (Provider | EnvironmentProviders)[] {
  const { url, realm } = parseIssuerUrl(config.keycloakIssuerUrl);
  return [
    provideKeycloak({
      config: { url, realm, clientId: config.keycloakClientId },
      initOptions: {
        onLoad: 'login-required',
        pkceMethod: 'S256',
        checkLoginIframe: false,
      },
    }),
    provideHttpClient(withInterceptors([sessionInterceptor])),
  ];
}
