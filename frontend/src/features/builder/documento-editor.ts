/**
 * L'interno dell'editor di sezione su ProseMirror (spec 012, T073-T076).
 *
 * Una sezione e' un solo documento ProseMirror, cosi' che selezione, enfasi,
 * copia e incolla attraversino i capoversi come in Word: con un'area di
 * scrittura per blocco il browser non estende una selezione da un'area
 * all'altra (riscontro del 2026-10-02). Lo schema ricalca `GEMODO_DOCUMENT_V1`
 * e nient'altro: cio' che l'editor puo' contenere e' cio' che il formato
 * ammette, e la conversione da e verso i blocchi e' tutta qui.
 *
 * Le voci di un elenco sono nodi piatti (`voce`), non annidati: Invio, Tab e
 * Backspace restano operazioni su un capoverso. Le voci consecutive con lo
 * stesso `id` sono un blocco `ELENCO`.
 */
import {
  Fragment,
  Schema,
  Slice,
  type Mark,
  type MarkType,
  type Node as NodoPm,
} from 'prosemirror-model';
import {
  EditorState,
  Plugin,
  TextSelection,
  type Command,
  type Selection,
} from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import { baseKeymap, chainCommands, splitBlockAs, toggleMark } from 'prosemirror-commands';
import { keymap } from 'prosemirror-keymap';

import {
  gruppiDiRighe,
  normalizzaFrammenti,
  parolaSpezzata,
  placeholderNeiFrammenti,
  type BloccoIncollato,
  type ElementoElenco,
  type FrammentoTesto,
  type TipoMarcatore,
} from './frammenti';

export type Allineamento = 'SINISTRA' | 'CENTRO' | 'DESTRA' | 'GIUSTIFICATO';

/** Il blocco di `GEMODO_DOCUMENT_V1` come lo scambiano editor e servizio. */
export type BloccoDocumento = {
  id: string;
  tipo: string;
  frammenti: FrammentoTesto[];
  allineamento?: Allineamento | null;
  elementi?: ElementoElenco[];
  posizionamento: string;
  ordine: number;
  stile?: string | null;
  placeholder_usati: string[];
  regole_layout?: Record<string, string>;
  asset_ref?: string | null;
  colonne?: string[];
};

export type TipoBloccoInseribile = 'PARAGRAFO' | 'TITOLO' | 'ELENCO' | 'FIRMA';

/** Una voce del menu Stile: che cosa diventa il blocco col cursore. */
export type VoceStile = {
  valore: string;
  etichetta: string;
  tipo: TipoBloccoInseribile;
  stile?: 'H1' | 'H2';
  marcatore?: TipoMarcatore;
};

/**
 * Le voci del menu Stile. Fuori, per ora: `TABELLA` (fuori scope della spec),
 * `LOGO` (gli asset versionati non esistono ancora), `FOOTER` e
 * `INTESTAZIONE` (si ripetono su ogni pagina: sono la cornice, US3).
 */
export const STILI: VoceStile[] = [
  { valore: 'PARAGRAFO', etichetta: 'Paragrafo', tipo: 'PARAGRAFO' },
  { valore: 'TITOLO', etichetta: "Titolo d'articolo", tipo: 'TITOLO' },
  { valore: 'H1', etichetta: 'Titolo 1', tipo: 'PARAGRAFO', stile: 'H1' },
  { valore: 'H2', etichetta: 'Titolo 2', tipo: 'PARAGRAFO', stile: 'H2' },
  {
    valore: 'ELENCO_NUMERICO',
    etichetta: 'Elenco numerato',
    tipo: 'ELENCO',
    marcatore: 'NUMERICO',
  },
  {
    valore: 'ELENCO_ALFABETICO',
    etichetta: 'Elenco a lettere',
    tipo: 'ELENCO',
    marcatore: 'ALFABETICO',
  },
  { valore: 'ELENCO_PUNTATO', etichetta: 'Elenco puntato', tipo: 'ELENCO', marcatore: 'PUNTATO' },
  { valore: 'FIRMA', etichetta: 'Firma', tipo: 'FIRMA' },
];

// L'allineamento che il renderer deduce dal posizionamento quando il blocco
// non lo dichiara (`_ALLINEAMENTO` in `renderer.py`): l'editor mostra lo stesso.
const ALLINEAMENTO_DA_POSIZIONAMENTO: Record<string, Allineamento> = {
  TOP: 'CENTRO',
  BODY: 'SINISTRA',
  BOTTOM_LEFT: 'SINISTRA',
  BOTTOM_RIGHT: 'DESTRA',
  BOTTOM_CENTER: 'CENTRO',
  INLINE: 'SINISTRA',
  COLUMN_LEFT: 'SINISTRA',
  COLUMN_RIGHT: 'DESTRA',
};

export const ALLINEAMENTO_CSS: Record<Allineamento, string> = {
  SINISTRA: 'left',
  CENTRO: 'center',
  DESTRA: 'right',
  GIUSTIFICATO: 'justify',
};

export function allineamentoEffettivo(blocco: {
  allineamento?: Allineamento | null;
  posizionamento: string;
}): Allineamento {
  return blocco.allineamento ?? ALLINEAMENTO_DA_POSIZIONAMENTO[blocco.posizionamento] ?? 'SINISTRA';
}

/** Sotto un elenco numerato si va per lettere (`a)`), sotto uno puntato si resta puntati. */
export function sottoMarcatore(radice: TipoMarcatore): TipoMarcatore {
  return radice === 'NUMERICO' ? 'ALFABETICO' : 'PUNTATO';
}

export function formattaMarcatore(
  marcatore: TipoMarcatore,
  numero: number,
  livello: 0 | 1,
): string {
  if (marcatore === 'NUMERICO') return `${numero}.`;
  if (marcatore === 'ALFABETICO') return `${String.fromCharCode(96 + ((numero - 1) % 26) + 1)})`;
  // Gli stessi simboli della resa, che li disegna come cerchi (pieno, vuoto).
  return livello === 0 ? '●' : '○';
}

