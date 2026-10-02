/**
 * Il testo di un blocco come sequenza di frammenti (spec 012, FR-001).
 *
 * Qui l'HTML degli appunti diventa dati; il testo dell'editor lo converte
 * `documento-editor.ts` (012 T074). Al servizio arrivano frammenti - testo puro
 * con attributi booleani - e mai markup: il divieto di HTML del formato
 * (`GEMODO_DOCUMENT_V1`) non viene allentato, perche' l'HTML viene interpretato
 * e scartato nel browser (research.md R8).
 */

export type FrammentoTesto = {
  testo: string;
  grassetto?: boolean;
  corsivo?: boolean;
  sottolineato?: boolean;
  collegamento?: string | null;
};

export type TipoMarcatore = 'NUMERICO' | 'ALFABETICO' | 'PUNTATO';

export type ElementoElenco = {
  livello: 0 | 1;
  marcatore: TipoMarcatore;
  frammenti: FrammentoTesto[];
};

/** Cio' che l'incolla produce: capoversi e elenchi, nient'altro (FR-017). */
export type BloccoIncollato =
  | { tipo: 'PARAGRAFO'; frammenti: FrammentoTesto[] }
  | { tipo: 'ELENCO'; elementi: ElementoElenco[] };

type Enfasi = Required<Pick<FrammentoTesto, 'grassetto' | 'corsivo' | 'sottolineato'>> & {
  collegamento: string | null;
};

const NESSUNA_ENFASI: Enfasi = {
  grassetto: false,
  corsivo: false,
  sottolineato: false,
  collegamento: null,
};
const SCHEMI_COLLEGAMENTO = new Set(['http:', 'https:', 'mailto:']);

// --- Frammenti --------------------------------------------------------------

/**
 * Unisce i frammenti adiacenti con gli stessi attributi e scarta quelli vuoti.
 *
 * Senza questa unione ogni grassetto tolto e rimesso lascerebbe un frammento
 * spurio in piu', e un segnaposto spezzato fra due frammenti uguali non
 * verrebbe piu' sostituito (la sostituzione avviene per frammento, FR-005).
 * Gli attributi falsi non vengono scritti: sono il default del formato.
 */
export function normalizzaFrammenti(frammenti: FrammentoTesto[]): FrammentoTesto[] {
  const uniti: FrammentoTesto[] = [];
  for (const frammento of frammenti) {
    if (!frammento.testo) continue;
    const pulito = compatta(frammento);
    const precedente = uniti.at(-1);
    if (precedente && stessaEnfasi(precedente, pulito)) {
      precedente.testo += pulito.testo;
    } else {
      uniti.push(pulito);
    }
  }
  return uniti;
}

export function testoDiFrammenti(frammenti: FrammentoTesto[]): string {
  return frammenti.map((frammento) => frammento.testo).join('');
}

/**
 * I segnaposto `{{campo}}` usati, cercati **dentro ciascun frammento**.
 *
 * Un segnaposto spezzato da un cambio di enfasi (`{{ti` grassetto, `tolo}}`
 * normale) non e' un segnaposto: il servizio sostituisce per frammento e lo
 * lascerebbe come testo. Dichiararlo usato farebbe credere il contrario.
 */
export function placeholderNeiFrammenti(frammenti: FrammentoTesto[]): string[] {
  const trovati: string[] = [];
  for (const frammento of frammenti) {
    for (const match of frammento.testo.matchAll(/{{\s*([A-Za-z0-9_.-]+)\s*}}/g)) {
      if (!trovati.includes(match[1])) trovati.push(match[1]);
    }
  }
  return trovati;
}

function compatta(frammento: FrammentoTesto): FrammentoTesto {
  const risultato: FrammentoTesto = { testo: frammento.testo };
  if (frammento.grassetto) risultato.grassetto = true;
  if (frammento.corsivo) risultato.corsivo = true;
  if (frammento.sottolineato) risultato.sottolineato = true;
  if (frammento.collegamento) risultato.collegamento = frammento.collegamento;
  return risultato;
}

