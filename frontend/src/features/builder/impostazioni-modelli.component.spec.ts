import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { ImpostazioniModelliComponent } from './impostazioni-modelli.component';

describe('012 T069: impostazioni modelli del contesto', () => {
  it('lists the document types of the context integrations, with a link to their frame', () => {
    TestBed.configureTestingModule({
      imports: [ImpostazioniModelliComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ ctxId: 'geban' }) } },
        },
      ],
    });
    const fixture = TestBed.createComponent(ImpostazioniModelliComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    http.expectOne('/api/v1/builder/integrazioni').flush([
      { id: 'int-1', codice: 'GEBAN', nome: 'GEBAN', codice_contesto: 'geban' },
      { id: 'int-2', codice: 'ALTRO', nome: 'Altro', codice_contesto: 'altro' },
    ]);
    http.expectOne('/api/v1/builder/integrazioni/int-1/tipi-documento').flush(['BANDO_CONCORSO']);
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    const righe = root.querySelectorAll('tr[data-tipo]');
    expect(righe.length).toBe(1);
    expect(righe[0].querySelector('[data-imposta-cornice]')?.getAttribute('href')).toBe(
      '/contesti/geban/impostazioni/int-1/BANDO_CONCORSO',
    );
    http.verify();
  });
});
