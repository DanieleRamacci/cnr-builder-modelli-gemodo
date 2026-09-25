import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { ModelloCreaComponent } from './modello-crea.component';
/**
 * La lettura delle policy parte insieme alla struttura (007 FR-031): serve a
 * sapere se "Tutti i livelli" e' un'opzione valida per quel tipo documento.
 */
function flushPolicy(
  http: HttpTestingController,
  policy: {
    nome_dimensione: string;
    consente_valore_generico: boolean;
    valore_default?: string | null;
  }[] = [
    { nome_dimensione: 'lingua', consente_valore_generico: false, valore_default: 'IT' },
    {
      nome_dimensione: 'livello_professionale',
      consente_valore_generico: true,
      valore_default: null,
    },
  ],
) {
  http
    .match((r) => r.url.includes('/policy-dimensioni'))
    .forEach((r) =>
      r.flush({ codice_tipo_documento: 'BANDO', policy, dimensioni_non_configurate: [] }),
    );
}
describe('manager creation flow', () => {
  it('sends the complete leaf path and confirms BOZZA only after version creation', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'source' } } } },
      ],
    });
    const fixture = TestBed.createComponent(ModelloCreaComponent);
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/v1/builder/integrazioni/source/tipi-documento').flush(['BANDO']);
    const component = fixture.componentInstance as unknown as {
      loadTree: (code: string) => void;
      choose: (node: unknown) => void;
      create: () => void;
      scegliDimensione: (nome: string, valore: string) => void;
    };
    const leaf = {
      codice: 'RICERCATORE',
      descrizione: 'Ricercatore',
      lingue_possibili: ['IT', 'EN'],
      livelli_possibili: ['VI', 'VII'],
      campi: [
        {
          codice: 'titolo',
          lingua: 'IT',
          etichetta: 'Titolo',
          tipo: 'string',
          ordine: 1,
          obbligatorio: true,
        },
      ],
    };
    const root = { codice: 'TD', descrizione: 'TD', figli: [leaf] };
    component.loadTree('BANDO');
    http
      .expectOne('/api/v1/builder/integrazioni/source/tipi-documento/BANDO/struttura')
      .flush({ nodi: [root] });
    flushPolicy(http);
    component.choose(root);
    component.choose(leaf);
    component.scegliDimensione('lingua', 'EN');
    component.scegliDimensione('livello_professionale', 'VI');
    component.create();
    const model = http.expectOne('/api/v1/builder/modelli');
    expect(model.request.body.integrazione_id).toBe('source');
    expect(model.request.body.percorso_categorizzazione).toEqual(['TD', 'RICERCATORE']);
    expect(model.request.body.dimensioni).toEqual({
      lingua: 'EN',
      livello_professionale: 'VI',
    });
    expect(model.request.body.lingua).toBeUndefined();
    expect(model.request.body.livello_professionale).toBeUndefined();
    expect(model.request.body.codice).toBeUndefined();
    expect(model.request.body.nome).toBeUndefined();
    expect(model.request.body.variante).toBeUndefined();
    model.flush({ id: 'model', codice: 'generated-code', nome: 'Generated name' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('creato - BOZZA');
    const version = http.expectOne('/api/v1/builder/modelli/model/versioni');
    expect(version.request.body.campi).toEqual([{ codice: 'titolo', lingua: 'IT' }]);
    version.flush({ stato: 'BOZZA' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Generated name');
    expect(fixture.nativeElement.textContent).toContain('generated-code');
    expect(fixture.nativeElement.textContent).toContain('creato - BOZZA');
    http.verify();
  });
});