function stessaEnfasi(a: FrammentoTesto, b: FrammentoTesto): boolean {
  return (
    !!a.grassetto === !!b.grassetto &&
    !!a.corsivo === !!b.corsivo &&
    !!a.sottolineato === !!b.sottolineato &&
    (a.collegamento ?? null) === (b.collegamento ?? null)
  );
}

// --- Lettura dell'HTML ------------------------------------------------------

const ELEMENTO = 1;
const TESTO = 3;

/** L'enfasi di un elemento: il tag la imposta, lo stile in linea la puo' annullare. */
function enfasiDiElemento(elemento: Element, ereditata: Enfasi): Enfasi {
  const enfasi = { ...ereditata };
  const tag = elemento.localName;
  if (tag === 'b' || tag === 'strong') enfasi.grassetto = true;
  if (tag === 'i' || tag === 'em') enfasi.corsivo = true;
  if (tag === 'u' || tag === 'ins') enfasi.sottolineato = true;
  if (tag === 'a') {
    const href = elemento.getAttribute('href') ?? '';
    enfasi.collegamento = collegamentoAmmesso(href) ? href : ereditata.collegamento;
  }
  // Google Docs avvolge tutto in `<b style="font-weight:normal">`: lo stile
  // deve poter dire "non grassetto" anche dentro un `<b>`.
  const stile = (elemento as HTMLElement).style;
  if (stile) {
    const peso = stile.fontWeight;
    if (peso === 'bold' || peso === 'bolder' || Number(peso) >= 600) enfasi.grassetto = true;
    if (peso === 'normal' || peso === 'lighter' || (Number(peso) > 0 && Number(peso) < 600)) {
      enfasi.grassetto = false;
    }
    if (stile.fontStyle === 'italic' || stile.fontStyle === 'oblique') enfasi.corsivo = true;
    if (stile.fontStyle === 'normal') enfasi.corsivo = false;
    const decorazione = `${stile.textDecoration} ${stile.textDecorationLine}`;
    if (decorazione.includes('underline')) enfasi.sottolineato = true;
    else if (/\bnone\b/.test(decorazione)) enfasi.sottolineato = false;
  }
  return enfasi;
}

function collegamentoAmmesso(href: string): boolean {
  try {
    return SCHEMI_COLLEGAMENTO.has(new URL(href).protocol);
  } catch {
    return false;
  }
}

// --- Incolla da elaboratore di testi (FR-017) --------------------------------

// Sottoalberi scartati per intero: non portano testo del documento, o portano
// cio' che questo incremento dichiara fuori scope (tabelle, immagini).
const SCARTATI = new Set([
  'head',
  'style',
  'script',
  'title',
  'meta',
  'link',
  'img',
  'svg',
  'table',
  'object',
  'iframe',
  'template',
]);
const BLOCCHI = new Set([
  'p',
  'div',
  'h1',
  'h2',
  'h3',
  'h4',
  'h5',
  'h6',
  'blockquote',
  'pre',
  'section',
  'article',
]);

// Un marcatore scritto come testo all'inizio del capoverso: `1.`, `1)`,
// `a)`, `a.`, o un simbolo di punto elenco. Se restasse nel testo si
// sommerebbe alla numerazione calcolata in resa: `1. 1. Sono indetti...`.
const MARCATORE_A_MANO = /^\s*(?:(\d{1,3})[.)]|([a-z])\)|([a-z])\.(?=\s)|([•·▪◦‣-]))[\s\u00a0]+/;

type ElementoGrezzo = {
  frammenti: FrammentoTesto[];
  livello: 0 | 1;
  marcatore: TipoMarcatore | null;
};
type Capoverso =
  { tipo: 'PARAGRAFO'; frammenti: FrammentoTesto[] } | { tipo: 'VOCE'; voce: ElementoGrezzo };

