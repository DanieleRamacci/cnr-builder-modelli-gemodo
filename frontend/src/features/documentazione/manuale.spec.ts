import { convertiAvvisi, type IndiceManuale, rendiPagina, slugTitolo } from './manuale';

const indice: IndiceManuale = {
  sezioni: [
    {
      codice: 'utenti',
      titolo: 'Per gli utenti',
      pagine: [{ slug: 'utenti-modelli', titolo: 'Modelli', sorgente: 'utenti/modelli.md' }],
    },
    {
      codice: 'sviluppatori',
      titolo: 'Per gli sviluppatori',
      pagine: [{ slug: 'contratto-dati', titolo: 'Contratto dati', sorgente: 'contratto-dati.md' }],
    },
  ],
};
const [modelli, contratto] = indice.sezioni.flatMap((s) => s.pagine);
const nessunaSanificazione = (html: string) => html;

function rendi(md: string, pagina = modelli) {
  const div = document.createElement('div');
  div.innerHTML = rendiPagina(md, pagina, indice, nessunaSanificazione);
  return div;
}

describe('manuale', () => {
  it('slugs headings like mkdocs, so the same anchors work in both', () => {
    expect(slugTitolo('Campi ripetibili (0.8.0)')).toBe('campi-ripetibili-080');
    expect(slugTitolo('Intestazione e piè di pagina')).toBe('intestazione-e-pie-di-pagina');
    expect(slugTitolo("Cosa può cambiare l'integratore")).toBe('cosa-puo-cambiare-lintegratore');
  });

  it('gives each heading an id, disambiguating repeated titles', () => {
    const div = rendi('# Titolo\n\n## Esempio\n\n## Esempio\n');
    expect([...div.querySelectorAll('h1, h2')].map((h) => h.id)).toEqual([
      'titolo',
      'esempio',
      'esempio_1',
    ]);
  });

  it('rewrites links between manual pages to in-app routes, keeping the anchor', () => {
    const div = rendi('[contratto](../contratto-dati.md#campi-ripetibili-080) e [qui](#sezione)');
    const [primo, secondo] = [...div.querySelectorAll('a')];
    expect(primo.getAttribute('href')).toBe('/documentazione/contratto-dati#campi-ripetibili-080');
    expect(secondo.getAttribute('href')).toBe('/documentazione/utenti-modelli#sezione');
  });

  it('resolves links relative to the page folder', () => {
    const div = rendi('[guida](utenti/modelli.md)', contratto);
    expect(div.querySelector('a')!.getAttribute('href')).toBe('/documentazione/utenti-modelli');
  });

  it('turns links to files outside the manual into plain text, never a broken link', () => {
    const div = rendi('vedi [la spec](../specs/014/spec.md)', contratto);
    expect(div.querySelector('a')).toBeNull();
    expect(div.querySelector('.link-esterno-manuale')!.textContent).toBe('la spec');
  });

  it('opens absolute links in a new tab', () => {
    const a = rendi('[sito](https://example.org)').querySelector('a')!;
    expect(a.getAttribute('target')).toBe('_blank');
    expect(a.getAttribute('rel')).toBe('noopener');
  });

  it('renders mkdocs admonitions as a quote instead of a code block', () => {
    const md = '!!! warning "Proposta non implementata"\n    Questa pagina non vale.\n\nDopo.\n';
    expect(convertiAvvisi(md)).toBe(
      '> **Proposta non implementata**\n>\n> Questa pagina non vale.\n\nDopo.\n',
    );
    const div = rendi(md);
    expect(div.querySelector('blockquote strong')!.textContent).toBe('Proposta non implementata');
    expect(div.querySelector('pre')).toBeNull();
  });

  it('wraps tables so wide ones scroll instead of overflowing the page', () => {
    const div = rendi('| a | b |\n|---|---|\n| 1 | 2 |\n');
    expect(div.querySelector('.tabella-manuale > table.table')).not.toBeNull();
  });

  it('adds ids after sanitizing, so the sanitizer cannot strip them', () => {
    const togliId = (html: string) => html.replace(/ id="[^"]*"/g, '');
    const div = document.createElement('div');
    div.innerHTML = rendiPagina('## Sezione\n', modelli, indice, togliId);
    expect(div.querySelector('h2')!.id).toBe('sezione');
  });
});
