import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { RegistroAttivitaComponent, type EventoAttivita } from './registro-attivita.component';

const URL = '/api/v1/admin/attivita';

function evento(overrides: Partial<EventoAttivita> = {}): EventoAttivita {
  return {
    quando: '2026-10-05T12:30:00Z',
    categoria: 'GENERAZIONE',
    azione: 'GENERAZIONE',
    esito: 'COMPLETATO',
    soggetto: '8eec3096-6009-4487-a605-c61e0f2445ad',
    username: 'daniele.ramacci',
    client_id: 'geri-angular-public',
    contesto: 'geban',
    oggetto_tipo: 'documento',
    oggetto_id: '08388c5d906a4152beaab7dc77b5aa0c',
    oggetto_nome: 'TI Collaboratore di Amministrazione',
    dettaglio: { external_context_id: 'GEBAN-2026-000123', hash_file: 'abc' },
    ...overrides,
  };
}

describe('RegistroAttivitaComponent (013 US4)', () => {
  function crea() {
    TestBed.configureTestingModule({
      imports: [RegistroAttivitaComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(RegistroAttivitaComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    return { fixture, http, root: fixture.nativeElement as HTMLElement };
  }

  it('shows who did what, with the user name and a readable outcome', () => {
    const { fixture, http, root } = crea();
    const richiesta = http.expectOne((r) => r.url === URL);
    expect(richiesta.request.params.get('limite')).toBe('50');
    expect(richiesta.request.params.get('salto')).toBe('0');
    richiesta.flush({
      eventi: [
        evento(),
        evento({
          categoria: 'ACCESSO',
          azione: 'ACCESSO_NEGATO',
          esito: '403',
          username: null,
          oggetto_nome: null,
          oggetto_id: 'GET /api/v1/admin/attivita',
        }),
        evento({ categoria: 'MODELLO', azione: 'MODELLO_CREATO', esito: 'OK' }),
      ],
      altri: false,
    });
    fixture.detectChanges();

    const righe = root.querySelectorAll('[data-evento]');
    expect(righe.length).toBe(3);
    expect(righe[0].textContent).toContain('daniele.ramacci');
    expect(righe[0].textContent).toContain('Generazioni');
    expect(righe[0].textContent).toContain('TI Collaboratore di Amministrazione');
    expect(righe[0].querySelector('[data-esito]')?.textContent?.trim()).toBe('Generato');
    // Senza username si mostra l'id del token, non uno spazio vuoto.
    expect(righe[1].textContent).toContain('8eec3096');
    expect(righe[1].querySelector('[data-esito]')?.textContent?.trim()).toBe('Non autorizzato');
    expect(righe[2].textContent).toContain('Modello creato');
    expect(root.querySelector('[data-carica-altri]')).toBeNull();
    http.verify();
  });

  it('opens the details of an event on click', () => {
    const { fixture, http, root } = crea();
    http.expectOne((r) => r.url === URL).flush({ eventi: [evento()], altri: false });
    fixture.detectChanges();

    (root.querySelector('[data-evento]') as HTMLElement).click();
    fixture.detectChanges();
    const dettaglio = root.querySelector('[data-dettaglio-evento]')?.textContent ?? '';
    expect(dettaglio).toContain('GEBAN-2026-000123');
    expect(dettaglio).toContain('08388c5d906a4152beaab7dc77b5aa0c');
    http.verify();
  });

  it('sends only the filters that are set, and loads more with the same filters', async () => {
    const { fixture, http, root } = crea();
    http.expectOne((r) => r.url === URL).flush({ eventi: [], altri: false });
    fixture.detectChanges();
    expect(root.querySelector('[data-registro-vuoto]')).not.toBeNull();
    // I campi del form si legano al modello dopo il primo giro.
    await fixture.whenStable();

    const utente = root.querySelector('[data-filtro-utente]') as HTMLInputElement;
    utente.value = 'mario';
    utente.dispatchEvent(new Event('input'));
    const categoria = root.querySelector('[data-filtro-categoria]') as HTMLSelectElement;
    categoria.value = 'GENERAZIONE';
    categoria.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    (root.querySelector('[data-applica-filtri]') as HTMLButtonElement).click();

    const filtrata = http.expectOne((r) => r.url === URL);
    expect(filtrata.request.params.get('utente')).toBe('mario');
    expect(filtrata.request.params.get('categoria')).toBe('GENERAZIONE');
    expect(filtrata.request.params.has('esito')).toBe(false);
    filtrata.flush({ eventi: [evento()], altri: true });
    fixture.detectChanges();

    (root.querySelector('[data-carica-altri]') as HTMLButtonElement).click();
    const seguito = http.expectOne((r) => r.url === URL);
    expect(seguito.request.params.get('salto')).toBe('1');
    expect(seguito.request.params.get('utente')).toBe('mario');
    seguito.flush({ eventi: [evento({ username: 'secondo' })], altri: false });
    fixture.detectChanges();
    expect(root.querySelectorAll('[data-evento]').length).toBe(2);
    http.verify();
  });
});
