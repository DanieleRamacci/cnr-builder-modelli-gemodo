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

  it('shows the contract fields returned by the API, with type and obligation', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
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

  it('offers the English edition here, not in the list, and only for an IT original', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    fixture.detectChanges();
    const dialog = root.querySelector('dialog')!;
    // jsdom non implementa showModal/close: stubbati come gia' fatto per la lista.
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    const bottone = Array.from(
      root.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((b) => b.textContent?.includes('Crea versione inglese'))!;
    expect(bottone).toBeTruthy();
    bottone.click();
    expect(dialog.showModal).toHaveBeenCalled();
    fixture.detectChanges();
    const conferma = Array.from(
      root.querySelectorAll('dialog button') as NodeListOf<HTMLButtonElement>,
    ).find((b) => b.textContent?.trim() === 'Crea')!;
    conferma.click();
    const richiesta = http.expectOne('/api/v1/builder/modelli/model/edizioni-derivate');
    expect(richiesta.request.body).toEqual({ lingua: 'EN' });
    richiesta.flush({ ...dettaglio, id: 'derivato', lingua: 'EN' });
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    http.verify();
  });

  it('hides the English action for a model that is already an English edition', () => {
    const { fixture, http, root } = setup();
    http
      .expectOne('/api/v1/builder/modelli/model')
      .flush({ ...dettaglio, lingua: 'EN', derivato_da_modello_id: 'padre' });
    fixture.detectChanges();
    expect(
      Array.from(root.querySelectorAll('button')).find((b) =>
        b.textContent?.includes('Crea versione inglese'),
      ),
    ).toBeUndefined();
    http.verify();
  });

  it('states plainly that sections and placeholders do not exist yet, without faking them', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/model').flush(dettaglio);
    fixture.detectChanges();
    expect(root.querySelector('.vuoto-sezioni')?.textContent).toContain('003');
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
