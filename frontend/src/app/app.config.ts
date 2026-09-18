import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideDesignAngularKit } from 'design-angular-kit';

import { provideKeycloakAuth } from './auth/keycloak.providers';
import { routes } from './app.routes';
import { RUNTIME_CONFIG, type RuntimeConfig } from './runtime-config';

// A factory, not a static constant: Keycloak needs the issuer/client id from
// runtime-config.json (main.ts fetches it before bootstrap - see runtime-config.ts
// for why this can't be a build-time constant).
export function buildAppConfig(runtimeConfig: RuntimeConfig): ApplicationConfig {
  return {
    providers: [
      provideBrowserGlobalErrorListeners(),
      provideRouter(routes),
      provideDesignAngularKit(),
      { provide: RUNTIME_CONFIG, useValue: runtimeConfig },
      ...provideKeycloakAuth(runtimeConfig),
    ],
  };
}