/**
 * I marcatori di ogni voce degli elenchi di una sequenza di blocchi. Il
 * contatore del primo livello prosegue fra elenchi e si azzera a ogni `TITOLO`
 * e a ogni blocco il cui `ordine` apre una sezione (`inizi`); quello del
 * secondo si azzera a ogni voce di primo livello. E' la regola di
 * `marcatori_elenchi` nel renderer: l'editor mostra cio' che il PDF scrive.
 */
export function numeraElenchi(
  blocchi: BloccoDocumento[],
  inizi: Set<number> = new Set(),
): Map<BloccoDocumento, string[]> {
  const marcatori = new Map<BloccoDocumento, string[]>();
  const contatore = new Contatore();
  for (const blocco of blocchi) {
    if (blocco.tipo === 'TITOLO' || inizi.has(blocco.ordine)) contatore.azzera();
    if (blocco.tipo !== 'ELENCO') continue;
    marcatori.set(
      blocco,
      (blocco.elementi ?? []).map((elemento) =>
        contatore.voce(elemento.livello, elemento.marcatore),
      ),
    );
  }
  return marcatori;
}

class Contatore {
  private primo = 0;
  private secondo = 0;

  azzera(): void {
    this.primo = 0;
    this.secondo = 0;
  }

  voce(livello: 0 | 1, marcatore: TipoMarcatore): string {
    // Un punto elenco non consuma numeri, come in Word.
    const conta = marcatore === 'PUNTATO' ? 0 : 1;
    if (livello === 0) {
      this.secondo = 0;
      this.primo += conta;
      return formattaMarcatore(marcatore, this.primo, 0);
    }
    this.secondo += conta;
    return formattaMarcatore(marcatore, this.secondo, 1);
  }
}

// --- Schema -----------------------------------------------------------------

const ETICHETTE_RISERVATO: Record<string, string> = {
  TABELLA: 'Tabella',
  LOGO: 'Logo',
  INTESTAZIONE: 'Intestazione',
  FOOTER: 'Piè di pagina',
  COLONNE: 'Colonne',
};

/** Gli attributi comuni dei blocchi di testo, letti e scritti come `data-*`. */
const ATTRIBUTI_TESTO = {
  id: { default: null },
  allineamento: { default: null },
  posizionamento: { default: 'BODY' },
  stile: { default: null },
  // Campi del formato che l'editor non tocca ma non deve perdere.
  extra: { default: null },
};

type AttributiTesto = {
  id: string | null;
  allineamento: Allineamento | null;
  posizionamento: string;
  stile: string | null;
  extra: Pick<BloccoDocumento, 'regole_layout' | 'asset_ref' | 'colonne'> | null;
};

function domTesto(
  nodo: NodoPm,
  tipo: string,
  classi: string[],
): [string, Record<string, string>, 0] {
  const attrs = nodo.attrs as AttributiTesto;
  const allineamento = allineamentoEffettivo(attrs);
  const dom: Record<string, string> = {
    class: ['editor-text', ...classi].join(' '),
    'data-block-type': tipo,
    style: `text-align: ${ALLINEAMENTO_CSS[allineamento]}`,
  };
  if (attrs.id) dom['data-block-id'] = attrs.id;
  if (attrs.allineamento) dom['data-allineamento'] = attrs.allineamento;
  if (attrs.posizionamento !== 'BODY') dom['data-posizionamento'] = attrs.posizionamento;
  if (attrs.stile) dom['data-stile'] = attrs.stile;
  return ['p', dom, 0];
}

function leggiAttributiTesto(elemento: HTMLElement): Partial<AttributiTesto> {
  return {
    id: elemento.getAttribute('data-block-id'),
    allineamento: (elemento.getAttribute('data-allineamento') as Allineamento | null) ?? null,
    posizionamento: elemento.getAttribute('data-posizionamento') ?? 'BODY',
    stile: elemento.getAttribute('data-stile'),
  };
}