describe('2a categorization cascade', () => {
  const campo = {
    codice: 'titolo',
    lingua: 'IT',
    etichetta: 'Titolo',
    tipo: 'string',
    ordine: 1,
    obbligatorio: true,
  };
  const leafA = {
    codice: 'RICERCATORE',
    descrizione: 'Ricercatore',
    tipo_livello: 'profilo',
    lingue_possibili: ['IT'],
    livelli_possibili: ['VI', 'VII'],
    campi: [campo],
  };
  const leafB = {
    codice: 'TECNOLOGO',
    descrizione: 'Tecnologo',
    tipo_livello: 'profilo',
    lingue_possibili: ['IT'],
    livelli_possibili: ['VI', 'VII'],
    campi: [campo],
  };
  const nodi = [
    {
      codice: 'TD',
      descrizione: 'Tempo determinato',
      tipo_livello: 'tipologia',
      figli: [leafA, leafB],
    },
    { codice: 'TI', descrizione: 'Tempo indeterminato', tipo_livello: 'tipologia', figli: [leafB] },
  ];

  function setup(
    policy:
      | {
          nome_dimensione: string;
          consente_valore_generico: boolean;
          valore_default?: string | null;
        }[]
      | undefined = undefined,
  ) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'source' } } } },
      ],
    });
    const fixture = TestBed.createComponent(ModelloCreaComponent);
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/v1/builder/integrazioni/source/tipi-documento').flush(['BANDO']);
    const component = fixture.componentInstance as unknown as {
      loadTree: (code: string) => void;
      chooseAt: (indice: number, code: string) => void;
      create: () => void;
      path: () => string[];
    };
    component.loadTree('BANDO');
    http
      .expectOne('/api/v1/builder/integrazioni/source/tipi-documento/BANDO/struttura')
      .flush({ nodi });
    flushPolicy(http, policy);
    fixture.detectChanges();
    return { fixture, http, component };
  }

  const genera = (root: HTMLElement) =>
    Array.from(root.querySelectorAll('button')).find((b) =>
      b.textContent?.includes('Genera modello'),
    )!;

  it('shows one level block per reached depth with named levels and disables Genera until a leaf', () => {
    const { fixture } = setup();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('#livello-0')).not.toBeNull();
    expect(root.querySelector('#livello-1')).toBeNull();
    expect(root.textContent).toContain('Tipologia');
    expect(genera(root).disabled).toBe(true);
    expect(root.textContent).toContain('BANDO');
  });

  it('descends level by level and resets deeper choices when a parent changes', () => {
    const { fixture, component } = setup();
    const root = fixture.nativeElement as HTMLElement;
    component.chooseAt(0, 'TD');
    fixture.detectChanges();
    expect(root.querySelector('#livello-1')).not.toBeNull();
    expect(root.textContent).toContain('Profilo');
    component.chooseAt(1, 'RICERCATORE');
    fixture.detectChanges();
    expect(component.path()).toEqual(['TD', 'RICERCATORE']);
    expect(root.textContent).toContain('3 di 3 livelli selezionati');
    component.chooseAt(0, 'TI');
    fixture.detectChanges();
    expect(component.path()).toEqual(['TI']);
    expect(root.querySelector('#dimensione-lingua')).toBeNull();
    expect(root.textContent).toContain('2 di 3 livelli selezionati');
    component.chooseAt(0, '');
    fixture.detectChanges();
    expect(component.path()).toEqual([]);
  });

  it('enables Genera only with a leaf and a language, and shows the backend error for an ambiguous path', async () => {
    const { fixture, http, component } = setup();
    const root = fixture.nativeElement as HTMLElement;
    component.chooseAt(0, 'TD');
    component.chooseAt(1, 'RICERCATORE');
    const setLingua = async (value: string) => {
      const select = root.querySelector<HTMLSelectElement>('#dimensione-lingua')!;
      select.value = value;
      select.dispatchEvent(new Event('change'));
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
    };
    await fixture.whenStable();
    fixture.detectChanges();
    await setLingua('');
    expect(genera(root).disabled).toBe(true);
    await setLingua('IT');
    expect(genera(root).disabled).toBe(false);
    component.create();
    http
      .expectOne('/api/v1/builder/modelli')
      .flush(
        { codice: 'CONTESTO_NON_VALIDO', messaggio: 'Percorso ambiguo' },
        { status: 400, statusText: 'Bad Request' },
      );
    fixture.detectChanges();
    expect(root.querySelector('[role=alert]')?.textContent).toContain('Percorso ambiguo');
    expect(root.textContent).not.toContain('creato - BOZZA');
    http.verify();
  });

  it('keeps INTEGRAZIONE_NON_CONNESSA and transport failures distinct from an empty tree', () => {
    const { fixture, http, component } = setup();
    const root = fixture.nativeElement as HTMLElement;
    component.loadTree('BANDO');
    http
      .expectOne('/api/v1/builder/integrazioni/source/tipi-documento/BANDO/struttura')
      .flush(
        { codice: 'INTEGRAZIONE_NON_CONNESSA', messaggio: 'Integrazione non connessa' },
        { status: 409, statusText: 'Conflict' },
      );
    fixture.detectChanges();
    expect(root.querySelector('[role=alert]')?.textContent).toContain('Integrazione non connessa');
    expect(root.querySelector('#livello-0')).toBeNull();
    component.loadTree('BANDO');
    http
      .expectOne('/api/v1/builder/integrazioni/source/tipi-documento/BANDO/struttura')
      .error(new ProgressEvent('error'));
    fixture.detectChanges();
    expect(root.querySelector('[role=alert]')).not.toBeNull();
    expect(root.querySelector('#livello-0')).toBeNull();
    http.verify();
  });

  // 007 FR-031: il form non deve proporre una scelta che il backend rifiutera'.
  it('offers an empty value only when the policy allows a generic value', () => {
    const { fixture, component } = setup([
      { nome_dimensione: 'lingua', consente_valore_generico: false },
      { nome_dimensione: 'livello_professionale', consente_valore_generico: true },
    ]);
    component.chooseAt(0, 'TD');
    component.chooseAt(1, 'RICERCATORE');
    fixture.detectChanges();
    const livelli = fixture.nativeElement.querySelector(
      '#dimensione-livello_professionale',
    ) as HTMLSelectElement;
    const opzioni = Array.from(livelli.options).map((o) => o.textContent?.trim());
    expect(opzioni).toContain('Nessun valore specifico');
  });
  it('requires a value when the dimension does not allow a generic model', () => {
    const { fixture, component } = setup([
      { nome_dimensione: 'lingua', consente_valore_generico: false },
      { nome_dimensione: 'livello_professionale', consente_valore_generico: false },
    ]);
    component.chooseAt(0, 'TD');
    component.chooseAt(1, 'RICERCATORE');
    fixture.detectChanges();
    const livelli = fixture.nativeElement.querySelector(
      '#dimensione-livello_professionale',
    ) as HTMLSelectElement;
    const opzioni = Array.from(livelli.options).map((o) => o.textContent?.trim());
    expect(opzioni).not.toContain('Nessun valore specifico');
    expect(opzioni).toContain('Seleziona un valore');
  });

  it('proposes a variant, with the occupying model, only when the slot is taken', async () => {
    const { fixture, http, component } = setup([
      { nome_dimensione: 'lingua', consente_valore_generico: false },
      { nome_dimensione: 'livello_professionale', consente_valore_generico: true },
    ]);
    component.chooseAt(0, 'TD');
    component.chooseAt(1, 'RICERCATORE');
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    // Finche' la categorizzazione e' libera non si parla di varianti.
    expect(root.querySelector('[data-variante-richiesta]')).toBeNull();

    // La lingua e' obbligatoria per questa policy: senza, il form resta
    // invalido e il bottone non invia nulla.
    await fixture.whenStable();
    fixture.detectChanges();
    const lingua = root.querySelector('#dimensione-lingua') as HTMLSelectElement;
    lingua.selectedIndex = Array.from(lingua.options).findIndex(
      (opzione) => opzione.textContent?.trim() === 'IT',
    );
    lingua.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    genera(root).click();
    http.expectOne('/api/v1/builder/modelli').flush(
      {
        codice: 'MODELLO_VARIANTE_RICHIESTA',
        messaggio: 'Esiste gia un modello su questa categorizzazione',
        dettagli: [
          {
            modello_id: 'esistente',
            codice: 'bando-td-ricercatore',
            nome: 'Bando Ricercatore',
            variante: 'STANDARD',
          },
        ],
      },
      { status: 409, statusText: 'Conflict' },
    );
    fixture.detectChanges();

    const proposta = root.querySelector('[data-variante-richiesta]')!;
    expect(proposta.textContent).toContain('Bando Ricercatore');
    expect(proposta.textContent).toContain('bando-td-ricercatore');
    // Il rifiuto non si mostra come errore generico: e' diventato una richiesta.
    expect(root.querySelector('.alert-danger')).toBeNull();
    // `genera` cerca per testo, e il bottone ora si chiama diversamente: e'
    // proprio il cambiamento che questo test verifica.
    const invia = () => root.querySelector('.azioni-2a button[type=submit]') as HTMLButtonElement;
    expect(invia().textContent).toContain('Crea variante');
    expect(invia().disabled).toBe(true);

    // Il campo e' appena comparso: `ngModel` vi si aggancia su microtask.
    await fixture.whenStable();
    fixture.detectChanges();
    const nota = root.querySelector('#nota-variante') as HTMLInputElement;
    nota.value = 'Senza prova preselettiva';
    nota.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(invia().disabled).toBe(false);

    invia().click();
    const seconda = http.expectOne('/api/v1/builder/modelli');
    expect(seconda.request.body.nota).toBe('Senza prova preselettiva');
    http.verify();
  });

  it('keeps the value chosen before the policy response arrives', async () => {
    // La policy si carica in parallelo alla struttura: se l'utente sceglie
    // prima che risponda, la risposta non deve cancellargli la scelta sotto le
    // dita (trovato dall'e2e della 011, T041).
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'source' } } } },
      ],
    });
    const fixture = TestBed.createComponent(ModelloCreaComponent);
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/v1/builder/integrazioni/source/tipi-documento').flush(['BANDO']);
    const component = fixture.componentInstance as unknown as {
      loadTree: (code: string) => void;
      chooseAt: (indice: number, code: string) => void;
    };
    component.loadTree('BANDO');
    http
      .expectOne('/api/v1/builder/integrazioni/source/tipi-documento/BANDO/struttura')
      .flush({ nodi });
    fixture.detectChanges();
    component.chooseAt(0, 'TD');
    component.chooseAt(1, 'RICERCATORE');
    fixture.detectChanges();

    // `ngModel` registra il control su microtask: prima di allora il select
    // non e' ancora collegato e un change non arriverebbe al modello.
    await fixture.whenStable();
    fixture.detectChanges();
    const livelli = fixture.nativeElement.querySelector(
      '#dimensione-livello_professionale',
    ) as HTMLSelectElement;
    // `SelectControlValueAccessor` rimpiazza i value delle option con id
    // interni: si seleziona per indice, non per valore.
    livelli.selectedIndex = Array.from(livelli.options).findIndex(
      (opzione) => opzione.textContent?.trim() === 'VII',
    );
    livelli.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    // La policy arriva adesso, con un default diverso da quello scelto.
    flushPolicy(http, [
      { nome_dimensione: 'lingua', consente_valore_generico: false, valore_default: 'IT' },
      {
        nome_dimensione: 'livello_professionale',
        consente_valore_generico: false,
        valore_default: 'VI',
      },
    ]);
    fixture.detectChanges();
    // `ngModel` scrive nella vista su microtask: senza attendere, il select
    // mostrerebbe ancora il valore vecchio e il test non proverebbe nulla.
    await fixture.whenStable();
    fixture.detectChanges();

    expect(
      (
        fixture.nativeElement.querySelector(
          '#dimensione-livello_professionale',
        ) as HTMLSelectElement
      ).value,
    ).toBe('VII');
    http.verify();
  });

  it('uses valore_default instead of the first value returned by discovery', async () => {
    const original = [...leafA.lingue_possibili];
    leafA.lingue_possibili.splice(0, leafA.lingue_possibili.length, 'EN', 'IT');
    try {
      const { fixture, component } = setup([
        {
          nome_dimensione: 'lingua',
          consente_valore_generico: false,
          valore_default: 'IT',
        },
      ]);
      component.chooseAt(0, 'TD');
      component.chooseAt(1, 'RICERCATORE');
      fixture.detectChanges();
      await fixture.whenStable();
      fixture.detectChanges();
      const lingua = fixture.nativeElement.querySelector('#dimensione-lingua') as HTMLSelectElement;
      expect(lingua.value).toBe('IT');
    } finally {
      leafA.lingue_possibili.splice(0, leafA.lingue_possibili.length, ...original);
    }
  });
});
