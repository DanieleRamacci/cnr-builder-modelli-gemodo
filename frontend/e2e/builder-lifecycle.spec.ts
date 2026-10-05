import { test, expect, type Locator, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  accedi,
  bordiSforati,
  creaUtenteUsaEGetta,
  tokenDellaSessione,
  type UtenteUsaEGetta,
} from './support/keycloak';
import { concediAlManager } from './support/accessi';
import { RIGHE_VISTI } from './support/visti';
import { gruppiDiRighe } from '../src/features/builder/frammenti';

// Un "visto" e un elenco come li mette negli appunti Word desktop: le liste
// sono paragrafi `mso-list` con il marcatore in uno span `mso-list:Ignore`.
const APPUNTI_WORD = `<html xmlns:o="urn:schemas-microsoft-com:office:office"><body lang=IT>
<!--StartFragment--><p class=MsoNormal style='text-align:justify'><b><span style='color:#1F3864'>VISTO</span></b>
il Decreto Legislativo 4 giugno 2003, n. 127, recante <i>“Riordino del Consiglio Nazionale delle Ricerche”</i>;<o:p></o:p></p>
<p class=MsoListParagraph style='mso-list:l0 level1 lfo1'><![if !supportLists]><span style='mso-list:Ignore'>1.<span>&nbsp;&nbsp; </span></span><![endif]>Sono indetti i seguenti concorsi:<o:p></o:p></p>
<p class=MsoListParagraph style='mso-list:l0 level2 lfo1'><![if !supportLists]><span style='mso-list:Ignore'>a)<span>&nbsp;&nbsp; </span></span><![endif]>un posto presso la sede di Roma;<o:p></o:p></p>
<!--EndFragment--></body></html>`;

// Un logo di prova: il servizio lo ricodifica in PNG e lo mette nella testata.
const LOGO_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAHgAAAA8CAYAAACtrX6oAAABIElEQVR42u3dQQ6CMBQGYXjhbh7Ic3ggT4crEjesFO37+83KhVHCZEo1tKz7vi/IpZyCbLbjxXp7SDmI/XlfFWyIBsHocQ0+G8PRg7M5lIIN0SAYBINg/HIWnT67nOUXwzar1LP3p8neZpU6i+wi9/efq+CBBBzf0bXmIje75iI3W3KRmy25yM2W7J+sxV+V6m1csYIVrJbOFStYwSB44mFw9ONTsIJBMAgGwSAYcYJHv5Ni9ONTsIJB8KTDYIcb8RSsYLV0Xu6iYAWrpvNiteq6/xO5wUP0v05yx+Ur1X0nN3KX3MVnx0m/8q6K7ktIK2lfRnKDF4C/y/ikaCv8A2Xbo8Pw7RoMgkEwCMZ3Jlme4aBgEAyCcSmrJ58pGI15AcLOeofe1LUoAAAAAElFTkSuQmCC';

/** I marcatori calcolati delle voci di una sezione, come li disegna l'editor. */
async function marcatori(testo: Locator): Promise<string[]> {
  return testo
    .locator('[data-marcatore]')
    .evaluateAll((voci) => voci.map((voce) => voce.getAttribute('data-marcatore') ?? ''));
}

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
  await allineaSelezione(page);
}

/**
 * L'editor (ProseMirror) legge la selezione all'evento `selectionchange`, che
 * il browser manda dopo: con le mani arriva prima di qualunque tasto, coi
 * tasti di Playwright no, e il tasto agirebbe sulla selezione di prima
 * (tutto il testo, dopo un Ctrl+A). Lo si manda subito.
 */