export const schema = new Schema({
  nodes: {
    doc: { content: 'blocco+' },
    // Il primo del gruppo e' il blocco che nasce da Invio a fine titolo.
    paragrafo: {
      group: 'blocco',
      content: 'inline*',
      attrs: ATTRIBUTI_TESTO,
      parseDOM: [
        {
          tag: 'p[data-block-type="PARAGRAFO"]',
          priority: 60,
          getAttrs: (dom) => leggiAttributiTesto(dom as HTMLElement),
        },
        { tag: 'p' },
        { tag: 'h1', attrs: { stile: 'H1' } },
        { tag: 'h2', attrs: { stile: 'H2' } },
      ],
      toDOM: (nodo) =>
        domTesto(
          nodo,
          'PARAGRAFO',
          nodo.attrs['stile'] === 'H1'
            ? ['style-h1']
            : nodo.attrs['stile'] === 'H2'
              ? ['style-h2']
              : [],
        ),
    },
    titolo: {
      group: 'blocco',
      content: 'inline*',
      attrs: ATTRIBUTI_TESTO,
      defining: true,
      parseDOM: [
        {
          tag: 'p[data-block-type="TITOLO"]',
          priority: 70,
          getAttrs: (dom) => leggiAttributiTesto(dom as HTMLElement),
        },
      ],
      toDOM: (nodo) => domTesto(nodo, 'TITOLO', ['block-titolo']),
    },
    firma: {
      group: 'blocco',
      content: 'inline*',
      attrs: { ...ATTRIBUTI_TESTO, posizionamento: { default: 'BOTTOM_RIGHT' } },
      defining: true,
      parseDOM: [
        {
          tag: 'p[data-block-type="FIRMA"]',
          priority: 70,
          getAttrs: (dom) => leggiAttributiTesto(dom as HTMLElement),
        },
      ],
      toDOM: (nodo) => domTesto(nodo, 'FIRMA', ['block-firma']),
    },
    voce: {
      group: 'blocco',
      content: 'inline*',
      attrs: { ...ATTRIBUTI_TESTO, livello: { default: 0 }, marcatore: { default: 'NUMERICO' } },
      defining: true,
      parseDOM: [
        {
          tag: 'li[data-marcatore-tipo]',
          priority: 70,
          getAttrs: (dom) => {
            const elemento = dom as HTMLElement;
            return {
              ...leggiAttributiTesto(elemento),
              livello: elemento.getAttribute('data-livello') === '1' ? 1 : 0,
              marcatore: elemento.getAttribute('data-marcatore-tipo') ?? 'NUMERICO',
            };
          },
        },
      ],
      toDOM: (nodo) => {
        const [, dom] = domTesto(nodo, 'ELENCO', []);
        const livello = nodo.attrs['livello'] as number;
        return [
          'li',
          {
            ...dom,
            class: `editor-item${livello === 1 ? ' level-1' : ''}`,
            'data-livello': String(livello),
            'data-marcatore-tipo': nodo.attrs['marcatore'] as string,
          },
          0,
        ];
      },
    },
    interruzione: {
      group: 'blocco',
      atom: true,
      selectable: true,
      attrs: { id: { default: null } },
      parseDOM: [{ tag: 'div[data-block-type="INTERRUZIONE_PAGINA"]' }],
      toDOM: (nodo) => [
        'div',
        {
          class: 'page-break',
          'data-block-type': 'INTERRUZIONE_PAGINA',
          ...(nodo.attrs['id'] ? { 'data-block-id': nodo.attrs['id'] as string } : {}),
          contenteditable: 'false',
        },
        ['span', 'Interruzione di pagina'],
      ],
    },
    // Un blocco che l'editor non sa modificare (una tabella, un logo): resta
    // nel documento intatto, e si puo' solo spostare o eliminare.
    riservato: {
      group: 'blocco',
      atom: true,
      selectable: true,
      attrs: { blocco: { default: null } },
      toDOM: (nodo) => {
        const blocco = nodo.attrs['blocco'] as BloccoDocumento;
        return [
          'div',
          {
            class: 'reserved-block',
            'data-block-type': blocco.tipo,
            'data-block-id': blocco.id,
            contenteditable: 'false',
          },
          `${ETICHETTE_RISERVATO[blocco.tipo] ?? blocco.tipo}: non modificabile dall'editor`,
        ];
      },
    },
    text: { group: 'inline' },
    a_capo: {
      inline: true,
      group: 'inline',
      selectable: false,
      parseDOM: [{ tag: 'br' }],
      toDOM: () => ['br'],
    },
  },
  marks: {
    collegamento: {
      attrs: { href: {} },
      inclusive: false,
      parseDOM: [
        {
          tag: 'a[href]',
          getAttrs: (dom) => ({ href: (dom as HTMLElement).getAttribute('href') }),
        },
      ],
      toDOM: (mark) => ['a', { href: mark.attrs['href'] as string, rel: 'noopener' }, 0],
    },
    grassetto: {
      parseDOM: [{ tag: 'strong' }, { tag: 'b' }],
      toDOM: () => ['strong', 0],
    },
    corsivo: {
      parseDOM: [{ tag: 'em' }, { tag: 'i' }],
      toDOM: () => ['em', 0],
    },
    sottolineato: {
      parseDOM: [{ tag: 'u' }],
      toDOM: () => ['u', 0],
    },
  },
});

const N = schema.nodes;
const M = schema.marks;
export type AttributoEnfasi = 'grassetto' | 'corsivo' | 'sottolineato';

// --- Conversione ------------------------------------------------------------

function inlineDaFrammenti(frammenti: FrammentoTesto[]): NodoPm[] {
  const nodi: NodoPm[] = [];
  for (const frammento of frammenti) {
    const marchi: Mark[] = [];
    if (frammento.collegamento)
      marchi.push(M['collegamento'].create({ href: frammento.collegamento }));
    if (frammento.grassetto) marchi.push(M['grassetto'].create());
    if (frammento.corsivo) marchi.push(M['corsivo'].create());
    if (frammento.sottolineato) marchi.push(M['sottolineato'].create());
    frammento.testo.split('\n').forEach((riga, indice) => {
      if (indice > 0) nodi.push(N['a_capo'].create(null, null, marchi));
      if (riga) nodi.push(schema.text(riga, marchi));
    });
  }
  return nodi;
}

function frammentiDaInline(nodo: NodoPm): FrammentoTesto[] {
  const frammenti: FrammentoTesto[] = [];
  nodo.forEach((figlio) => {
    const frammento: FrammentoTesto = {
      testo: figlio.isText ? (figlio.text ?? '') : '\n',
    };
    for (const marchio of figlio.marks) {
      if (marchio.type === M['collegamento'])
        frammento.collegamento = marchio.attrs['href'] as string;
      else frammento[marchio.type.name as AttributoEnfasi] = true;
    }
    frammenti.push(frammento);
  });
  return normalizzaFrammenti(frammenti);
}

function attributiDa(blocco: BloccoDocumento): AttributiTesto {
  const conExtra =
    Object.keys(blocco.regole_layout ?? {}).length ||
    !!blocco.asset_ref ||
    !!blocco.colonne?.length;
  const extra = conExtra
    ? { regole_layout: blocco.regole_layout, asset_ref: blocco.asset_ref, colonne: blocco.colonne }
    : null;
  return {
    id: blocco.id,
    allineamento: blocco.allineamento ?? null,
    posizionamento: blocco.posizionamento,
    stile: blocco.stile ?? null,
    extra,
  };
}

