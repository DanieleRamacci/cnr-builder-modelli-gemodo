import { test, expect, type Locator, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  accedi,
  creaUtenteUsaEGetta,
  tokenDellaSessione,
  type UtenteUsaEGetta,
} from './support/keycloak';
import { concediAlManager } from './support/accessi';

/**
 * Bando multiplo (spec 014, T036): dal discovery con le tematiche al PDF con
 * una riga per tematica, passando dall'interfaccia come farebbe il gestore.
 * La foglia `DEMO - Collaboratore Tecnico E.R.` del discovery-mock dichiara il
 * campo ripetibile `articolazioni`.
 *
 * Come gli altri e2e non e' ripetibile su un database gia' usato (FR-024):
 * ripulire il database prima di rieseguire.
 */
const contesto = 'geban';
let utente: UtenteUsaEGetta;

test.beforeAll(async () => {
  utente = await creaUtenteUsaEGetta({ prefisso: 'multiplo', contesto });
});

test.afterAll(async () => {
  await utente?.rimuovi();
});

function testoDelPdf(percorso: string): string {
  const backend = resolve(__dirname, '../../backend');
  return execFileSync(
    resolve(backend, '.venv/bin/python'),
    ['-c', 'import sys; from pathlib import Path; from tests.support.pdf import estrai_testo; print(estrai_testo(Path(sys.argv[1]).read_bytes()))', percorso],
    { cwd: backend, encoding: 'utf-8' },
  );
}

/** Il cursore in una cella della tabella dell'editor, come col mouse. */
async function inCella(page: Page, cella: Locator): Promise<void> {
  await cella.click();
  await page.evaluate(() => document.dispatchEvent(new Event('selectionchange')));
}

