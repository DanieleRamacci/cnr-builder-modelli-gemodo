import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Keycloak from 'keycloak-js';
import { HomeComponent } from './home.component';
import { ProfileComponent } from './profile.component';
describe('home and profile', () => {
  it('shows an explicit denial without operational links', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Keycloak, useValue: { tokenParsed: {} } },
      ],
    });
    const fixture = TestBed.createComponent(HomeComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Non sei autorizzato');
    expect(fixture.nativeElement.querySelector('a')).toBeNull();
  });
  it('shows both operational areas for an admin manager', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Keycloak,
          useValue: {
            tokenParsed: {
              resource_access: {
                'gemodo-backend': { roles: ['GEMODO_ADMIN', 'GEMODO_MODELLI_GESTORE'] },
              },
            },
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(HomeComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/configurazione/integrazioni').flush([]);
    http.expectOne('/api/v1/builder/contesti').flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('a[href="/configurazione"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('a[href="/contesti"]')).toBeTruthy();
    expect(fixture.nativeElement.textContent).not.toContain('canale');
    http.verify();
  });
  // 007 FR-030: fino al 2026-09-23 questa schermata mostrava integrazioni
  // inventate nel template e nascondeva quelle vere. Questi test sono la
  // guardia contro un ritorno a quel comportamento.
  it('shows the integrations that really exist, never invented ones', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Keycloak,
          useValue: {
            tokenParsed: { resource_access: { 'gemodo-backend': { roles: ['GEMODO_ADMIN'] } } },
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(HomeComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/configurazione/integrazioni').flush([
      {
        id: 'a1',
        codice: 'Geban',
        nome: 'Geban',
        codice_contesto: 'geban',
        modalita: 'SINGOLO_ENDPOINT',
        revisione: 5,
        url: 'https://esempio.test/discovery',
        timeout_ms: 5000,
        stato: 'CONNESSO',
        ultima_verifica: { data: '2026-09-22T12:25:38Z', esito: 'CONFORME', errori: [] },
      },
    ]);
    fixture.detectChanges();
    const testo = fixture.nativeElement.textContent as string;
    expect(testo).toContain('Geban');
    expect(testo).toContain('Connesso');
    expect(testo).toContain('ultima verifica conforme');
    expect(testo).not.toContain('SIGLA');
    expect(testo).not.toContain('Appalti e contratti');
    http.verify();
  });
  it('says the list is empty instead of inventing entries', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Keycloak,
          useValue: {
            tokenParsed: { resource_access: { 'gemodo-backend': { roles: ['GEMODO_ADMIN'] } } },
          },
        },
      ],
    });
    const fixture = TestBed.createComponent(HomeComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/configurazione/integrazioni').flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Nessuna integrazione registrata');
    http.verify();
  });
  it('keeps the token hidden until requested and logs out through Keycloak', () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    TestBed.configureTestingModule({
      providers: [
        {
          provide: Keycloak,
          useValue: { token: 'TEST_TOKEN', tokenParsed: { name: 'Demo Utente' }, logout },
        },
      ],
    });
    const fixture = TestBed.createComponent(ProfileComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Demo Utente');
    expect(fixture.nativeElement.textContent).not.toContain('TEST_TOKEN');
    fixture.nativeElement.querySelector('button').click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('TEST_TOKEN');
    fixture.nativeElement.querySelectorAll('button')[1].click();
    expect(logout).toHaveBeenCalledWith({ redirectUri: window.location.origin });
  });
});
