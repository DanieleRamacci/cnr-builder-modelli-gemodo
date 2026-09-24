import type { FullConfig } from '@playwright/test';
import { registraOrigine } from './keycloak';

/** L'origine da cui gira la suite, la stessa che usano i test nel browser. */
export function origineSuite(config: FullConfig): string {
  const baseURL =
    config.projects[0]?.use?.baseURL ??
    process.env['GEMODO_FRONTEND_BASE_URL'] ??
    'http://localhost:4200';
  return new URL(baseURL).origin;
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  await registraOrigine(origineSuite(config), true);
}
