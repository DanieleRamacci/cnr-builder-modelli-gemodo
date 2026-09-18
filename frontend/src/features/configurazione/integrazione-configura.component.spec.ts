import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { IntegrazioneConfiguraComponent } from './integrazione-configura.component';
import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';
import type { ApiError } from '../../shared/api-error';

function integrazione(overrides: Partial<IntegrazioneAdmin> = {}): IntegrazioneAdmin {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    codice: 'GEBAN',
    nome: 'GEBAN',
    codice_contesto: 'geban',
    modalita: 'SINGOLO_ENDPOINT',
    revisione: 1,
    url: null,
    timeout_ms: 5000,
    stato: 'DEFINITO',
    ultima_verifica: null,
    ...overrides,
  };
}

describe('IntegrazioneConfiguraComponent', () => {
  let fixture: ComponentFixture<IntegrazioneConfiguraComponent>;
  let service: {
    ottieni: ReturnType<typeof vi.fn>;
    configura: ReturnType<typeof vi.fn>;
    verifica: ReturnType<typeof vi.fn>;
  };

  function setup(iniziale: IntegrazioneAdmin) {
    service = {
      ottieni: vi.fn().mockReturnValue(of(iniziale)),
      configura: vi.fn(),
      verifica: vi.fn(),
    };
    TestBed.configureTestingModule({
      imports: [IntegrazioneConfiguraComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: IntegrazioniAdminService, useValue: service },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: iniziale.id }) } },
        },
      ],
    });
    fixture = TestBed.createComponent(IntegrazioneConfiguraComponent);
    fixture.detectChanges();
  }

  it('reloads (never overwrites) on REVISIONE_SUPERATA instead of applying the stale form', () => {
    setup(integrazione({ revisione: 1 }));
    const error: ApiError = {
      codice: 'REVISIONE_SUPERATA',
      messaggio: 'Rileggere la configurazione corrente',
      status: 409,
    };
    service.configura.mockReturnValue(throwError(() => error));
    service.ottieni.mockReturnValue(
      of(integrazione({ revisione: 2, nome: 'Nome aggiornato da un altro' })),
    );

    (
      fixture.componentInstance as unknown as { salvaConfigurazione: () => void }
    ).salvaConfigurazione();
    fixture.detectChanges();

    expect(service.ottieni).toHaveBeenCalledTimes(2); // initial load + reload after conflict
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Rileggere la configurazione corrente');
    const nomeInput = fixture.nativeElement.querySelector('#nome') as HTMLInputElement;
    expect(nomeInput.value).toBe('Nome aggiornato da un altro');
  });

  it('shows DESTINAZIONE_NON_APPROVATA as a form error', () => {
    setup(integrazione());
    const error: ApiError = {
      codice: 'DESTINAZIONE_NON_APPROVATA',
      messaggio: 'Destinazione non approvata',
      status: 422,
    };
    service.configura.mockReturnValue(throwError(() => error));

    (
      fixture.componentInstance as unknown as { salvaConfigurazione: () => void }
    ).salvaConfigurazione();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Destinazione non approvata');
  });

  it('shows a load failure and lets the user retry', () => {
    setup(integrazione());
    service.ottieni.mockReturnValue(
      throwError(() => ({
        codice: 'NON_TROVATO',
        messaggio: 'Integrazione non disponibile',
        status: 404,
      })),
    );
    (
      fixture.componentInstance as unknown as { caricaStatoCorrente: () => void }
    ).caricaStatoCorrente();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Integrazione non disponibile');
    service.ottieni.mockReturnValue(of(integrazione({ nome: 'Ripristinata' })));
    const retry = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('button'),
    ).find((button) => button.textContent?.trim() === 'Riprova')!;
    retry.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Integrazione non disponibile');
    expect((fixture.nativeElement.querySelector('#nome') as HTMLInputElement).value).toBe(
      'Ripristinata',
    );
  });

  it('shows VERIFICA_IN_CORSO as an informational state, not a blocking error', () => {
    setup(integrazione({ url: 'https://software.example.test/discovery' }));
    const error: ApiError = {
      codice: 'VERIFICA_IN_CORSO',
      messaggio: "Verifica gia' avviata",
      status: 409,
    };
    service.verifica.mockReturnValue(throwError(() => error));

    (fixture.componentInstance as unknown as { avviaVerifica: () => void }).avviaVerifica();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain("Verifica gia' avviata");
  });

  it('shows the CONNESSO outcome after a successful verify', () => {
    setup(integrazione({ url: 'https://software.example.test/discovery' }));
    service.verifica.mockReturnValue(
      of(
        integrazione({
          url: 'https://software.example.test/discovery',
          stato: 'CONNESSO',
          ultima_verifica: {
            data: '2026-09-18T10:00:00Z',
            revisione: 1,
            versione_contratto: '0.4.0',
            esito: 'CONFORME',
            errori: [],
          },
        }),
      ),
    );

    (fixture.componentInstance as unknown as { avviaVerifica: () => void }).avviaVerifica();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Connesso');
  });

  it('shows sanitized ERRORE reasons after a failed verify, never a raw exception', () => {
    setup(integrazione({ url: 'https://unreachable.example.test/discovery' }));
    service.verifica.mockReturnValue(
      of(
        integrazione({
          url: 'https://unreachable.example.test/discovery',
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
      ),
    );

    (fixture.componentInstance as unknown as { avviaVerifica: () => void }).avviaVerifica();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Discovery non disponibile');
  });
});
