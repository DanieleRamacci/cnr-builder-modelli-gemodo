import { test, expect, type Locator, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  accedi,
  bordiSforati,
  creaUtenteUsaEGetta,
  tokenGeneratore,
  type UtenteUsaEGetta,
} from './support/keycloak';

// Un "visto" e un elenco come li mette negli appunti Word desktop: le liste
// sono paragrafi `mso-list` con il marcatore in uno span `mso-list:Ignore`.
const APPUNTI_WORD = `<html xmlns:o="urn:schemas-microsoft-com:office:office"><body lang=IT>
<!--StartFragment--><p class=MsoNormal style='text-align:justify'><b><span style='color:#1F3864'>VISTO</span></b>
il Decreto Legislativo 4 giugno 2003, n. 127, recante <i>“Riordino del Consiglio Nazionale delle Ricerche”</i>;<o:p></o:p></p>
<p class=MsoListParagraph style='mso-list:l0 level1 lfo1'><![if !supportLists]><span style='mso-list:Ignore'>1.<span>&nbsp;&nbsp; </span></span><![endif]>Sono indetti i seguenti concorsi:<o:p></o:p></p>
<p class=MsoListParagraph style='mso-list:l0 level2 lfo1'><![if !supportLists]><span style='mso-list:Ignore'>a)<span>&nbsp;&nbsp; </span></span><![endif]>un posto presso la sede di Roma;<o:p></o:p></p>
<!--EndFragment--></body></html>`;

/** Incolla come fa il browser: un `ClipboardEvent` vero, con l'HTML negli appunti. */
async function incolla(editor: Locator, html: string, testo: string): Promise<void> {
  await editor.evaluate(
    (elemento, [html, testo]) => {
      const appunti = new DataTransfer();
      appunti.setData('text/html', html);
      appunti.setData('text/plain', testo);
      elemento.dispatchEvent(
        new ClipboardEvent('paste', { clipboardData: appunti, bubbles: true, cancelable: true }),
      );
    },
    [html, testo],
  );
}

/** Seleziona una parola dentro un editor, come farebbe il gestore col mouse. */
async function selezionaParola(page: Page, editor: Locator, parola: string): Promise<void> {
  await editor.evaluate((elemento, parola) => {
    const camminatore = document.createTreeWalker(elemento, NodeFilter.SHOW_TEXT);
    for (let nodo = camminatore.nextNode(); nodo; nodo = camminatore.nextNode()) {
      const inizio = nodo.textContent!.indexOf(parola);
      if (inizio < 0) continue;
      const range = document.createRange();
      range.setStart(nodo, inizio);
      range.setEnd(nodo, inizio + parola.length);
      getSelection()!.removeAllRanges();
      getSelection()!.addRange(range);
      return;
    }
    throw new Error(`parola non trovata: ${parola}`);
  }, parola);
  await page.waitForTimeout(0);
}

/**
 * Parola -> font con cui il PDF la scrive. Il grassetto non e' un attributo
 * del testo estratto ma la variante di font: lo legge lo stesso helper
 * `pypdf` dei test del renderer (`backend/tests/support/pdf.py`).
 */