/** I blocchi di una sezione come documento ProseMirror; una sezione vuota ha una riga vuota. */
export function documentoDaBlocchi(blocchi: BloccoDocumento[]): NodoPm {
  const nodi: NodoPm[] = [];
  for (const blocco of [...blocchi].sort((a, b) => a.ordine - b.ordine)) {
    const attrs = attributiDa(blocco);
    switch (blocco.tipo) {
      case 'PARAGRAFO':
        nodi.push(N['paragrafo'].create(attrs, inlineDaFrammenti(blocco.frammenti)));
        break;
      case 'TITOLO':
        nodi.push(N['titolo'].create(attrs, inlineDaFrammenti(blocco.frammenti)));
        break;
      case 'FIRMA':
        nodi.push(N['firma'].create(attrs, inlineDaFrammenti(blocco.frammenti)));
        break;
      case 'ELENCO':
        for (const elemento of blocco.elementi ?? []) {
          nodi.push(
            N['voce'].create(
              { ...attrs, livello: elemento.livello, marcatore: elemento.marcatore },
              inlineDaFrammenti(elemento.frammenti),
            ),
          );
        }
        break;
      case 'INTERRUZIONE_PAGINA':
        nodi.push(N['interruzione'].create({ id: blocco.id }));
        break;
      default:
        nodi.push(N['riservato'].create({ blocco: structuredClone(blocco) }));
    }
  }
  if (!nodi.length) nodi.push(N['paragrafo'].create());
  return N['doc'].create(null, nodi);
}

const TIPO_DI_NODO: Record<string, string> = {
  paragrafo: 'PARAGRAFO',
  titolo: 'TITOLO',
  firma: 'FIRMA',
};

/**
 * Il documento ProseMirror come blocchi del formato. `ordine` e
 * `placeholder_usati` si ricalcolano qui, cosi' che non possano divergere dal
 * testo; le voci consecutive con lo stesso `id` sono un elenco.
 */
export function blocchiDaDocumento(documento: NodoPm, prefisso = 'b'): BloccoDocumento[] {
  const blocchi: BloccoDocumento[] = [];
  const generatore = new GeneratoreId(prefisso, idPresenti(documento));
  let elenco: BloccoDocumento | null = null;
  documento.forEach((nodo) => {
    const attrs = nodo.attrs as AttributiTesto & { livello: 0 | 1; marcatore: TipoMarcatore };
    if (nodo.type === N['voce']) {
      const id = attrs.id ?? generatore.nuovo();
      if (!elenco || elenco.id !== id) {
        elenco = {
          ...baseBlocco(id, 'ELENCO', attrs),
          elementi: [],
        };
        blocchi.push(elenco);
      }
      elenco.elementi!.push({
        livello: attrs.livello === 1 ? 1 : 0,
        marcatore: attrs.marcatore,
        frammenti: frammentiDaInline(nodo),
      });
      return;
    }
    elenco = null;
    if (nodo.type === N['interruzione']) {
      blocchi.push({
        ...baseBlocco(
          (nodo.attrs['id'] as string | null) ?? generatore.nuovo(),
          'INTERRUZIONE_PAGINA',
          {
            allineamento: null,
            posizionamento: 'BODY',
            stile: null,
            extra: null,
          },
        ),
      });
      return;
    }
    if (nodo.type === N['riservato']) {
      blocchi.push(structuredClone(nodo.attrs['blocco'] as BloccoDocumento));
      return;
    }
    blocchi.push({
      ...baseBlocco(attrs.id ?? generatore.nuovo(), TIPO_DI_NODO[nodo.type.name], attrs),
      frammenti: frammentiDaInline(nodo),
    });
  });
  return blocchi.map((blocco, ordine) => ({
    ...blocco,
    ordine,
    placeholder_usati: placeholderNeiFrammenti([
      ...blocco.frammenti,
      ...(blocco.elementi ?? []).flatMap((elemento) => elemento.frammenti),
    ]),
  }));
}

function baseBlocco(id: string, tipo: string, attrs: Omit<AttributiTesto, 'id'>): BloccoDocumento {
  return {
    id,
    tipo,
    frammenti: [],
    allineamento: attrs.allineamento ?? null,
    elementi: [],
    posizionamento: attrs.posizionamento,
    ordine: 0,
    stile: tipo === 'PARAGRAFO' ? (attrs.stile ?? null) : null,
    placeholder_usati: [],
    regole_layout: attrs.extra?.regole_layout ?? {},
    asset_ref: attrs.extra?.asset_ref ?? null,
    colonne: attrs.extra?.colonne ?? [],
  };
}

/**
 * Una forma confrontabile dei blocchi: cio' che conta per il documento, con
 * gli attributi falsi omessi e le chiavi in ordine fisso. Serve a capire se i
 * blocchi arrivati da fuori sono gia' quelli nell'editor.
 */
export function impronta(blocchi: BloccoDocumento[]): string {
  return JSON.stringify(
    [...blocchi]
      .sort((a, b) => a.ordine - b.ordine)
      .map((blocco) => [
        blocco.id,
        blocco.tipo,
        blocco.allineamento ?? null,
        blocco.posizionamento,
        blocco.stile ?? null,
        normalizzaFrammenti(blocco.frammenti ?? []),
        (blocco.elementi ?? []).map((elemento) => [
          elemento.livello,
          elemento.marcatore,
          normalizzaFrammenti(elemento.frammenti),
        ]),
      ]),
  );
}

function idPresenti(documento: NodoPm): Set<string> {
  const id = new Set<string>();
  documento.forEach((nodo) => {
    const valore = (nodo.attrs['id'] ?? (nodo.attrs['blocco'] as BloccoDocumento | null)?.id) as
      string | null | undefined;
    if (valore) id.add(valore);
  });
  return id;
}

class GeneratoreId {
  private progressivo: number;

  constructor(
    private readonly prefisso: string,
    private readonly usati: Set<string>,
  ) {
    this.progressivo = usati.size + 1;
  }

  nuovo(): string {
    while (this.usati.has(`${this.prefisso}-b${this.progressivo}`)) this.progressivo += 1;
    const id = `${this.prefisso}-b${this.progressivo}`;
    this.usati.add(id);
    return id;
  }
}

/**
 * Ogni blocco ha un `id` suo, unico nella sezione, come vuole il formato.
 * Dividere un capoverso, incollarne una copia o staccare un elenco in due
 * duplicherebbe l'id: qui chi arriva dopo ne riceve uno nuovo. Le voci
 * consecutive con lo stesso id restano un elenco solo e cambiano nome insieme.
 */
