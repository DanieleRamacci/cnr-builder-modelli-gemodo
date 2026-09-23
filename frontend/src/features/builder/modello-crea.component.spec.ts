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
  policy: { nome_dimensione: string; consente_valore_generico: boolean }[] = [
    { nome_dimensione: 'lingua', consente_valore_generico: false },
    { nome_dimensione: 'livello', consente_valore_generico: true },
  ],
) {
  http
    .match((r) => r.url.includes('/policy-dimensioni'))
    .forEach((r) => r.flush({ codice_tipo_documento: 'BANDO', policy, dimensioni_non_configurate: [] }));
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
      lingua: string;
      livelloProfessionale: string;
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
    component.lingua = 'EN';
    component.livelloProfessionale = 'VI';
    component.create();
    const model = http.expectOne('/api/v1/builder/modelli');
    expect(model.request.body.integrazione_id).toBe('source');
    expect(model.request.body.percorso_categorizzazione).toEqual(['TD', 'RICERCATORE']);
    expect(model.request.body.lingua).toBe('EN');
    expect(model.request.body.livello_professionale).toBe('VI');
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
    campi: [campo],
  };
  const leafB = {
    codice: 'TECNOLOGO',
    descrizione: 'Tecnologo',
    tipo_livello: 'profilo',
    lingue_possibili: ['IT'],
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
    policy: { nome_dimensione: string; consente_valore_generico: boolean }[] | undefined = undefined,
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
      lingua: string;
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
    expect(root.querySelector('#lingua')).toBeNull();
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
      const select = root.querySelector<HTMLSelectElement>('#lingua')!;
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
  it('offers "Tutti i livelli" only when the policy allows a generic value', () => {
    const { fixture, component } = setup([
      { nome_dimensione: 'lingua', consente_valore_generico: false },
      { nome_dimensione: 'livello', consente_valore_generico: true },
    ]);
    component.chooseAt(0, 'TD');
    component.chooseAt(1, 'RICERCATORE');
    fixture.detectChanges();
    const livelli = fixture.nativeElement.querySelector('#livello') as HTMLSelectElement;
    const opzioni = Array.from(livelli.options).map((o) => o.textContent?.trim());
    expect(opzioni).toContain('Tutti i livelli');
  });
  it('hides "Tutti i livelli" when the dimension requires an explicit value', () => {
    const { fixture, component } = setup([
      { nome_dimensione: 'lingua', consente_valore_generico: false },
      { nome_dimensione: 'livello', consente_valore_generico: false },
    ]);
    component.chooseAt(0, 'TD');
    component.chooseAt(1, 'RICERCATORE');
    fixture.detectChanges();
    const livelli = fixture.nativeElement.querySelector('#livello') as HTMLSelectElement;
    const opzioni = Array.from(livelli.options).map((o) => o.textContent?.trim());
    expect(opzioni).not.toContain('Tutti i livelli');
    expect(opzioni).toContain('Scegli un livello');
  });
});
