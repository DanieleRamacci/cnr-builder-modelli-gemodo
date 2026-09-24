import { test, expect } from '@playwright/test';
import {
  accedi,
  bordiSforati,
  creaUtenteUsaEGetta,
  type UtenteUsaEGetta,
} from './support/keycloak';

// Il contesto DEVE essere fra quelli mappati in
// infra/local/integration-profiles.local.yaml (ROLE_MANAGER#geban -> permessi
// GEMODO, FR-018): un codice arbitrario non concede alcun permesso.
// Di conseguenza il test non e' ripetibile su un database gia' usato: FR-024
// ammette un solo tipo documento non inattivo per (codice_contesto, codice) e
// la seconda esecuzione otterrebbe TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE. Ripulire
// il database prima di rieseguire (comando `gemodo-reset-database`, T079/T080).
const contesto = 'geban';
let utente: UtenteUsaEGetta;

test.beforeAll(async () => {
  utente = await creaUtenteUsaEGetta({
    prefisso: 'lifecycle',
    contesto,
  });
});

test.afterAll(async () => {
  await utente?.rimuovi();
});

test('ACE manager creates a draft and publishes from the context list', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await accedi(page, utente);
  // La card della home porta il numero e la descrizione dentro l'accessible
  // name: si aggancia la card, non un nome esatto che il redesign cambia.
  await page.locator('a.home-action', { hasText: 'Integrazione servizi' }).click();
  // La 010 ha rinominato l'integrazione in "contesto" in interfaccia.
  await page.getByRole('link', { name: 'Nuovo contesto' }).first().click();
  await page.locator('#codice').fill(`LIFECYCLE_${Date.now()}`);
  await page.locator('#nome').fill('Discovery lifecycle');
  await page.locator('#codiceContesto').fill(contesto);
  await page.locator('button[type=submit]').click();
  await page.locator('#url').fill('http://127.0.0.1:9100/discovery');
  await page.getByRole('button', { name: 'Salva configurazione' }).click();
  await page.getByRole('button', { name: 'Verifica ora', exact: true }).click();
  await expect(page.getByText('Connesso', { exact: true })).toBeVisible();
  // /configurazione/contesti/<id>/integrazione: l'id sta prima del tab, non in
  // fondo al path (la 010 ha aggiunto i tab alla pagina di configurazione).
  const sourceId = new URL(page.url()).pathname.split('/').at(-2)!;
  await page.getByRole('link', { name: 'Contesti', exact: true }).click();
  // Schermata 1a: card del contesto autorizzato, poi lista modelli 1b.
  await page.locator(`a[href="/contesti/${contesto}/modelli"]`).click();
  await page.locator(`a[href^="/builder/${sourceId}"]`).click();
  await page.locator('#tipo').selectOption('BANDO_CONCORSO');
  // Schermata 2a: tendine a cascata L2 (tipologia) -> L3 (profilo), attributi
  // del modello e Genera modello.
  await page.locator('#livello-0').selectOption({ label: 'DEMO - Tempo determinato' });
  await page.locator('#livello-1').selectOption({ label: 'DEMO - Ricercatore' });
  // La 011 ha reso generiche le dimensioni: non piu' un campo `lingua`
  // dedicato ma un select per ogni dimensione dichiarata dalla foglia
  // (qui lingua e livello professionale, da discovery-mock).
  await page.locator('#dimensione-lingua').selectOption('IT');
  await page.locator('#dimensione-livello_professionale').selectOption('VI');
  await page.getByRole('button', { name: 'Genera modello' }).click();
  await expect(page.getByRole('status')).toContainText('BOZZA');
  // Codice e nome sono generati dal backend: si leggono dall'esito, non si inseriscono.
  const esito = (await page.getByRole('status').textContent()) ?? '';
  const modelName = /Modello (.+) \(/.exec(esito)![1];
  await page.getByRole('link', { name: 'Torna ai modelli' }).click();
  // Il nome del modello porta all'anteprima (2b ridotta): li' vivono i campi
  // del contratto e la creazione dell'edizione inglese, non nella lista.
  await page.getByRole('link', { name: modelName }).click();
  await expect(page.getByRole('button', { name: 'Crea modello derivato' })).toBeVisible();

  // T130: la 2b e' un editor a schermo intero. L'header e il footer della
  // shell non ci sono: l'unica barra e' la topbar della pagina.
  await expect(page.locator('.topbar')).toBeVisible();
  await expect(page.locator('header.app-header')).toHaveCount(0);
  await expect(page.locator('footer.app-footer')).toHaveCount(0);
  await expect(page.locator('main.app-main-editor')).toHaveCount(1);
  await expect(page.locator('.pannello [data-placeholder]').first()).toBeVisible();

  // Editor centrale: sezione nuova, testo, segnaposto dal pannello e
  // salvataggio automatico all'uscita dal blocco.
  await page.locator('[data-add-section-inline]').click();
  const editor = page.locator('[data-section-text]').first();
  await editor.click();
  await editor.pressSequentially('Premesso che ');
  await page.locator('.pannello [data-placeholder]').first().click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Modifiche non salvate/);
  await page.locator('.format-toolbar .hint').click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  // Il testo deve essere quello scritto, nell'ordine in cui e' stato scritto:
  // con il caret che tornava a inizio blocco usciva mescolato.
  await expect(editor).toHaveText('Premesso che {{titolo_it}}');
  await expect(page.locator('[data-readiness]')).toContainText('Nessun blocco');
  await expect(page.locator('[data-export-docx]')).toBeDisabled();
  expect(await bordiSforati(page), 'elementi oltre il bordo a 1280px').toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('builder-2b-desktop.png'), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('[data-document-preview]')).toBeVisible();
  await expect(page.locator('.pannello [data-placeholder]').first()).toBeVisible();
  await expect(page.locator('header.app-header')).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath('builder-2b-mobile.png'), fullPage: true });
  expect(await bordiSforati(page), 'elementi oltre il bordo a 390px').toEqual([]);
  await page.setViewportSize({ width: 1280, height: 720 });

  await page.getByRole('link', { name: 'Modelli' }).click();
  const row = page.getByRole('row').filter({ hasText: modelName });
  for (const action of ['Invia in revisione', 'Approva', 'Pubblica']) {
    // Le azioni di ciclo di vita vivono nel kebab della riga (design 1b).
    await row.getByRole('button', { name: /Altre azioni/ }).click();
    await page.getByRole('menuitem', { name: action, exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Conferma', exact: true }).click();
  }
  await expect(row).toContainText('PUBBLICATO');
  // L'identificativo pubblico per GEBAN vive nel dettaglio del modello, non
  // nella lista: la tabella 1b ha le colonne Ver. e Stato, non le versioni.
  await page.getByRole('link', { name: modelName }).click();
  await expect(page.getByText(/ID API: \d+/)).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('contesti-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('contesti-mobile.png'), fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
