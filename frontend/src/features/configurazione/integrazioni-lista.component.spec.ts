import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import Keycloak from 'keycloak-js';

import { IntegrazioniListaComponent } from './integrazioni-lista.component';
import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';

function integrazione(overrides: Partial<IntegrazioneAdmin>): IntegrazioneAdmin {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    codice: 'SOFTWARE_DEMO',
    nome: 'Software demo',
    codice_contesto: 'demo',
    modalita: 'SINGOLO_ENDPOINT',
    revisione: 1,
    url: null,
    timeout_ms: 5000,
    stato: 'DEFINITO',
    ultima_verifica: null,
    ...overrides,
  };
}

describe('IntegrazioniListaComponent', () => {
  let fixture: ComponentFixture<IntegrazioniListaComponent>;
  let service: { lista: ReturnType<typeof vi.fn> };
  let login: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    service = { lista: vi.fn() };
    login = vi.fn().mockResolvedValue(undefined);
    TestBed.configureTestingModule({
      imports: [IntegrazioniListaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: IntegrazioniAdminService, useValue: service },
        { provide: Keycloak, useValue: { login } },
      ],
    });
  });

  it('forces a new authentication after server rejection without reporting expiration', () => {
    service.lista.mockReturnValue(
      throwError(() => ({
        status: 401,
        codice: 'ACCESSO_NON_AUTENTICATO',
        messaggio: 'Token non valido',
      })),
    );
    fixture = TestBed.createComponent(IntegrazioniListaComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain("server ha rifiutato l'autenticazione");
    fixture.nativeElement.querySelector('button').click();
    expect(login).toHaveBeenCalledWith({
      redirectUri: window.location.origin + '/configurazione',
      prompt: 'login',
    });
  });

  it('shows the empty state when no integration exists yet (FR-021)', () => {
    service.lista.mockReturnValue(of([]));
    fixture = TestBed.createComponent(IntegrazioniListaComponent);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Nessuna integrazione');
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(0);
  });

  it('shows a neutral badge for DEFINITO', () => {
    service.lista.mockReturnValue(of([integrazione({ stato: 'DEFINITO' })]));
    fixture = TestBed.createComponent(IntegrazioniListaComponent);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Da completare');
    expect(fixture.nativeElement.querySelector('tbody a').getAttribute('href')).toBe(
      '/00000000-0000-4000-8000-000000000001',
    );
  });

  it('shows a failed load instead of an empty registry and allows retry', () => {
    service.lista.mockReturnValue(
      throwError(() => ({ status: 503, messaggio: 'Servizio non disponibile' })),
    );
    fixture = TestBed.createComponent(IntegrazioniListaComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Servizio non disponibile');
    expect(fixture.nativeElement.textContent).not.toContain('Nessuna integrazione');
    service.lista.mockReturnValue(of([integrazione({})]));
    fixture.nativeElement.querySelector('button').click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Da completare');
  });

  it('shows a positive badge for CONNESSO', () => {
    service.lista.mockReturnValue(
      of([
        integrazione({
          stato: 'CONNESSO',
          ultima_verifica: {
            data: '2026-09-18T10:00:00Z',
            revisione: 1,
            versione_contratto: '0.4.0',
            esito: 'CONFORME',
            errori: [],
          },
        }),
      ]),
    );
    fixture = TestBed.createComponent(IntegrazioniListaComponent);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Connesso');
  });

  it('shows an error badge with sanitized reasons for ERRORE', () => {
    service.lista.mockReturnValue(
      of([
        integrazione({
          stato: 'ERRORE',
          ultima_verifica: {
            data: '2026-09-18T10:00:00Z',
            revisione: 1,
            versione_contratto: '0.4.0',
            esito: 'NON_RAGGIUNGIBILE',
            errori: [
              { codice: 'DISCOVERY_NON_DISPONIBILE', messaggio: 'Discovery non disponibile' },
            ],
          },
        }),
      ]),
    );
    fixture = TestBed.createComponent(IntegrazioniListaComponent);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Errore');
    expect(text).toContain('Discovery non disponibile');
  });
});
