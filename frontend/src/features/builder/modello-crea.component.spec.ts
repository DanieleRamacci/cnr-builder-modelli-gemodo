import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { ModelloCreaComponent } from './modello-crea.component';
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
