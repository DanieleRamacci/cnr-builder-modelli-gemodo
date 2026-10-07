import { marked } from 'marked';

/** L'indice scritto da scripts/sync-documentazione.mjs in public/manuale/. */
export interface PaginaManuale {
  slug: string;
  titolo: string;
  /** Percorso della pagina dentro docs/, base dei suoi link relativi. */
  sorgente: string;
}

/** Un link fuori dal manuale, per esempio una pagina Swagger. */
export interface CollegamentoManuale {
  titolo: string;
  href: string;
}

export interface SezioneManuale {
  codice: string;
  titolo: string;
  pagine: PaginaManuale[];
  collegamenti?: CollegamentoManuale[];
}

export interface IndiceManuale {
  sezioni: SezioneManuale[];
}

export const BASE_MANUALE = '/manuale';
export const ROTTA_MANUALE = '/documentazione';

/** Lo stesso slug di mkdocs (toc.slugify), cosi' le ancore valgono in entrambi. */
export function slugTitolo(testo: string): string {
  return testo
    .normalize('NFKD')
    .replace(/[^\p{ASCII}]/gu, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, '-');
}

/**
 * Gli avvisi mkdocs (`!!! warning "Titolo"` con corpo rientrato) diventano una
 * citazione: marked non li conosce e li mostrerebbe come codice.
 */
export function convertiAvvisi(md: string): string {
  return md.replace(
    /^!!! *(\w+)(?: +"([^"]*)")?\n((?:(?: {4}.*)?\n)*)/gm,
    (_tutto, tipo: string, titolo: string | undefined, corpo: string) => {
      const righe = corpo
        .replace(/\n+$/, '')
        .split('\n')
        .map((riga) => riga.replace(/^ {4}/, ''));
      return (
        [
          `> **${titolo ?? tipo}**`,
          '>',
          ...righe.map((riga) => (riga ? `> ${riga}` : '>')),
          '',
        ].join('\n') + '\n'
      );
    },
  );
}

function risolvi(base: string, relativo: string): string {
  const parti = base.split('/').slice(0, -1);
  for (const pezzo of relativo.split('/')) {
    if (pezzo === '..') parti.pop();
    else if (pezzo && pezzo !== '.') parti.push(pezzo);
  }
  return parti.join('/');
}

/**
 * Markdown -> HTML di una pagina del manuale.
 *
 * `sanifica` e' la sanificazione Angular, applicata **prima** di aggiungere gli
 * id ai titoli e di riscrivere i link: Angular toglie `id` e `data-*`, e quello
 * che si aggiunge dopo deriva solo dal testo dei titoli e dall'indice.
 */
export function rendiPagina(
  md: string,
  pagina: PaginaManuale,
  indice: IndiceManuale,
  sanifica: (html: string) => string,
): string {
  const html = sanifica(marked.parse(convertiAvvisi(md), { async: false, gfm: true }));
  const doc = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html');
  const radice = doc.body.firstElementChild as HTMLElement;
  const perSorgente = new Map(
    indice.sezioni.flatMap((sezione) => sezione.pagine).map((p) => [p.sorgente, p.slug] as const),
  );

  const usati = new Map<string, number>();
  radice.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach((titolo) => {
    const base = slugTitolo(titolo.textContent ?? '');
    const volte = usati.get(base) ?? 0;
    usati.set(base, volte + 1);
    titolo.id = volte ? `${base}_${volte}` : base;
  });

  radice.querySelectorAll('a[href]').forEach((link) => {
    const href = link.getAttribute('href')!;
    if (/^[a-z]+:/i.test(href)) {
      link.setAttribute('target', '_blank');
      link.setAttribute('rel', 'noopener');
      return;
    }
    if (href.startsWith('/')) {
      // Swagger, ReDoc e YAML vivono fuori dall'app: si aprono a parte.
      if (!href.startsWith(`${ROTTA_MANUALE}/`)) {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noopener');
      }
      return;
    }
    const [percorso, ancora] = href.split('#');
    const destinazione = percorso
      ? perSorgente.get(risolvi(pagina.sorgente, percorso))
      : pagina.slug;
    if (destinazione === undefined) {
      // Un link a un file fuori dal manuale (spec, sorgenti): resta testo.
      const testo = doc.createElement('span');
      testo.className = 'link-esterno-manuale';
      testo.title = `Non incluso nel manuale: ${href}`;
      testo.innerHTML = link.innerHTML;
      link.replaceWith(testo);
      return;
    }
    link.setAttribute('href', `${ROTTA_MANUALE}/${destinazione}${ancora ? `#${ancora}` : ''}`);
  });

  radice.querySelectorAll('table').forEach((tabella) => {
    tabella.classList.add('table', 'table-sm');
    const contenitore = doc.createElement('div');
    contenitore.className = 'tabella-manuale';
    tabella.replaceWith(contenitore);
    contenitore.appendChild(tabella);
  });
  return radice.innerHTML;
}
