import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { TipiDocumentoListaComponent } from './tipi-documento-lista.component';
import { TipiDocumentoService, type TipoDocumentoDashboard } from './tipi-documento.service';

function tipo(overrides: Partial<TipoDocumentoDashboard>): TipoDocumentoDashboard {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    codice: 'BANDO_CONCORSO',
    nome: 'Bando di concorso',
    codice_contesto: 'geban',
    stato_integrazione: 'CONNESSO',
    ...overrides,
  };
}

describe('TipiDocumentoListaComponent', () => {
  let fixture: ComponentFixture<TipiDocumentoListaComponent>;
  let service: { dashboard: ReturnType<typeof vi.fn>; disattiva: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    service = { dashboard: vi.fn(), disattiva: vi.fn() };
    TestBed.configureTestingModule({
      imports: [TipiDocumentoListaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TipiDocumentoService, useValue: service },
      ],
    });
  });

  it('lists both rows of a duplicated codice so the admin can tell them apart by id/stato', () => {
    service.dashboard.mockReturnValue(
      of([
        tipo({ id: 'a', stato_integrazione: 'INCOMPLETO' }),
        tipo({ id: 'b', stato_integrazione: 'CONNESSO' }),
      ]),
    );
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(2);
  });

  it('deactivates the row the admin confirms and reloads the list', () => {
    service.dashboard.mockReturnValueOnce(of([tipo({ id: 'a', stato_integrazione: 'INCOMPLETO' })]));
    service.disattiva.mockReturnValue(of(undefined));
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();

    service.dashboard.mockReturnValueOnce(of([]));
    (fixture.nativeElement.querySelector('button.btn-outline-danger') as HTMLButtonElement).click();

    expect(service.disattiva).toHaveBeenCalledWith('a');
    expect(service.dashboard).toHaveBeenCalledTimes(2);
  });

  it('does not call the backend when the admin cancels the confirmation', () => {
    service.dashboard.mockReturnValue(of([tipo({ id: 'a' })]));
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('button.btn-outline-danger') as HTMLButtonElement).click();

    expect(service.disattiva).not.toHaveBeenCalled();
  });

  it('shows TIPO_DOCUMENTO_HA_MODELLI as a form error instead of a generic one', () => {
    service.dashboard.mockReturnValue(of([tipo({ id: 'a' })]));
    service.disattiva.mockReturnValue(
      throwError(() => ({
        status: 409,
        codice: 'TIPO_DOCUMENTO_HA_MODELLI',
        messaggio: 'Non disattivabile: esistono modelli collegati a questo tipo documento',
      })),
    );
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('button.btn-outline-danger') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Non disattivabile');
  });
});
