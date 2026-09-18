import { InjectionToken } from '@angular/core';

/**
 * Environment-specific config the browser needs before bootstrapping (Keycloak
 * issuer/client). Fetched once from /runtime-config.json, regenerated from
 * container env vars at container startup (scripts/genera-runtime-config.sh) -
 * Angular's build-time bundling cannot substitute process.env the way a
 * server-rendered app or Vite's import.meta.env would.
 */
export interface RuntimeConfig {
  readonly keycloakIssuerUrl: string;
  readonly keycloakClientId: string;
  /**
   * Link to the separately-deployed external documentation (deploy/coolify-test/,
   * GEBAN discovery/auth docs) shown in the shell footer. Undefined/empty hides
   * the link - only set once that deployment has a real URL.
   */
  readonly externalDocsUrl?: string;
}

export const RUNTIME_CONFIG = new InjectionToken<RuntimeConfig>('RUNTIME_CONFIG');

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  const response = await fetch('/runtime-config.json');
  if (!response.ok) {
    throw new Error(`Impossibile caricare runtime-config.json (${response.status})`);
  }
  return (await response.json()) as RuntimeConfig;
}
