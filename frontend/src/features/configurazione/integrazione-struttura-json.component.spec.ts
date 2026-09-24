import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';
import { IntegrazioneStrutturaJsonComponent } from './integrazione-struttura-json.component';

const GEBAN: IntegrazioneAdmin = {
  id: '00000000-0000-4000-8000-000000000001',
  codice: 'GEBAN',
  nome: 'GEBAN',
  codice_contesto: 'geban',
  modalita: 'SINGOLO_ENDPOINT',
  revisione: 1,
  url: 'https://geban.example/discovery',
  timeout_ms: 5000,
  stato: 'CONNESSO',
  ultima_verifica: null,
};

describe('IntegrazioneStrutturaJsonComponent', () => {
  let fixture: ComponentFixture<IntegrazioneStrutturaJsonComponent>;
  let service: { ottieni: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    service = { ottieni: vi.fn() };
    TestBed.configureTestingModule({
      imports: [IntegrazioneStrutturaJsonComponent],
      providers: [
        provideRouter([]),
        { provide: IntegrazioniAdminService, useValue: service },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => GEBAN.id } } },
        },
      ],
    });
  });

  it('shows the contract example for the selected integration, not the creation form', () => {
    service.ottieni.mockReturnValue(of(GEBAN));
    fixture = TestBed.createComponent(IntegrazioneStrutturaJsonComponent);
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    expect(service.ottieni).toHaveBeenCalledWith(GEBAN.id);
    expect(root.textContent).toContain('Struttura JSON di esempio');
    expect(root.querySelector('pre')?.textContent).toContain('BANDO_CONCORSO');
    expect(root.querySelector('form')).toBeNull();
    expect(
      root.querySelector(
        'a[href="/configurazione/tipi-documento?integrazioneId=' + GEBAN.id + '"]',
      ),
    ).not.toBeNull();
  });

  it('shows an explicit error when the integration cannot be loaded', () => {
    service.ottieni.mockReturnValue(
      throwError(() => ({
        status: 404,
        codice: 'RISORSA_NON_TROVATA',
        messaggio: 'Integrazione non trovata',
      })),
    );
    fixture = TestBed.createComponent(IntegrazioneStrutturaJsonComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Integrazione non trovata');
  });
});
