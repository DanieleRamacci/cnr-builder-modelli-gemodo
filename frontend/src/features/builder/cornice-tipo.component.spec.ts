import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { CorniceTipoComponent } from './cornice-tipo.component';

const INDIRIZZO = '/api/v1/builder/integrazioni/int-1/tipi-documento/BANDO_CONCORSO/cornice';
const VUOTA = {
  cornice: null,
  logo_presente: false,
  maschere_intestazione: ['LOGO_CENTRO_TESTO_SOTTO'],
  maschere_pie_pagina: ['TESTO_SINISTRA_NUMERO_DESTRA'],
};

describe('012 T069: intestazione e piè di pagina del tipo documento', () => {
  let originale: typeof globalThis.URL.createObjectURL;

  beforeEach(() => {
    originale = globalThis.URL.createObjectURL;
    globalThis.URL.createObjectURL = () => 'blob:logo';
    globalThis.URL.revokeObjectURL = () => undefined;
  });
  afterEach(() => {
    globalThis.URL.createObjectURL = originale;
  });

  function setup() {
    TestBed.configureTestingModule({
      imports: [CorniceTipoComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: convertToParamMap({
                ctxId: 'geban',
                integrazioneId: 'int-1',
                codice: 'BANDO_CONCORSO',
              }),
              queryParamMap: convertToParamMap({}),
            },
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(CorniceTipoComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    return { fixture, http, root: fixture.nativeElement as HTMLElement };
  }

  function clic(root: HTMLElement, selettore: string): void {
    (root.querySelector(selettore) as HTMLElement).click();
  }

  function scrivi(root: HTMLElement, selettore: string, valore: string): void {
    const campo = root.querySelector(selettore) as HTMLInputElement;
    campo.value = valore;
    campo.dispatchEvent(new Event('input'));
  }

  it('adds a header from a mask, fills it and saves header and footer independently', () => {
    const { fixture, http, root } = setup();
    http.expectOne(INDIRIZZO).flush(VUOTA);
    fixture.detectChanges();

    clic(root, '[data-aggiungi-intestazione]');
    fixture.detectChanges();
    clic(root, '[data-maschera="LOGO_CENTRO_TESTO_SOTTO"]');
    fixture.detectChanges();
    scrivi(
      root,
      '[data-testo-intestazione]',
      'Consiglio Nazionale delle Ricerche\nUfficio Reclutamento',
    );
    fixture.detectChanges();

    // L'anteprima si aggiorna mentre si scrive, come la disegnera' il PDF.
    expect(root.querySelector('[data-cornice-testata] .b')?.textContent).toBe(
      'Consiglio Nazionale delle Ricerche',
    );
    expect(root.querySelector('[data-cornice-piede]')).toBeNull();

    clic(root, '[data-salva-cornice]');
    const richiesta = http.expectOne(INDIRIZZO);
    expect(richiesta.request.method).toBe('PUT');
    expect(richiesta.request.body).toEqual({
      intestazione: {
        maschera: 'LOGO_CENTRO_TESTO_SOTTO',
        con_logo: true,
        testo: [
          { testo: 'Consiglio Nazionale delle Ricerche', grassetto: true },
          { testo: '\nUfficio Reclutamento' },
        ],
      },
      pie_pagina: null,
    });
    richiesta.flush({ ...VUOTA, cornice: richiesta.request.body });
    fixture.detectChanges();
    expect(root.querySelector('[data-cornice-salvata]')).toBeTruthy();
    http.verify();
  });

  it('uploads the logo as a file and shows it in the preview', () => {
    const { fixture, http, root } = setup();
    http.expectOne(INDIRIZZO).flush({
      ...VUOTA,
      cornice: {
        intestazione: { maschera: 'LOGO_CENTRO_TESTO_SOTTO', con_logo: true, testo: [] },
        pie_pagina: null,
      },
    });
    fixture.detectChanges();

    const campo = root.querySelector('[data-logo-file]') as HTMLInputElement;
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'logo.png', { type: 'image/png' });
    Object.defineProperty(campo, 'files', { value: [file] });
    campo.dispatchEvent(new Event('change'));

    const caricamento = http.expectOne(`${INDIRIZZO}/logo`);
    expect(caricamento.request.method).toBe('PUT');
    expect(caricamento.request.body).toBe(file);
    expect(caricamento.request.headers.get('Content-Type')).toBe('image/png');
    caricamento.flush(null);
    http
      .expectOne(`${INDIRIZZO}/logo`)
      .flush(new Blob([new Uint8Array([1])], { type: 'image/png' }));
    fixture.detectChanges();

    expect(root.querySelector('[data-cornice-testata] img')?.getAttribute('src')).toBe('blob:logo');
    expect(root.querySelector('[data-rimuovi-logo]')).toBeTruthy();
    http.verify();
  });

  it('shows why the service refused a logo', () => {
    const { fixture, http, root } = setup();
    http.expectOne(INDIRIZZO).flush({
      ...VUOTA,
      cornice: {
        intestazione: { maschera: 'LOGO_CENTRO_TESTO_SOTTO', con_logo: true, testo: [] },
        pie_pagina: null,
      },
    });
    fixture.detectChanges();
    const campo = root.querySelector('[data-logo-file]') as HTMLInputElement;
    Object.defineProperty(campo, 'files', {
      value: [new File(['<svg/>'], 'logo.png', { type: 'image/png' })],
    });
    campo.dispatchEvent(new Event('change'));
    http.expectOne(`${INDIRIZZO}/logo`).flush(
      {
        codice: 'MODELLO_DOCUMENTALE_NON_VALIDO',
        messaggio: 'Logo non valido',
        dettagli: [{ violazione: "il file non e' un'immagine PNG o JPEG leggibile" }],
      },
      { status: 422, statusText: 'x' },
    );
    fixture.detectChanges();

    expect(root.querySelector('[data-cornice-error]')?.textContent).toContain('PNG o JPEG');
    http.verify();
  });
});
