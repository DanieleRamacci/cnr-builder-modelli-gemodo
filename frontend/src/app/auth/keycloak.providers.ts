import {
  INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
  includeBearerTokenInterceptor,
  provideKeycloak,
} from 'keycloak-angular';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import type { EnvironmentProviders, Provider } from '@angular/core';

import { parseIssuerUrl } from './keycloak-config';
import type { RuntimeConfig } from '../runtime-config';

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
    provideHttpClient(withInterceptors([includeBearerTokenInterceptor])),
    {
      provide: INCLUDE_BEARER_TOKEN_INTERCEPTOR_CONFIG,
      // Only the backend, proxied through /api by ng serve (proxy.conf.js) - never
      // an external origin, so a token is never sent where it should not be.
      useValue: [{ urlPattern: /^\/api\// }],
    },
  ];
}
