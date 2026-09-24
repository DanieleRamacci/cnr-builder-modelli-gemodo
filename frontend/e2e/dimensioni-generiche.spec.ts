import { test, expect } from '@playwright/test';
import { accedi, creaUtenteUsaEGetta, type UtenteUsaEGetta } from './support/keycloak';

/**
 * 011 T041 (US5): un tipo documento con dimensioni proprie, dall'interfaccia.
 *
 * `CONTRATTI` e' il caso portante della spec: la sua foglia dichiara
 * `area_geografica` e **non** dichiara la lingua. Il percorso qui e' quello
 * vero di un admin - registra il contesto, scopre il tipo, configura la policy
 * della dimensione, crea due modelli che differiscono solo per quella
 * dimensione e li pubblica entrambi.
 *
 * Il punto della spec e' che niente di tutto questo richiede una modifica di
 * codice: se `area_geografica` fosse ancora un elenco scritto nel sorgente,
 * questo test non arriverebbe alla seconda pubblicazione (FR-004: l'unicita'
 * della versione corrente considera tutte le dimensioni, quindi il secondo
 * modello non deve archiviare il primo).
 *
 * Come builder-lifecycle, non e' ripetibile su un database gia' usato: FR-024
 * ammette un solo tipo documento non inattivo per (codice_contesto, codice).
 */
const contesto = 'geban';
const AREE = ['NORD', 'CENTRO'] as const;
let utente: UtenteUsaEGetta;

test.beforeAll(async () => {
  utente = await creaUtenteUsaEGetta({
    prefisso: 'dimensioni',
    contesto,
  });
});

test.afterAll(async () => {
  await utente?.rimuovi();
});

test('admin configures a dimension policy and publishes two models that differ only by it', async ({
  page,
}, testInfo) => {
  const errori: string[] = [];
  page.on('pageerror', (e) => errori.push(e.message));
  await accedi(page, utente);

  // 1. Registrazione del contesto e verifica dell'endpoint discovery.
  await page.locator('a.home-action', { hasText: 'Integrazione servizi' }).click();
  await page.getByRole('link', { name: 'Nuovo contesto' }).first().click();
  // Ne' il codice ne' il nome del contesto contengono "contratti": la riga del
  // tipo documento va riconosciuta senza ambiguita' con la colonna accanto.
  await page.locator('#codice').fill(`E2E_DIM_${Date.now()}`);
  await page.locator('#nome').fill('Discovery aree');
  await page.locator('#codiceContesto').fill(contesto);
  await page.locator('button[type=submit]').click();
  await page.locator('#url').fill('http://127.0.0.1:9100/discovery');
  await page.getByRole('button', { name: 'Salva configurazione' }).click();
  await page.getByRole('button', { name: 'Verifica ora', exact: true }).click();
  await expect(page.getByText('Connesso', { exact: true })).toBeVisible();
  // L'id sta prima del tab in /configurazione/contesti/<id>/integrazione. Serve
  // perche' il builder deve partire da QUESTA integrazione: i tipi documento
  // appartengono a una sola integrazione per contesto (FR-024), e gli altri
  // test della suite ne registrano altre.
  const sourceId = new URL(page.url()).pathname.split('/').at(-2)!;

  // 2. CONTRATTI e' scoperto dal discovery, non dichiarato a mano.
  await page.getByRole('link', { name: 'Policy dati', exact: true }).click();
  const riga = page.getByRole('row').filter({ hasText: /CONTRATTI/ });
  await expect(riga).toBeVisible();
  await riga.getByRole('link', { name: 'Configura policy' }).click();

  // 3. Policy di `area_geografica`: ogni valore e' un modello a se'. La
  //    dimensione arriva dall'albero live, non da un elenco nel codice.
  await page.locator('[data-node="COLLABORAZIONE"]').click();
  await page.locator('[data-node="PRESTAZIONE_OCCASIONALE"]').click();
  const scheda = page.locator('.dimension-card', { hasText: 'area_geografica' });
  await expect(scheda).toBeVisible();
  await expect(scheda).toContainText('NORD');
  await scheda.locator('#area_geografica-distinto').check();
  await page.locator('[data-save-policy="area_geografica"]').click();
  await expect(page.locator('.summary-panel')).toContainText('biforca il modello');

  // 4. Due modelli che differiscono solo per `area_geografica`.
  const nomi: string[] = [];
  for (const area of AREE) {
    // La navigazione ha due voci verso /contesti ("Contesti" e "Modelli") e
    // "Contesti" torna anche nelle briciole di pane: qui basta arrivarci.
    await page.locator('.app-nav a[href="/contesti"]').first().click();
    await page.locator(`a[href="/contesti/${contesto}/modelli"]`).click();
    await page.locator(`a[href^="/builder/${sourceId}"]`).click();
    await page.locator('#tipo').selectOption('CONTRATTI');
    await page.locator('#livello-0').selectOption({ label: 'DEMO - Contratto di collaborazione' });
    await page.locator('#livello-1').selectOption({ label: 'DEMO - Prestazione occasionale' });
    // Nessun campo lingua: questa foglia non la dichiara (FR-006).
    await expect(page.locator('#dimensione-lingua')).toHaveCount(0);
    await page.locator('#dimensione-area_geografica').selectOption(area);
    await page.getByRole('button', { name: 'Genera modello' }).click();
    await expect(page.getByRole('status')).toContainText('BOZZA');
    const esito = (await page.getByRole('status').textContent()) ?? '';
    nomi.push(/Modello (.+) \(/.exec(esito)![1]);
  }
  // FR-003: l'identita' generata include il valore che li distingue.
  expect(nomi[0]).not.toEqual(nomi[1]);

  // 5. Pubblicazione di entrambi: il secondo non deve archiviare il primo,
  //    perche' l'unicita' della versione corrente considera anche
  //    `area_geografica` (FR-004).
  await page.getByRole('link', { name: 'Torna ai modelli' }).click();
  for (const nome of nomi) {
    const rigaModello = page.getByRole('row').filter({ hasText: nome });
    for (const azione of ['Invia in revisione', 'Approva', 'Pubblica']) {
      await rigaModello.getByRole('button', { name: /Altre azioni/ }).click();
      await page.getByRole('menuitem', { name: azione, exact: true }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await page.getByRole('button', { name: 'Conferma', exact: true }).click();
    }
    await expect(rigaModello).toContainText('PUBBLICATO');
  }
  for (const nome of nomi) {
    const rigaFinale = page.getByRole('row').filter({ hasText: nome });
    await expect(rigaFinale).toContainText('PUBBLICATO');
    // FR-006: la lista mostra le dimensioni che il modello ha davvero. Questi
    // modelli non hanno lingua, e l'elenco non deve inventargliene una.
    await expect(rigaFinale).toContainText('area geografica:');
    await expect(rigaFinale).not.toContainText('Italiano');
    await expect(rigaFinale).not.toContainText('Inglese');
  }

  await page.screenshot({ path: testInfo.outputPath('contratti-pubblicati.png'), fullPage: true });
  expect(errori).toEqual([]);
});
