import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed, type ComponentFixture } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, provideRouter } from '@angular/router';
import { NodeSelection, TextSelection } from 'prosemirror-state';
import type { EditorView } from 'prosemirror-view';
import { ModelloAnteprimaComponent } from './modello-anteprima.component';
import { EditorSezioneComponent } from './editor-sezione.component';

const dettaglio = {
  id: 'model',
  public_id: 1,
  codice: 'bando-cter-it-abc',
  nome: 'Collaboratore Tecnico E.R. - Tutti i livelli - Italiano',
  codice_tipo_documento: 'BANDO_CONCORSO',
  codice_categoria: 'CTER',
  codice_tipologia: 'TI',
  percorso_categorizzazione: ['TI', 'CTER'],
  variante: 'STANDARD',
  lingua: 'IT',
  livello_professionale: null,
  dimensioni: { lingua: 'IT' },
  derivato_da_modello_id: null,
  codice_contesto: 'geban',
  integrazione_id: 'source',
  created_at: '2026-09-22T10:00:00Z',
  versioni: [
    {
      id: 'v2',
      public_id: 2,
      modello_id: 'model',
      numero_versione: 2,
      stato: 'BOZZA',
      pubblicato_at: null,
      campi: [
        {
          codice: 'titolo_it',
          etichetta: 'Titolo',
          tipo: 'string',
          lingua: 'IT',
          obbligatorio: true,
          ordine: 1,
          descrizione: null,
        },
        {
          codice: 'numero_posti',
          etichetta: 'Numero posti',
          tipo: 'number',
          lingua: 'IT',
          obbligatorio: false,
          ordine: 2,
          descrizione: null,
        },
      ],
    },
  ],
};

const struttura = {
  codice_tipo_documento: 'BANDO_CONCORSO',
  validita: '2026-09-22T10:00:00Z',
  nodi: [
    {
      codice: 'TI',
      figli: [{ codice: 'CTER', lingue_possibili: ['IT', 'EN'], campi: [] }],
    },
  ],
};

type RispostaPolicy = {
  codice_tipo_documento: string;
  policy: {
    nome_dimensione: string;
    consente_valore_generico: boolean;
    // `ripiego` quando l'admin non ha ancora deciso: il backend restituisce
    // comunque la regola che applica, e il builder la usa cosi' com'e'.
    origine?: 'registrata' | 'ripiego';
  }[];
  dimensioni_non_configurate: { nome_dimensione: string }[];
};

const policy: RispostaPolicy = {
  codice_tipo_documento: 'BANDO_CONCORSO',
  policy: [{ nome_dimensione: 'lingua', consente_valore_generico: false }],
  dimensioni_non_configurate: [],
};

const sezioniResponse = {
  modello_versione_id: 'v2',
  stato_versione: 'BOZZA',
  modificabile: true,
  sezioni: [
    {
      codice: 'intro',
      ordine: 0,
      contenuto: [
        {
          id: 'intro-p1',
          tipo: 'PARAGRAFO',
          frammenti: [
            {
              testo: 'Introduzione {{titolo_it}}',
              grassetto: false,
              corsivo: false,
              sottolineato: false,
              collegamento: null,
            },
          ],
          allineamento: null,
          elementi: [],
          posizionamento: 'BODY',
          ordine: 0,
          stile: null,
          placeholder_usati: ['titolo_it'],
          regole_layout: {},
          asset_ref: null,
          colonne: [],
        },
      ],
    },
    {
      codice: 'dettagli',
      ordine: 1,
      contenuto: [
        {
          id: 'dettagli-p1',
          tipo: 'PARAGRAFO',
          frammenti: [{ testo: 'Posti disponibili {{numero_posti}}' }],
          posizionamento: 'BODY',
          ordine: 0,
          stile: null,
          placeholder_usati: ['numero_posti'],
          regole_layout: {},
          asset_ref: null,
          colonne: [],
        },
      ],
    },
  ],
  documento: {
    blocchi: [
      {
        id: 'intro-p1',
        tipo: 'PARAGRAFO',
        frammenti: [{ testo: 'Introduzione {{titolo_it}}' }],
        posizionamento: 'BODY',
        ordine: 0,
        stile: null,
        placeholder_usati: ['titolo_it'],
        regole_layout: {},
        asset_ref: null,
        colonne: [],
      },
      {
        id: 'dettagli-p1',
        tipo: 'PARAGRAFO',
        frammenti: [{ testo: 'Posti disponibili {{numero_posti}}' }],
        posizionamento: 'BODY',
        ordine: 1,
        stile: null,
        placeholder_usati: ['numero_posti'],
        regole_layout: {},
        asset_ref: null,
        colonne: [],
      },
    ],
    placeholder_usati: ['titolo_it', 'numero_posti'],
  },
};

const CORNICE_ASSENTE = {
  cornice: null,
  logo_presente: false,
  maschere_intestazione: ['LOGO_CENTRO_TESTO_SOTTO'],
  maschere_pie_pagina: ['TESTO_SINISTRA_NUMERO_DESTRA'],
  integrazione_id: 'int-1',
  codice_tipo_documento: 'BANDO_CONCORSO',
  codice_contesto: 'geban',
};

