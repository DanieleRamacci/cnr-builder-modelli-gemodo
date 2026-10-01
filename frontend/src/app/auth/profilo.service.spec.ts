import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ProfiloService } from './profilo.service';

const PROFILO = {
  soggetto: 's',
  client_id: 'gemodo-frontend',
  permessi_diretti: [],
  contesti: [],
  permessi: ['GEMODO_MODELLI_GESTORE'],
};

describe('ProfiloService (007 T115)', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    return {
      servizio: TestBed.inject(ProfiloService),
      http: TestBed.inject(HttpTestingController),
    };
  }

  it('asks the backend once, however many components need it', () => {
    const { servizio, http } = setup();
    servizio.carica().subscribe();
    servizio.carica().subscribe();
    http.expectOne('/api/v1/builder/profilo').flush(PROFILO);

    expect(servizio.ha('GEMODO_MODELLI_GESTORE')).toBe(true);
    expect(servizio.ha('GEMODO_ADMIN')).toBe(false);
    http.verify();
  });

  it('knows nothing until the profile arrives, and retries after an error', () => {
    const { servizio, http } = setup();
    expect(servizio.ha('GEMODO_MODELLI_GESTORE')).toBe(false);
    servizio.carica().subscribe({ error: () => undefined });
    http.expectOne('/api/v1/builder/profilo').flush(null, { status: 503, statusText: 'x' });
    expect(servizio.profilo()).toBeNull();

    servizio.carica().subscribe();
    http.expectOne('/api/v1/builder/profilo').flush(PROFILO);
    expect(servizio.ha('GEMODO_MODELLI_GESTORE')).toBe(true);
    http.verify();
  });
});
