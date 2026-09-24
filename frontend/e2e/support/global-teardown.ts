import type { FullConfig } from '@playwright/test';
import { registraOrigine } from './keycloak';
import { origineSuite } from './global-setup';

export default async function globalTeardown(config: FullConfig): Promise<void> {
  // Toglie esattamente quello che il setup ha aggiunto: il realm torna come
  // sta nel file di import, senza bisogno di conservare uno snapshot.
  await registraOrigine(origineSuite(config), false);
}
