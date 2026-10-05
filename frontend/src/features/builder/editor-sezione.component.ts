import {
  type AfterViewInit,
  Component,
  DestroyRef,
  ElementRef,
  ViewEncapsulation,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { ReplaceStep } from 'prosemirror-transform';
import { TextSelection, type Command, type EditorState, type Transaction } from 'prosemirror-state';
import { Decoration, DecorationSet, EditorView } from 'prosemirror-view';

import { MenuSegnapostoComponent, type VoceSegnaposto } from './menu-segnaposto.component';
import { convertiAppunti } from './frammenti';
import {
  blocchiDaDocumento,
  comandoTesto,
  creaStato,
  documentoDaBlocchi,
  impronta,
  porzioneDaIncollare,
  selezioneSicura,
  statoSelezione,
  type BloccoDocumento,
  type StatoSelezione,
} from './documento-editor';

/** Una porzione del documento della sezione, come posizioni ProseMirror. */
export type Intervallo = { da: number; a: number };

/**
 * Dove comincia una pagina dentro questa sezione, come lo misura il renderer
 * (012 T080): il blocco (la voce, se e' un elenco) e quante sue righe restano
 * sulla pagina prima; e lo spazio fra i due fogli, in mm del PDF (T083).
 */
export type InizioPaginaSezione = {
  pagina: number;
  blocco: string | null;
  voce: number | null;
  riga: number;
  spazio_libero_mm: number;
  margine_basso_mm: number;
  margine_alto_mm: number;
};

/** Lo stacco fra due fogli, in pixel: non e' nel PDF, separa i fogli a schermo. */
export const STACCO_FOGLI = 24;

export type ModificaSezione = {
  blocchi: BloccoDocumento[];
  /** Una battuta di testo: la cronologia la raggruppa con le vicine. */
  digitazione: boolean;
  /** Dov'era la selezione prima della modifica: annullando si torna li'. */
  prima: Intervallo;
};

const SINCRONIZZAZIONE = 'gemodo-sincronizzazione';
const COMANDO = 'gemodo-comando';

/**
 * Il testo di una sezione: una sola area di scrittura per tutti i suoi
 * blocchi, su ProseMirror (012 T075).
 *
 * L'editor non salva e non conosce le altre sezioni: riceve i blocchi, ne
 * restituisce di nuovi a ogni modifica, e la toolbar del builder gli manda i
 * comandi. La cronologia (annulla, ripeti) e' del builder, che la tiene per
 * tutto il documento; qui si segnala solo che e' stata chiesta.
 */
@Component({
  selector: 'app-editor-sezione',
  standalone: true,
  imports: [MenuSegnapostoComponent],
  // Il DOM del testo lo crea ProseMirror, non Angular: gli stili incapsulati
  // non lo raggiungerebbero. Sono tutti sotto `.testo-sezione`.
  encapsulation: ViewEncapsulation.None,
  styleUrl: './editor-sezione.component.scss',
  host: {
    // Il menu `/` e' fisso rispetto alla finestra: se il foglio scorre non
    // starebbe piu' sotto il cursore, quindi si chiude.
    '(window:scroll)': 'chiudiMenuSlash()',
    '(window:resize)': 'chiudiMenuSlash()',
  },
  template: `
    <div #area></div>
    @if (menuSlash(); as menu) {
      <app-menu-segnaposto
        [voci]="vociSlash()"
        [indice]="menu.indice"
        [filtro]="menu.filtro"
        [x]="menu.x"
        [y]="menu.y"
        (scelto)="inserisciDaSlash($event)"
      />
    }
  `,
})
export class EditorSezioneComponent implements AfterViewInit {
  readonly codice = input.required<string>();
  readonly blocchi = input.required<BloccoDocumento[]>();
  /** I segnaposto che il menu `/` propone: i campi della versione. */
  readonly campi = input<VoceSegnaposto[]>([]);

  readonly modificato = output<ModificaSezione>();
  readonly attivato = output<void>();
  readonly uscito = output<FocusEvent>();
  readonly selezione = output<StatoSelezione>();
  readonly cronologia = output<'annulla' | 'ripeti'>();

  private readonly area = viewChild.required<ElementRef<HTMLElement>>('area');
  private vista: EditorView | null = null;
  /** I blocchi che l'editor contiene, nella forma confrontabile. */
  private improntaCorrente = '';
  /** Il cursore e' mai stato nella sezione? Se no, un segnaposto va in fondo. */
  private toccato = false;
  private slashDa: number | null = null;
  /** Lo spazio fra due fogli, nel testo dove il PDF va a pagina nuova (T083). */
  private salti = DecorationSet.empty;

  /**
   * Il menu dei segnaposto aperto da `/` (012 T064): dove sta la `/`, cosa e'
   * stato scritto dopo e dove disegnarlo.
   */
  protected readonly menuSlash = signal<{
    inizio: number;
    filtro: string;
    indice: number;
    x: number;
    y: number;
  } | null>(null);
  protected readonly vociSlash = computed<VoceSegnaposto[]>(() => {
    const filtro = this.menuSlash()?.filtro.toLocaleLowerCase() ?? '';
    return this.campi()
      .filter((campo) => `${campo.codice} ${campo.etichetta}`.toLocaleLowerCase().includes(filtro))
      .slice(0, 8);
  });

  constructor() {
    // I blocchi che arrivano da fuori (annulla, un salvataggio, una sezione
    // rinominata) entrano nell'editor solo se sono davvero diversi da quelli
    // che contiene: riscrivere a ogni battuta sposterebbe il cursore.
    effect(() => {
      const blocchi = this.blocchi();
      if (this.vista) this.sincronizza(blocchi);
    });
    inject(DestroyRef).onDestroy(() => this.vista?.destroy());
  }

  ngAfterViewInit(): void {
    const blocchi = this.blocchi();
    this.improntaCorrente = impronta(blocchi);
    this.vista = new EditorView(this.area().nativeElement, {
      state: creaStato(blocchi, () => this.codice(), {
        annulla: () => this.cronologia.emit('annulla'),
        ripeti: () => this.cronologia.emit('ripeti'),
      }),
      attributes: (stato) => ({
        class: `testo-sezione${vuoto(stato) ? ' vuoto' : ''}`,
        role: 'textbox',
        'aria-multiline': 'true',
        'aria-label': `Testo della sezione ${this.codice()}`,
        spellcheck: 'true',
        'data-section-text': this.codice(),
      }),
      dispatchTransaction: (tr) => this.applica(tr),
      decorations: () => this.salti,
      handleTextInput: (vista, da, _a, testo) => {
        this.slashDa = testo === '/' && apreComando(vista.state, da) ? da : null;
        return false;
      },
      handleKeyDown: (_vista, evento) => this.tastoMenuSlash(evento),
      handlePaste: (vista, evento) => this.incolla(vista, evento),
      handleDrop: (vista, evento) => this.rilascia(vista, evento),
      handleDOMEvents: {
        focus: () => {
          this.toccato = true;
          this.attivato.emit();
          this.selezione.emit(statoSelezione(this.vista!.state));
          return false;
        },
        blur: (_vista, evento) => {
          this.chiudiMenuSlash();
          this.uscito.emit(evento);
          return false;
        },
      },
    });
  }

  /**
   * Mette fra il testo lo spazio che separa due fogli del PDF (012 T083): il
   * vuoto in fondo al foglio che finisce, il suo pie' di pagina, lo stacco e
   * l'intestazione del foglio dopo. Va all'inizio della riga annotata dal
   * renderer, nel blocco che la contiene: il foglio dell'editor ha le misure
   * del PDF (012 T078), quindi la riga N del blocco qui e' la riga N li'. Le
   * righe si contano senza gli spazi della misura prima, che si tolgono e si
   * rimettono nello stesso giro, prima che il browser disegni. Se il blocco
   * non c'e' piu' lo spazio aspetta la misura successiva.
   */
  impagina(inizi: readonly InizioPaginaSezione[]): void {
    const vista = this.vista;
    if (!vista) return;
    this.salti = DecorationSet.empty;
    vista.setProps({});
    const figli = Array.from(vista.dom.children);
    const salti: Decoration[] = [];
    for (const inizio of inizi) {
      const candidati = figli.filter(
        (figlio) => figlio.getAttribute('data-block-id') === inizio.blocco,
      );
      const elemento = candidati[inizio.voce ?? 0];
      if (!(elemento instanceof HTMLElement)) continue;
      const dove = this.posizioneSalto(vista, figli.indexOf(elemento), elemento, inizio.riga);
      if (!dove) continue;
      salti.push(
        Decoration.widget(dove.pos, () => spazioFraFogli(inizio, dove.inRiga), {
          side: -1,
          marks: [],
          ignoreSelection: true,
          key: `salto-${inizio.pagina}-${altezzaFraFogli(inizio)}-${dove.inRiga}`,
        }),
      );
    }
    this.salti = DecorationSet.create(vista.state.doc, salti);
    vista.setProps({});
  }

  /**
   * La posizione del testo dove comincia la pagina: prima del blocco se ci
   * comincia intero, dopo un'interruzione di pagina, altrimenti all'inizio
   * della riga `riga` del blocco.
   */
  private posizioneSalto(
    vista: EditorView,
    indice: number,
    elemento: HTMLElement,
    riga: number,
  ): { pos: number; inRiga: boolean } | null {
    const { doc } = vista.state;
    if (indice < 0 || indice >= doc.childCount) return null;
    let inizioNodo = 0;
    for (let i = 0; i < indice; i += 1) inizioNodo += doc.child(i).nodeSize;
    const nodo = doc.child(indice);
    if (!nodo.isTextblock) return { pos: inizioNodo + nodo.nodeSize, inRiga: false };
    if (riga === 0) return { pos: inizioNodo, inRiga: false };
    const box = elemento.getBoundingClientRect();
    const interlinea = parseFloat(getComputedStyle(elemento).lineHeight) || 0;
    const rientro = parseFloat(getComputedStyle(elemento).paddingLeft) || 0;
    let trovata: { pos: number } | null = null;
    try {
      trovata = vista.posAtCoords({
        left: box.left + rientro + 1,
        top: box.top + (riga + 0.5) * interlinea,
      });
    } catch {
      // Senza impaginazione del browser (i test unitari) non si misura.
    }
    const pos = trovata?.pos;
    if (pos === undefined || pos <= inizioNodo + 1 || pos >= inizioNodo + nodo.nodeSize - 1) {
      return { pos: inizioNodo, inRiga: false };
    }
    return { pos, inRiga: true };
  }

  /** Lo stato dell'editor, per chi deve leggerlo (un collegamento gia' presente). */
  get stato(): EditorState | null {
    return this.vista?.state ?? null;
  }

  /** Esegue un comando della toolbar sulla selezione, e rimette il fuoco nel testo. */
  esegui(comando: Command): boolean {
    const vista = this.vista;
    if (!vista) return false;
    vista.focus();
    return comando(vista.state, (tr) => vista.dispatch(tr.setMeta(COMANDO, true)), vista);
  }

  intervallo(): Intervallo {
    const selezione = this.vista?.state.selection;
    return { da: selezione?.from ?? 0, a: selezione?.to ?? 0 };
  }

  /** La selezione rimessa dov'era, e il fuoco nel testo. */
  seleziona(intervallo: Intervallo): void {
    const vista = this.vista;
    if (!vista) return;
    const selezione = selezioneSicura(vista.state.doc, intervallo.da, intervallo.a);
    vista.dispatch(vista.state.tr.setSelection(selezione).setMeta(SINCRONIZZAZIONE, true));
    vista.focus();
  }

  /** Il cursore alla fine del testo (una sezione appena aggiunta). */
  scriviInFondo(): void {
    const fine = this.vista?.state.doc.content.size ?? 0;
    this.seleziona({ da: fine, a: fine });
  }

  /**
   * Un testo (un segnaposto dal pannello) al cursore, o in fondo se nella
   * sezione non si e' ancora scritto.
   */
  inserisciTesto(testo: string): void {
    if (!this.toccato) this.scriviInFondo();
    this.esegui(comandoTesto(testo));
  }

  /** Riporta l'editor ai blocchi dati, se sono diversi da quelli che ha. */
  sincronizza(blocchi: BloccoDocumento[] = this.blocchi()): void {
    const vista = this.vista;
    const nuova = impronta(blocchi);
    if (!vista || nuova === this.improntaCorrente) return;
    this.improntaCorrente = nuova;
    const { doc } = vista.state;
    const tr = vista.state.tr
      .replaceWith(0, doc.content.size, documentoDaBlocchi(blocchi).content)
      .setMeta(SINCRONIZZAZIONE, true);
    vista.dispatch(tr);
  }

  private applica(tr: Transaction): void {
    const vista = this.vista!;
    const prima = vista.state;
    const { state: dopo, transactions } = prima.applyTransaction(tr);
    // Lo spazio fra i fogli segue il testo finche' non arriva la misura nuova.
    for (const fatta of transactions) this.salti = this.salti.map(fatta.mapping, fatta.doc);
    vista.updateState(dopo);
    if (this.slashDa !== null && dopo.doc.textBetween(this.slashDa, this.slashDa + 1) === '/') {
      this.apriMenuSlash(this.slashDa);
    }
    this.slashDa = null;
    this.seguiMenuSlash(dopo);
    this.selezione.emit(statoSelezione(dopo));
    if (dopo.doc.eq(prima.doc) || tr.getMeta(SINCRONIZZAZIONE)) {
      // Una sincronizzazione puo' aver dato id nuovi a blocchi duplicati:
      // l'impronta segue cio' che l'editor contiene davvero.
      if (!dopo.doc.eq(prima.doc)) {
        this.improntaCorrente = impronta(blocchiDaDocumento(dopo.doc, this.codice()));
      }
      return;
    }
    const blocchi = blocchiDaDocumento(dopo.doc, this.codice());
    this.improntaCorrente = impronta(blocchi);
    this.modificato.emit({
      blocchi,
      digitazione: digitazione(transactions, prima, dopo),
      prima: { da: prima.selection.from, a: prima.selection.to },
    });
  }

  // --- Menu `/` ---------------------------------------------------------------

  private apriMenuSlash(inizio: number): void {
    const { x, y } = this.coordinate(inizio);
    this.menuSlash.set({ inizio, filtro: '', indice: 0, x, y });
  }

  /**
   * Cio' che si scrive dopo la `/` filtra l'elenco; uno spazio, una
   * selezione, o il cursore che torna prima della `/`, chiude il menu
   * lasciando il testo com'e'.
   */
  private seguiMenuSlash(stato: EditorState): void {
    const menu = this.menuSlash();
    if (!menu) return;
    const { empty, head } = stato.selection;
    const fine = stato.doc.content.size;
    if (
      !empty ||
      head <= menu.inizio ||
      menu.inizio >= fine ||
      stato.doc.textBetween(menu.inizio, menu.inizio + 1) !== '/'
    ) {
      this.chiudiMenuSlash();
      return;
    }
    const filtro = stato.doc.textBetween(menu.inizio + 1, head);
    if (/\s/.test(filtro)) this.chiudiMenuSlash();
    else if (filtro !== menu.filtro) this.menuSlash.set({ ...menu, filtro, indice: 0 });
  }

  protected chiudiMenuSlash(): void {
    if (this.menuSlash()) this.menuSlash.set(null);
  }

  /** Sostituisce `/filtro` con il segnaposto scelto, con l'enfasi del testo intorno. */
  protected inserisciDaSlash(codice: string): void {
    const menu = this.menuSlash();
    this.chiudiMenuSlash();
    if (!menu) return;
    this.esegui(comandoTesto(`{{${codice}}}`, menu.inizio, menu.inizio + 1 + menu.filtro.length));
  }

  /** I tasti che il menu `/` usa per se'; `true` se il tasto e' stato consumato. */
  private tastoMenuSlash(evento: KeyboardEvent): boolean {
    const menu = this.menuSlash();
    if (!menu) return false;
    const voci = this.vociSlash();
    switch (evento.key) {
      case 'ArrowDown':
      case 'ArrowUp': {
        const passo = evento.key === 'ArrowDown' ? 1 : -1;
        const totale = Math.max(voci.length, 1);
        this.menuSlash.set({ ...menu, indice: (menu.indice + passo + totale) % totale });
        return true;
      }
      case 'Enter':
      case 'Tab':
        if (!voci.length) return false;
        this.inserisciDaSlash(voci[menu.indice]?.codice ?? voci[0].codice);
        return true;
      case 'Escape':
        // Chiude e basta: la `/` resta nel testo, era forse una barra vera.
        this.chiudiMenuSlash();
        return true;
      case 'ArrowLeft':
      case 'ArrowRight':
        this.chiudiMenuSlash();
        return false;
      default:
        return false;
    }
  }

  /** Dove disegnare il menu: sotto il cursore, o sotto l'editor se il browser non lo sa dire. */
  private coordinate(pos: number): { x: number; y: number } {
    const vista = this.vista!;
    let base: { left: number; bottom: number };
    try {
      base = vista.coordsAtPos(pos);
    } catch {
      base = vista.dom.getBoundingClientRect();
    }
    const larghezza = vista.dom.ownerDocument.defaultView?.innerWidth ?? 1024;
    return { x: Math.max(8, Math.min(base.left, larghezza - 316)), y: base.bottom + 4 };
  }

  // --- Incolla e trascina -----------------------------------------------------

  /**
   * Incolla da un elaboratore di testi (FR-017). L'HTML degli appunti viene
   * convertito da `convertiAppunti` e non arriva mai al servizio. Cio' che si
   * copia da questo stesso editor, invece, ProseMirror lo riconosce e lo
   * rimette con la sua struttura.
   */
  private incolla(vista: EditorView, evento: ClipboardEvent): boolean {
    const appunti = evento.clipboardData;
    if (!appunti) return false;
    const html = appunti.getData('text/html');
    if (html.includes('data-pm-slice')) return false;
    const incollati = convertiAppunti(html, appunti.getData('text/plain'));
    if (incollati.length) {
      vista.dispatch(
        vista.state.tr
          .replaceSelection(porzioneDaIncollare(incollati))
          .setMeta('uiEvent', 'paste')
          .scrollIntoView(),
      );
    }
    return true;
  }

  /** Un segnaposto trascinato dal pannello cade dove lo si lascia. */
  private rilascia(vista: EditorView, evento: DragEvent): boolean {
    const codice = evento.dataTransfer?.getData('application/x-gemodo-placeholder');
    if (!codice) return false;
    const punto = vista.posAtCoords({ left: evento.clientX, top: evento.clientY });
    const pos = punto?.pos ?? vista.state.selection.from;
    evento.preventDefault();
    vista.dispatch(vista.state.tr.setSelection(TextSelection.near(vista.state.doc.resolve(pos))));
    this.esegui(comandoTesto(`{{${codice}}}`));
    return true;
  }
}

/** La sezione ha solo una riga vuota: si mostra l'invito a scrivere. */
function vuoto(stato: EditorState): boolean {
  const { doc } = stato;
  return doc.childCount === 1 && doc.firstChild!.isTextblock && doc.firstChild!.content.size === 0;
}

/**
 * La `/` apre il menu solo se comincia una parola: "e/o" o "01/10" sono
 * testo, non un comando.
 */
function apreComando(stato: EditorState, da: number): boolean {
  const $da = stato.doc.resolve(da);
  if (!$da.parent.isTextblock) return false;
  const prima = $da.parentOffset > 0 ? stato.doc.textBetween(da - 1, da, '\n', '\n') : '';
  return !prima || /[\s(«"“'’]/.test(prima);
}

/**
 * Una battuta di testo, da raggruppare con le vicine nella cronologia: solo
 * sostituzioni di testo nello stesso capoverso, senza blocchi nuovi.
 */
function digitazione(
  transazioni: readonly Transaction[],
  prima: EditorState,
  dopo: EditorState,
): boolean {
  if (prima.doc.childCount !== dopo.doc.childCount) return false;
  return transazioni.every(
    (tr) =>
      !tr.getMeta(COMANDO) &&
      !tr.getMeta('uiEvent') &&
      tr.steps.every((passo) => passo instanceof ReplaceStep),
  );
}

/** Quanto e' alto lo spazio fra due fogli, come espressione CSS sul foglio. */
function altezzaFraFogli(inizio: InizioPaginaSezione): string {
  const mm = inizio.spazio_libero_mm + inizio.margine_basso_mm + inizio.margine_alto_mm;
  return `calc(var(--foglio-mm) * ${mm.toFixed(2)} + ${STACCO_FOGLI}px)`;
}

/**
 * Lo spazio fra due fogli: vuoto, alto quanto quello del PDF. Il foglio ci
 * disegna sopra pie' di pagina e intestazione. Dentro un capoverso e' un
 * blocco in linea largo quanto la riga: la riga prima resta giustificata.
 */
function spazioFraFogli(inizio: InizioPaginaSezione, inRiga: boolean): HTMLElement {
  const spazio = document.createElement(inRiga ? 'span' : 'div');
  spazio.className = inRiga ? 'salto-foglio in-riga' : 'salto-foglio';
  spazio.contentEditable = 'false';
  spazio.setAttribute('aria-hidden', 'true');
  spazio.setAttribute('data-salto-pagina', String(inizio.pagina));
  spazio.style.height = altezzaFraFogli(inizio);
  return spazio;
}
