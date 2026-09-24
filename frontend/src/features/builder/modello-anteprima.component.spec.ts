import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
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

const policy = {
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
          contenuto: 'Introduzione {{titolo_it}}',
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
          contenuto: 'Posti disponibili {{numero_posti}}',
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
        contenuto: 'Introduzione {{titolo_it}}',
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
        contenuto: 'Posti disponibili {{numero_posti}}',
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
    policyResponse = policy,
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
    const dialog = root.querySelector('dialog')!;
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

    expect(root.querySelector('.section-editor.style-h1 [data-section-text="intro"]')).toBeTruthy();
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
    const action = Array.from(root.querySelectorAll('.topbar button')).find((button) =>
      button.textContent?.includes('Invia in revisione'),
    ) as HTMLButtonElement;
    expect(action).toBeTruthy();
    action.click();

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
        contenuto: [sezioniResponse.sezioni[1].contenuto[0]],
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