function pluginId(prefisso: () => string): Plugin {
  return new Plugin({
    appendTransaction: (transazioni, _prima, stato) => {
      if (!transazioni.some((tr) => tr.docChanged)) return null;
      const generatore = new GeneratoreId(prefisso(), idPresenti(stato.doc));
      const visti = new Set<string>();
      const tr = stato.tr;
      // L'elenco in corso: l'id che le sue voci avevano, e quello che hanno ora.
      let elenco: { originale: string | null; assegnato: string } | null = null;
      stato.doc.forEach((nodo, pos) => {
        if (nodo.type === N['riservato']) {
          visti.add((nodo.attrs['blocco'] as BloccoDocumento).id);
          elenco = null;
          return;
        }
        const id = nodo.attrs['id'] as string | null;
        const voce = nodo.type === N['voce'];
        if (voce && elenco && elenco.originale === id) {
          if (id !== elenco.assegnato) {
            tr.setNodeMarkup(pos, undefined, { ...nodo.attrs, id: elenco.assegnato });
          }
          return;
        }
        let assegnato = id;
        if (!assegnato || visti.has(assegnato)) {
          assegnato = generatore.nuovo();
          tr.setNodeMarkup(pos, undefined, { ...nodo.attrs, id: assegnato });
        }
        visti.add(assegnato);
        elenco = voce ? { originale: id, assegnato } : null;
      });
      return tr.docChanged ? tr : null;
    },
  });
}

/** I marcatori delle voci, calcolati e mai scritti nel testo (FR-015). */
const pluginMarcatori = new Plugin({
  props: {
    decorations: (stato) => {
      const decorazioni: Decoration[] = [];
      const contatore = new Contatore();
      stato.doc.forEach((nodo, pos) => {
        if (nodo.type === N['titolo']) contatore.azzera();
        if (nodo.type !== N['voce']) return;
        const marcatore = contatore.voce(
          nodo.attrs['livello'] as 0 | 1,
          nodo.attrs['marcatore'] as TipoMarcatore,
        );
        decorazioni.push(
          Decoration.node(pos, pos + nodo.nodeSize, { 'data-marcatore': marcatore }),
        );
      });
      return DecorationSet.create(stato.doc, decorazioni);
    },
  },
});

// --- Comandi ----------------------------------------------------------------

/**
 * I blocchi di primo livello toccati dalla selezione, con la loro posizione.
 * Una selezione che finisce all'inizio di un capoverso non lo tocca, come in
 * Word con il triplo clic.
 */
function blocchiSelezionati(stato: EditorState): { nodo: NodoPm; pos: number }[] {
  const { from, to, empty, $to } = stato.selection;
  const fine = empty
    ? from + 1
    : $to.depth === 1 && $to.parentOffset === 0 && to > from
      ? to - 1
      : to;
  const trovati: { nodo: NodoPm; pos: number }[] = [];
  stato.doc.forEach((nodo, pos) => {
    if (pos < Math.max(fine, from + 1) && pos + nodo.nodeSize > from) trovati.push({ nodo, pos });
  });
  if (!trovati.length)
    trovati.push({
      nodo: stato.doc.lastChild!,
      pos: stato.doc.content.size - stato.doc.lastChild!.nodeSize,
    });
  return trovati;
}

/** Con il solo cursore in una voce, tutte le voci del suo elenco. */
function elencoIntero(
  stato: EditorState,
  blocchi: { nodo: NodoPm; pos: number }[],
): { nodo: NodoPm; pos: number }[] {
  if (!stato.selection.empty || blocchi.length !== 1 || blocchi[0].nodo.type !== N['voce']) {
    return blocchi;
  }
  const id = blocchi[0].nodo.attrs['id'] as string | null;
  const tutti: { nodo: NodoPm; pos: number }[] = [];
  stato.doc.forEach((nodo, pos) => tutti.push({ nodo, pos }));
  let inizio = tutti.findIndex((voce) => voce.pos === blocchi[0].pos);
  let fine = inizio;
  const stesso = (i: number) =>
    tutti[i]?.nodo.type === N['voce'] && tutti[i].nodo.attrs['id'] === id;
  while (stesso(inizio - 1)) inizio -= 1;
  while (stesso(fine + 1)) fine += 1;
  return tutti.slice(inizio, fine + 1);
}

/** Il blocco col cursore (l'inizio della selezione). */
export function bloccoCorrente(stato: EditorState): NodoPm {
  return blocchiSelezionati(stato)[0].nodo;
}

const TESTUALI = new Set(['paragrafo', 'titolo', 'firma', 'voce']);

function testuale(nodo: NodoPm): boolean {
  return TESTUALI.has(nodo.type.name);
}

/** La voce del menu Stile che descrive il blocco; vuota se non e' testo. */
export function stileDelNodo(nodo: NodoPm): string {
  switch (nodo.type.name) {
    case 'voce':
      return `ELENCO_${radiceDi(nodo)}`;
    case 'paragrafo':
      return (nodo.attrs['stile'] as string | null) ?? 'PARAGRAFO';
    case 'titolo':
      return 'TITOLO';
    case 'firma':
      return 'FIRMA';
    default:
      return '';
  }
}

function radiceDi(voce: NodoPm): TipoMarcatore {
  const marcatore = voce.attrs['marcatore'] as TipoMarcatore;
  if (voce.attrs['livello'] === 0) return marcatore;
  return marcatore === 'ALFABETICO' ? 'NUMERICO' : marcatore;
}

/** Cio' che la toolbar mostra per la selezione corrente. */
export type StatoSelezione = {
  stile: string;
  allineamento: Allineamento | null;
  marchi: Record<AttributoEnfasi, boolean>;
};

