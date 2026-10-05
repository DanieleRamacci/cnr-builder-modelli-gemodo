import { expect, type Page } from '@playwright/test';

/**
 * Dalla pagina dell'integrazione appena registrata, concede a ROLE_MANAGER del
 * suo contesto i tre permessi GEMODO e ammette il client tecnico
 * `geban-backend`, dalla scheda "Profilo di accesso"
 * (001 T091). Un'integrazione nasce senza ruoli: senza questo passo l'utente
 * ACE del contesto non puo' usare il builder.
 */
export async function concediAlManager(page: Page): Promise<void> {
  await page.getByRole('link', { name: 'Profilo di accesso' }).click();
  await page.getByRole('button', { name: 'Aggiungi ruolo' }).click();
  await page.getByLabel('Ruolo 1', { exact: true }).fill('ROLE_MANAGER');
  for (const permesso of ['DOCUMENTI_VIEWER', 'DOCUMENTI_GENERATORE', 'GEMODO_MODELLI_GESTORE']) {
    await page.getByLabel(`ROLE_MANAGER: ${permesso}`).check();
  }
  // Il client tecnico con cui gli e2e generano i PDF (`tokenGeneratore`): con
  // l'isolamento per contesto acceso genera solo se l'integrazione lo ammette.
  await page.getByLabel('Nuovo client').fill('geban-backend');
  await page.getByRole('button', { name: 'Aggiungi client' }).click();
  await page.getByRole('button', { name: 'Salva profilo di accesso' }).click();
  await expect(page.getByText('Profilo salvato')).toBeVisible();
  await page.getByRole('link', { name: 'Integrazione', exact: true }).click();
}
