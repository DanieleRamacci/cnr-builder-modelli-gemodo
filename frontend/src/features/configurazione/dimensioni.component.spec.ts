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
          area_geografica: ['NORD', 'CENTRO', 'SUD'],
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
            {
              nome_dimensione: 'lingua',
              consente_valore_generico: false,
              valore_default: 'IT',
              modelli_pubblicati_che_la_valorizzano: 2,
            },
            {
              nome_dimensione: 'livello_professionale',
              consente_valore_generico: true,
              valore_default: null,
              modelli_pubblicati_che_la_valorizzano: 1,
            },
          ],
          dimensioni_non_configurate: [
            {
              nome_dimensione: 'area_geografica',
              motivo: 'Nessuna policy registrata per questa dimensione',
              modelli_pubblicati_che_la_valorizzano: 3,
            },
          ],
        }),
      ),
      salvaPolicy: vi.fn().mockReturnValue(
        of({
          nome_dimensione: 'area_geografica',
          consente_valore_generico: false,
          valore_default: null,
          modelli_pubblicati_che_la_valorizzano: 3,
        }),
      ),
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
    expect(text).toContain('area_geografica');
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

    (fixture.nativeElement.querySelector('#area_geografica-distinto') as HTMLInputElement).click();
    fixture.detectChanges();
    (
      fixture.nativeElement.querySelector(
        '[data-save-policy="area_geografica"]',
      ) as HTMLButtonElement
    ).click();

    expect(policyService.salvaPolicy).toHaveBeenCalledWith('integration-1', 'BANDO_CONCORSO', {
      nome_dimensione: 'area_geografica',
      consente_valore_generico: false,
      valore_default: null,
    });
  });

  it('allows a generic language policy and warns using live model counts', () => {
    fixture = TestBed.createComponent(DimensioniComponent);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="TD"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="RICERCATORE"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const modifica = Array.from<HTMLButtonElement>(
      fixture.nativeElement.querySelectorAll(
        '.dimension-card button',
      ) as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.closest('.dimension-card')?.textContent?.includes('lingua')) as
      HTMLButtonElement | undefined;
    modifica?.click();
    fixture.detectChanges();
    const generico = fixture.nativeElement.querySelector('#lingua-generico') as HTMLInputElement;
    expect(generico.disabled).toBe(false);
    generico.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-policy-impact]').textContent).toContain(
      '2 modelli pubblicati',
    );
  });

  it('warns for an arbitrary dimension using that dimension model count', () => {
    fixture = TestBed.createComponent(DimensioniComponent);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="TD"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="RICERCATORE"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    (fixture.nativeElement.querySelector('#area_geografica-generico') as HTMLInputElement).click();
    fixture.detectChanges();

    const warning = fixture.nativeElement.querySelector('[data-policy-impact]');
    expect(warning.textContent).toContain('3 modelli pubblicati');
    expect(warning.closest('.dimension-card')?.textContent).toContain('area_geografica');
  });

  it('signals a configured default that disappeared from the live tree', () => {
    policyService.policy.mockReturnValue(
      of({
        codice_tipo_documento: 'BANDO_CONCORSO',
        policy: [
          {
            nome_dimensione: 'lingua',
            consente_valore_generico: false,
            valore_default: 'FR',
            modelli_pubblicati_che_la_valorizzano: 2,
          },
        ],
        dimensioni_non_configurate: [],
      }),
    );
    fixture = TestBed.createComponent(DimensioniComponent);
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="TD"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('[data-node="RICERCATORE"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    const warning = fixture.nativeElement.querySelector('[data-stale-default]');
    expect(warning.textContent).toContain('FR');
    expect(warning.textContent).toContain('non è più presente');
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