export function statoSelezione(stato: EditorState): StatoSelezione {
  const nodo = bloccoCorrente(stato);
  const marchi = (tipo: MarkType): boolean => {
    const { from, to, empty } = stato.selection;
    if (empty) return !!tipo.isInSet(stato.storedMarks ?? stato.selection.$from.marks());
    return stato.doc.rangeHasMark(from, to, tipo);
  };
  return {
    stile: stileDelNodo(nodo),
    allineamento: testuale(nodo) ? allineamentoEffettivo(nodo.attrs as AttributiTesto) : null,
    marchi: {
      grassetto: marchi(M['grassetto']),
      corsivo: marchi(M['corsivo']),
      sottolineato: marchi(M['sottolineato']),
    },
  };
}

export function comandoEnfasi(attributo: AttributoEnfasi): Command {
  // Come in Word: se una parte della selezione non ha l'enfasi, la riceve
  // tutta; la si toglie solo quando ce l'ha gia' tutta.
  return toggleMark(M[attributo], null, { removeWhenPresent: false });
}

/**
 * Il menu Stile su ogni blocco di testo della selezione (T059, T076): cambia
 * cio' che il blocco e', tenendone il testo e l'enfasi.
 */
export function comandoStile(voce: VoceStile): Command {
  return (stato, dispatch) => {
    const blocchi = blocchiSelezionati(stato).filter(({ nodo }) => testuale(nodo));
    if (!blocchi.length) return false;
    if (voce.marcatore) return comandoElenco(voce.marcatore, true)(stato, dispatch);
    if (dispatch) {
      const tr = stato.tr;
      for (const { nodo, pos } of blocchi) {
        const attrs = nodo.attrs as AttributiTesto;
        const base = { id: attrs.id, extra: attrs.extra };
        switch (voce.tipo) {
          case 'TITOLO':
            tr.setNodeMarkup(pos, N['titolo'], {
              ...base,
              allineamento: nodo.type === N['titolo'] ? attrs.allineamento : 'CENTRO',
              posizionamento: 'BODY',
            });
            break;
          case 'FIRMA':
            tr.setNodeMarkup(pos, N['firma'], {
              ...base,
              allineamento: null,
              posizionamento: 'BOTTOM_RIGHT',
            });
            break;
          default:
            tr.setNodeMarkup(pos, N['paragrafo'], {
              ...base,
              allineamento:
                nodo.type === N['titolo'] || nodo.type === N['firma'] ? null : attrs.allineamento,
              posizionamento: 'BODY',
              stile: voce.stile ?? null,
            });
        }
      }
      dispatch(tr.scrollIntoView());
    }
    return true;
  };
}

/**
 * I pulsanti `1.`, `•`, `a)`. Se i blocchi sono gia' tutti voci con quel
 * marcatore, tornano capoversi (come in Word); altrimenti diventano voci,
 * agganciate all'elenco che li precede se c'e'. `forza` e' il menu Stile, che
 * non toglie mai l'elenco.
 */
export function comandoElenco(marcatore: TipoMarcatore, forza = false): Command {
  return (stato, dispatch) => {
    const selezionati = blocchiSelezionati(stato).filter(({ nodo }) => testuale(nodo));
    if (!selezionati.length) return false;
    const giaElenco = selezionati.every(
      ({ nodo }) => nodo.type === N['voce'] && radiceDi(nodo) === marcatore,
    );
    if (!dispatch) return true;
    const tr = stato.tr;
    if (giaElenco && !forza) {
      for (const { nodo, pos } of selezionati) {
        tr.setNodeMarkup(pos, N['paragrafo'], {
          id: null,
          allineamento: nodo.attrs['allineamento'] as string | null,
          posizionamento: 'BODY',
          stile: null,
          extra: nodo.attrs['extra'],
        });
      }
      dispatch(tr.scrollIntoView());
      return true;
    }
    // Un marcatore nuovo vale per tutto l'elenco col cursore, come in Word.
    const blocchi = elencoIntero(stato, selezionati);
    const primo = blocchi[0];
    const $primo = stato.doc.resolve(primo.pos);
    const precedente = $primo.index(0) > 0 ? stato.doc.child($primo.index(0) - 1) : null;
    const id =
      primo.nodo.type === N['voce']
        ? (primo.nodo.attrs['id'] as string)
        : precedente?.type === N['voce']
          ? (precedente.attrs['id'] as string)
          : (primo.nodo.attrs['id'] as string | null);
    for (const { nodo, pos } of blocchi) {
      const livello = nodo.type === N['voce'] ? (nodo.attrs['livello'] as 0 | 1) : 0;
      tr.setNodeMarkup(pos, N['voce'], {
        id,
        allineamento:
          nodo.type === N['titolo'] ? null : (nodo.attrs['allineamento'] as string | null),
        posizionamento: 'BODY',
        stile: null,
        extra: nodo.attrs['extra'],
        livello,
        marcatore: livello === 0 ? marcatore : sottoMarcatore(marcatore),
      });
    }
    dispatch(tr.scrollIntoView());
    return true;
  };
}

/** Tab e Maiusc+Tab sulle voci della selezione; `null` alterna. */
export function comandoLivello(livello: 0 | 1 | null): Command {
  return (stato, dispatch) => {
    const voci = blocchiSelezionati(stato).filter(({ nodo }) => nodo.type === N['voce']);
    if (!voci.length) return false;
    if (dispatch) {
      const tr = stato.tr;
      for (const { nodo, pos } of voci) {
        const nuovo = livello ?? (nodo.attrs['livello'] === 1 ? 0 : 1);
        // La prima voce di un elenco non puo' stare al secondo livello: non
        // avrebbe una voce sopra a cui appartenere.
        const $pos = stato.doc.resolve(pos);
        const sopra = $pos.index(0) > 0 ? stato.doc.child($pos.index(0) - 1) : null;
        if (nuovo === 1 && sopra?.type !== N['voce']) continue;
        const radice = radiceDi(nodo);
        tr.setNodeMarkup(pos, undefined, {
          ...nodo.attrs,
          livello: nuovo,
          marcatore: nuovo === 1 ? sottoMarcatore(radice) : radice,
        });
      }
      dispatch(tr);
    }
    return true;
  };
}