test('il gestore crea un bando multiplo, lo impagina in tabella e GEBAN genera una riga per tematica', async ({
  page,
}, testInfo) => {
  const errori: string[] = [];
  page.on('pageerror', (e) => errori.push(e.message));
  await accedi(page, utente);

  // Integrazione connessa sul discovery-mock, con il profilo di accesso.
  await page.locator('a.home-action', { hasText: 'Integrazione servizi' }).click();
  await page.getByRole('link', { name: 'Nuovo contesto' }).first().click();
  await page.locator('#codice').fill(`MULTIPLO_${Date.now()}`);
  await page.locator('#nome').fill('Discovery multiplo');
  await page.locator('#codiceContesto').fill(contesto);
  await page.locator('button[type=submit]').click();
  await page.locator('#url').fill('http://127.0.0.1:9100/discovery');
  await page.getByRole('button', { name: 'Salva configurazione' }).click();
  await page.getByRole('button', { name: 'Verifica ora', exact: true }).click();
  await expect(page.getByText('Connesso', { exact: true })).toBeVisible();
  const sourceId = new URL(page.url()).pathname.split('/').at(-2)!;
  await concediAlManager(page);

  // Creazione: la foglia con le tematiche offre la scelta singolo/multiplo.
  await page.goto(`/contesti/${contesto}/modelli`);
  await page.locator(`a[href^="/builder/${sourceId}"]`).click();
  await page.locator('#tipo').selectOption('BANDO_CONCORSO');
  await page.locator('#livello-0').selectOption({ label: 'DEMO - Tempo determinato' });
  await page.locator('#livello-1').selectOption({ label: 'DEMO - Ricercatore' });
  await expect(page.locator('[data-tipo-bando]')).toHaveCount(0);
  await page.locator('#livello-1').selectOption({ label: 'DEMO - Collaboratore Tecnico E.R.' });
  await expect(page.locator('[data-tipo-bando]')).toContainText('tematiche');
  // In Bootstrap Italia il pallino e' coperto dalla sua etichetta: si clicca quella.
  await page.locator('label[for="tipo-bando-multiplo"]').click();
  await expect(page.locator('#tipo-bando-multiplo')).toBeChecked();
  await page.locator('#dimensione-lingua').selectOption('IT');
  await page.locator('#dimensione-livello_professionale').selectOption('V');
  await expect(page.locator('.riepilogo .sotto-campi')).toContainText('Codice sottobando');
  await page.getByRole('button', { name: 'Genera modello' }).click();
  await expect(page.getByRole('status')).toContainText('BOZZA');
  await page.locator('[data-apri-modello]').click();

  // Builder: il gruppo "Bando multiplo" e il blocco finche' manca la tabella.
  await expect(page.locator('[data-badge-multiplo]')).toBeVisible();
  const gruppo = page.locator('[data-gruppo-multiplo]');
  await expect(gruppo).toContainText('Tematiche');
  await expect(page.locator('.pannello > .panel-body > .campo[data-placeholder="articolazioni"]')).toHaveCount(0);

  // Una sezione con la tabella: la prima riga si ripete, la seconda e' il totale.
  await page.locator('[data-add-section-inline]').click();
  const editor = page.locator('[data-section-text]').first();
  await editor.click();
  await editor.pressSequentially('I posti sono cosi ripartiti:');
  await expect(page.locator('[data-readiness]')).toContainText('non ha una tabella con la riga ripetuta');
  await page.locator('[data-insert-block="TABELLA"]').click();
  const tabella = editor.locator('table.editor-tabella');
  await expect(tabella.locator('th')).toHaveCount(3);

  const celle = tabella.locator('tr').nth(1).locator('td');
  await inCella(page, celle.nth(0));
  await page.locator('[data-ripeti-riga]').selectOption('articolazioni');
  await expect(tabella.locator('tr.riga-ripetuta')).toHaveCount(1);
  for (const [indice, token] of [
    [0, 'articolazioni.campi.codice_bando'],
    [1, 'articolazioni.campi.numero_posti'],
    [2, 'articolazioni.campi.sede_lavoro'],
  ] as const) {
    await inCella(page, celle.nth(indice));
    await gruppo.locator(`[data-placeholder="${token}"]`).click();
  }
  await inCella(page, celle.nth(0));
  await page.locator('[data-strumenti-tabella]').getByRole('button', { name: '+ riga' }).click();
  const totale = tabella.locator('tr').nth(2).locator('td');
  await inCella(page, totale.nth(0));
  await page.keyboard.type('Totale');
  await inCella(page, totale.nth(1));
  await page.locator('.campo[data-placeholder="numero_posti"]').first().click();
  await expect(tabella.locator('tr.riga-ripetuta')).toHaveCount(1);

  await page.locator('[data-salva-documento]').click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  await expect(page.locator('[data-readiness-block]')).toHaveCount(0);
  await page.screenshot({ path: testInfo.outputPath('bando-multiplo-builder.png'), fullPage: true });

  // Pubblicazione dalla lista, come per ogni modello.
  const nomeModello = (await page.locator('[data-titolo-modello]').textContent())!.trim();
  await page.getByRole('link', { name: 'Modelli' }).click();
  const riga = page.getByRole('row').filter({ hasText: nomeModello });
  for (const azione of ['Invia in revisione', 'Approva', 'Pubblica']) {
    await riga.getByRole('button', { name: /Altre azioni/ }).click();
    await page.getByRole('menuitem', { name: azione, exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Conferma', exact: true }).click();
  }
  await expect(riga).toContainText('PUBBLICATO');

  // GEBAN: trova il modello solo con multiplo=true e genera il 367.501.
  const token = await tokenDellaSessione(page);
  const intestazioni = { Authorization: `Bearer ${token}` };
  // Il discovery-mock non dichiara `tipo_livello`: niente filtro di tipologia.
  const ricerca =
    '/api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO' +
    '&profilo=COLLABORATORE_TECNICO_ER&lingua=IT&livello_professionale=V';
  const singoli = await (await page.request.get(ricerca, { headers: intestazioni })).json();
  expect(singoli.modelli).toEqual([]);
  const multipli = await (await page.request.get(`${ricerca}&multiplo=true`, { headers: intestazioni })).json();
  expect(multipli.modelli).toHaveLength(1);
  expect(multipli.modelli[0].multiplo).toBe(true);

  const generato = await page.request.post('/api/v1/documenti/genera', {
    headers: intestazioni,
    data: {
      sistema_richiedente: 'GEBAN',
      external_context_id: `367.501-${Date.now()}`,
      modello_versione_id: multipli.modelli[0].modello_versione_id,
      dati: {
        codice_bando: '367.501',
        numero_posti: 10,
        articolazioni: [
          { codice: 'TEMA_A', descrizione: 'Chimica', campi: { codice_bando: '367.501-A', numero_posti: 2, sede_lavoro: 'Roma' } },
          { codice: 'TEMA_B', descrizione: 'Oceanografia', campi: { codice_bando: '367.501-B', numero_posti: 5, sede_lavoro: 'Napoli' } },
          { codice: 'TEMA_C', descrizione: 'Calcolo', campi: { codice_bando: '367.501-C', numero_posti: 3 } },
        ],
      },
    },
  });
  expect(generato.status(), await generato.text()).toBe(200);
  const percorso = testInfo.outputPath('bando-367-501.pdf');
  writeFileSync(percorso, await generato.body());
  const testo = testoDelPdf(percorso);
  expect(testo).toContain('367.501-A 2 Roma');
  expect(testo).toContain('367.501-B 5 Napoli');
  expect(testo).toContain('367.501-C 3');
  expect(testo).toContain('Totale 10');
  expect(errori).toEqual([]);
});