/**
 * Converte gli appunti in blocchi. Usa l'HTML quando c'e' (e' li' che sta
 * l'enfasi), il testo semplice altrimenti.
 *
 * Cio' che non e' enfasi, capoverso o elenco viene scartato, sempre allo
 * stesso modo: colori, font, dimensioni, rientri, immagini, tabelle.
 */
export function convertiAppunti(html: string | null | undefined, testo: string): BloccoIncollato[] {
  const capoversi =
    html && html.trim() ? capoversiDaHtml(html) : capoversiDaTesto(testo.replace(/\r\n?/g, '\n'));
  return raggruppa(capoversi.map(riconosciMarcatoreAMano));
}

/**
 * Il testo semplice in capoversi. Copiato da un PDF, il testo porta un a capo
 * a ogni riga **visiva** della pagina: trattarlo come un capoverso spezzava un
 * titolo di cinque righe in cinque blocchi (visto sul bando 367.501, 2026-10-02).
 * Le righe si uniscono quindi in un capoverso finche' una non chiude la frase
 * (`.` `;` `:` `!` `?`), o finche' non arriva una riga vuota o una voce di
 * elenco. Una parola spezzata a fine riga col trattino si ricuce.
 */
function capoversiDaTesto(testo: string): Capoverso[] {
  const capoversi: string[] = [];
  let corrente = '';
  const chiudi = (): void => {
    if (corrente) capoversi.push(corrente);
    corrente = '';
  };
  for (const grezza of testo.split('\n')) {
    const riga = grezza.replace(/\t/g, ' ').replace(/ {2,}/g, ' ').trim();
    if (!riga) {
      chiudi();
      continue;
    }
    if (MARCATORE_A_MANO.test(riga)) chiudi();
    // Un titolo tutto maiuscolo finisce dove comincia il testo normale, anche
    // senza punteggiatura: "... VARIE SEDI" e poi "VISTO il decreto ...".
    if (corrente && maiuscolo(corrente) && /[a-zà-ÿ]/.test(riga)) chiudi();
    if (!corrente) {
      corrente = riga;
    } else if (/[A-Za-zÀ-ÿ]-$/.test(corrente) && /^[a-zà-ÿ]/.test(riga)) {
      corrente = corrente.slice(0, -1) + riga;
    } else {
      corrente = `${corrente} ${riga}`;
    }
    if (/[.;:!?]["”»)]?$/.test(riga)) chiudi();
  }
  chiudi();
  return capoversi.map((riga) => ({ tipo: 'PARAGRAFO', frammenti: [{ testo: riga }] }));
}

function maiuscolo(testo: string): boolean {
  return /[A-ZÀ-Ý]/.test(testo) && testo === testo.toLocaleUpperCase('it');
}

function capoversiDaHtml(html: string): Capoverso[] {
  const documento = new DOMParser().parseFromString(html, 'text/html');
  const capoversi: Capoverso[] = [];
  let corrente: FrammentoTesto[] = [];
  let voce: ElementoGrezzo | null = null;

  const chiudi = (): void => {
    const frammenti = rifinisci(corrente);
    corrente = [];
    if (voce) {
      voce.frammenti = frammenti;
      if (frammenti.length) capoversi.push({ tipo: 'VOCE', voce });
      voce = null;
    } else if (frammenti.length) {
      capoversi.push({ tipo: 'PARAGRAFO', frammenti });
    }
  };

  const visita = (
    nodo: Node,
    enfasi: Enfasi,
    profonditaElenco: number,
    ordinato: TipoMarcatore | null,
  ): void => {
    if (nodo.nodeType === TESTO) {
      // Nell'HTML gli a capo del sorgente sono spazi, non a capo.
      const testo = (nodo.textContent ?? '').replace(/[\s\u00a0]+/g, ' ');
      if (testo) corrente.push({ testo, ...enfasi });
      return;
    }
    if (nodo.nodeType !== ELEMENTO) return;
    const elemento = nodo as HTMLElement;
    const tag = elemento.localName;
    if (SCARTATI.has(tag)) return;
    const stileGrezzo = elemento.getAttribute('style') ?? '';
    // Il marcatore che Word stesso genera per le sue liste: va via, la resa
    // ne calcola uno proprio.
    if (/mso-list\s*:\s*ignore/i.test(stileGrezzo)) return;
    if (tag === 'br') {
      corrente.push({ testo: '\n', ...enfasi });
      return;
    }
    const propria = enfasiDiElemento(elemento, enfasi);

    if (tag === 'ul' || tag === 'ol') {
      chiudi();
      const marcatore: TipoMarcatore =
        tag === 'ul'
          ? 'PUNTATO'
          : /^[a-z]$/i.test(elemento.getAttribute('type') ?? '')
            ? 'ALFABETICO'
            : 'NUMERICO';
      elemento.childNodes.forEach((figlio) =>
        visita(figlio, propria, profonditaElenco + 1, marcatore),
      );
      chiudi();
      return;
    }
    if (tag === 'li') {
      chiudi();
      voce = {
        frammenti: [],
        livello: profonditaElenco > 1 ? 1 : 0,
        marcatore: ordinato,
      };
      elemento.childNodes.forEach((figlio) => {
        // Una lista annidata dentro la voce chiude la voce prima di iniziare.
        visita(figlio, propria, profonditaElenco, ordinato);
      });
      chiudi();
      return;
    }
    const livelloWord = /mso-list\s*:[^;]*level(\d+)/i.exec(stileGrezzo);
    if (BLOCCHI.has(tag) && voce && !livelloWord) {
      // Google Docs scrive `<li><p>...</p></li>`: il capoverso dentro la voce
      // appartiene alla voce. Un secondo capoverso nella stessa voce e' un a capo.
      if (corrente.some((frammento) => frammento.testo.trim())) {
        corrente.push({ testo: '\n', ...enfasi });
      }
      elemento.childNodes.forEach((figlio) => visita(figlio, propria, profonditaElenco, ordinato));
      return;
    }
    if (BLOCCHI.has(tag)) {
      chiudi();
      if (livelloWord) {
        voce = {
          frammenti: [],
          livello: Number(livelloWord[1]) > 1 ? 1 : 0,
          marcatore: marcatoreWord(elemento),
        };
      }
      elemento.childNodes.forEach((figlio) => visita(figlio, propria, profonditaElenco, ordinato));
      chiudi();
      return;
    }
    elemento.childNodes.forEach((figlio) => visita(figlio, propria, profonditaElenco, ordinato));
  };

  visita(documento.body, NESSUNA_ENFASI, 0, null);
  chiudi();
  return capoversi;
}

/** Il tipo di marcatore di una voce di lista di Word, letto dal marcatore che sta per essere scartato. */
function marcatoreWord(elemento: HTMLElement): TipoMarcatore {
  const ignorato = [...elemento.querySelectorAll('[style]')].find((figlio) =>
    /mso-list\s*:\s*ignore/i.test(figlio.getAttribute('style') ?? ''),
  );
  const testo = (ignorato?.textContent ?? '').trim();
  if (/^\d/.test(testo)) return 'NUMERICO';
  if (/^[a-z][.)]/i.test(testo)) return 'ALFABETICO';
  return 'PUNTATO';
}

/** Spazi compressi, nessuno spazio ai bordi del capoverso, frammenti uniti. */
function rifinisci(frammenti: FrammentoTesto[]): FrammentoTesto[] {
  const uniti = normalizzaFrammenti(
    frammenti.map((frammento) => ({ ...frammento, testo: frammento.testo.replace(/ {2,}/g, ' ') })),
  );
  // Gli spazi attorno a un a capo e ai bordi vengono dal sorgente HTML, non dal testo.
  for (const frammento of uniti) frammento.testo = frammento.testo.replace(/ *\n */g, '\n');
  if (uniti.length) {
    uniti[0].testo = uniti[0].testo.replace(/^[\s]+/, '');
    const ultimo = uniti[uniti.length - 1];
    ultimo.testo = ultimo.testo.replace(/[\s]+$/, '');
  }
  return normalizzaFrammenti(uniti);
}

/**
 * Toglie il marcatore scritto a mano dall'inizio del capoverso. Un capoverso
 * che lo porta diventa una voce di elenco; una voce gia' riconosciuta come
 * tale lo perde comunque, perche' resterebbe doppio.
 */
function riconosciMarcatoreAMano(capoverso: Capoverso): Capoverso {
  const frammenti = capoverso.tipo === 'VOCE' ? capoverso.voce.frammenti : capoverso.frammenti;
  const primo = frammenti[0];
  const trovato = primo && MARCATORE_A_MANO.exec(primo.testo);
  if (!trovato) return capoverso;
  const resto = [{ ...primo, testo: primo.testo.slice(trovato[0].length) }, ...frammenti.slice(1)];
  const marcatore: TipoMarcatore = trovato[1]
    ? 'NUMERICO'
    : trovato[2] || trovato[3]
      ? 'ALFABETICO'
      : 'PUNTATO';
  if (capoverso.tipo === 'VOCE') {
    return {
      tipo: 'VOCE',
      voce: {
        ...capoverso.voce,
        marcatore: capoverso.voce.marcatore ?? marcatore,
        frammenti: normalizzaFrammenti(resto),
      },
    };
  }
  return {
    tipo: 'VOCE',
    voce: { livello: 0, marcatore, frammenti: normalizzaFrammenti(resto) },
  };
}

/**
 * Voci consecutive -> un solo `ELENCO`. Nei bandi una voce `a)` dopo una
 * voce `1.` e' un sottopunto: se il marcatore non porta gia' un livello
 * (come in `<ul>` annidate o in Word), lo si deduce cosi'.
 */
function raggruppa(capoversi: Capoverso[]): BloccoIncollato[] {
  const blocchi: BloccoIncollato[] = [];
  for (const capoverso of capoversi) {
    if (capoverso.tipo === 'PARAGRAFO') {
      blocchi.push({ tipo: 'PARAGRAFO', frammenti: capoverso.frammenti });
      continue;
    }
    const precedente = blocchi.at(-1);
    const elenco = precedente?.tipo === 'ELENCO' ? precedente : null;
    const voce = capoverso.voce;
    const marcatore = voce.marcatore ?? 'PUNTATO';
    let livello = voce.livello;
    if (livello === 0 && elenco && marcatore === 'ALFABETICO') {
      const radice = elenco.elementi.find((elemento) => elemento.livello === 0);
      if (radice && radice.marcatore === 'NUMERICO') livello = 1;
    }
    const elemento: ElementoElenco = { livello, marcatore, frammenti: voce.frammenti };
    if (elenco) elenco.elementi.push(elemento);
    else blocchi.push({ tipo: 'ELENCO', elementi: [elemento] });
  }
  return blocchi;
}

// --- Collegamenti (FR-014) -----------------------------------------------------

/**
 * L'indirizzo come lo scrive il gestore, nella forma che il formato accetta,
 * o `null` se non e' un collegamento ammesso. Come in Word: un indirizzo email
 * diventa `mailto:`, un `www.` diventa `https://`. Qualunque altro schema
 * (`javascript:`, `file:`...) e' rifiutato qui e di nuovo dal servizio.
 */
export function normalizzaIndirizzo(scritto: string): string | null {
  const indirizzo = scritto.trim();
  if (!indirizzo || /\s/.test(indirizzo)) return null;
  const candidato = /^[^@/:]+@[^@/:]+\.[a-z]{2,}$/i.test(indirizzo)
    ? `mailto:${indirizzo}`
    : /^www\./i.test(indirizzo)
      ? `https://${indirizzo}`
      : indirizzo;
  return collegamentoAmmesso(candidato) ? candidato : null;
}