async function allineaSelezione(page: Page): Promise<void> {
  await page.evaluate(() => document.dispatchEvent(new Event('selectionchange')));
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
  collegamenti: string[];
  immagini: number[];
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
# I collegamenti cliccabili: le annotazioni del PDF, non il testo.
collegamenti = [
    annotazione.get_object()["/A"]["/URI"]
    for pagina in PdfReader(BytesIO(contenuto)).pages
    for annotazione in pagina.get("/Annots", [])
]
immagini = [len(pagina.images) for pagina in PdfReader(BytesIO(contenuto)).pages]
print(json.dumps({"font": font, "testo": estrai_testo(contenuto), "x": x, "collegamenti": collegamenti,
                  "immagini": immagini}))
`;
  return JSON.parse(
    execFileSync('uv', ['run', 'python', '-c', script, pdf], { cwd: backend, encoding: 'utf-8' }),
  );
}

// Il contesto concede permessi solo dopo che l'integrazione ne ha il profilo
// di accesso (001 T091): il test lo imposta dalla scheda, subito dopo la
// verifica (ROLE_MANAGER -> permessi GEMODO).
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
  await concediAlManager(page);

  // 012 T069: chi gestisce i modelli del contesto imposta intestazione e pie'
  // di pagina del tipo documento, da Contesti -> geban -> Impostazioni modelli.
  // Valgono per anteprima e generazione di ogni modello di quel tipo.
  await page.goto(`/contesti/${contesto}/impostazioni`);
  await page
    .getByRole('row')
    .filter({ hasText: 'Discovery lifecycle' })
    .filter({ hasText: 'BANDO_CONCORSO' })
    .locator('[data-imposta-cornice]')
    .click();
  await page.locator('[data-aggiungi-intestazione]').click();
  await page.locator('[data-maschera="LOGO_CENTRO_TESTO_SOTTO"]').click();
  await page.locator('[data-logo-file]').setInputFiles({
    name: 'logo.png',
    mimeType: 'image/png',
    buffer: Buffer.from(LOGO_PNG, 'base64'),
  });
  await expect(page.locator('[data-cornice-testata] img')).toBeVisible();
  await page
    .locator('[data-testo-intestazione]')
    .fill('Consiglio Nazionale delle Ricerche\nUfficio Reclutamento del Personale');
  await page.locator('[data-aggiungi-piede]').click();
  await page.locator('[data-testo-piede]').fill('Piazzale Aldo Moro 7 - 00185 Roma');
  await page.locator('[data-salva-cornice]').click();
  await expect(page.locator('[data-cornice-salvata]')).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('cornice-tipo.png'), fullPage: true });
  await page
    .getByRole('navigation', { name: 'Navigazione principale' })
    .getByRole('link', { name: 'Contesti', exact: true })
    .click();
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
  // Le azioni di rado stanno nel menu "Altre azioni" (riscontro del 2026-10-05).
  await page.locator('[data-altre-azioni] summary').click();
  await expect(page.getByRole('menuitem', { name: 'Crea modello derivato' })).toBeVisible();
  await page.locator('.topbar .meta').click();
  await expect(page.getByRole('menuitem', { name: 'Crea modello derivato' })).toBeHidden();

  // T130: la 2b e' un editor a schermo intero. L'header e il footer della
  // shell non ci sono: l'unica barra e' la topbar della pagina.
  await expect(page.locator('.topbar')).toBeVisible();
  await expect(page.locator('header.app-header')).toHaveCount(0);
  await expect(page.locator('footer.app-footer')).toHaveCount(0);
  await expect(page.locator('main.app-main-editor')).toHaveCount(1);
  await expect(page.locator('.pannello [data-placeholder]').first()).toBeVisible();

  // Editor centrale: sezione nuova, testo, segnaposto col comando / (012
  // T064) e salvataggio automatico all'uscita dal blocco.
  await page.locator('[data-add-section-inline]').click();
  const editor = page.locator('[data-section-text]').first();
  await editor.click();
  await editor.pressSequentially('Premesso che ');
  await page.keyboard.type('/tit');
  await expect(page.locator('[data-slash-menu]')).toBeVisible();
  await expect(page.locator('[data-slash-item]')).toHaveText([/titolo_it/]);
  await page.screenshot({ path: testInfo.outputPath('builder-2b-slash.png') });
  await page.keyboard.press('Enter');
  await expect(page.locator('[data-slash-menu]')).toHaveCount(0);
  await expect(page.locator('[data-save-state]')).toHaveText(/Modifiche non salvate/);
  await page.locator('.format-toolbar .hint').click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  // Riscontro del 2026-10-02: Ctrl+Z deve annullare e Ctrl+Maiusc+Z ripetere,
  // anche dopo che l'editor ha riscritto il testo (qui: il segnaposto).
  await editor.click();
  await page.keyboard.press('End');
  await page.keyboard.press('ControlOrMeta+ArrowRight');
  await page.keyboard.type(' (bozza)');
  await expect(editor).toHaveText('Premesso che {{titolo_it}} (bozza)');
  await page.keyboard.press('ControlOrMeta+z');
  await expect(editor).toHaveText('Premesso che {{titolo_it}}');
  await page.keyboard.press('ControlOrMeta+Shift+z');
  await expect(editor).toHaveText('Premesso che {{titolo_it}} (bozza)');
  await page.keyboard.press('ControlOrMeta+z');
  await expect(editor).toHaveText('Premesso che {{titolo_it}}');
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
  // Una sola area di scrittura per la sezione (T077): un capoverso e due voci.
  await expect(visto.locator(':scope > *')).toHaveCount(3);
  await expect(visto.locator('strong')).toHaveText('VISTO');
  await expect(visto.locator('em')).toHaveText('“Riordino del Consiglio Nazionale delle Ricerche”');
  expect(await marcatori(visto)).toEqual(['1.', 'a)']);
  await expect(visto.locator('li').first()).toHaveText('Sono indetti i seguenti concorsi:');

  // Riscontro del 2026-10-02 (T077): cio' che si e' incollato si riseleziona
  // tutto insieme, capoversi e voci, e prende l'enfasi in un colpo solo.
  await visto.click();
  await page.keyboard.press('ControlOrMeta+a');
  await page.locator('[data-emphasis="grassetto"]').click();
  for (const blocco of await visto.locator(':scope > *').all()) {
    await expect(blocco.locator('strong')).toHaveText(await blocco.innerText());
  }
  await page.screenshot({ path: testInfo.outputPath('builder-2b-selezione-sezione.png') });
  await page.keyboard.press('ControlOrMeta+z');
  await expect(visto.locator('strong')).toHaveText('VISTO');

  // 012 T070: il foglio mostra la cornice del tipo documento, e la scheda
  // Pagina dice cosa c'e' e dove si imposta.
  await expect(page.locator('[data-sheet-intestazione] [data-cornice-testata]')).toContainText(
    'Ufficio Reclutamento del Personale',
  );
  await expect(page.locator('[data-sheet-intestazione] img')).toBeVisible();
  await page.getByRole('tab', { name: 'Pagina' }).click();
  await expect(page.locator('[data-pagina-intestazione]')).toContainText('Logo al centro');
  await expect(page.locator('[data-modifica-cornice]')).toBeVisible();
  await page.getByRole('tab', { name: 'Segnaposto' }).click();

  // 012 T050: un collegamento dalla toolbar, sulla parola selezionata.
  await visto.click();
  await selezionaParola(page, visto, 'Decreto');
  await page.locator('[data-link-open]').click();
  await page.locator('[data-link-input]').fill('www.normattiva.it');
  await page.keyboard.press('Enter');
  await expect(visto.locator('a')).toHaveAttribute('href', 'https://www.normattiva.it');
  await expect(visto.locator('a')).toHaveText('Decreto');

  // 012 T033: l'art. 3 del bando di riferimento, composto solo con tastiera e
  // pulsanti: nessun `1.` o `a)` scritto a mano (SC-002).
  await page.locator('[data-add-section-inline]').click();
  const testoArt3 = page.locator('[data-section-text="sezione-3"]');
  await testoArt3.click();
  await page.keyboard.type('Art. 3 - Requisiti di ammissione');
  // T059: lo stile si sceglie dalla barra, dove sta il cursore.
  await page.locator('[data-style-select]').selectOption('TITOLO');
  const titolo = testoArt3.locator('[data-block-type="TITOLO"]');
  await expect(testoArt3).toBeFocused();
  await expect(titolo).toHaveCSS('text-align', 'center');
  await page.keyboard.press('Enter');
  await page.keyboard.type(
    'Per la partecipazione al concorso sono richiesti i seguenti requisiti:',
  );
  await page.locator('[data-list="NUMERICO"]').click();
  const voce = (indice: number) => testoArt3.locator('li').nth(indice);
  await expect(testoArt3).toBeFocused();
  await page.keyboard.press('Enter');
  await page.keyboard.type('cittadinanza di uno degli Stati membri dell’Unione Europea;');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await page.keyboard.type('età non inferiore a 18 anni;');
  await page.keyboard.press('Enter');
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.type(
    'I requisiti richiesti devono essere posseduti alla data di scadenza del termine per la presentazione della domanda.',
  );
  await page.locator('[data-align="GIUSTIFICATO"]').click();
  expect(await marcatori(testoArt3)).toEqual(['1.', 'a)', 'b)', '2.']);
  // I marcatori non sono nel testo: la voce contiene solo la frase.
  await expect(voce(1)).toHaveText('cittadinanza di uno degli Stati membri dell’Unione Europea;');
  await expect(voce(3)).toHaveCSS('text-align', 'justify');

  // Riscontro del 2026-10-02 (T078-T080) sui visti della versione 36: salvati
  // una riga del PDF per capoverso, non si giustificavano, e il foglio non
  // diceva dove finiscono le pagine. Si incollano cosi', si ricompongono con
  // "Unisci righe", si giustificano, e i fogli disegnati devono essere quelli
  // del PDF dell'anteprima.
  await page.locator('[data-add-section-inline]').click();
  const testoVisti = page.locator('[data-section-text="sezione-4"]');
  await testoVisti.click();
  const html = RIGHE_VISTI.map(
    (riga) => `<p>${riga.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</p>`,
  ).join('');
  await incolla(testoVisti, html, RIGHE_VISTI.join('\n'));
  await expect(testoVisti.locator(':scope > p')).toHaveCount(RIGHE_VISTI.length);
  await page.keyboard.press('ControlOrMeta+a');
  await page.locator('[data-join-lines]').click();
  const capoversiVisti = gruppiDiRighe(RIGHE_VISTI).length;
  await expect(testoVisti.locator(':scope > p')).toHaveCount(capoversiVisti);
  expect(capoversiVisti).toBeLessThan(RIGHE_VISTI.length / 2);
  await expect(testoVisti.locator(':scope > p').nth(2)).toHaveText(
    /^VISTO il D\.Lgs 31 dicembre 2009 n\. 213, .* legge 27 settembre 2007, n\. 165”;$/,
  );
  await page.keyboard.press('ControlOrMeta+a');
  await page.locator('[data-align="GIUSTIFICATO"]').click();
  await expect(testoVisti.locator(':scope > p').nth(2)).toHaveCSS('text-align', 'justify');
  // Il foglio e' largo come il PDF: 190 mm di testo su 210.
  const misure = await page.locator('.pagina').evaluate((foglio) => ({
    foglio: foglio.getBoundingClientRect().width,
    testo: foglio.querySelector('.testo-sezione')!.getBoundingClientRect().width,
  }));
  expect(misure.testo / misure.foglio).toBeCloseTo(190 / 210, 2);

  // Uscendo dal testo si salva, e il renderer dice dove cominciano le pagine.
  await page.locator('.format-toolbar .hint').click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  await expect(page.locator('[data-pagine]')).toHaveText(/^\s*\d+ pagine nel PDF\s*$/);
  const pagine = Number(
    /(\d+)/.exec((await page.locator('[data-pagine]').textContent()) ?? '')![1],
  );
  expect(pagine).toBeGreaterThanOrEqual(2);
  await expect(page.locator('[data-fine-pagina]')).toHaveCount(pagine - 1);
  await expect(page.locator('[data-fine-pagina]').first()).toHaveText('Pagina 2');
  await page.locator('[data-preview-open]').click();
  await expect(page.locator('[data-preview-frame]')).toBeVisible();
  const pagineAnteprima = await page
    .locator('[data-preview-frame]')
    .evaluate(async (cornice: HTMLIFrameElement) => {
      const pdf = await (await fetch(cornice.src)).text();
      return (pdf.match(/\/Type\s*\/Page(?![s\w])/g) ?? []).length;
    });
  expect(pagineAnteprima).toBe(pagine);
  await page.getByRole('button', { name: 'Chiudi', exact: true }).click();
  // Riscontro del 2026-10-05 (T082, T083): fra due fogli c'e' lo spazio che
  // c'e' nel PDF, con pie' di pagina e intestazione; il fondo del foglio sta
  // fermo, e' il testo a passare alla pagina dopo. Si va a capo davanti al
  // capoverso che apre la pagina 2: dopo la misura nuova il pie' di pagina
  // della pagina 1 e' dov'era, e il capoverso e' sotto la fascia.
  const sulFoglio = (selettore: string, lato: 'top' | 'bottom' = 'top') =>
    page
      .locator(selettore)
      .first()
      .evaluate((elemento, lato) => {
        const foglio = elemento.closest('.pagina')!.getBoundingClientRect();
        return elemento.getBoundingClientRect()[lato] - foglio.top;
      }, lato);
  const piedePrima = await sulFoglio('[data-zona-piede]');
  const inizioPagina2 = await testoVisti.evaluate((testo) => {
    const spazio = testo.querySelector('[data-salto-pagina="2"]')!;
    const capoverso = spazio.closest('p') ?? spazio.nextElementSibling!;
    return (capoverso.textContent ?? '').slice(0, 40);
  });
  const apre = testoVisti.locator(':scope > p', { hasText: inizioPagina2 }).first();
  // Fra due fogli c'e' tutto lo spazio del PDF: pie' di pagina e intestazione.
  const fascia = page.locator('[data-fra-fogli]').first();
  await expect(fascia.locator('[data-zona-piede]')).toContainText('Piazzale Aldo Moro 7');
  await expect(fascia.locator('[data-zona-testa] [data-cornice-testata]')).toContainText(
    'Consiglio Nazionale delle Ricerche',
  );
  expect(await sulFoglio('[data-fra-fogli]', 'bottom')).toBeGreaterThan(piedePrima + 60);
  const misurato = page.waitForResponse(
    (risposta) =>
      risposta.url().endsWith('/impaginazione') && risposta.request().method() === 'POST',
  );
  await apre.click({ position: { x: 2, y: 4 } });
  await allineaSelezione(page);
  for (let i = 0; i < 3; i += 1) await page.keyboard.press('Enter');
  await expect(testoVisti.locator(':scope > p').filter({ hasText: /^$/ })).toHaveCount(3);
  const nuova = await (await misurato).json();
  expect(nuova.pagine).toBeGreaterThanOrEqual(pagine);
  await expect
    .poll(async () => Math.abs((await sulFoglio('[data-zona-piede]')) - piedePrima))
    .toBeLessThan(3);
  const sotto = await sulFoglio('[data-fra-fogli]', 'bottom');
  expect(
    await apre.evaluate(
      (p) => p.getBoundingClientRect().top - p.closest('.pagina')!.getBoundingClientRect().top,
    ),
  ).toBeGreaterThanOrEqual(sotto - 1);
  // Una riga vuota davanti all'ultimo capoverso della pagina 1: non ci sta
  // piu' intero e la pagina finisce a meta'. Lo spazio fra i fogli va dentro
  // il capoverso, all'inizio della riga che passa alla pagina 2.
  const ultimoSopra = await testoVisti.evaluate((testo) => {
    const spazio = testo.querySelector('[data-salto-pagina="2"]')!;
    const capoversi = Array.from(testo.querySelectorAll(':scope > p')).filter(
      (p) =>
        p.textContent && p.getBoundingClientRect().bottom <= spazio.getBoundingClientRect().top,
    );
    return (capoversi.at(-1)!.textContent ?? '').slice(0, 40);
  });
  const spezzato = testoVisti.locator(':scope > p', { hasText: ultimoSopra }).first();
  const rimisurato = page.waitForResponse(
    (risposta) =>
      risposta.url().endsWith('/impaginazione') && risposta.request().method() === 'POST',
  );
  await spezzato.click({ position: { x: 2, y: 4 } });
  await allineaSelezione(page);
  await page.keyboard.press('Enter');
  const dentro = (await (await rimisurato).json()).inizi_pagina[0];
  expect(dentro.riga).toBeGreaterThan(0);
  await expect(spezzato.locator('[data-salto-pagina="2"]')).toHaveCount(1);
  await expect
    .poll(async () => Math.abs((await sulFoglio('[data-zona-piede]')) - piedePrima))
    .toBeLessThan(3);
  // Il testo continua sotto la fascia, e le righe sopra restano giustificate.
  const righe = await spezzato.evaluate((p) => {
    const spazio = p.querySelector('[data-salto-pagina]')!.getBoundingClientRect();
    const intervallo = document.createRange();
    intervallo.selectNodeContents(p);
    const rettangoli = Array.from(intervallo.getClientRects()).filter((r) => r.width > 0);
    return {
      // Mezzo pixel di qua o di la': le righe stanno su frazioni di pixel.
      sopra: rettangoli.filter((r) => r.bottom <= spazio.top + 2).length,
      sotto: rettangoli.filter((r) => r.top >= spazio.bottom - 2).length,
    };
  });
  expect(righe.sopra).toBeGreaterThan(0);
  expect(righe.sotto).toBeGreaterThan(0);
  await page.locator('[data-fra-fogli]').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('builder-2b-fogli-capoverso.png') });
  // Riscontro del 2026-10-05: si salva dalla barra degli strumenti, che resta
  // in alto scorrendo il documento; salvato, il pulsante lo dice e si spegne.
  const salvaDocumento = page.locator('[data-salva-documento]');
  await expect(salvaDocumento).toHaveText('Salva documento');
  await expect(salvaDocumento).toBeEnabled();
  await salvaDocumento.click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  await expect(salvaDocumento).toHaveText('Documento salvato');
  await expect(salvaDocumento).toBeDisabled();
  // Il nome del modello e' generato e lungo: va su due righe al piu', il
  // codice con l'id non c'e', e i pulsanti restano su una riga sola.
  await page.locator('[data-titolo-modello]').evaluate((titolo) => {
    titolo.textContent =
      'Tempo Indeterminato - Collaboratore di Amministrazione - EN - 2026-10-01 - Tempo Indeterminato - Collaboratore di Amministrazione';
  });
  const barra = await page.locator('.topbar').evaluate((topbar) => {
    const titolo = topbar.querySelector('[data-titolo-modello]')!;
    return {
      righeTitolo: Math.round(
        titolo.getBoundingClientRect().height / parseFloat(getComputedStyle(titolo).lineHeight),
      ),
      meta: topbar.querySelector('.meta')!.textContent,
      larghezzaTitolo: titolo.getBoundingClientRect().width,
      strumenti: document.querySelector('.format-toolbar')!.getBoundingClientRect().height,
      pulsanti: Array.from(topbar.querySelectorAll('.azioni .btn')).map(
        (pulsante) => pulsante.getBoundingClientRect().height,
      ),
    };
  });
  expect(barra.righeTitolo).toBeLessThanOrEqual(2);
  expect(barra.larghezzaTitolo).toBeGreaterThan(300);
  // La barra degli strumenti, col pulsante di salvataggio, sta su una riga.
  expect(barra.strumenti).toBeLessThan(56);
  expect(barra.meta).toMatch(/^v\d+ · BOZZA$/);
  for (const altezza of barra.pulsanti) expect(altezza).toBeLessThanOrEqual(36);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath('builder-2b-barra.png') });
  // Capoversi e voci hanno il corpo del PDF, non quello di Bootstrap Italia;
  // e il testo col cursore non ha la cornice nera di focus.
  const stili = await testoVisti.evaluate((testo) => ({
    p: getComputedStyle(testo.querySelector('p')!).fontSize,
    li: getComputedStyle(document.querySelector('[data-section-text] li')!).fontSize,
    cornice: getComputedStyle(testo).boxShadow,
  }));
  expect(stili.p).toBe(stili.li);
  expect(stili.cornice).toBe('none');
  await page.locator('[data-fra-fogli]').first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('builder-2b-fogli.png') });
  // La sezione di prova esce dal documento: il resto del flusso confronta il
  // PDF generato con quello di sempre.
  await page.locator('[data-remove-section="sezione-4"]').click();
  await page.locator('[data-save-sections]').click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  await expect(page.locator('[data-fine-pagina]')).toHaveCount(0);

  // T063: scorrendo, la barra degli strumenti resta in cima.
  await page.mouse.wheel(0, 1500);
  await expect
    .poll(async () => Math.abs((await page.locator('.format-toolbar').boundingBox())?.y ?? 999))
    .toBeLessThan(2);
  // Riscontro del 2026-10-05: anche le sidebar restano a vista, subito sotto
  // la barra; e i comandi di una sezione stanno su una riga, col cestino.
  const sottoBarra = (await page.locator('.format-toolbar').boundingBox())!;
  for (const sidebar of ['.outline', '.pannello']) {
    const box = (await page.locator(sidebar).boundingBox())!;
    expect(Math.abs(box.y - (sottoBarra.y + sottoBarra.height))).toBeLessThan(2);
  }
  const comandi = await page
    .locator('.outline-item')
    .first()
    .locator('.section-actions button')
    .evaluateAll((pulsanti) => pulsanti.map((p) => Math.round(p.getBoundingClientRect().top)));
  expect(comandi).toHaveLength(3);
  expect(new Set(comandi).size).toBe(1);
  await expect(page.locator('.outline-item .handle')).toHaveCount(0);
  // Cio' che si vede davvero in cima allo schermo: la barra, e sotto le sidebar.
  const inCima = await page.evaluate((y) => {
    const qui = (x: number, altezza: number) =>
      document.elementFromPoint(x, altezza)?.closest('.format-toolbar, .outline, .pannello')
        ?.className ?? '';
    return { barra: qui(640, 20), sinistra: qui(100, y + 20), destra: qui(1100, y + 20) };
  }, sottoBarra.y + sottoBarra.height);
  expect(inCima.barra).toContain('format-toolbar');
  expect(inCima.sinistra).toContain('outline');
  expect(inCima.destra).toContain('pannello');
  await page.screenshot({ path: testInfo.outputPath('builder-2b-sidebar.png') });
  // Riscontro del 2026-10-05: con molti segnaposto la colonna di destra
  // scorre fino all'ultimo, invece di tagliarli; e "Aggiungi sezione" e
  // "Salva documento" stanno in cima all'elenco delle sezioni.
  await page.locator('.panel-body').evaluate((corpo) => {
    const campo = corpo.querySelector('.campo')!;
    for (let i = 0; i < 40; i += 1) {
      const copia = campo.cloneNode(true) as HTMLElement;
      copia.setAttribute('data-copia-prova', '');
      campo.parentElement!.appendChild(copia);
    }
  });
  const colonna = await page.locator('.pannello').evaluate((pannello) => {
    pannello.scrollTop = pannello.scrollHeight;
    const ultimo = Array.from(pannello.querySelectorAll('.campo')).at(-1)!;
    return {
      scorre: pannello.scrollHeight > pannello.clientHeight + 100,
      ultimoVisibile:
        ultimo.getBoundingClientRect().bottom <= pannello.getBoundingClientRect().bottom + 1,
      schedeInCima:
        Math.abs(
          pannello.querySelector('.panel-tabs')!.getBoundingClientRect().top -
            pannello.getBoundingClientRect().top,
        ) < 2,
    };
  });
  expect(colonna).toEqual({ scorre: true, ultimoVisibile: true, schedeInCima: true });
  await page.screenshot({ path: testInfo.outputPath('builder-2b-segnaposto-molti.png') });
  await page.locator('.panel-body').evaluate((corpo) => {
    corpo.querySelectorAll('[data-copia-prova]').forEach((copia) => copia.remove());
    corpo.closest('.pannello')!.scrollTop = 0;
  });
  const azioniInCima = await page
    .locator('.outline')
    .evaluate(
      (outline) =>
        outline.querySelector('[data-add-section]')!.getBoundingClientRect().bottom <=
        outline.querySelector('.outline-item')!.getBoundingClientRect().top,
    );
  expect(azioniInCima).toBe(true);
  // E la colonna non scorre di lato: niente resta tagliato a sinistra.
  expect(
    await page
      .locator('.outline')
      .evaluate(
        (outline) => outline.scrollWidth <= outline.clientWidth && outline.scrollLeft === 0,
      ),
  ).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));

  // T062: la sezione prende un nome, che compare nella struttura a sinistra.
  await titolo.click();
  await page.getByRole('tab', { name: 'Proprietà' }).click();
  await page.locator('[data-section-name]').fill('Art. 3 - Requisiti');
  await page.locator('[data-section-name]').press('Tab');
  await expect(
    page.locator('.outline-item strong', { hasText: 'Art. 3 - Requisiti' }),
  ).toBeVisible();

  await page.locator('.format-toolbar .hint').click();
  await page.locator('[data-save-sections]').click();
  await expect(page.locator('[data-save-state]')).toHaveText(/Tutte le modifiche salvate/);
  await page.screenshot({ path: testInfo.outputPath('builder-2b-enfasi.png'), fullPage: true });

  // 012 T040: l'anteprima della bozza, dall'editor, senza pubblicare.
  await page.locator('[data-preview-open]').click();
  const cornice = page.locator('[data-preview-frame]');
  await expect(cornice).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('builder-2b-anteprima.png') });
  const pdfAnteprima = testInfo.outputPath('anteprima-012.pdf');
  const base64 = await cornice.evaluate(async (elemento: HTMLIFrameElement) => {
    const byte = new Uint8Array(await (await fetch(elemento.src)).arrayBuffer());
    let binario = '';
    for (const b of byte) binario += String.fromCharCode(b);
    return btoa(binario);
  });
  writeFileSync(pdfAnteprima, Buffer.from(base64, 'base64'));
  await page.getByRole('button', { name: 'Chiudi', exact: true }).click();
  await expect(page.locator('[data-preview-dialog]')).not.toBeVisible();

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
  // Genera con il token ACE dell'utente: ROLE_MANAGER concede anche
  // DOCUMENTI_GENERATORE nel contesto, ed e' cosi' che chiama GEBAN.
  const token = await tokenDellaSessione(page);
  {
    const generato = await page.request.post('/api/v1/documenti/genera', {
      headers: { Authorization: `Bearer ${token}` },
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
    const { font, testo, x, collegamenti, immagini } = fontPerParola(percorsoPdf);
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

    // T044: la cornice del tipo documento, configurata dall'amministratore.
    expect(testo).toContain(
      'Consiglio Nazionale delle Ricerche Ufficio Reclutamento del Personale',
    );
    expect(testo).toContain('Piazzale Aldo Moro 7 - 00185 Roma');
    expect(testo).toMatch(/Pagina 1 di \d/);
    // T066: il logo caricato e' su ogni pagina.
    expect(immagini.length).toBeGreaterThan(0);
    expect(immagini.every((n) => n === 1)).toBe(true);
    // T049: il collegamento e' cliccabile, e il suo testo resta nel documento.
    expect(collegamenti).toEqual(['https://www.normattiva.it']);
    expect(testo).toContain('VISTO il Decreto Legislativo');

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

    // T041, SC-003: anteprima e documento generato coincidono per struttura,
    // ordine, enfasi e numerazione; differiscono solo i valori.
    const anteprima = fontPerParola(pdfAnteprima);
    expect(anteprima.testo).toContain('ANTEPRIMA DELLA BOZZA');
    expect(anteprima.testo).toContain('Premesso che «Titolo»');
    const corpo = (testo: string) => testo.slice(testo.indexOf('Premesso'));
    expect(corpo(anteprima.testo).replace('«Titolo»', 'Ricercatore in fisica applicata')).toBe(
      corpo(testo),
    );
    for (const parola of ['Premesso', 'che', 'VISTO', '“Riordino', 'Requisiti', 'cittadinanza']) {
      expect(anteprima.font[parola], parola).toBe(font[parola]);
    }
    expect(anteprima.x['a)']).toBeCloseTo(x['a)'], 0);
  }
  // 013, riscontro GEBAN del 2026-10-05: lo stesso bando si rigenera a ogni
  // correzione con la stessa chiave. Ogni volta il PDF coi dati nuovi e un
  // riferimento nuovo; GEMODO non lo conserva, quindi non c'e' download.
  {
    const chiaveBando = `e2e-bando-${Date.now()}`;
    const generaBando = (titolo: string) =>
      page.request.post('/api/v1/documenti/genera', {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          sistema_richiedente: 'GEBAN',
          external_context_id: chiaveBando,
          modello_versione_id: Number(idApi),
          dati: { titolo_it: titolo },
        },
      });
    const riferimenti = new Set<string>();
    for (const titolo of ['Prima stesura', 'Seconda stesura corretta', 'Definitivo']) {
      const risposta = await generaBando(titolo);
      expect(risposta.status(), await risposta.text()).toBe(200);
      expect(risposta.headers()['content-type']).toBe('application/pdf');
      const percorso = testInfo.outputPath(`bando-013-${riferimenti.size}.pdf`);
      writeFileSync(percorso, await risposta.body());
      expect(fontPerParola(percorso).testo).toContain(`Premesso che ${titolo}`);
      riferimenti.add(risposta.headers()['x-riferimento-documentale']);
    }
    expect(riferimenti.size).toBe(3);
    const [primo] = riferimenti;
    const download = await page.request.get(`/api/v1/documenti/${primo}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(download.status()).toBe(404);

    // 013: l'amministratore vede nel registro attivita' chi ha generato cosa,
    // col nome dell'utente e non l'id del token.
    await page.goto('/configurazione/attivita');
    await page.locator('[data-filtro-testo]').fill(chiaveBando);
    await page.locator('[data-applica-filtri]').click();
    const righe = page.locator('[data-evento]');
    await expect(righe).toHaveCount(3);
    for (const riga of await righe.all()) {
      await expect(riga).toContainText(utente.username);
      await expect(riga).toContainText('Generazioni');
      await expect(riga.locator('[data-esito]')).toHaveText('Generato');
    }
    await righe.first().click();
    await expect(page.locator('[data-dettaglio-evento]')).toContainText(chiaveBando);
    await page.screenshot({ path: testInfo.outputPath('registro-attivita.png'), fullPage: true });
    await page.goBack();
  }
  await page.screenshot({ path: testInfo.outputPath('contesti-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('contesti-mobile.png'), fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
