import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, provideRouter } from '@angular/router';
import { ModelloAnteprimaComponent } from './modello-anteprima.component';

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
  ): void {
    http
      .expectOne(`/api/v1/builder/modelli/${modelId}/versioni/${versionId}/sezioni`)
      .flush(response);
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
    http.verify();
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
    http.verify();
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
    http.verify();
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
    http.verify();
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
    http.verify();
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
    http.verify();
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
    http.verify();
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
    http.verify();
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
    http.verify();
  });

  it('uses the fullscreen editor controls instead of a textarea form', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    expect(root.querySelector('textarea')).toBeNull();
    const editor = root.querySelector(
      '[contenteditable][data-section-text="intro"]',
    ) as HTMLElement;
    expect(editor.textContent).toContain('Introduzione');
    editor.dispatchEvent(new Event('focus'));
    (
      Array.from(root.querySelectorAll('.format-toolbar button')).find((button) =>
        button.textContent?.includes('H1'),
      ) as HTMLButtonElement
    ).click();
    fixture.detectChanges();

    expect(root.querySelector('[data-section-text="intro"].style-h1')).toBeTruthy();
    http.verify();
  });

  it('renders the 2b document frame with header, signature and inline add command', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    expect(root.querySelector('.document-header')?.textContent).toContain('Comune di');
    expect(root.querySelector('.document-header')?.textContent).toContain('Det. n.');
    expect(root.querySelector('.document-signature')?.textContent).toContain(
      'Il Responsabile del procedimento',
    );
    expect(root.querySelector('[data-add-section-inline]')?.textContent).toContain(
      'Inserisci una nuova sezione di testo',
    );
    http.verify();
  });

  it('inserts predefined blocks from the side panel as controlled document sections', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    (
      Array.from(root.querySelectorAll('.panel-tabs button')).find((button) =>
        button.textContent?.includes('Blocchi'),
      ) as HTMLButtonElement
    ).click();
    fixture.detectChanges();
    (root.querySelector('[data-block-template="oggetto"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(root.querySelector('[data-section-text="oggetto"]')?.textContent).toContain(
      'Oggetto: {{titolo_it}}',
    );
    expect(root.querySelector('[data-section-text="oggetto"].style-h1')).toBeTruthy();

    (root.querySelector('[data-save-sections]') as HTMLButtonElement).click();
    const request = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
    const aggiunta = request.request.body.sezioni.find(
      (sezione: { codice: string }) => sezione.codice === 'oggetto',
    );
    expect(aggiunta.contenuto[0].stile).toBe('H1');
    request.flush({
      ...sezioniResponse,
      sezioni: request.request.body.sezioni,
      documento: {
        ...sezioniResponse.documento,
        blocchi: request.request.body.sezioni[2].contenuto,
      },
    });
    http.verify();
  });

  it('edits the selected section style from the properties tab', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    (
      Array.from(root.querySelectorAll('.panel-tabs button')).find((button) =>
        button.textContent?.includes('Proprietà'),
      ) as HTMLButtonElement
    ).click();
    fixture.detectChanges();
    const select = root.querySelector('#proprieta-stile') as HTMLSelectElement;
    select.value = 'H2';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(root.querySelector('[data-section-text="intro"].style-h2')).toBeTruthy();
    http.verify();
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
    http.verify();
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
    http.verify();
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

    expect(root.querySelector('[data-section-text="sezione-1"]')?.textContent).toBe(
      '{{titolo_it}}',
    );
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
    http.verify();
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
    http.verify();
  });

  it('shows backend placeholder violations when saving fails', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    editor.textContent = 'Testo con {{campo_non_dichiarato}}';
    editor.dispatchEvent(new Event('input'));
    fixture.detectChanges();
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
    http.verify();
  });

  function seleziona(nodo: Node, da: number, a: number): void {
    const range = document.createRange();
    range.setStart(nodo, da);
    range.setEnd(nodo, a);
    const selezione = document.getSelection()!;
    selezione.removeAllRanges();
    selezione.addRange(range);
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

  it('012 US1: applies bold to the selected words and saves fragments, never markup', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    editor.focus();
    editor.dispatchEvent(new Event('focus'));
    seleziona(editor.firstChild!, 0, 'Introduzione'.length);
    (root.querySelector('[data-emphasis="grassetto"]') as HTMLButtonElement).click();
    fixture.detectChanges();

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
    http.verify();
  });

  it('012 US1: Ctrl+I toggles italic on the selection like a word processor', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    editor.focus();
    editor.dispatchEvent(new Event('focus'));
    seleziona(editor.firstChild!, 0, 5);
    const tasto = new KeyboardEvent('keydown', { key: 'i', ctrlKey: true, cancelable: true });
    editor.dispatchEvent(tasto);
    expect(tasto.defaultPrevented).toBe(true);
    expect(editor.querySelector('em')?.textContent).toBe('Intro');
    http.verify();
  });

  it('012 US1: pasting from Word splits the paragraph into visible blocks and a computed list', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    editor.focus();
    editor.dispatchEvent(new Event('focus'));
    // Il cursore alla fine del testo esistente.
    seleziona(editor.firstChild!, editor.textContent!.length, editor.textContent!.length);
    incollaIn(
      editor,
      `<p class=MsoNormal><b>VISTO</b> il decreto;</p>
       <p class=MsoListParagraph style='mso-list:l0 level1 lfo1'><span style='mso-list:Ignore'>1.<span>&nbsp; </span></span>Sono indetti:</p>
       <p class=MsoListParagraph style='mso-list:l0 level2 lfo1'><span style='mso-list:Ignore'>a)<span>&nbsp; </span></span>un posto a Roma</p>`,
    );
    fixture.detectChanges();

    const editori = root.querySelectorAll('[data-section-text="intro"]');
    expect(editori.length).toBe(4);
    const marcatori = Array.from(root.querySelectorAll('.item-marker')).map((m) => m.textContent);
    expect(marcatori).toEqual(['1.', 'a)']);
    // Il marcatore di Word non resta nel testo: si sommerebbe a quello calcolato.
    expect(editori[2].textContent).toBe('Sono indetti:');

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
    http.verify();
  });

  it('012: the list button turns the paragraph into a list without writing numbers in the text', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="dettagli"]') as HTMLElement;
    editor.focus();
    editor.dispatchEvent(new Event('focus'));
    (root.querySelector('[data-list="NUMERICO"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(root.querySelector('.item-marker')?.textContent).toBe('1.');
    expect(root.querySelector('[data-section-text="dettagli"]')?.textContent).toBe(
      'Posti disponibili {{numero_posti}}',
    );
    const request = salva(root, http);
    const blocco = request.request.body.sezioni[1].contenuto[0];
    expect(blocco.tipo).toBe('ELENCO');
    expect(blocco.frammenti).toEqual([]);
    expect(blocco.placeholder_usati).toEqual(['numero_posti']);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    http.verify();
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
    http.verify();
  });

  function apriEditor(root: HTMLElement, sezione = 'intro'): HTMLElement {
    const editor = root.querySelector(`[data-section-text="${sezione}"]`) as HTMLElement;
    editor.focus();
    editor.dispatchEvent(new Event('focus'));
    return editor;
  }

  function apriPannello(root: HTMLElement, nome: string): void {
    (
      Array.from(root.querySelectorAll('.panel-tabs button')).find((button) =>
        button.textContent?.includes(nome),
      ) as HTMLButtonElement
    ).click();
  }

  function caricaBozza() {
    const contesto = setup();
    contesto.http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(contesto.http);
    flushDerivationConfig(contesto.http);
    contesto.fixture.detectChanges();
    return contesto;
  }

  it('012 T027: inserts a centred article heading after the selected block', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(root);
    apriPannello(root, 'Blocchi');
    fixture.detectChanges();
    (root.querySelector('[data-insert-block="TITOLO"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const titolo = root.querySelector('[data-block-type="TITOLO"]') as HTMLElement;
    expect(titolo.classList).toContain('block-titolo');
    expect(titolo.style.textAlign).toBe('center');
    const request = salva(root, http);
    const blocchi = request.request.body.sezioni[0].contenuto;
    expect(blocchi.map((b: { tipo: string }) => b.tipo)).toEqual(['PARAGRAFO', 'TITOLO']);
    expect(blocchi[1]).toMatchObject({ posizionamento: 'BODY', allineamento: 'CENTRO', ordine: 1 });
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    http.verify();
  });

  it('012 T027: turning a paragraph into a signature moves it where the format allows a signature', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(root);
    apriPannello(root, 'Proprietà');
    fixture.detectChanges();
    const select = root.querySelector('[data-block-type-select]') as HTMLSelectElement;
    select.value = 'FIRMA';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    const request = salva(root, http);
    const blocco = request.request.body.sezioni[0].contenuto[0];
    expect(blocco).toMatchObject({ tipo: 'FIRMA', posizionamento: 'BOTTOM_RIGHT' });
    expect(blocco.frammenti).toEqual([{ testo: 'Introduzione {{titolo_it}}' }]);
    expect((root.querySelector('[data-block-type="FIRMA"]') as HTMLElement).style.textAlign).toBe(
      'right',
    );
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    http.verify();
  });

  it('012 T030: justifies the selected block from the toolbar', () => {
    const { fixture, http, root } = caricaBozza();
    const editor = apriEditor(root);
    const giustifica = root.querySelector('[data-align="GIUSTIFICATO"]') as HTMLButtonElement;
    expect(giustifica.getAttribute('aria-pressed')).toBe('false');
    giustifica.click();
    fixture.detectChanges();

    expect(editor.style.textAlign).toBe('justify');
    expect(giustifica.getAttribute('aria-pressed')).toBe('true');
    const request = salva(root, http);
    expect(request.request.body.sezioni[0].contenuto[0].allineamento).toBe('GIUSTIFICATO');
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    http.verify();
  });

  it('012: Enter opens a new paragraph at the caret and Backspace at its start joins it back', () => {
    const { fixture, http, root } = caricaBozza();
    const editor = apriEditor(root);
    seleziona(editor.firstChild!, 'Introduzione'.length, 'Introduzione'.length);
    editor.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', cancelable: true }));
    fixture.detectChanges();

    let editori = root.querySelectorAll<HTMLElement>('[data-section-text="intro"]');
    expect(Array.from(editori).map((e) => e.textContent)).toEqual([
      'Introduzione',
      ' {{titolo_it}}',
    ]);

    const secondo = editori[1];
    secondo.focus();
    secondo.dispatchEvent(new Event('focus'));
    seleziona(secondo.firstChild!, 0, 0);
    secondo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Backspace', cancelable: true }));
    fixture.detectChanges();

    editori = root.querySelectorAll<HTMLElement>('[data-section-text="intro"]');
    expect(editori.length).toBe(1);
    const request = salva(root, http);
    expect(request.request.body.sezioni[0].contenuto[0].frammenti).toEqual([
      { testo: 'Introduzione {{titolo_it}}' },
    ]);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    http.verify();
  });

  it('012 T027: a page break is inserted and removed with Delete like in a word processor', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(root);
    apriPannello(root, 'Blocchi');
    fixture.detectChanges();
    (root.querySelector('[data-insert-block="INTERRUZIONE_PAGINA"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const interruzione = root.querySelector('.page-break[data-block-id]') as HTMLElement;
    expect(interruzione.textContent).toContain('Interruzione di pagina');
    interruzione.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete', cancelable: true }));
    fixture.detectChanges();

    expect(root.querySelector('.page-break[data-block-id]')).toBeNull();
    const request = salva(root, http);
    expect(request.request.body.sezioni[0].contenuto.length).toBe(1);
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    http.verify();
  });

  it('012 T029: list numbering restarts after an article heading, as in the PDF', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(root);
    (root.querySelector('[data-list="NUMERICO"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    apriPannello(root, 'Blocchi');
    fixture.detectChanges();
    (root.querySelector('[data-insert-block="TITOLO"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (root.querySelector('[data-insert-block="ELENCO"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const marcatori = Array.from(root.querySelectorAll('.item-marker')).map((m) => m.textContent);
    expect(marcatori).toEqual(['1.', '1.']);
    http.verify();
  });

  it('012: after an autosave the next command still applies to the block being edited', () => {
    const { fixture, http, root } = caricaBozza();
    const editor = apriEditor(root, 'dettagli');
    editor.textContent = 'Posti disponibili: {{numero_posti}}';
    editor.dispatchEvent(new Event('input'));
    editor.dispatchEvent(new FocusEvent('blur'));
    const autosave = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');
    autosave.flush({ ...sezioniResponse, sezioni: autosave.request.body.sezioni });
    fixture.detectChanges();

    apriPannello(root, 'Proprietà');
    fixture.detectChanges();
    const select = root.querySelector('[data-block-type-select]') as HTMLSelectElement;
    select.value = 'TITOLO';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    const request = salva(root, http);
    const [intro, dettagli] = request.request.body.sezioni;
    expect(intro.contenuto[0].tipo).toBe('PARAGRAFO');
    expect(dettagli.contenuto[0].tipo).toBe('TITOLO');
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    http.verify();
  });

  it('012: a numbered list after a bulleted one starts again from 1, like Word', () => {
    const { fixture, http, root } = caricaBozza();
    apriEditor(root);
    (root.querySelector('[data-list="PUNTATO"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    apriPannello(root, 'Blocchi');
    fixture.detectChanges();
    (root.querySelector('[data-insert-block="ELENCO"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const marcatori = Array.from(root.querySelectorAll('.item-marker'));
    expect(marcatori.map((m) => m.textContent?.trim())).toEqual(['●', '1.']);
    expect(marcatori[0].classList).toContain('marker-puntato');
    http.verify();
  });

  it('tracks unsaved changes in the topbar and autosaves when the block loses focus', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    expect(root.querySelector('[data-save-state]')?.textContent).toContain(
      'Tutte le modifiche salvate',
    );
    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    editor.textContent = 'Introduzione riscritta {{titolo_it}}';
    editor.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(root.querySelector('[data-save-state]')?.textContent).toContain('Modifiche non salvate');

    editor.dispatchEvent(new Event('blur'));
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
    http.verify();
  });

  it('keeps edits typed while a save is in flight instead of overwriting them', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    editor.textContent = 'Primo testo';
    editor.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    (root.querySelector('[data-save-sections]') as HTMLButtonElement).click();
    const request = http.expectOne('/api/v1/builder/modelli/model/versioni/v2/sezioni');

    // L'utente continua a scrivere mentre il PUT e' ancora in volo.
    editor.textContent = 'Primo testo, poi il seguito';
    editor.dispatchEvent(new Event('input'));
    request.flush({ ...sezioniResponse, sezioni: request.request.body.sezioni });
    fixture.detectChanges();

    expect(root.querySelector('[data-section-text="intro"]')?.textContent).toBe(
      'Primo testo, poi il seguito',
    );
    expect(root.querySelector('[data-save-state]')?.textContent).toContain('Modifiche non salvate');
    http.verify();
  });

  it('blocks the version transition while there are unsaved changes', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    flushSections(http);
    flushDerivationConfig(http);
    fixture.detectChanges();

    const editor = root.querySelector('[data-section-text="intro"]') as HTMLElement;
    editor.textContent = 'Testo non ancora salvato';
    editor.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const dialog = root.querySelector('[data-confirm-transition]') as HTMLDialogElement;
    expect(dialog.textContent).toContain('modifiche non salvate');
    expect(
      (root.querySelector('[data-confirm-transition-submit]') as HTMLButtonElement).disabled,
    ).toBe(true);
    http.verify();
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
    http.verify();
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
    http.verify();
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
    http.verify();
  });
});
