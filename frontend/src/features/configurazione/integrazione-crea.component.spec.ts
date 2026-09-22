import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { throwError, of } from 'rxjs';

import { IntegrazioneCreaComponent } from './integrazione-crea.component';
import { IntegrazioniAdminService } from './integrazioni-admin.service';
import type { ApiError } from '../../shared/api-error';

describe('IntegrazioneCreaComponent', () => {
  let fixture: ComponentFixture<IntegrazioneCreaComponent>;
  let service: { crea: ReturnType<typeof vi.fn> };
  let router: Router;

  beforeEach(() => {
    service = { crea: vi.fn() };
    TestBed.configureTestingModule({
      imports: [IntegrazioneCreaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: IntegrazioniAdminService, useValue: service },
      ],
    });
    fixture = TestBed.createComponent(IntegrazioneCreaComponent);
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  function fillAndSubmit(codice: string, nome: string, contesto: string) {
    const el = fixture.nativeElement as HTMLElement;
    (el.querySelector('#codice') as HTMLInputElement).value = codice;
    (el.querySelector('#codice') as HTMLInputElement).dispatchEvent(new Event('input'));
    (el.querySelector('#nome') as HTMLInputElement).value = nome;
    (el.querySelector('#nome') as HTMLInputElement).dispatchEvent(new Event('input'));
    (el.querySelector('#codiceContesto') as HTMLInputElement).value = contesto;
    (el.querySelector('#codiceContesto') as HTMLInputElement).dispatchEvent(new Event('input'));
    fixture.detectChanges();
    (el.querySelector('form') as HTMLFormElement).dispatchEvent(new Event('submit'));
    fixture.detectChanges();
  }

  it('rejects an empty codice without calling the backend (client-side length validation)', () => {
    fillAndSubmit('', 'Nome valido', 'geban');
    expect(service.crea).not.toHaveBeenCalled();
  });

  it('creates the integration and navigates to its configure screen on success', () => {
    service.crea.mockReturnValue(
      of({
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
      }),
    );
    const navigateSpy = vi.spyOn(router, 'navigate');
    fillAndSubmit('GEBAN', 'GEBAN', 'geban');
    expect(service.crea).toHaveBeenCalledWith({
      codice: 'GEBAN',
      nome: 'GEBAN',
      codice_contesto: 'geban',
    });
    expect(navigateSpy).toHaveBeenCalledWith([
      '/configurazione/contesti',
      '00000000-0000-4000-8000-000000000001',
      'integrazione',
    ]);
  });

  it('shows INTEGRAZIONE_DUPLICATA as a form error, not a generic one', () => {
    const error: ApiError = {
      codice: 'INTEGRAZIONE_DUPLICATA',
      messaggio: 'Codice integrazione gia registrato',
      status: 409,
    };
    service.crea.mockReturnValue(throwError(() => error));
    fillAndSubmit('GEBAN', 'GEBAN', 'geban');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Codice integrazione gia registrato');
  });
});