export function comandoAllineamento(allineamento: Allineamento): Command {
  return (stato, dispatch) => {
    const blocchi = blocchiSelezionati(stato).filter(({ nodo }) => testuale(nodo));
    if (!blocchi.length) return false;
    if (dispatch) {
      const tr = stato.tr;
      for (const { nodo, pos } of blocchi) {
        tr.setNodeMarkup(pos, undefined, { ...nodo.attrs, allineamento });
      }
      dispatch(tr);
    }
    return true;
  };
}

/**
 * Un'interruzione di pagina al cursore, come in Word (FR-012, T060): su una
 * riga vuota va prima della riga, che resta pronta sulla pagina nuova;
 * altrimenti va dopo il blocco, seguita da una riga vuota col cursore.
 */
export const comandoInterruzione: Command = (stato, dispatch) => {
  const { nodo, pos } = blocchiSelezionati(stato).at(-1)!;
  if (dispatch) {
    const tr = stato.tr;
    const interruzione = N['interruzione'].create();
    if (testuale(nodo) && nodo.content.size === 0) {
      tr.insert(pos, interruzione);
      tr.setSelection(TextSelection.create(tr.doc, pos + interruzione.nodeSize + 1));
    } else {
      const dopo = pos + nodo.nodeSize;
      tr.insert(dopo, [interruzione, N['paragrafo'].create()]);
      tr.setSelection(TextSelection.create(tr.doc, dopo + interruzione.nodeSize + 1));
    }
    dispatch(tr.scrollIntoView());
  }
  return true;
};

/**
 * Ricompone in capoversi le righe selezionate di un testo spezzato dalla
 * pagina: un visto che occupa tre righe torna un capoverso solo, e il
 * giustificato lo allarga per intero (riscontro del 2026-10-02). La regola e'
 * quella dell'incolla da PDF (`gruppiDiRighe`); l'enfasi resta dov'era. Una
 * voce d'elenco apre sempre un capoverso: le righe che la seguono sono il suo
 * seguito.
 */
export const comandoUnisciRighe: Command = (stato, dispatch) => {
  if (stato.selection.empty) return false;
  const blocchi = blocchiSelezionati(stato).filter(({ nodo }) => testuale(nodo));
  const inizi = new Set(
    blocchi.flatMap(({ nodo }, i) => (i > 0 && nodo.type === N['voce'] ? [i] : [])),
  );
  const gruppi = gruppiDiRighe(
    blocchi.map(({ nodo }) => nodo.textContent),
    inizi,
  ).filter((gruppo) => gruppo.length > 1);
  if (!gruppi.length) return false;
  if (dispatch) {
    const tr = stato.tr;
    // Dall'ultima giuntura alla prima: le posizioni prima restano valide.
    for (const gruppo of [...gruppi].reverse()) {
      for (let k = gruppo.length - 1; k > 0; k -= 1) {
        const prima = blocchi[gruppo[k - 1]].nodo;
        const dopo = blocchi[gruppo[k]].nodo;
        const confine = blocchi[gruppo[k]].pos;
        if (parolaSpezzata(prima.textContent, dopo.textContent)) {
          tr.delete(confine - 2, confine - 1);
          tr.join(confine - 1);
        } else {
          tr.insertText(' ', confine - 1);
          tr.join(confine + 1);
        }
      }
    }
    dispatch(tr.scrollIntoView());
  }
  return true;
};

/** Il testo dato al posto della selezione, con l'enfasi di cio' che lo precede (FR-005). */
export function comandoTesto(testo: string, da?: number, a?: number): Command {
  return (stato, dispatch) => {
    if (dispatch) {
      const inizio = da ?? stato.selection.from;
      const fine = a ?? stato.selection.to;
      const marchi =
        da === undefined && stato.storedMarks
          ? stato.storedMarks
          : stato.doc
              .resolve(inizio)
              .marks()
              .filter((marchio) => marchio.type !== M['collegamento']);
      const tr = stato.tr.replaceWith(inizio, fine, schema.text(testo, marchi));
      tr.setSelection(TextSelection.create(tr.doc, inizio + testo.length));
      dispatch(tr.scrollIntoView());
    }
    return true;
  };
}

/** Il collegamento sulla porzione `[da, a)`; `null` lo toglie. */
export function comandoCollegamento(da: number, a: number, href: string | null): Command {
  return (stato, dispatch) => {
    if (a <= da) return false;
    if (dispatch) {
      const tr = stato.tr.removeMark(da, a, M['collegamento']);
      if (href) tr.addMark(da, a, M['collegamento'].create({ href }));
      tr.setSelection(TextSelection.create(tr.doc, da, a));
      dispatch(tr);
    }
    return true;
  };
}

/** L'indirizzo di un collegamento gia' presente nella porzione, se c'e'. */
export function collegamentoIn(stato: EditorState, da: number, a: number): string | null {
  let trovato: string | null = null;
  stato.doc.nodesBetween(da, a, (nodo) => {
    const marchio = M['collegamento'].isInSet(nodo.marks);
    if (marchio && !trovato) trovato = marchio.attrs['href'] as string;
  });
  return trovato;
}

/** Il cursore in una voce, all'inizio del suo testo. */
function voceAlCursore(stato: EditorState): { nodo: NodoPm; pos: number } | null {
  const { $from, empty } = stato.selection;
  if (!empty || $from.depth !== 1) return null;
  const nodo = $from.parent;
  return nodo.type === N['voce'] ? { nodo, pos: $from.before(1) } : null;
}

/**
 * Invio su una voce vuota: al secondo livello risale al primo, al primo esce
 * dall'elenco e diventa un capoverso, come in Word.
 */
const invioSuVoceVuota: Command = (stato, dispatch) => {
  const voce = voceAlCursore(stato);
  if (!voce || voce.nodo.content.size > 0) return false;
  return esciDaVoce(voce)(stato, dispatch);
};