describe('2b ridotta: anteprima modello', () => {
  function setup(id = 'model') {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => id } } } },
      ],
    });
    const fixture = TestBed.createComponent(ModelloAnteprimaComponent);
    const http = TestBed.inject(HttpTestingController);
    return { fixture, http, root: fixture.nativeElement as HTMLElement };
  }

  function flushDerivationConfig(
    http: HttpTestingController,
    strutturaResponse = struttura,
    policyResponse: RispostaPolicy = policy,
  ): void {
    http
      .expectOne('/api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile')
      .flush(strutturaResponse);
    http
      .expectOne('/api/v1/builder/tipi-documento/BANDO_CONCORSO/policy-dimensioni')
      .flush(policyResponse);
  }

  function flushSections(
    http: HttpTestingController,
    response = sezioniResponse,
    modelId = 'model',
    versionId = 'v2',
    cornice: object = CORNICE_ASSENTE,
  ): void {
    http
      .expectOne(`/api/v1/builder/modelli/${modelId}/versioni/${versionId}/sezioni`)
      .flush(response);
    // La cornice del tipo documento parte insieme alle sezioni (012 T070).
    http
      .match(`/api/v1/builder/modelli/${modelId}/cornice`)
      .forEach((richiesta) => richiesta.flush(cornice));
  }

  const IMPAGINAZIONE_VUOTA = { pagine: 1, inizi_pagina: [] };

  /**
   * Il builder chiede dove cominciano le pagine dopo ogni caricamento e
   * salvataggio (012 T080): chi non le guarda le risponde con una pagina sola.
   */
  function verifica(http: HttpTestingController): void {
    http
      .match((richiesta) => richiesta.url.endsWith('/impaginazione'))
      .forEach((richiesta) => richiesta.flush(IMPAGINAZIONE_VUOTA));
    http.verify();
  }

  // --- L'editor di sezione (012 T077) ---------------------------------------
  //
  // Il testo e' un editor ProseMirror per sezione. Selezioni, tasti e incolla
  // gli arrivano come dal browser; la sola cosa che jsdom non sa fare e'
  // scrivere nel DOM una battuta, quindi la battuta entra dalla stessa porta
  // che ProseMirror usa per il testo digitato (`handleTextInput`).

  type Fixture = ComponentFixture<ModelloAnteprimaComponent>;

  function editoreDi(fixture: Fixture, sezione: string): EditorSezioneComponent {
    const trovato = fixture.debugElement
      .queryAll(By.directive(EditorSezioneComponent))
      .map((elemento) => elemento.componentInstance as EditorSezioneComponent)
      .find((editor) => editor.codice() === sezione);
    if (!trovato) throw new Error(`nessun editor per la sezione ${sezione}`);
    return trovato;
  }

  function vistaDi(fixture: Fixture, sezione: string): EditorView {
    return editoreDi(fixture, sezione)['vista']!;
  }

  /** Il fuoco nel testo della sezione, come con un clic. */
  function apriEditor(fixture: Fixture, sezione = 'intro'): HTMLElement {
    const vista = vistaDi(fixture, sezione);
    vista.focus();
    fixture.detectChanges();
    return vista.dom as HTMLElement;
  }

  /** I capoversi della sezione come li vede chi legge. */
  function capoversi(fixture: Fixture, sezione = 'intro'): string[] {
    return Array.from(vistaDi(fixture, sezione).dom.children).map((c) => c.textContent ?? '');
  }

  function posizione(vista: EditorView, testo: string): { da: number; a: number } {
    let trovata: { da: number; a: number } | null = null;
    vista.state.doc.descendants((nodo, pos) => {
      const indice = nodo.isText ? nodo.text!.indexOf(testo) : -1;
      if (!trovata && indice >= 0) trovata = { da: pos + indice, a: pos + indice + testo.length };
    });
    if (!trovata) throw new Error(`"${testo}" non e' nel testo`);
    return trovata;
  }

  /** Seleziona da `testo` fino alla fine di `finoA`, anche in un altro capoverso. */
  function selezionaTesto(fixture: Fixture, sezione: string, testo: string, finoA = testo): void {
    const vista = vistaDi(fixture, sezione);
    vista.focus();
    const da = posizione(vista, testo).da;
    const a = posizione(vista, finoA).a;
    vista.dispatch(vista.state.tr.setSelection(TextSelection.create(vista.state.doc, da, a)));
    fixture.detectChanges();
  }

  function cursoreDopo(fixture: Fixture, sezione: string, testo: string): void {
    const vista = vistaDi(fixture, sezione);
    vista.focus();
    const pos = posizione(vista, testo).a;
    vista.dispatch(vista.state.tr.setSelection(TextSelection.create(vista.state.doc, pos)));
    fixture.detectChanges();
  }

  function cursoreInFondo(fixture: Fixture, sezione: string): void {
    const vista = vistaDi(fixture, sezione);
    vista.focus();
    const fine = vista.state.doc.content.size - 1;
    vista.dispatch(vista.state.tr.setSelection(TextSelection.create(vista.state.doc, fine)));
    fixture.detectChanges();
  }

  /** Scrive al cursore, una battuta alla volta, come la tastiera. */
  function digita(fixture: Fixture, sezione: string, testo: string): void {
    const vista = vistaDi(fixture, sezione);
    for (const carattere of testo) {
      const { from, to } = vista.state.selection;
      const predefinito = () => vista.state.tr.insertText(carattere, from, to);
      if (!vista.someProp('handleTextInput', (f) => f(vista, from, to, carattere, predefinito))) {
        vista.dispatch(predefinito());
      }
    }
    fixture.detectChanges();
  }

  function premi(
    fixture: Fixture,
    sezione: string,
    key: string,
    modificatori: KeyboardEventInit = {},
  ): KeyboardEvent {
    const evento = new KeyboardEvent('keydown', {
      key,
      bubbles: true,
      cancelable: true,
      ...modificatori,
    });
    vistaDi(fixture, sezione).dom.dispatchEvent(evento);
    fixture.detectChanges();
    return evento;
  }

  function incollaIn(editor: HTMLElement, html: string, testo = ''): void {
    const evento = new Event('paste', { bubbles: true, cancelable: true });
    Object.defineProperty(evento, 'clipboardData', {
      value: { getData: (tipo: string) => (tipo === 'text/html' ? html : testo) },
    });
    editor.dispatchEvent(evento);
  }

  function salva(root: HTMLElement, http: HttpTestingController) {
    (root.querySelector('[data-save-sections]') as HTMLButtonElement).click();
    return http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
  }

  function apriPannello(root: HTMLElement, nome: string): void {
    (
      Array.from(root.querySelectorAll('.panel-tabs button')).find((button) =>
        button.textContent?.includes(nome),
      ) as HTMLButtonElement
    ).click();
  }

  function scegliStile(root: HTMLElement, valore: string): void {
    const menu = root.querySelector('[data-style-select]') as HTMLSelectElement;
    menu.value = valore;
    menu.dispatchEvent(new Event('change'));
  }

  function paragrafo(id: string, frammenti: object[], ordine = 0) {
    return {
      id,
      tipo: 'PARAGRAFO',
      frammenti,
      posizionamento: 'BODY',
      ordine,
      stile: null,
      placeholder_usati: [] as string[],
    };
  }

  function elenco(id: string, voci: string[], marcatore = 'NUMERICO') {
    return {
      id,
      tipo: 'ELENCO',
      frammenti: [] as { testo: string }[],
      elementi: voci.map((testo) => ({ livello: 0, marcatore, frammenti: [{ testo }] })),
      posizionamento: 'BODY',
      ordine: 0,
      stile: null,
      placeholder_usati: [] as string[],
    };
  }

  /** Una bozza con una sola sezione, `art`, fatta dei blocchi indicati. */
  function caricaBozzaCon(blocchi: unknown[]) {
    const contesto = setup();
    contesto.http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(contesto.http, {
      ...sezioniResponse,
      sezioni: [{ codice: 'art', ordine: 0, contenuto: blocchi }],
    } as unknown as typeof sezioniResponse);
    flushDerivationConfig(contesto.http);
    contesto.fixture.detectChanges();
    return contesto;
  }

  function caricaBozza() {
    const contesto = setup();
    contesto.http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(contesto.http);
    flushDerivationConfig(contesto.http);
    contesto.fixture.detectChanges();
    return contesto;
  }

  /** I marcatori calcolati delle voci, come li mostra l'editor. */
  function marcatori(root: HTMLElement): string[] {
    return Array.from(root.querySelectorAll('[data-section-text] [data-marcatore]')).map(
      (voce) => voce.getAttribute('data-marcatore') ?? '',
    );
  }

  it('shows the contract fields returned by the API, with type and obligation', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();
    const campi = root.querySelectorAll('.campo');
    expect(campi.length).toBe(2);
    expect(campi[0].textContent).toContain('titolo_it');
    expect(campi[0].textContent).toContain('Titolo');
    expect(campi[0].textContent).toContain('string');
    expect(campi[0].textContent).toContain('obbligatorio');
    expect(campi[1].textContent).not.toContain('obbligatorio');
    expect(root.textContent).toContain('TI / CTER');
    expect(root.textContent).toContain('v2');
    expect(root.textContent).toContain('BOZZA');
    verifica(http);
  });

  it('keeps the IT/EN flow automatic while sending the generic contract', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();
    const dialog = root.querySelector(
      'dialog[aria-labelledby="derivazione-titolo"]',
    ) as HTMLDialogElement;
    // jsdom non implementa showModal/close: stubbati come gia' fatto per la lista.
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    const bottone = Array.from(
      root.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((b) => b.textContent?.includes('Crea modello derivato'))!;
    expect(bottone).toBeTruthy();
    bottone.click();
    expect(dialog.showModal).toHaveBeenCalled();
    fixture.detectChanges();
    expect(root.querySelector('#dimensione-derivazione')).toBeNull();
    expect(root.querySelector('#valore-derivazione')).toBeNull();
    const conferma = Array.from(
      root.querySelectorAll('dialog button') as NodeListOf<HTMLButtonElement>,
    ).find((b) => b.textContent?.trim() === 'Crea')!;
    conferma.click();
    const richiesta = http.expectOne('/api/v1/builder/modelli/model/edizioni-derivate');
    expect(richiesta.request.body).toEqual({ nome_dimensione: 'lingua', valore: 'EN' });
    richiesta.flush({ ...dettaglio, id: 'derivato', lingua: 'EN' });
    http
      .expectOne('/api/v1/builder/modelli/model')
      .flush({ ...dettaglio, derivato_da_modello_id: 'padre' });
    flushSections(http);
    verifica(http);
  });

  it('creates a variant from the builder editor and opens the new model', () => {
    const { fixture, http, root } = setup();
    const router = TestBed.inject(Router);
    const navigate = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const dialog = root.querySelector('[data-create-variant-dialog]') as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    (root.querySelector('[data-create-variant-open]') as HTMLButtonElement).click();
    expect(dialog.showModal).toHaveBeenCalled();
    fixture.detectChanges();
    expect((root.querySelector('[data-create-variant-submit]') as HTMLButtonElement).disabled).toBe(
      true,
    );

    const nota = root.querySelector('[data-variant-note]') as HTMLInputElement;
    nota.value = 'Senza prova preselettiva';
    nota.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    (root.querySelector('[data-create-variant-submit]') as HTMLButtonElement).click();

    const richiesta = http.expectOne('/api/v1/builder/modelli/model/varianti');
    expect(richiesta.request.method).toBe('POST');
    expect(richiesta.request.body).toEqual({ nota: 'Senza prova preselettiva' });
    richiesta.flush({ id: 'variante' });
    expect(dialog.close).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith(['/modelli', 'variante', 'builder']);
    verifica(http);
  });

  it('asks which value to derive when the dimension has more than one alternative', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http, {
      ...struttura,
      nodi: [
        {
          codice: 'TI',
          figli: [{ codice: 'CTER', lingue_possibili: ['IT', 'EN', 'FR'], campi: [] }],
        },
      ],
    });
    fixture.detectChanges();

    expect(root.querySelector('#valore-derivazione')).toBeTruthy();
    const valori = Array.from(root.querySelectorAll('#valore-derivazione option')).map(
      (option) => option.textContent,
    );
    expect(valori).toEqual(['EN', 'FR']);
    verifica(http);
  });

  it('does not offer derivation when no multivalue dimension is mandatory', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http, struttura, {
      ...policy,
      policy: [{ nome_dimensione: 'lingua', consente_valore_generico: true }],
    });
    fixture.detectChanges();

    expect(root.textContent).not.toContain('Crea edizione collegata');
    verifica(http);
  });

  it('hides the English action for a model that is already an English edition', () => {
    const { fixture, http, root } = setup();
    http
      .expectOne('/api/v1/builder/modelli/model')
      .flush({ ...dettaglio, lingua: 'EN', derivato_da_modello_id: 'padre' });
    flushSections(http);
    fixture.detectChanges();
    expect(
      Array.from(root.querySelectorAll('button')).find((b) =>
        b.textContent?.includes('Crea modello derivato'),
      ),
    ).toBeUndefined();
    verifica(http);
  });

  it('offers derivation on a dimension whose policy is only the fallback', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    // Nessuna policy registrata: il backend risponde con la riga di ripiego,
    // che per la lingua dice "biforca il modello". Prima il frontend guardava
    // solo le righe registrate e nascondeva il pulsante, pur essendo la
    // derivazione accettata dall'API.
    flushDerivationConfig(http, struttura, {
      ...policy,
      policy: [{ nome_dimensione: 'lingua', consente_valore_generico: false, origine: 'ripiego' }],
      dimensioni_non_configurate: [{ nome_dimensione: 'lingua' }],
    });
    fixture.detectChanges();

    expect(
      Array.from(root.querySelectorAll('button')).find((b) =>
        b.textContent?.includes('Crea modello derivato'),
      ),
    ).toBeTruthy();
    expect(root.querySelector('[data-derivazione-ko]')).toBeNull();
    verifica(http);
  });

  it('says why derivation is unavailable instead of hiding the button silently', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    // La policy risponde, l'albero live no: e' il caso reale in cui
    // l'integrazione e' configurata ma il servizio esterno non risponde.
    // Si serve prima quella che riesce, altrimenti `forkJoin` annulla l'altra
    // e resterebbe una richiesta pendente che `verify()` reclama.
    http.expectOne('/api/v1/builder/tipi-documento/BANDO_CONCORSO/policy-dimensioni').flush(policy);
    http.expectOne('/api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile').flush(
      {
        codice: 'DISCOVERY_NON_DISPONIBILE',
        messaggio: 'Servizio di categorizzazione non raggiungibile',
      },
      { status: 503, statusText: 'Service Unavailable' },
    );
    fixture.detectChanges();

    // "Non esiste" e "ora non si puo'" sono due cose diverse.
    expect(root.querySelector('[data-derivazione-ko]')?.textContent).toContain(
      'Derivazione non disponibile',
    );
    expect(root.querySelector('[data-derivazione-ko]')?.getAttribute('title')).toContain(
      'non raggiungibile',
    );
    verifica(http);
  });

  it('shows the composed document returned by the sections API', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();
    expect(root.querySelector('[data-document-preview]')?.textContent).toContain(
      'Introduzione {{titolo_it}}',
    );
    expect(root.querySelector('[data-document-preview]')?.textContent).toContain(
      'Posti disponibili {{numero_posti}}',
    );
    expect(root.querySelectorAll('.outline-item').length).toBe(2);
    verifica(http);
  });

  it('uses the fullscreen editor controls instead of a textarea form', () => {
    const { fixture, http, root } = caricaBozza();

    expect(root.querySelector('textarea')).toBeNull();
    const editor = apriEditor(fixture);
    expect(editor.textContent).toContain('Introduzione');
    scegliStile(root, 'H1');
    fixture.detectChanges();

    expect(root.querySelector('[data-section-text="intro"] .style-h1')).toBeTruthy();
    verifica(http);
  });

  it('012 T070: without a frame the sheet and the Pagina tab offer to add header and footer', () => {
    const { fixture, http, root } = caricaBozza();

    // Niente piu' intestazione e firma finte del prototipo (FR-008).
    expect(root.textContent).not.toContain('Comune di');
    expect(root.textContent).not.toContain('Il Responsabile del procedimento');
    const aggiungi = root.querySelector('[data-sheet-add-intestazione]') as HTMLAnchorElement;
    expect(aggiungi.getAttribute('href')).toBe('/contesti/geban/impostazioni/int-1/BANDO_CONCORSO');
    expect(root.querySelector('[data-sheet-add-piede]')).toBeTruthy();

    apriPannello(root, 'Pagina');
    fixture.detectChanges();
    expect(root.querySelector('[data-pagina-intestazione]')?.textContent).toContain('Nessuna');
    expect(root.querySelector('[data-aggiungi-intestazione]')?.getAttribute('href')).toBe(
      '/contesti/geban/impostazioni/int-1/BANDO_CONCORSO',
    );
    expect(root.querySelector('[data-aggiungi-piede]')).toBeTruthy();
    expect(root.querySelector('[data-add-section-inline]')?.textContent).toContain(
      'Inserisci una nuova sezione di testo',
    );
    verifica(http);
  });

  it('012 T070: the frame of the document type shows on the sheet as in the PDF', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http, sezioniResponse, 'model', 'v2', {
      ...CORNICE_ASSENTE,
      logo_presente: false,
      cornice: {
        intestazione: {
          maschera: 'LOGO_CENTRO_TESTO_SOTTO',
          con_logo: true,
          testo: [
            { testo: 'Consiglio Nazionale delle Ricerche', grassetto: true },
            { testo: '\nUfficio Reclutamento' },
          ],
        },
        pie_pagina: {
          maschera: 'TESTO_SINISTRA_NUMERO_DESTRA',
          testo: [{ testo: 'Roma' }],
          numerazione_pagine: true,
        },
      },
    });
    flushDerivationConfig(http);
    fixture.detectChanges();

    const testata = root.querySelector('[data-cornice-testata]')!;
    expect(testata.querySelector('.b')?.textContent).toBe('Consiglio Nazionale delle Ricerche');
    expect(testata.textContent).toContain('Ufficio Reclutamento');
    // Logo richiesto ma non ancora caricato: lo si dice, non lo si inventa.
    expect(testata.textContent).toContain('logo da caricare');
    expect(root.querySelector('[data-cornice-piede]')?.textContent).toContain('Pagina 1 di N');
    expect(root.querySelector('[data-sheet-add-intestazione]')).toBeNull();

    apriPannello(root, 'Pagina');
    fixture.detectChanges();
    expect(root.querySelector('[data-pagina-intestazione]')?.textContent).toContain(
      'Logo non ancora caricato',
    );
    expect(root.querySelector('[data-modifica-cornice]')).toBeTruthy();
    verifica(http);
  });

  it('012 T060: a new section starts with an empty line and the caret in it', () => {
    const { fixture, http, root } = caricaBozza();
    (root.querySelector('[data-add-section-inline]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const testo = root.querySelector('[data-section-text="sezione-3"]') as HTMLElement;
    expect(capoversi(fixture, 'sezione-3')).toEqual(['']);
    expect(document.activeElement).toBe(testo);
    // Il pannello Blocchi non c'e' piu': inserire blocchi e' compito dell'editor (T061).
    const schede = Array.from(root.querySelectorAll('.panel-tabs button')).map((b) =>
      b.textContent?.trim(),
    );
    expect(schede).toEqual(['Segnaposto', 'Pagina', 'Proprietà']);
    verifica(http);
  });

  it('012 T062: renames the section from the properties tab and refuses a duplicate name', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(fixture, 'dettagli');
    apriPannello(root, 'Proprietà');
    fixture.detectChanges();

    const nome = root.querySelector('[data-section-name]') as HTMLInputElement;
    expect(nome.value).toBe('dettagli');
    nome.value = 'intro';
    nome.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(root.querySelector('[data-section-name-error]')?.textContent).toContain('intro');
    expect(nome.value).toBe('dettagli');

    nome.value = '  Art. 1 - Posti a concorso ';
    nome.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(root.querySelector('[data-section-name-error]')).toBeNull();
    expect(root.querySelector('.outline-item.selected strong')?.textContent).toBe(
      'Art. 1 - Posti a concorso',
    );
    // Il blocco segue la sezione: l'editor resta collegato al nome nuovo.
    expect(root.querySelector('[data-section-text="Art. 1 - Posti a concorso"]')).toBeTruthy();

    const request = salva(root, http);
    expect(request.request.body.sezioni.map((s: { codice: string }) => s.codice)).toEqual([
      'intro',
      'Art. 1 - Posti a concorso',
    ]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('offers the builder-editor topbar actions and runs the version transition', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    expect(root.textContent).toContain('Anteprima');
    expect(root.textContent).toContain('Esporta .docx');
    // L'export .docx resta disabilitato finche' il backend non lo espone: il
    // bottone dichiara il motivo invece di fingere una funzione che non c'e'.
    expect((root.querySelector('[data-export-docx]') as HTMLButtonElement).disabled).toBe(true);
    const dialog = root.querySelector('[data-confirm-transition]') as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    const action = root.querySelector('[data-version-action]') as HTMLButtonElement;
    expect(action.textContent).toContain('Invia in revisione');
    action.click();
    fixture.detectChanges();
    expect(dialog.showModal).toHaveBeenCalled();
    expect(dialog.textContent).toContain('non sono piu');

    const conferma = root.querySelector('[data-confirm-transition-submit]') as HTMLButtonElement;
    expect(conferma.disabled).toBe(false);
    conferma.click();

    const request = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/invia-revisione');
    expect(request.request.method).toBe('POST');
    request.flush({ ...dettaglio.versioni[0], stato: 'IN_REVISIONE' });
    http.expectOne('/api/v1/builder/modelli/model').flush({
      ...dettaglio,
      versioni: [{ ...dettaglio.versioni[0], stato: 'IN_REVISIONE' }],
    });
    flushSections(http, {
      ...sezioniResponse,
      stato_versione: 'IN_REVISIONE',
      modificabile: false,
    });
    flushDerivationConfig(http);
    verifica(http);
  });

  it('saves the whole section set after reordering and removing sections', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    (
      root.querySelector('[data-move-section="dettagli"][data-direction="up"]') as HTMLButtonElement
    ).click();
    fixture.detectChanges();
    (root.querySelector('[data-remove-section="intro"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (root.querySelector('[data-save-sections]') as HTMLButtonElement).click();

    const request = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.sezioni).toEqual([
      {
        codice: 'dettagli',
        ordine: 0,
        contenuto: [{ ...sezioniResponse.sezioni[1].contenuto[0], elementi: [] }],
      },
    ]);
    request.flush({
      ...sezioniResponse,
      sezioni: [{ ...sezioniResponse.sezioni[1], ordine: 0 }],
      documento: { ...sezioniResponse.documento, blocchi: [sezioniResponse.documento.blocchi[1]] },
    });
    verifica(http);
  });

  it('inserts placeholders from the version fields list before saving', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush({
      ...dettaglio,
      versioni: [{ ...dettaglio.versioni[0], campi: dettaglio.versioni[0].campi }],
    });
    flushSections(http, {
      ...sezioniResponse,
      sezioni: [],
      documento: { blocchi: [], placeholder_usati: [] },
    });
    flushDerivationConfig(http);
    fixture.detectChanges();

    (root.querySelector('[data-add-section]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(root.querySelector('[data-section-placeholder]')).toBeNull();
    const placeholder = root.querySelector(
      '.pannello [data-placeholder="titolo_it"]',
    ) as HTMLButtonElement;
    expect(placeholder).toBeTruthy();
    placeholder.click();
    fixture.detectChanges();

    expect(capoversi(fixture, 'sezione-1')).toEqual(['{{titolo_it}}']);
    (root.querySelector('[data-save-sections]') as HTMLButtonElement).click();
    const request = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
    expect(request.request.body.sezioni[0].contenuto[0].placeholder_usati).toEqual(['titolo_it']);
    request.flush({
      ...sezioniResponse,
      sezioni: request.request.body.sezioni,
      documento: {
        blocchi: request.request.body.sezioni[0].contenuto,
        placeholder_usati: ['titolo_it'],
      },
    });
    verifica(http);
  });

  it('keeps a published version readable without edit controls', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush({
      ...dettaglio,
      versioni: [{ ...dettaglio.versioni[0], stato: 'PUBBLICATO' }],
    });
    flushSections(http, { ...sezioniResponse, stato_versione: 'PUBBLICATO', modificabile: false });
    flushDerivationConfig(http);
    fixture.detectChanges();

    expect(root.querySelector('[data-document-preview]')?.textContent).toContain('Introduzione');
    expect(root.querySelector('[data-add-section]')).toBeNull();
    expect(root.querySelector('[data-save-sections]')).toBeNull();
    expect(root.textContent).toContain('sola lettura');
    verifica(http);
  });

  it('shows backend placeholder violations when saving fails', () => {
    const { fixture, http, root } = caricaBozza();
    cursoreInFondo(fixture, 'intro');
    digita(fixture, 'intro', ' {{campo_non_dichiarato}}');
    (root.querySelector('[data-save-sections]') as HTMLButtonElement).click();
    http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni').flush(
      {
        codice: 'PLACEHOLDER_NON_VALIDO',
        messaggio: 'Il documento non e coerente',
        dettagli: [{ violazione: "placeholder 'campo_non_dichiarato' non dichiarato" }],
      },
      { status: 400, statusText: 'Bad Request' },
    );
    fixture.detectChanges();

    expect(root.querySelector('[role=alert]')?.textContent).toContain(
      "placeholder 'campo_non_dichiarato'",
    );
    verifica(http);
  });

  it('012 US1: applies bold to the selected words and saves fragments, never markup', () => {
    const { fixture, http, root } = caricaBozza();
    selezionaTesto(fixture, 'intro', 'Introduzione');
    (root.querySelector('[data-emphasis="grassetto"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    expect(editor.querySelector('strong')?.textContent).toBe('Introduzione');
    const request = salva(root, http);
    const blocco = request.request.body.sezioni[0].contenuto[0];
    expect(blocco.frammenti).toEqual([
      { testo: 'Introduzione', grassetto: true },
      { testo: ' {{titolo_it}}' },
    ]);
    expect(JSON.stringify(request.request.body)).not.toContain('<strong>');
    expect(blocco.placeholder_usati).toEqual(['titolo_it']);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T077: one selection across paragraphs, list and heading of a section takes the bold', () => {
    const { fixture, http, root } = caricaBozzaCon([
      { ...paragrafo('t', [{ testo: 'Art. 1 - Indizione' }]), tipo: 'TITOLO' },
      paragrafo('p1', [{ testo: 'VISTO il decreto;' }], 1),
      paragrafo('p2', [{ testo: 'CONSIDERATO che ' }, { testo: 'serve', corsivo: true }], 2),
      { ...elenco('e', ['un posto a Roma']), ordine: 3 },
    ]);
    // Dal titolo fino a meta' della voce: quattro blocchi in una selezione sola.
    selezionaTesto(fixture, 'art', 'Art. 1', 'un posto');
    (root.querySelector('[data-emphasis="grassetto"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const request = salva(root, http);
    const [titolo, p1, p2, lista] = request.request.body.sezioni[0].contenuto;
    expect(titolo.frammenti).toEqual([{ testo: 'Art. 1 - Indizione', grassetto: true }]);
    expect(p1.frammenti).toEqual([{ testo: 'VISTO il decreto;', grassetto: true }]);
    expect(p2.frammenti).toEqual([
      { testo: 'CONSIDERATO che ', grassetto: true },
      { testo: 'serve', grassetto: true, corsivo: true },
    ]);
    expect(lista.elementi[0].frammenti).toEqual([
      { testo: 'un posto', grassetto: true },
      { testo: ' a Roma' },
    ]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T077: the style menu applies to every selected paragraph', () => {
    const { fixture, http, root } = caricaBozzaCon([
      paragrafo('p1', [{ testo: 'primo requisito' }]),
      paragrafo('p2', [{ testo: 'secondo requisito' }], 1),
    ]);
    selezionaTesto(fixture, 'art', 'primo', 'secondo');
    scegliStile(root, 'ELENCO_NUMERICO');
    fixture.detectChanges();

    expect(marcatori(root)).toEqual(['1.', '2.']);
    const request = salva(root, http);
    const blocchi = request.request.body.sezioni[0].contenuto;
    expect(blocchi).toHaveLength(1);
    expect(
      blocchi[0].elementi.map((e: { frammenti: { testo: string }[] }) => e.frammenti[0].testo),
    ).toEqual(['primo requisito', 'secondo requisito']);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T079: Unisci righe recomposes PDF lines into whole paragraphs', () => {
    const { fixture, http, root } = caricaBozzaCon([
      paragrafo('r0', [
        { testo: 'VISTO', grassetto: true },
        { testo: ' il D.Lgs 31 dicembre 2009, “Riordino degli Enti' },
      ]),
      paragrafo('r1', [{ testo: 'di ricerca”;' }], 1),
      paragrafo('r2', [{ testo: 'VISTO lo Statuto del CNR, n. 93 prot.' }], 2),
      paragrafo('r3', [{ testo: '0051080/2018 del 19/07/2018;' }], 3),
    ]);
    selezionaTesto(fixture, 'art', 'VISTO', '19/07/2018;');
    (root.querySelector('[data-join-lines]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(capoversi(fixture, 'art')).toEqual([
      'VISTO il D.Lgs 31 dicembre 2009, “Riordino degli Enti di ricerca”;',
      'VISTO lo Statuto del CNR, n. 93 prot. 0051080/2018 del 19/07/2018;',
    ]);
    const request = salva(root, http);
    expect(request.request.body.sezioni[0].contenuto[0].frammenti[0]).toEqual({
      testo: 'VISTO',
      grassetto: true,
    });
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T080-T081: shows where each PDF page starts and measures again what is typed, before saving', async () => {
    const { fixture, http, root } = caricaBozzaCon([
      paragrafo('p0', [{ testo: 'primo capoverso' }]),
      paragrafo('p1', [{ testo: 'secondo capoverso' }], 1),
    ]);
    const URL_PAGINE = '/api/v1/builder/modelli/model/versioni/v2/impaginazione';
    const pausa = () => new Promise((fatto) => setTimeout(fatto, 450));
    await pausa();
    const prima = http.expectOne(URL_PAGINE);
    expect(prima.request.method).toBe('POST');
    expect(prima.request.body.sezioni[0].codice).toBe('art');
    prima.flush({
      pagine: 2,
      inizi_pagina: [
        {
          pagina: 2,
          sezione: 'art',
          blocco: 'p1',
          voce: null,
          riga: 0,
          spazio_libero_mm: 4,
          margine_basso_mm: 22,
          margine_alto_mm: 41,
        },
      ],
    });
    fixture.detectChanges();
    fixture.detectChanges();

    expect(root.querySelector('[data-pagine]')?.textContent?.trim()).toBe('2 pagine nel PDF');
    // Fra i due fogli: lo spazio nel testo, prima del capoverso che apre la
    // pagina, e sopra di lui la fascia con il numero della pagina.
    const confini = root.querySelectorAll('[data-fra-fogli] [data-fine-pagina]');
    const spazio = root.querySelector('[data-section-text="art"] > [data-salto-pagina="2"]');
    expect(spazio?.nextElementSibling?.getAttribute('data-block-id')).toBe('p1');
    expect(Array.from(confini).map((c) => c.textContent?.trim())).toEqual(['Pagina 2']);

    // Si scrive, senza salvare: il renderer misura il testo sullo schermo.
    cursoreInFondo(fixture, 'art');
    digita(fixture, 'art', ' allungato');
    await pausa();
    const dopo = http.expectOne(URL_PAGINE);
    expect(dopo.request.body.sezioni[0].contenuto[1].frammenti).toEqual([
      { testo: 'secondo capoverso allungato' },
    ]);
    dopo.flush({ pagine: 1, inizi_pagina: [] });
    fixture.detectChanges();
    fixture.detectChanges();
    expect(root.querySelector('[data-fine-pagina]')).toBeNull();
    expect(root.querySelector('[data-pagine]')?.textContent?.trim()).toBe('1 pagina nel PDF');
    verifica(http);
  });

  it('012 US1: Ctrl+I toggles italic on the selection like a word processor', () => {
    const { fixture, http, root } = caricaBozza();
    selezionaTesto(fixture, 'intro', 'Intro');
    const tasto = premi(fixture, 'intro', 'i', { ctrlKey: true });
    expect(tasto.defaultPrevented).toBe(true);
    expect(root.querySelector('[data-section-text="intro"] em')?.textContent).toBe('Intro');
    verifica(http);
  });

  it('012 US1: pasting from Word gives visible paragraphs and a computed list', () => {
    const { fixture, http, root } = caricaBozza();
    // Una riga nuova dopo il testo esistente, e li' si incolla.
    cursoreInFondo(fixture, 'intro');
    premi(fixture, 'intro', 'Enter');
    incollaIn(
      apriEditor(fixture),
      `<p class=MsoNormal><b>VISTO</b> il decreto;</p>
       <p class=MsoListParagraph style='mso-list:l0 level1 lfo1'><span style='mso-list:Ignore'>1.<span>&nbsp; </span></span>Sono indetti:</p>
       <p class=MsoListParagraph style='mso-list:l0 level2 lfo1'><span style='mso-list:Ignore'>a)<span>&nbsp; </span></span>un posto a Roma</p>`,
    );
    fixture.detectChanges();

    expect(capoversi(fixture)).toEqual([
      'Introduzione {{titolo_it}}',
      'VISTO il decreto;',
      // Il marcatore di Word non resta nel testo: si sommerebbe a quello calcolato.
      'Sono indetti:',
      'un posto a Roma',
    ]);
    expect(marcatori(root)).toEqual(['1.', 'a)']);

    const request = salva(root, http);
    const blocchi = request.request.body.sezioni[0].contenuto;
    expect(blocchi.map((b: { tipo: string }) => b.tipo)).toEqual([
      'PARAGRAFO',
      'PARAGRAFO',
      'ELENCO',
    ]);
    expect(blocchi[1].frammenti).toEqual([
      { testo: 'VISTO', grassetto: true },
      { testo: ' il decreto;' },
    ]);
    expect(blocchi[2].elementi).toEqual([
      { livello: 0, marcatore: 'NUMERICO', frammenti: [{ testo: 'Sono indetti:' }] },
      { livello: 1, marcatore: 'ALFABETICO', frammenti: [{ testo: 'un posto a Roma' }] },
    ]);
    expect(new Set(blocchi.map((b: { id: string }) => b.id)).size).toBe(3);
    expect(blocchi.map((b: { ordine: number }) => b.ordine)).toEqual([0, 1, 2]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012: the list button turns the paragraph into a list without writing numbers in the text', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(fixture, 'dettagli');
    (root.querySelector('[data-list="NUMERICO"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(marcatori(root)).toEqual(['1.']);
    expect(capoversi(fixture, 'dettagli')).toEqual(['Posti disponibili {{numero_posti}}']);
    const request = salva(root, http);
    const blocco = request.request.body.sezioni[1].contenuto[0];
    expect(blocco.tipo).toBe('ELENCO');
    expect(blocco.frammenti).toEqual([]);
    expect(blocco.placeholder_usati).toEqual(['numero_posti']);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T029: a published document restarts list numbering at every section, like the PDF', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    const elenco = (id: string, ordine: number, testi: string[]) => ({
      id,
      tipo: 'ELENCO',
      frammenti: [],
      elementi: testi.map((testo) => ({
        livello: 0,
        marcatore: 'NUMERICO',
        frammenti: [{ testo }],
      })),
      posizionamento: 'BODY',
      ordine,
      stile: null,
      placeholder_usati: [],
    });
    const art1 = [elenco('a1', 0, ['primo', 'secondo'])];
    const art2 = [elenco('a2', 0, ['terzo'])];
    flushSections(http, {
      ...sezioniResponse,
      modificabile: false,
      sezioni: [
        { codice: 'art-1', ordine: 0, contenuto: art1 },
        { codice: 'art-2', ordine: 1, contenuto: art2 },
      ],
      documento: {
        blocchi: [
          { ...art1[0], ordine: 0 },
          { ...art2[0], ordine: 1 },
        ],
        placeholder_usati: [],
      },
    } as unknown as typeof sezioniResponse);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const marcatori = Array.from(root.querySelectorAll('.item-marker')).map((m) => m.textContent);
    expect(marcatori).toEqual(['1.', '2.', '1.']);
    verifica(http);
  });

  it('012 T059: the style menu turns the current line into a centred article heading', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(fixture);
    const menu = root.querySelector('[data-style-select]') as HTMLSelectElement;
    expect(menu.value).toBe('PARAGRAFO');
    scegliStile(root, 'TITOLO');
    fixture.detectChanges();

    const titolo = root.querySelector('[data-block-type="TITOLO"]') as HTMLElement;
    expect(titolo.classList).toContain('block-titolo');
    expect(titolo.style.textAlign).toBe('center');
    expect(titolo.textContent).toBe('Introduzione {{titolo_it}}');
    expect(menu.value).toBe('TITOLO');
    const request = salva(root, http);
    const blocchi = request.request.body.sezioni[0].contenuto;
    expect(blocchi.length).toBe(1);
    expect(blocchi[0]).toMatchObject({
      tipo: 'TITOLO',
      posizionamento: 'BODY',
      allineamento: 'CENTRO',
    });
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T059: turning a paragraph into a signature moves it where the format allows a signature', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(fixture);
    scegliStile(root, 'FIRMA');
    fixture.detectChanges();

    const request = salva(root, http);
    const blocco = request.request.body.sezioni[0].contenuto[0];
    expect(blocco).toMatchObject({ tipo: 'FIRMA', posizionamento: 'BOTTOM_RIGHT' });
    expect(blocco.frammenti).toEqual([{ testo: 'Introduzione {{titolo_it}}' }]);
    expect((root.querySelector('[data-block-type="FIRMA"]') as HTMLElement).style.textAlign).toBe(
      'right',
    );
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T030: justifies the selected block from the toolbar', () => {
    const { fixture, http, root } = caricaBozza();
    const editor = apriEditor(fixture);
    const giustifica = root.querySelector('[data-align="GIUSTIFICATO"]') as HTMLButtonElement;
    expect(giustifica.getAttribute('aria-pressed')).toBe('false');
    giustifica.click();
    fixture.detectChanges();

    expect((editor.firstElementChild as HTMLElement).style.textAlign).toBe('justify');
    expect(giustifica.getAttribute('aria-pressed')).toBe('true');
    const request = salva(root, http);
    expect(request.request.body.sezioni[0].contenuto[0].allineamento).toBe('GIUSTIFICATO');
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012: Enter opens a new paragraph at the caret and Backspace at its start joins it back', () => {
    const { fixture, http, root } = caricaBozza();
    cursoreDopo(fixture, 'intro', 'Introduzione');
    premi(fixture, 'intro', 'Enter');
    expect(capoversi(fixture)).toEqual(['Introduzione', ' {{titolo_it}}']);

    // Il cursore e' all'inizio del capoverso nuovo.
    premi(fixture, 'intro', 'Backspace');
    expect(capoversi(fixture)).toEqual(['Introduzione {{titolo_it}}']);
    const request = salva(root, http);
    expect(request.request.body.sezioni[0].contenuto).toHaveLength(1);
    expect(request.request.body.sezioni[0].contenuto[0].frammenti).toEqual([
      { testo: 'Introduzione {{titolo_it}}' },
    ]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T060: a page break goes after the text with a new line, and Delete removes it', () => {
    const { fixture, http, root } = caricaBozza();
    const editor = apriEditor(fixture);
    (root.querySelector('[data-insert-block="INTERRUZIONE_PAGINA"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    // Come in Word: dopo l'interruzione c'e' una riga vuota, col cursore, sulla pagina nuova.
    expect(capoversi(fixture)).toEqual([
      'Introduzione {{titolo_it}}',
      'Interruzione di pagina',
      '',
    ]);
    const vista = vistaDi(fixture, 'intro');
    expect(vista.state.selection.$from.parent.content.size).toBe(0);
    expect(document.activeElement).toBe(editor);

    // Un clic sull'interruzione la seleziona; Canc la elimina.
    const pos = vista.state.doc.firstChild!.nodeSize;
    vista.dispatch(vista.state.tr.setSelection(NodeSelection.create(vista.state.doc, pos)));
    premi(fixture, 'intro', 'Delete');

    expect(root.querySelector('.page-break')).toBeNull();
    const request = salva(root, http);
    expect(request.request.body.sezioni[0].contenuto.map((b: { tipo: string }) => b.tipo)).toEqual([
      'PARAGRAFO',
      'PARAGRAFO',
    ]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T060: on an empty line the page break goes before it, leaving the line on the new page', () => {
    const { fixture, http, root } = caricaBozza();
    (root.querySelector('[data-add-section-inline]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (root.querySelector('[data-insert-block="INTERRUZIONE_PAGINA"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const request = salva(root, http);
    expect(request.request.body.sezioni[2].contenuto.map((b: { tipo: string }) => b.tipo)).toEqual([
      'INTERRUZIONE_PAGINA',
      'PARAGRAFO',
    ]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012 T029: list numbering restarts after an article heading, as in the PDF', () => {
    const { http, root } = caricaBozzaCon([
      elenco('e1', ['primo comma', 'secondo comma']),
      {
        ...elenco('t', []),
        tipo: 'TITOLO',
        frammenti: [{ testo: 'Art. 2' }],
        elementi: [],
        ordine: 1,
      },
      { ...elenco('e2', ['comma dell articolo 2']), ordine: 2 },
    ]);
    expect(marcatori(root)).toEqual(['1.', '2.', '1.']);
    verifica(http);
  });

  it('012: after an autosave the next command still applies to the block being edited', () => {
    const { fixture, http, root } = caricaBozza();
    const editor = apriEditor(fixture, 'dettagli');
    cursoreDopo(fixture, 'dettagli', 'Posti disponibili');
    digita(fixture, 'dettagli', ':');
    editor.dispatchEvent(new FocusEvent('blur'));
    const autosave = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
    autosave.flush({ ...sezioniResponse, sezioni: autosave.request.body.sezioni });
    fixture.detectChanges();

    scegliStile(root, 'TITOLO');
    fixture.detectChanges();

    const request = salva(root, http);
    const [intro, dettagli] = request.request.body.sezioni;
    expect(intro.contenuto[0].tipo).toBe('PARAGRAFO');
    expect(dettagli.contenuto[0].tipo).toBe('TITOLO');
    expect(dettagli.contenuto[0].frammenti).toEqual([
      { testo: 'Posti disponibili: {{numero_posti}}' },
    ]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    verifica(http);
  });

  it('012: a numbered list after a bulleted one starts again from 1, like Word', () => {
    const { http, root } = caricaBozzaCon([
      elenco('p', ['punto'], 'PUNTATO'),
      { ...elenco('n', ['comma']), ordine: 1 },
    ]);
    expect(marcatori(root)).toEqual(['●', '1.']);
    expect(root.querySelector('[data-marcatore]')?.getAttribute('data-marcatore-tipo')).toBe(
      'PUNTATO',
    );
    verifica(http);
  });

  describe('012 US4: anteprima della bozza', () => {
    const URL_ANTEPRIMA = '/api/v1/builder/modelli/model/versioni/v2/anteprima';
    let creati: string[];
    let revocati: string[];
    const originali = { crea: URL.createObjectURL, revoca: URL.revokeObjectURL };

    afterEach(() => {
      URL.createObjectURL = originali.crea;
      URL.revokeObjectURL = originali.revoca;
    });

    beforeEach(() => {
      creati = [];
      revocati = [];
      URL.createObjectURL = () => {
        creati.push(`blob:anteprima-${creati.length}`);
        return creati[creati.length - 1];
      };
      URL.revokeObjectURL = (url: string) => revocati.push(url);
      // jsdom non disegna dialog modali: basta che si apra e si chiuda.
      HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
        this.open = true;
      };
    });

    it('shows the PDF of the saved draft in the preview dialog', () => {
      const { fixture, http, root } = caricaBozza();
      (root.querySelector('[data-preview-open]') as HTMLButtonElement).click();

      const richiesta = http.expectOne(URL_ANTEPRIMA);
      expect(richiesta.request.method).toBe('POST');
      expect(richiesta.request.responseType).toBe('blob');
      richiesta.flush(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
      fixture.detectChanges();

      const cornice = root.querySelector('[data-preview-frame]') as HTMLIFrameElement;
      expect(cornice.getAttribute('src')).toBe('blob:anteprima-0');
      expect(root.querySelector('[data-preview-dialog] a[download]')?.getAttribute('href')).toBe(
        'blob:anteprima-0',
      );
      verifica(http);
    });

    it('saves unsaved edits first, so the preview shows what is on screen', () => {
      const { fixture, http, root } = caricaBozza();
      cursoreInFondo(fixture, 'intro');
      digita(fixture, 'intro', ' appena scritto');
      (root.querySelector('[data-preview-open]') as HTMLButtonElement).click();

      // Nessuna anteprima prima che il salvataggio sia concluso.
      const salvataggio = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
      http.expectNone(URL_ANTEPRIMA);
      salvataggio.flush({ ...sezioniResponse, sezioni: salvataggio.request.body.sezioni });
      http.expectOne(URL_ANTEPRIMA).flush(new Blob(['%PDF-1.4']));
      fixture.detectChanges();

      expect(root.querySelector('[data-preview-frame]')).toBeTruthy();
      verifica(http);
    });

    it('reads the service error out of the binary response instead of a generic failure', async () => {
      const { fixture, http, root } = caricaBozza();
      (root.querySelector('[data-preview-open]') as HTMLButtonElement).click();
      http.expectOne(URL_ANTEPRIMA).flush(
        new Blob(
          [
            JSON.stringify({
              codice: 'MODELLO_DOCUMENTALE_NON_VALIDO',
              messaggio: 'Struttura del modello documentale non valida',
              dettagli: [{ violazione: 'blocco b1: il testo contiene markup, non ammesso' }],
            }),
          ],
          { type: 'application/json' },
        ),
        { status: 422, statusText: 'Unprocessable Entity' },
      );
      await fixture.whenStable();
      fixture.detectChanges();

      const errore = root.querySelector('[data-preview-error]')?.textContent ?? '';
      expect(errore).toContain('Struttura del modello documentale non valida');
      expect(errore).toContain('il testo contiene markup');
      verifica(http);
    });

    it('frees the PDF from memory when the dialog closes', () => {
      const { fixture, http, root } = caricaBozza();
      (root.querySelector('[data-preview-open]') as HTMLButtonElement).click();
      http.expectOne(URL_ANTEPRIMA).flush(new Blob(['%PDF-1.4']));
      fixture.detectChanges();
      root.querySelector('[data-preview-dialog]')!.dispatchEvent(new Event('close'));
      fixture.detectChanges();

      expect(revocati).toEqual(['blob:anteprima-0']);
      expect(root.querySelector('[data-preview-frame]')).toBeNull();
      verifica(http);
    });
  });

  describe('012 T064: comando / per i segnaposto', () => {
    function preparaEditor(frammenti: object[] = [{ testo: 'Posti:' }]) {
      const contesto = caricaBozzaCon([paragrafo('p', frammenti)]);
      cursoreInFondo(contesto.fixture, 'art');
      return contesto;
    }

    it('opens on a / that starts a word, filters while typing and inserts with Enter', () => {
      const { fixture, http, root } = preparaEditor();
      digita(fixture, 'art', ' /');
      expect(root.querySelector('[data-slash-menu]')).toBeTruthy();
      expect(root.querySelectorAll('[data-slash-item]').length).toBeGreaterThan(1);

      digita(fixture, 'art', 'num');
      const voci = Array.from(root.querySelectorAll('[data-slash-item]')).map((v) =>
        v.getAttribute('data-slash-item'),
      );
      expect(voci).toEqual(['numero_posti']);

      expect(premi(fixture, 'art', 'Enter').defaultPrevented).toBe(true);
      expect(capoversi(fixture, 'art')).toEqual(['Posti: {{numero_posti}}']);
      expect(root.querySelector('[data-slash-menu]')).toBeNull();
      const request = salva(root, http);
      expect(request.request.body.sezioni[0].contenuto[0].placeholder_usati).toEqual([
        'numero_posti',
      ]);
      request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
      verifica(http);
    });

    it('does not open inside a word: "e/o" and dates are text', () => {
      const { fixture, http, root } = preparaEditor();
      digita(fixture, 'art', ' e/o 01/10');
      expect(root.querySelector('[data-slash-menu]')).toBeNull();
      expect(capoversi(fixture, 'art')).toEqual(['Posti: e/o 01/10']);
      verifica(http);
    });

    it('Escape closes the menu and keeps the / as typed; a space closes it too', () => {
      const { fixture, http, root } = preparaEditor();
      digita(fixture, 'art', ' /');
      expect(premi(fixture, 'art', 'Escape').defaultPrevented).toBe(true);
      expect(root.querySelector('[data-slash-menu]')).toBeNull();
      expect(capoversi(fixture, 'art')).toEqual(['Posti: /']);

      digita(fixture, 'art', ' /x ');
      expect(root.querySelector('[data-slash-menu]')).toBeNull();
      expect(capoversi(fixture, 'art')).toEqual(['Posti: / /x ']);
      verifica(http);
    });

    it('arrows move the choice and a click inserts it', () => {
      const { fixture, http, root } = preparaEditor();
      digita(fixture, 'art', ' /');
      premi(fixture, 'art', 'ArrowDown');
      const attiva = root.querySelector('[data-slash-item][aria-selected="true"]');
      const seconda = root.querySelectorAll('[data-slash-item]')[1];
      expect(attiva).toBe(seconda);

      const codice = seconda.getAttribute('data-slash-item');
      seconda.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
      fixture.detectChanges();
      expect(capoversi(fixture, 'art')).toEqual([`Posti: {{${codice}}}`]);
      verifica(http);
    });

    it('the placeholder takes the emphasis of the text it is typed into (FR-005)', () => {
      const { fixture, http, root } = preparaEditor([{ testo: 'Posti:', grassetto: true }]);
      digita(fixture, 'art', ' /num');
      premi(fixture, 'art', 'Enter');

      expect(root.querySelector('[data-section-text="art"] strong')?.textContent).toBe(
        'Posti: {{numero_posti}}',
      );
      verifica(http);
    });
  });

  describe('012 T050: collegamenti dall editor', () => {
    function apriBarra(root: HTMLElement, fixture: { detectChanges: () => void }) {
      (root.querySelector('[data-link-open]') as HTMLButtonElement).click();
      fixture.detectChanges();
      return root.querySelector('[data-link-input]') as HTMLInputElement | null;
    }

    it('links the selected words and saves the address on the fragment', () => {
      const { fixture, http, root } = caricaBozza();
      const editor = apriEditor(fixture);
      selezionaTesto(fixture, 'intro', 'Introduzione');
      const campo = apriBarra(root, fixture)!;
      campo.value = 'www.cnr.it';
      (root.querySelector('[data-link-apply]') as HTMLButtonElement).click();
      fixture.detectChanges();

      expect(editor.querySelector('a')?.getAttribute('href')).toBe('https://www.cnr.it');
      expect(root.querySelector('[data-link-bar]')).toBeNull();
      const request = salva(root, http);
      expect(request.request.body.sezioni[0].contenuto[0].frammenti).toEqual([
        { testo: 'Introduzione', collegamento: 'https://www.cnr.it' },
        { testo: ' {{titolo_it}}' },
      ]);
      request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
      verifica(http);
    });

    it('T051: refuses a javascript: address and leaves the text untouched', () => {
      const { fixture, http, root } = caricaBozza();
      const editor = apriEditor(fixture);
      selezionaTesto(fixture, 'intro', 'Intro');
      const campo = apriBarra(root, fixture)!;
      campo.value = 'javascript:alert(1)';
      campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
      fixture.detectChanges();

      expect(root.querySelector('[data-link-error]')?.textContent).toContain('non valido');
      expect(editor.querySelector('a')).toBeNull();
      verifica(http);
    });

    it('asks to select the text first instead of linking nothing', () => {
      const { fixture, http, root } = caricaBozza();
      cursoreDopo(fixture, 'intro', 'Int');
      expect(apriBarra(root, fixture)).toBeNull();
      expect(root.querySelector('[data-link-error]')?.textContent).toContain('Seleziona prima');
      verifica(http);
    });
  });

  describe('annulla e ripeti (riscontro del 2026-10-02)', () => {
    it('undoes a burst of typing in one step and redoes it', () => {
      const { fixture, http } = caricaBozza();
      cursoreInFondo(fixture, 'intro');
      digita(fixture, 'intro', ' e altro ancora');

      expect(premi(fixture, 'intro', 'z', { ctrlKey: true }).defaultPrevented).toBe(true);
      expect(capoversi(fixture)).toEqual(['Introduzione {{titolo_it}}']);

      premi(fixture, 'intro', 'z', { ctrlKey: true, shiftKey: true });
      expect(capoversi(fixture)).toEqual(['Introduzione {{titolo_it}} e altro ancora']);
      verifica(http);
    });

    it('undoes bold applied from the toolbar, with the toolbar button too', () => {
      const { fixture, http, root } = caricaBozza();
      selezionaTesto(fixture, 'intro', 'Introduzione');
      (root.querySelector('[data-emphasis="grassetto"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
      expect(editor.querySelector('strong')).toBeTruthy();

      (root.querySelector('[data-undo]') as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(editor.querySelector('strong')).toBeNull();
      expect((root.querySelector('[data-redo]') as HTMLButtonElement).disabled).toBe(false);
      // La selezione torna dov'era: si puo' rifare subito un'altra scelta.
      const { from, to } = vistaDi(fixture, 'intro').state.selection;
      expect(vistaDi(fixture, 'intro').state.doc.textBetween(from, to)).toBe('Introduzione');
      verifica(http);
    });

    it('undoes a paragraph split by Enter, putting the text back in one block', () => {
      const { fixture, http } = caricaBozza();
      cursoreDopo(fixture, 'intro', 'Introduzione');
      premi(fixture, 'intro', 'Enter');
      expect(capoversi(fixture)).toHaveLength(2);

      premi(fixture, 'intro', 'z', { ctrlKey: true });
      expect(capoversi(fixture)).toEqual(['Introduzione {{titolo_it}}']);
      verifica(http);
    });

    it('pastes a title copied from a PDF as one block, not one per line', () => {
      const { fixture, http } = caricaBozza();
      cursoreInFondo(fixture, 'intro');
      incollaIn(
        apriEditor(fixture),
        '',
        'CONCORSO PUBBLICO PER TITOLI ED ESAMI\nDI LAVORO A TEMPO PIENO\nRICERCHE - VARIE SEDI',
      );
      fixture.detectChanges();

      expect(capoversi(fixture)).toEqual([
        'Introduzione {{titolo_it}}CONCORSO PUBBLICO PER TITOLI ED ESAMI DI LAVORO A TEMPO PIENO RICERCHE - VARIE SEDI',
      ]);
      verifica(http);
    });

    it('012 T077: a pasted text can be selected whole and set bold in one go', () => {
      const { fixture, http, root } = caricaBozza();
      cursoreInFondo(fixture, 'intro');
      premi(fixture, 'intro', 'Enter');
      incollaIn(apriEditor(fixture), '', 'Primo capoverso.\n\nSecondo capoverso.\n\nTerzo.');
      fixture.detectChanges();
      expect(capoversi(fixture)).toHaveLength(4);

      selezionaTesto(fixture, 'intro', 'Primo', 'Terzo.');
      (root.querySelector('[data-emphasis="grassetto"]') as HTMLButtonElement).click();
      fixture.detectChanges();
      const grassetti = Array.from(root.querySelectorAll('[data-section-text="intro"] strong')).map(
        (s) => s.textContent,
      );
      expect(grassetti).toEqual(['Primo capoverso.', 'Secondo capoverso.', 'Terzo.']);
      verifica(http);
    });
  });

  it('tracks unsaved changes in the topbar and autosaves when the text loses focus', () => {
    const { fixture, http, root } = caricaBozza();
    expect(root.querySelector('[data-save-state]')?.textContent).toContain(
      'Tutte le modifiche salvate',
    );
    selezionaTesto(fixture, 'intro', 'Introduzione');
    digita(fixture, 'intro', 'Introduzione riscritta');
    expect(root.querySelector('[data-save-state]')?.textContent).toContain('Modifiche non salvate');

    vistaDi(fixture, 'intro').dom.dispatchEvent(new FocusEvent('blur'));
    const request = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.sezioni[0].contenuto[0].frammenti).toEqual([
      { testo: 'Introduzione riscritta {{titolo_it}}' },
    ]);
    expect(request.request.body.sezioni[0].contenuto[0]).not.toHaveProperty('contenuto');
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    fixture.detectChanges();

    expect(root.querySelector('[data-save-state]')?.textContent).toContain(
      'Tutte le modifiche salvate',
    );
    verifica(http);
  });

  it('moving from one section to another does not autosave', () => {
    const { fixture, http } = caricaBozza();
    cursoreInFondo(fixture, 'intro');
    digita(fixture, 'intro', '!');
    const verso = vistaDi(fixture, 'dettagli').dom;
    vistaDi(fixture, 'intro').dom.dispatchEvent(new FocusEvent('blur', { relatedTarget: verso }));
    http.expectNone('/api/v1/builder/modelli/model/versioni/v2/sezioni');
    verifica(http);
  });

  it('keeps edits typed while a save is in flight instead of overwriting them', () => {
    const { fixture, http, root } = caricaBozza();
    selezionaTesto(fixture, 'intro', 'Introduzione {{titolo_it}}');
    digita(fixture, 'intro', 'Primo testo');
    (root.querySelector('[data-save-sections]') as HTMLButtonElement).click();
    const request = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');

    // L'utente continua a scrivere mentre il PUT e' ancora in volo.
    digita(fixture, 'intro', ', poi il seguito');
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    fixture.detectChanges();

    expect(capoversi(fixture)).toEqual(['Primo testo, poi il seguito']);
    expect(root.querySelector('[data-save-state]')?.textContent).toContain('Modifiche non salvate');
    verifica(http);
  });

  it('blocks the version transition while there are unsaved changes', () => {
    const { fixture, http, root } = caricaBozza();
    cursoreInFondo(fixture, 'intro');
    digita(fixture, 'intro', ' non ancora salvato');

    const dialog = root.querySelector('[data-confirm-transition]') as HTMLDialogElement;
    expect(dialog.textContent).toContain('modifiche non salvate');
    expect(
      (root.querySelector('[data-confirm-transition-submit]') as HTMLButtonElement).disabled,
    ).toBe(true);
    verifica(http);
  });

  it('lists the publication blocks for placeholders outside the version contract', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http, {
      ...sezioniResponse,
      sezioni: [
        {
          ...sezioniResponse.sezioni[0],
          contenuto: [
            {
              ...sezioniResponse.sezioni[0].contenuto[0],
              frammenti: [{ testo: 'Testo con {{campo_fantasma}}' }],
              placeholder_usati: ['campo_fantasma'],
            },
          ],
        },
      ],
    });
    flushDerivationConfig(http);
    fixture.detectChanges();

    const readiness = root.querySelector('[data-readiness]')!;
    expect(readiness.textContent).toContain('{{campo_fantasma}}');
    expect(readiness.textContent).toContain('intro');
    verifica(http);
  });

  it('shows the backend violations when the publication is refused', () => {
    const { fixture, http, root } = setup();
    const approvato = { ...dettaglio.versioni[0], stato: 'APPROVATO' };
    http.expectOne('/api/v1/builder/modelli/model').flush({ ...dettaglio, versioni: [approvato] });
    flushSections(http, {
      ...sezioniResponse,
      stato_versione: 'APPROVATO',
      modificabile: false,
    });
    flushDerivationConfig(http);
    fixture.detectChanges();

    const dialog = root.querySelector('[data-confirm-transition]') as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    expect(root.querySelector('[data-readiness]')?.textContent).toContain('Nessun blocco');
    (root.querySelector('[data-version-action]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (root.querySelector('[data-confirm-transition-submit]') as HTMLButtonElement).click();

    http.expectOne('/api/v1/builder/modelli/model/versioni/v2/pubblica').flush(
      {
        codice: 'PLACEHOLDER_NON_VALIDO',
        messaggio: 'Il documento non e coerente con il contratto dati del modello',
        dettagli: [{ violazione: "placeholder 'campo_fantasma' non dichiarato" }],
      },
      { status: 400, statusText: 'Bad Request' },
    );
    fixture.detectChanges();

    expect(root.querySelector('[data-transition-blocks]')?.textContent).toContain(
      "placeholder 'campo_fantasma' non dichiarato",
    );
    verifica(http);
  });

  it('shows a functional error instead of an empty page when the model is not readable', () => {
    const { fixture, http, root } = setup('assente');
    http
      .expectOne('/api/v1/builder/modelli/assente')
      .flush(
        { codice: 'RISORSA_NON_TROVATA', messaggio: 'Risorsa non disponibile' },
        { status: 404, statusText: 'Not Found' },
      );
    fixture.detectChanges();
    expect(root.querySelector('[role=alert]')?.textContent).toContain('Risorsa non disponibile');
    expect(root.querySelector('.campo')).toBeNull();
    verifica(http);
  });
});
