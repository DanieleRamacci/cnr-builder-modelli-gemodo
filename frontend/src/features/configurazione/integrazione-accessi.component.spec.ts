import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { IntegrazioneAccessiComponent } from './integrazione-accessi.component';
import {
  IntegrazioniAdminService,
  type AccessiIntegrazione,
  type IntegrazioneAdmin,
} from './integrazioni-admin.service';

const ID = '00000000-0000-4000-8000-000000000001';
const ALTRA = '00000000-0000-4000-8000-000000000002';

const PERMESSI: AccessiIntegrazione['permessi_disponibili'] = [
  { codice: 'DOCUMENTI_VIEWER', descrizione: 'Consulta il catalogo' },
  { codice: 'DOCUMENTI_GENERATORE', descrizione: 'Genera documenti' },
  { codice: 'GEMODO_MODELLI_GESTORE', descrizione: 'Crea e pubblica i modelli' },
];

function integrazione(id: string, contesto: string): IntegrazioneAdmin {
  return {
    id,
    codice: contesto.toUpperCase(),
    nome: contesto,
    codice_contesto: contesto,
    modalita: 'SINGOLO_ENDPOINT',
    revisione: 1,
    url: null,
    timeout_ms: 5000,
    stato: 'DEFINITO',
    ultima_verifica: null,
  };
}

function profilo(
  ruoli: AccessiIntegrazione['ruoli'],
  client: string[] = [],
  contesto = 'test',
): AccessiIntegrazione {
  return { codice_contesto: contesto, ruoli, client, permessi_disponibili: PERMESSI };
}

describe('IntegrazioneAccessiComponent (001 T091)', () => {
  let fixture: ComponentFixture<IntegrazioneAccessiComponent>;
  let service: Record<'ottieni' | 'accessi' | 'lista' | 'impostaAccessi', ReturnType<typeof vi.fn>>;

  function setup(iniziale: AccessiIntegrazione, altre: Record<string, AccessiIntegrazione> = {}) {
    service = {
      ottieni: vi.fn().mockReturnValue(of(integrazione(ID, 'test'))),
      accessi: vi.fn((id: string) => of(id === ID ? iniziale : altre[id])),
      lista: vi.fn().mockReturnValue(of([integrazione(ID, 'test'), integrazione(ALTRA, 'geban')])),
      impostaAccessi: vi.fn((_id: string, body: AccessiIntegrazione) =>
        of(profilo(body.ruoli, body.client)),
      ),
    };
    TestBed.configureTestingModule({
      imports: [IntegrazioneAccessiComponent],
      providers: [
        provideRouter([]),
        { provide: IntegrazioniAdminService, useValue: service },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: ID }) } },
        },
      ],
    });
    fixture = TestBed.createComponent(IntegrazioneAccessiComponent);
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;
  const pulsante = (testo: string) =>
    Array.from(el().querySelectorAll('button')).find(
      (b) => b.textContent?.trim() === testo,
    ) as HTMLButtonElement;
  const casella = (etichetta: string) =>
    el().querySelector(`input[aria-label="${etichetta}"]`) as HTMLInputElement;

  it('mostra i ruoli con i permessi che concedono e cosa consente ciascun permesso', () => {
    setup(profilo([{ ruolo: 'ROLE_MANAGER', permessi: ['GEMODO_MODELLI_GESTORE'] }]));

    expect(casella('ROLE_MANAGER: GEMODO_MODELLI_GESTORE').checked).toBe(true);
    expect(casella('ROLE_MANAGER: DOCUMENTI_VIEWER').checked).toBe(false);
    expect(el().textContent).toContain('Crea e pubblica i modelli');
    expect(el().textContent).toContain('ROLE_MANAGER#test');
    expect(pulsante('Salva profilo di accesso').disabled).toBe(true);
  });

  it('un profilo vuoto dice che nessuno entra', () => {
    setup(profilo([]));

    expect(el().textContent).toContain("Nessun ruolo: nessun utente di questo contesto puo' usare");
  });

  it('salva il profilo intero dopo una modifica', () => {
    setup(profilo([{ ruolo: 'ROLE_USER', permessi: ['DOCUMENTI_VIEWER'] }], ['geban-backend']));

    casella('ROLE_USER: DOCUMENTI_GENERATORE').click();
    fixture.detectChanges();
    pulsante('Salva profilo di accesso').click();
    fixture.detectChanges();

    expect(service.impostaAccessi).toHaveBeenCalledWith(ID, {
      ruoli: [{ ruolo: 'ROLE_USER', permessi: ['DOCUMENTI_GENERATORE', 'DOCUMENTI_VIEWER'] }],
      client: ['geban-backend'],
    });
    expect(el().textContent).toContain('Profilo salvato');
    expect(pulsante('Salva profilo di accesso').disabled).toBe(true);
  });

  it('non salva un ruolo senza nome, con #contesto o senza permessi', () => {
    setup(profilo([]));

    pulsante('Aggiungi ruolo').click();
    fixture.detectChanges();
    expect(el().textContent).toContain('Ogni riga deve avere il nome del ruolo.');
    expect(pulsante('Salva profilo di accesso').disabled).toBe(true);

    const nome = casella('Ruolo 1');
    nome.value = 'ROLE_MANAGER#test';
    nome.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(el().textContent).toContain('senza "#contesto"');
    expect(el().textContent).toContain('almeno un permesso');
    expect(pulsante('Salva profilo di accesso').disabled).toBe(true);
    expect(service.impostaAccessi).not.toHaveBeenCalled();
  });

  it("copia il profilo di un'altra integrazione senza salvarlo", () => {
    const geban = profilo(
      [{ ruolo: 'ROLE_MANAGER', permessi: ['GEMODO_MODELLI_GESTORE', 'DOCUMENTI_VIEWER'] }],
      ['geban-backend'],
      'geban',
    );
    setup(profilo([]), { [ALTRA]: geban });

    const select = el().querySelector('#copia-da') as HTMLSelectElement;
    select.value = ALTRA;
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(casella('ROLE_MANAGER: GEMODO_MODELLI_GESTORE').checked).toBe(true);
    expect(el().textContent).toContain('geban-backend');
    expect(service.impostaAccessi).not.toHaveBeenCalled();
    expect(pulsante('Salva profilo di accesso').disabled).toBe(false);
  });
});