/** Backspace all'inizio di una voce: toglie il marcatore, non unisce il testo. */
const backspaceInizioVoce: Command = (stato, dispatch) => {
  const voce = voceAlCursore(stato);
  if (!voce || stato.selection.$from.parentOffset > 0) return false;
  return esciDaVoce(voce)(stato, dispatch);
};

function esciDaVoce(voce: { nodo: NodoPm; pos: number }): Command {
  return (stato, dispatch) => {
    if (dispatch) {
      const attrs = voce.nodo.attrs;
      if (attrs['livello'] === 1) {
        const radice = radiceDi(voce.nodo);
        dispatch(
          stato.tr.setNodeMarkup(voce.pos, undefined, { ...attrs, livello: 0, marcatore: radice }),
        );
      } else {
        dispatch(
          stato.tr.setNodeMarkup(voce.pos, N['paragrafo'], {
            id: null,
            allineamento: attrs['allineamento'] as string | null,
            posizionamento: 'BODY',
            stile: null,
            extra: attrs['extra'],
          }),
        );
      }
    }
    return true;
  };
}

/** Maiusc+Invio: a capo dentro lo stesso capoverso. */
const aCapo: Command = (stato, dispatch) => {
  if (dispatch) {
    const marchi = stato.storedMarks ?? stato.selection.$from.marks();
    dispatch(
      stato.tr.replaceSelectionWith(N['a_capo'].create(null, null, marchi)).scrollIntoView(),
    );
  }
  return true;
};

/** Invio in una voce: la voce si divide, e la parte dopo e' una voce uguale. */
const dividiVoce: Command = (stato, dispatch) => {
  const { $from } = stato.selection;
  if ($from.depth !== 1 || $from.parent.type !== N['voce']) return false;
  if (dispatch) {
    const tr = stato.tr;
    if (!stato.selection.empty) tr.deleteSelection();
    tr.split(tr.selection.from, 1, [{ type: N['voce'], attrs: $from.parent.attrs }]);
    dispatch(tr.scrollIntoView());
  }
  return true;
};

/**
 * Invio in un capoverso: a fine riga il capoverso nuovo ne tiene
 * l'allineamento ma non lo stile di titolo; dopo un titolo d'articolo o una
 * firma si torna a scrivere corpo del testo.
 */
const dividiCapoverso = splitBlockAs((nodo, allaFine) =>
  nodo.type === N['paragrafo']
    ? {
        type: N['paragrafo'],
        attrs: { ...nodo.attrs, id: null, stile: allaFine ? null : nodo.attrs['stile'] },
      }
    : null,
);

/** La cronologia e' del builder intero, non della singola sezione. */
export type Cronologia = { annulla: () => void; ripeti: () => void };

export function tastiera(cronologia: Cronologia): Plugin[] {
  const annulla: Command = () => {
    cronologia.annulla();
    return true;
  };
  const ripeti: Command = () => {
    cronologia.ripeti();
    return true;
  };
  return [
    keymap({
      'Mod-z': annulla,
      'Mod-Shift-z': ripeti,
      'Mod-y': ripeti,
      'Mod-b': comandoEnfasi('grassetto'),
      'Mod-i': comandoEnfasi('corsivo'),
      'Mod-u': comandoEnfasi('sottolineato'),
      // Anche Ctrl su Mac, come il vecchio editor: chi arriva da Windows lo usa.
      'Ctrl-z': annulla,
      'Ctrl-Shift-z': ripeti,
      'Ctrl-y': ripeti,
      'Ctrl-b': comandoEnfasi('grassetto'),
      'Ctrl-i': comandoEnfasi('corsivo'),
      'Ctrl-u': comandoEnfasi('sottolineato'),
      Enter: chainCommands(invioSuVoceVuota, dividiVoce, dividiCapoverso),
      'Shift-Enter': aCapo,
      Backspace: backspaceInizioVoce,
      // Tab non deve mai portare il fuoco fuori dal testo.
      Tab: (stato, dispatch) => {
        comandoLivello(1)(stato, dispatch);
        return true;
      },
      'Shift-Tab': (stato, dispatch) => {
        comandoLivello(0)(stato, dispatch);
        return true;
      },
    }),
    keymap(baseKeymap),
  ];
}

// --- Incolla ----------------------------------------------------------------

/**
 * Cio' che `convertiAppunti` ha riconosciuto, come porzione da incollare. La
 * porzione e' aperta ai due capi: il primo capoverso continua quello col
 * cursore e l'ultimo si salda al testo che segue, come in Word.
 */
export function porzioneDaIncollare(incollati: BloccoIncollato[]): Slice {
  const nodi: NodoPm[] = [];
  for (const incollato of incollati) {
    if (incollato.tipo === 'ELENCO') {
      for (const elemento of incollato.elementi) {
        nodi.push(
          N['voce'].create(
            { livello: elemento.livello, marcatore: elemento.marcatore },
            inlineDaFrammenti(elemento.frammenti),
          ),
        );
      }
    } else {
      nodi.push(N['paragrafo'].create(null, inlineDaFrammenti(incollato.frammenti)));
    }
  }
  return new Slice(Fragment.from(nodi), 1, 1);
}

// --- Stato ------------------------------------------------------------------

export function creaStato(
  blocchi: BloccoDocumento[],
  prefisso: () => string,
  cronologia: Cronologia,
  altri: Plugin[] = [],
): EditorState {
  return EditorState.create({
    doc: documentoDaBlocchi(blocchi),
    plugins: [...altri, ...tastiera(cronologia), pluginId(prefisso), pluginMarcatori],
  });
}

/** La selezione rimessa su un documento, dentro i suoi limiti. */
export function selezioneSicura(documento: NodoPm, da: number, a: number): Selection {
  const massimo = documento.content.size;
  const inizio = Math.max(0, Math.min(da, massimo));
  const fine = Math.max(0, Math.min(a, massimo));
  return TextSelection.between(documento.resolve(inizio), documento.resolve(fine));
}
