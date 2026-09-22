import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { DimensioniComponent } from './dimensioni.component';
import { IntegrazioniAdminService } from './integrazioni-admin.service';
import { PolicyDimensioniService } from './policy-dimensioni.service';

const STRUTTURA = {
  codice_tipo_documento: 'BANDO_CONCORSO',
  validita: '2026-09-22T10:00:00Z',
  nodi: [
    {
      codice: 'TD',
      descrizione: 'Tempo determinato',
      tipo_livello: 'tipologia',
      figli: [
        {
          codice: 'RICERCATORE',
          descrizione: 'Ricercatore',
          tipo_livello: 'profilo',
          livelli_possibili: ['I', 'II'],
          livello_base: 'II',
          lingue_possibili: ['IT', 'EN'],
          canale: ['PEC', 'Portale'],
          campi: [
            {
              codice: 'titolo',
              etichetta: 'Titolo',
              tipo: 'string',
              lingua: 'IT',
              obbligatorio: true,
              ordine: 1,
            },
          ],
        },
      ],
    },
  ],
};

describe('DimensioniComponent', () => {
  let fixture: ComponentFixture<DimensioniComponent>;
  let policyService: {
    struttura: ReturnType<typeof vi.fn>;
    policy: ReturnType<typeof vi.fn>;
    salvaPolicy: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    policyService = {
      struttura: vi.fn().mockReturnValue(of(STRUTTURA)),
      policy: vi.fn().mockReturnValue(
        of({
          codice_tipo_documento: 'BANDO_CONCORSO',
          policy: [
            { nome_dimensione: 'lingua', consente_valore_generico: false },
            { nome_dimensione: 'livello', consente_valore_generico: true },
          ],
          dimensioni_non_configurate: [{ nome_dimensione: 'canale' }],
        }),
      ),
      salvaPolicy: vi
        .fn()
        .mockReturnValue(of({ nome_dimensione: 'canale', consente_valore_generico: false })),
    };
    TestBed.configureTestingModule({
      imports: [DimensioniComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: convertToParamMap({ codice: 'BANDO_CONCORSO' }),
              queryParamMap: convertToParamMap({ integrazioneId: 'integration-1' }),
            },
          },
        },
        {
          provide: IntegrazioniAdminService,
          useValue: {
            ottieni: vi.fn().mockReturnValue(
              of({
                id: 'integration-1',
                codice: 'GEBAN',
                nome: 'GEBAN',
                codice_contesto: 'geban',
                stato: 'CONNESSO',
                revisione: 1,
                timeout_ms: 5000,
              }),
            ),
          },
        },
        { provide: PolicyDimensioniService, useValue: policyService },
      ],
    });
  });

  it('navigates the live tree node by node and shows saved and new dimensions', () => {
    fixture = TestBed.createComponent(DimensioniComponent);
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('[data-node="TD"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="RICERCATORE"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Ricercatore');
    expect(text).toContain('lingua');
    expect(text).toContain('configurata');
    expect(text).toContain('canale');
    expect(text).toContain('nuova, non ancora configurata');
    expect(text).toContain('Titolo');
  });

  it('saves a policy for the whole document type', () => {
    fixture = TestBed.createComponent(DimensioniComponent);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="TD"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="RICERCATORE"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('#canale-distinto') as HTMLInputElement).click();
    fixture.detectChanges();
    (
      fixture.nativeElement.querySelector('[data-save-policy="canale"]') as HTMLButtonElement
    ).click();

    expect(policyService.salvaPolicy).toHaveBeenCalledWith('integration-1', 'BANDO_CONCORSO', {
      nome_dimensione: 'canale',
      consente_valore_generico: false,
    });
  });

  it('shows the exact live JSON next to the tree', () => {
    fixture = TestBed.createComponent(DimensioniComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-live-json]').textContent).toContain(
      '"codice_tipo_documento": "BANDO_CONCORSO"',
    );
  });

  it('shows a source error and never a silent empty list', () => {
    policyService.struttura.mockReturnValue(
      throwError(() => ({
        status: 502,
        codice: 'DISCOVERY_NON_DISPONIBILE',
        messaggio: 'Timeout GEBAN',
      })),
    );
    fixture = TestBed.createComponent(DimensioniComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain("l'integrazione non risponde");
    expect(fixture.nativeElement.textContent).toContain('Timeout GEBAN');
    expect(fixture.nativeElement.querySelector('[data-empty-tree]')).toBeNull();
  });
});
