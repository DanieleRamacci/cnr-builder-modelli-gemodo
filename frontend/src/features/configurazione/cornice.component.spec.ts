import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { CorniceComponent } from './cornice.component';

const URL = '/api/v1/configurazione/integrazioni/int-1/tipi-documento/BANDO_CONCORSO/cornice';

describe('012 T047: cornice di pagina del tipo documento', () => {
  function setup() {
    TestBed.configureTestingModule({
      imports: [CorniceComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: convertToParamMap({ codice: 'BANDO_CONCORSO' }),
              queryParamMap: convertToParamMap({ integrazioneId: 'int-1' }),
            },
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(CorniceComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    return { fixture, http, root: fixture.nativeElement as HTMLElement };
  }

  function scrivi(root: HTMLElement, selettore: string, valore: string): void {
    const campo = root.querySelector(selettore) as HTMLInputElement | HTMLTextAreaElement;
    campo.value = valore;
    campo.dispatchEvent(new Event('input'));
  }

  it('without a logo file it says so instead of offering a logo that would not show', () => {
    const { fixture, http, root } = setup();
    http.expectOne(URL).flush({ cornice: null, loghi_disponibili: [] });
    fixture.detectChanges();

    expect(root.querySelector('[data-cornice-logo]')).toBeNull();
    expect(root.querySelector('[data-cornice-no-logo]')?.textContent).toContain('non è ancora');
    http.verify();
  });

  it('saves the header as fragments, with the first line in bold', () => {
    const { fixture, http, root } = setup();
    http.expectOne(URL).flush({ cornice: null, loghi_disponibili: ['logo-ente'] });
    fixture.detectChanges();

    scrivi(
      root,
      '[data-cornice-intestazione]',
      'Consiglio Nazionale delle Ricerche\nUfficio Reclutamento',
    );
    scrivi(root, '[data-cornice-piede]', 'Piazzale Aldo Moro 7 - Roma');
    fixture.detectChanges();
    (root.querySelector('[data-cornice-salva]') as HTMLButtonElement).click();

    const richiesta = http.expectOne(URL);
    expect(richiesta.request.method).toBe('PUT');
    expect(richiesta.request.body).toEqual({
      logo_ref: 'logo-ente',
      intestazione: [
        { testo: 'Consiglio Nazionale delle Ricerche', grassetto: true },
        { testo: '\nUfficio Reclutamento' },
      ],
      pie_pagina: [{ testo: 'Piazzale Aldo Moro 7 - Roma' }],
      numerazione_pagine: true,
    });
    richiesta.flush({ cornice: richiesta.request.body, loghi_disponibili: ['logo-ente'] });
    fixture.detectChanges();
    expect(root.querySelector('[data-cornice-salvata]')).toBeTruthy();
    http.verify();
  });

  it('fills the form from the saved frame', () => {
    const { fixture, http, root } = setup();
    http.expectOne(URL).flush({
      cornice: {
        logo_ref: null,
        intestazione: [{ testo: 'CNR', grassetto: false }, { testo: '\nUfficio' }],
        pie_pagina: [{ testo: 'Roma' }],
        numerazione_pagine: false,
      },
      loghi_disponibili: ['logo-ente'],
    });
    fixture.detectChanges();

    expect((root.querySelector('[data-cornice-intestazione]') as HTMLTextAreaElement).value).toBe(
      'CNR\nUfficio',
    );
    expect((root.querySelector('[data-cornice-grassetto]') as HTMLInputElement).checked).toBe(
      false,
    );
    expect((root.querySelector('[data-cornice-logo]') as HTMLInputElement).checked).toBe(false);
    expect((root.querySelector('[data-cornice-numerazione]') as HTMLInputElement).checked).toBe(
      false,
    );
    http.verify();
  });

  it('does not let a header longer than three lines be saved', () => {
    const { fixture, http, root } = setup();
    http.expectOne(URL).flush({ cornice: null, loghi_disponibili: [] });
    fixture.detectChanges();

    scrivi(root, '[data-cornice-intestazione]', 'uno\ndue\ntre\nquattro');
    fixture.detectChanges();

    expect((root.querySelector('[data-cornice-salva]') as HTMLButtonElement).disabled).toBe(true);
    http.verify();
  });

  it('shows the service violations when the frame is refused', () => {
    const { fixture, http, root } = setup();
    http.expectOne(URL).flush({ cornice: null, loghi_disponibili: [] });
    fixture.detectChanges();
    scrivi(root, '[data-cornice-intestazione]', '<b>CNR</b>');
    fixture.detectChanges();
    (root.querySelector('[data-cornice-salva]') as HTMLButtonElement).click();

    http.expectOne(URL).flush(
      {
        codice: 'MODELLO_DOCUMENTALE_NON_VALIDO',
        messaggio: 'Cornice di pagina non valida',
        dettagli: [
          { violazione: 'intestazione, frammento 0: il testo contiene markup, non ammesso' },
        ],
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );
    fixture.detectChanges();

    expect(root.querySelector('[data-cornice-error]')?.textContent).toContain('contiene markup');
    http.verify();
  });
});
