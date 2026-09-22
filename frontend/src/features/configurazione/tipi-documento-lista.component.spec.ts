import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';
import { PolicyDimensioniService } from './policy-dimensioni.service';
import { TipiDocumentoListaComponent } from './tipi-documento-lista.component';

function integrazione(overrides: Partial<IntegrazioneAdmin> = {}): IntegrazioneAdmin {
  return {
    id: 'integration-1',
    codice: 'GEBAN',
    nome: 'GEBAN',
    codice_contesto: 'geban',
    modalita: 'SINGOLO_ENDPOINT',
    revisione: 1,
    url: 'https://geban.example.test/discovery',
    timeout_ms: 5000,
    stato: 'CONNESSO',
    ultima_verifica: null,
    ...overrides,
  };
}

describe('TipiDocumentoListaComponent', () => {
  let fixture: ComponentFixture<TipiDocumentoListaComponent>;
  let integrations: { lista: ReturnType<typeof vi.fn> };
  let policies: { tipiDocumento: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    integrations = { lista: vi.fn().mockReturnValue(of([integrazione()])) };
    policies = {
      tipiDocumento: vi.fn().mockReturnValue(of(['BANDO_CONCORSO', 'VERBALE'])),
    };
    TestBed.configureTestingModule({
      imports: [TipiDocumentoListaComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({}) } },
        },
        { provide: IntegrazioniAdminService, useValue: integrations },
        { provide: PolicyDimensioniService, useValue: policies },
      ],
    });
  });

  it('lists every document type returned live by a connected integration', () => {
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(2);
    expect(fixture.nativeElement.textContent).toContain('BANDO_CONCORSO');
    expect(fixture.nativeElement.textContent).toContain('VERBALE');
    const links = [...fixture.nativeElement.querySelectorAll('tbody a')] as HTMLAnchorElement[];
    expect(links[0].getAttribute('href')).toContain('integrazioneId=integration-1');
  });

  it('does not show disconnected integrations as configurable sources', () => {
    integrations.lista.mockReturnValue(of([integrazione({ stato: 'DEFINITO' })]));
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();

    expect(policies.tipiDocumento).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Nessun tipo disponibile');
  });

  it('shows a source failure instead of an empty list', () => {
    policies.tipiDocumento.mockReturnValue(
      throwError(() => ({
        status: 502,
        codice: 'DISCOVERY_NON_DISPONIBILE',
        messaggio: 'Timeout GEBAN',
      })),
    );
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Timeout GEBAN');
    expect(fixture.nativeElement.textContent).toContain('Nessun elenco vuoto');
    expect(fixture.nativeElement.textContent).not.toContain('Nessun tipo disponibile');
  });

  it('does not expose the legacy manual document type creation action', () => {
    fixture = TestBed.createComponent(TipiDocumentoListaComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Configura struttura');
    expect(fixture.nativeElement.querySelector('a[href*="nuovo"]')).toBeNull();
  });
});
