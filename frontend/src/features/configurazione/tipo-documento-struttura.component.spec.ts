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
    service.crea.mockReturnValue(of({ codice: 'NUOVO', nome: 'x', codice_contesto: 'demo', stato_integrazione: 'INCOMPLETO' }));
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
      of({ codice: 'ESISTENTE', nome: 'x', codice_contesto: 'demo', stato_integrazione: 'DEFINITO' }),
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
});
