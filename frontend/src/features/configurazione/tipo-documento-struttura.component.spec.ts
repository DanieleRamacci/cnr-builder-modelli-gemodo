import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { TipoDocumentoStrutturaComponent } from './tipo-documento-struttura.component';
import { TipiDocumentoService } from './tipi-documento.service';

function route(codice: string | null) {
  return { snapshot: { paramMap: { get: () => codice } } };
}

describe('TipoDocumentoStrutturaComponent', () => {
  let service: { crea: ReturnType<typeof vi.fn>; aggiornaStruttura: ReturnType<typeof vi.fn>; leggiStruttura: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    service = { crea: vi.fn(), aggiornaStruttura: vi.fn(), leggiStruttura: vi.fn() };
  });

  it('creates a new tipo documento with the default campo marked obbligatorio, sends only checked lingue', () => {
    TestBed.configureTestingModule({
      imports: [TipoDocumentoStrutturaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route(null) },
        { provide: TipiDocumentoService, useValue: service },
      ],
    });
    service.crea.mockReturnValue(
      of({ id: '00000000-0000-4000-8000-000000000001', codice: 'NUOVO', nome: 'x', codice_contesto: 'demo', stato_integrazione: 'INCOMPLETO' }),
    );
    const navigateSpy = vi.spyOn(TestBed.inject(Router), 'navigate');
    const fixture: ComponentFixture<TipoDocumentoStrutturaComponent> = TestBed.createComponent(
      TipoDocumentoStrutturaComponent,
    );
    const component = fixture.componentInstance;
    component['identita'].setValue({ codice: 'NUOVO', nome: 'Nuovo tipo', codiceContesto: 'demo' });
    component['tipologie'].at(0).patchValue({ codice: 'TD', descrizione: 'Tempo determinato' });
    component['profili'].at(0).patchValue({ codice: 'RIC', descrizione: 'Ricercatore' });
    component['campi'].at(0).patchValue({ codice: 'titolo', etichetta: 'Titolo', obbligatorio: true });
    fixture.detectChanges();

    (component as unknown as { salva: () => void }).salva();

    expect(service.crea).toHaveBeenCalledTimes(1);
    const request = service.crea.mock.calls[0][0];
    expect(request.codice).toBe('NUOVO');
    expect(request.struttura.lingue_possibili).toEqual(['IT']);
    expect(request.struttura.campi[0]).toMatchObject({ codice: 'titolo', obbligatorio: true });
    expect(navigateSpy).toHaveBeenCalledWith(['/configurazione/tipi-documento', 'NUOVO']);
  });

  it('prefills from the existing struttura and lets the admin flip a field to opzionale', () => {
    TestBed.configureTestingModule({
      imports: [TipoDocumentoStrutturaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route('ESISTENTE') },
        { provide: TipiDocumentoService, useValue: service },
      ],
    });
    service.leggiStruttura.mockReturnValue(
      of({
        tipologie: [{ codice: 'TD', descrizione: 'Tempo determinato' }],
        profili: [{ codice: 'RIC', descrizione: 'Ricercatore', attributi: [] }],
        combinazioni: [{ codice_tipologia: 'TD', codice_profilo: 'RIC' }],
        lingue_possibili: ['IT', 'EN'],
        campi: [
          { codice: 'titolo', etichetta: 'Titolo', tipo: 'string', lingua: 'IT', obbligatorio: true, ordine: 1 },
        ],
      }),
    );
    service.aggiornaStruttura.mockReturnValue(
      of({ id: '00000000-0000-4000-8000-000000000002', codice: 'ESISTENTE', nome: 'x', codice_contesto: 'demo', stato_integrazione: 'DEFINITO' }),
    );
    const fixture: ComponentFixture<TipoDocumentoStrutturaComponent> = TestBed.createComponent(
      TipoDocumentoStrutturaComponent,
    );
    const component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component['campi'].at(0).value.codice).toBe('titolo');
    expect(component['campi'].at(0).value.obbligatorio).toBe(true);

    component['campi'].at(0).patchValue({ obbligatorio: false });
    (component as unknown as { salva: () => void }).salva();

    expect(service.aggiornaStruttura).toHaveBeenCalledWith(
      'ESISTENTE',
      expect.objectContaining({
        campi: [expect.objectContaining({ codice: 'titolo', obbligatorio: false })],
      }),
    );
  });

  it('fills the form from a pasted JSON instead of requiring row-by-row entry', () => {
    TestBed.configureTestingModule({
      imports: [TipoDocumentoStrutturaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route(null) },
        { provide: TipiDocumentoService, useValue: service },
      ],
    });
    const fixture: ComponentFixture<TipoDocumentoStrutturaComponent> = TestBed.createComponent(
      TipoDocumentoStrutturaComponent,
    );
    const component = fixture.componentInstance;
    fixture.detectChanges();

    component['testoJson'].set(
      JSON.stringify({
        tipologie: [{ codice: 'CP', descrizione: 'Concorsi Pubblici' }],
        profili: [{ codice: 'CTER', descrizione: 'Collaboratore Tecnico E.R.', attributi: [] }],
        combinazioni: [{ codice_tipologia: 'CP', codice_profilo: 'CTER' }],
        lingue_possibili: ['IT', 'EN'],
        campi: [
          { codice: 'titolo', etichetta: 'Titolo', tipo: 'string', lingua: 'IT', obbligatorio: true, ordine: 1 },
        ],
      }),
    );

    (component as unknown as { caricaJson: () => void }).caricaJson();

    expect(component['tipologie'].at(0).value.codice).toBe('CP');
    expect(component['profili'].at(0).value.codice).toBe('CTER');
    expect(component['campi'].at(0).value).toMatchObject({ codice: 'titolo', obbligatorio: true });
    expect(component['linguePossibili'].value).toEqual({ IT: true, EN: true });
    expect((component as unknown as { erroreJson: () => string | null }).erroreJson()).toBeNull();
  });

  it('reports invalid JSON instead of silently leaving the form untouched', () => {
    TestBed.configureTestingModule({
      imports: [TipoDocumentoStrutturaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route(null) },
        { provide: TipiDocumentoService, useValue: service },
      ],
    });
    const fixture: ComponentFixture<TipoDocumentoStrutturaComponent> = TestBed.createComponent(
      TipoDocumentoStrutturaComponent,
    );
    const component = fixture.componentInstance;
    fixture.detectChanges();

    component['testoJson'].set('{ non e json valido');
    (component as unknown as { caricaJson: () => void }).caricaJson();

    expect((component as unknown as { erroreJson: () => string | null }).erroreJson()).toContain(
      'JSON non valido',
    );
  });
});
