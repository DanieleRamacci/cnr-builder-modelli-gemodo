import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';

import { StoricoModelloComponent } from './storico-modello.component';

const storico = {
  modello_id: 'm1',
  codice: 'bando-concorso-td-ricercatore-it-abc',
  nome: 'Tempo Determinato - Ricercatore - IT',
  codice_contesto: 'geban',
  stato: 'ATTIVA',
  eventi: [
    {
      quando: '2026-10-07T10:30:00Z',
      utente: 'geban.utente',
      canale: 'API',
      client_id: 'geri-angular-public',
      azione: 'DOCUMENTO_GENERATO',
      descrizione: 'Documento generato per GEBAN (chiave B-1)',
      versione: 1,
      dettaglio: {},
    },
    {
      quando: '2026-10-07T10:00:00Z',
      utente: 'mario.rossi',
      canale: 'INTERFACCIA',
      client_id: 'gemodo-frontend',
      azione: 'VERSIONE_PUBBLICATO',
      descrizione: 'Pubblicata',
      versione: 1,
      dettaglio: {},
    },
    {
      quando: '2026-10-07T09:00:00Z',
      utente: 'mario.rossi',
      canale: 'INTERFACCIA',
      client_id: 'gemodo-frontend',
      azione: 'SEZIONI_AGGIORNATE',
      descrizione: 'Documento modificato - sezioni modificate: premessa',
      versione: 1,
      dettaglio: { modificate: ['premessa'] },
    },
    {
      quando: '2026-10-06T09:00:00Z',
      utente: 'anna.bianchi',
      canale: 'INTERFACCIA',
      client_id: 'gemodo-frontend',
      azione: 'MODELLO_CREATO',
      descrizione: 'Modello creato',
      versione: null,
      dettaglio: {},
    },
  ],
};

function setup() {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([]),
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'm1' } } } },
    ],
  });
  const fixture = TestBed.createComponent(StoricoModelloComponent);
  const http = TestBed.inject(HttpTestingController);
  return { fixture, http, root: fixture.nativeElement as HTMLElement };
}

const righe = (root: HTMLElement) => Array.from(root.querySelectorAll('tr[data-evento]'));

describe('storico del modello', () => {
  it('lists every event with user, action, version and channel', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/m1/storico').flush(storico);
    fixture.detectChanges();
    expect(root.querySelector('h1')!.textContent).toContain('Storico del modello');
    expect(righe(root).length).toBe(4);
    const prima = righe(root)[0].textContent!;
    expect(prima).toContain('geban.utente');
    expect(prima).toContain('Documento generato per GEBAN');
    expect(prima).toContain('v1');
    expect(prima).toContain('API');
    expect(righe(root)[2].textContent).toContain('sezioni modificate: premessa');
    http.verify();
  });

  it('summarises who worked on the model, and filters on a person', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/m1/storico').flush(storico);
    fixture.detectChanges();
    const persone = Array.from(root.querySelectorAll<HTMLButtonElement>('button[data-persona]'));
    expect(persone.map((p) => p.querySelector('strong')!.textContent)).toEqual([
      'mario.rossi',
      'geban.utente',
      'anna.bianchi',
    ]);
    expect(persone[0].textContent).toContain('2 azioni');
    persone[0].click();
    fixture.detectChanges();
    expect(righe(root).map((r) => r.getAttribute('data-azione'))).toEqual([
      'VERSIONE_PUBBLICATO',
      'SEZIONI_AGGIORNATE',
    ]);
  });

  it('filters by action group and by channel', () => {
    const { fixture, http, root } = setup();
    http.expectOne('/api/v1/builder/modelli/m1/storico').flush(storico);
    fixture.detectChanges();
    const [, gruppo, canale] = Array.from(
      root.querySelectorAll<HTMLSelectElement>('.filtri select'),
    );
    gruppo.value = 'documento';
    gruppo.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(righe(root).map((r) => r.getAttribute('data-azione'))).toEqual(['SEZIONI_AGGIORNATE']);
    gruppo.value = '';
    gruppo.dispatchEvent(new Event('change'));
    canale.value = 'API';
    canale.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(righe(root).map((r) => r.getAttribute('data-azione'))).toEqual(['DOCUMENTO_GENERATO']);
  });

  it('explains when the user is not an administrator', () => {
    const { fixture, http, root } = setup();
    http
      .expectOne('/api/v1/builder/modelli/m1/storico')
      .flush(
        { codice: 'ACCESSO_NON_AUTORIZZATO', messaggio: 'no' },
        { status: 403, statusText: 'Forbidden' },
      );
    fixture.detectChanges();
    expect(root.querySelector('.alert')!.textContent).toContain('solo agli amministratori');
  });
});