function fontPerParola(pdf: string): {
  font: Record<string, string>;
  testo: string;
  x: Record<string, number>;
} {
  const backend = resolve(__dirname, '../../backend');
  const script = `
import json, sys
from pathlib import Path
from tests.support.pdf import estrai_font_e_testo, estrai_testo
contenuto = Path(sys.argv[1]).read_bytes()
from io import BytesIO
from pypdf import PdfReader
font = {}
for nome, pezzo in estrai_font_e_testo(contenuto):
    for parola in pezzo.split():
        font.setdefault(parola.strip(';:,.'), nome)
# Ascissa del primo pezzo di testo che inizia con una certa parola: dice se
# un titolo e' centrato e se le lettere rientrano rispetto ai commi.
x = {}
def visita(testo, cm, tm, _font, _dimensione):
    parole = testo.split()
    if parole:
        x.setdefault(parole[0], cm[4] + tm[4])
for pagina in PdfReader(BytesIO(contenuto)).pages:
    pagina.extract_text(visitor_text=visita)
print(json.dumps({"font": font, "testo": estrai_testo(contenuto), "x": x}))
`;
  return JSON.parse(
    execFileSync('uv', ['run', 'python', '-c', script, pdf], { cwd: backend, encoding: 'utf-8' }),
  );
}

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

  // 012 US1: enfasi selezionando il testo, come in un elaboratore di testi.
  await editor.click();
  await selezionaParola(page, editor, 'Premesso');
  await page.locator('[data-emphasis="grassetto"]').click();
  await expect(editor.locator('strong')).toHaveText('Premesso');
  await selezionaParola(page, editor, 'che');
  await page.keyboard.press('Control+i');
  await expect(editor.locator('em')).toHaveText('che');

  // 012 T023: incolla da Word in una sezione nuova. Il "visto" conserva
  // grassetto e corsivo; l'elenco diventa un ELENCO con i marcatori calcolati,
  // e i `1.`/`a)` di Word non restano nel testo.
  await page.locator('[data-add-section-inline]').click();
  const visto = page.locator('[data-section-text="sezione-2"]').first();
  await visto.click();
  await incolla(
    visto,
    APPUNTI_WORD,
    'VISTO il Decreto...\n1.\tSono indetti i seguenti concorsi:\na)\tun posto presso la sede di Roma;',
  );
  await expect(page.locator('[data-section-text="sezione-2"]')).toHaveCount(3);
  await expect(visto.locator('strong')).toHaveText('VISTO');
  await expect(visto.locator('em')).toHaveText('“Riordino del Consiglio Nazionale delle Ricerche”');
  await expect(page.locator('.item-marker')).toHaveText(['1.', 'a)']);
  await expect(page.locator('[data-item-index="0"]')).toHaveText(
    'Sono indetti i seguenti concorsi:',
  );

  // 012 T033: l'art. 3 del bando di riferimento, composto solo con tastiera e
  // pulsanti: nessun `1.` o `a)` scritto a mano (SC-002).
  await page.locator('[data-add-section-inline]').click();
  const intestazione = page.locator('[data-section-text="sezione-3"]').first();
  await intestazione.click();
  await page.keyboard.type('Art. 3 - Requisiti di ammissione');
  await page.getByRole('tab', { name: 'Proprietà' }).click();
  await page.locator('[data-block-type-select]').selectOption('TITOLO');
  const titolo = page.locator('[data-section-text="sezione-3"][data-block-type="TITOLO"]');
  await expect(titolo).toBeFocused();
  await expect(titolo).toHaveCSS('text-align', 'center');
  await page.keyboard.press('Enter');
  await page.keyboard.type(
    'Per la partecipazione al concorso sono richiesti i seguenti requisiti:',
  );
  await page.locator('[data-list="NUMERICO"]').click();
  const voce = (indice: number) =>
    page.locator(`[data-section-text="sezione-3"][data-item-index="${indice}"]`);
  await expect(voce(0)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(voce(1)).toBeFocused();
  await page.keyboard.type('cittadinanza di uno degli Stati membri dell’Unione Europea;');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await expect(voce(2)).toBeFocused();
  await page.keyboard.type('età non inferiore a 18 anni;');
  await page.keyboard.press('Enter');
  await expect(voce(3)).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.type(
    'I requisiti richiesti devono essere posseduti alla data di scadenza del termine per la presentazione della domanda.',
  );
  await page.locator('[data-align="GIUSTIFICATO"]').click();
  const sezione3 = page.locator('article', { has: titolo });
  await expect(sezione3.locator('.item-marker')).toHaveText(['1.', 'a)', 'b)', '2.']);
  // I marcatori non sono nel testo: l'editor della voce contiene solo la frase.
  await expect(voce(1)).toHaveText('cittadinanza di uno degli Stati membri dell’Unione Europea;');
  await expect(voce(3)).toHaveCSS('text-align', 'justify');

  await page.locator('.format-toolbar .hint').click();
  await page.locator('[data-save-sections]').click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  await page.screenshot({ path: testInfo.outputPath('builder-2b-enfasi.png'), fullPage: true });

  // Ricaricata la pagina, l'enfasi torna dal servizio e non dalla memoria del browser.
  await page.reload();
  await expect(
    page.locator('[data-section-text="intro"], [data-section-text]').first(),
  ).toBeVisible();
  await expect(
    page.locator('[data-section-text="sezione-2"]').first().locator('strong'),
  ).toHaveText('VISTO');
  await expect(page.locator('[data-section-text]').first().locator('strong')).toHaveText(
    'Premesso',
  );
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

  // 012 T025: generato il documento, l'enfasi e' nel PDF come variante di font.
  const idApi = /ID API: (\d+)/.exec((await page.getByText(/ID API: \d+/).textContent()) ?? '')![1];
  const generatore = await tokenGeneratore();
  try {
    const generato = await page.request.post('/api/v1/documenti/genera', {
      headers: { Authorization: `Bearer ${generatore.token}` },
      data: {
        sistema_richiedente: 'GEBAN',
        external_context_id: `e2e-${Date.now()}`,
        modello_versione_id: Number(idApi),
        dati: { titolo_it: 'Ricercatore in fisica applicata' },
      },
    });
    expect(generato.status(), await generato.text()).toBe(200);
    const percorsoPdf = testInfo.outputPath('bando-012.pdf');
    writeFileSync(percorsoPdf, await generato.body());
    const { font, testo, x } = fontPerParola(percorsoPdf);
    expect(font['Premesso']).toBe('TitilliumWebBold');
    expect(font['che']).toBe('TitilliumWebItalic');
    expect(font['VISTO']).toBe('TitilliumWebBold');
    expect(font['Decreto']).toBe('TitilliumWeb');
    expect(font['“Riordino']).toBe('TitilliumWebItalic');
    // Le virgolette curve di Word arrivano intatte (SC-006) e il valore del
    // segnaposto prende il posto del segnaposto.
    expect(testo).toContain('Premesso che Ricercatore in fisica applicata');
    expect(testo).toContain('“Riordino del Consiglio Nazionale delle Ricerche”');
    // T029: i marcatori li scrive la resa, non il testo incollato.
    expect(testo).toContain(
      '1. Sono indetti i seguenti concorsi: a) un posto presso la sede di Roma;',
    );
    expect(testo).not.toContain('{{');

    // T033: l'art. 3 com'e' nel bando, con numerazione calcolata in resa.
    expect(testo).toContain(
      'Art. 3 - Requisiti di ammissione 1. Per la partecipazione al concorso sono richiesti i seguenti requisiti: ' +
        'a) cittadinanza di uno degli Stati membri dell’Unione Europea; b) età non inferiore a 18 anni; ' +
        '2. I requisiti richiesti',
    );
    expect(font['Requisiti']).toBe('TitilliumWebBold');
    // Intestazione centrata: comincia ben oltre il margine dove stanno i commi.
    expect(x['Art.']).toBeGreaterThan(x['1.'] + 40);
    // Le lettere rientrano rispetto ai commi, e il testo rientra rispetto al marcatore.
    expect(x['a)']).toBeGreaterThan(x['1.'] + 5);
    expect(x['cittadinanza']).toBeGreaterThan(x['a)']);
    expect(x['2.']).toBeCloseTo(x['1.'], 0);
  } finally {
    await generatore.rimuovi();
  }
  await page.screenshot({ path: testInfo.outputPath('contesti-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('contesti-mobile.png'), fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
