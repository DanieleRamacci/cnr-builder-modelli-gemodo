import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { provideDesignAngularKit } from 'design-angular-kit';
import { IntegrazioniManagerComponent } from './integrazioni-manager.component';

const version = {
  id: 'version',
  public_id: 42,
  modello_id: 'model',
  numero_versione: 1,
  stato: 'BOZZA',
  pubblicato_at: null,
};
const model = {
  id: 'model',
  public_id: 1,
  codice: 'MODEL',
  nome: 'Modello CTER',
  codice_tipo_documento: 'BANDO',
  codice_categoria: 'CTER',
  codice_tipologia: 'TD',
  percorso_categorizzazione: ['TD', 'CTER'],
  variante: 'STANDARD',
  lingua: 'IT',
  livello_professionale: 'VI',
  derivato_da_modello_id: null,
  codice_contesto: 'geban',
  integrazione_id: 'source',
  created_at: '2026-09-18T12:00:00Z',
  versioni: [version],
};

describe('context models and lifecycle', () => {
  /** Le azioni di riga vivono nel kebab (design 1b): va aperto prima. */
  function apriKebab(fixture: { nativeElement: HTMLElement; detectChanges: () => void }) {
    fixture.nativeElement.querySelector<HTMLButtonElement>('button.kebab')!.click();
    fixture.detectChanges();
  }

  it('deletes only after confirmation and reloads the list', () => {
    const { fixture, http } = setup(['geban']);
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelector(
      'dialog[aria-labelledby="deletion-title"]',
    ) as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    apriKebab(fixture);
    Array.from(
      fixture.nativeElement.querySelectorAll(
        '.menu-azioni button',
      ) as NodeListOf<HTMLButtonElement>,
    )
      .find((b) => b.textContent?.trim() === 'Elimina')!
      .click();
    fixture.detectChanges();
    expect(dialog.showModal).toHaveBeenCalled();
    http.expectNone((r) => r.method === 'DELETE');
    Array.from(dialog.querySelectorAll('button'))
      .find((b) => b.textContent?.trim() === 'Elimina')!
      .click();
    const request = http.expectOne('/api/v1/builder/modelli/model');
    expect(request.request.method).toBe('DELETE');
    request.flush(null);
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Nessun modello presente');
    http.verify();
  });
  function setup(
    contexts = ['geban', 'altro'],
    ctxId: string | null = null,
    view: string | null = null,
  ) {
    TestBed.configureTestingModule({
      providers: [
        provideDesignAngularKit(),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        ...(ctxId || view
          ? [
              {
                provide: ActivatedRoute,
                useValue: {
                  snapshot: {
                    paramMap: { get: (name: string) => (name === 'ctxId' ? ctxId : null) },
                    queryParamMap: { get: (name: string) => (name === 'view' ? view : null) },
                  },
                },
              },
            ]
          : []),
      ],
    });
    const fixture = TestBed.createComponent(IntegrazioniManagerComponent);
    const http = TestBed.inject(HttpTestingController);
    http.match('./bootstrap-italia/i18n/it.json').forEach((r) => r.flush({}));
    http.expectOne('/api/v1/builder/contesti').flush(contexts);
    http
      .expectOne('/api/v1/builder/integrazioni')
      .flush([{ id: 'source', codice: 'GEBAN', nome: 'Software', codice_contesto: 'geban' }]);
    return { fixture, http };
  }
  it('lists the models of the context taken from the /contesti/:ctxId/modelli route', () => {
    const { fixture, http } = setup(['geban', 'altro'], 'altro');
    const first = http.expectOne((r) => r.url === '/api/v1/builder/modelli');
    expect(first.request.params.get('codice_contesto')).toBe('altro');
    first.flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('nav button')).toBeNull();
    expect(fixture.nativeElement.querySelector('a[href="/contesti"]')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Nessun modello presente');
    http.verify();
  });
  it('shows the model table with language and level for the default context', () => {
    const { fixture, http } = setup();
    const first = http.expectOne((r) => r.url === '/api/v1/builder/modelli');
    expect(first.request.params.get('codice_contesto')).toBe('geban');
    first.flush([model]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Modello CTER');
    expect(fixture.nativeElement.textContent).toContain('Italiano');
    expect(fixture.nativeElement.textContent).toContain('VI');
    http.verify();
  });
  it('refuses a context in the URL that the backend did not authorize, without querying models', () => {
    const { fixture, http } = setup(['geban'], 'estraneo');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role=alert]')?.textContent).toContain(
      'non autorizzato',
    );
    http.verify();
  });
  const altro = {
    ...model,
    id: 'model2',
    public_id: 2,
    codice: 'ALTRO-MODELLO',
    nome: 'Bando tecnologi',
    lingua: 'EN',
    livello_professionale: null,
    versioni: [{ ...version, id: 'v2', stato: 'PUBBLICATO' }],
  };
  it('summarises the loaded models by the state of their latest version', () => {
    const { fixture, http } = setup(['geban'], 'geban');
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model, altro]);
    fixture.detectChanges();
    const metrics = fixture.nativeElement.querySelector('.metriche') as HTMLElement;
    const values = Array.from(metrics.querySelectorAll('.metrica')).map((cell) => [
      cell.querySelector('.etichetta')!.textContent!.trim(),
      cell.querySelector('.valore')!.textContent!.trim(),
    ]);
    expect(values).toEqual([
      ['Modelli', '2'],
      ['Pubblicati', '1'],
      ['In revisione', '0'],
      ['Bozze', '1'],
    ]);
    http.verify();
  });
  it('filters the loaded models by search text and by state', () => {
    const { fixture, http } = setup(['geban'], 'geban');
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model, altro]);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const search = root.querySelector<HTMLInputElement>('input[type=search]')!;
    search.value = 'tecnologi';
    search.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(root.textContent).toContain('Bando tecnologi');
    expect(root.textContent).not.toContain('Modello CTER');
    search.value = '';
    search.dispatchEvent(new Event('input'));
    const stato = root.querySelector<HTMLSelectElement>('select[aria-label="Filtra per stato"]')!;
    stato.value = 'BOZZA';
    stato.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(root.textContent).toContain('Modello CTER');
    expect(root.textContent).not.toContain('Bando tecnologi');
    http.verify();
  });
  it('shows the grid variant for ?view=grid with the same workflow actions', () => {
    const { fixture, http } = setup(['geban'], 'geban', 'grid');
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model, altro]);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.querySelector('table')).toBeNull();
    expect(root.querySelectorAll('article.card-modello').length).toBe(2);
    expect(root.textContent).toContain('Invia in revisione');
    http.verify();
  });
  it('does not offer the English edition here: it belongs to the model screen (1b)', () => {
    const { fixture, http } = setup(['geban'], 'geban');
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.textContent).not.toContain('Crea versione inglese');
    expect(root.querySelector(`a[href="/modelli/${model.id}/builder"]`)).not.toBeNull();
    http.verify();
  });

  it('keeps lifecycle and delete in the row kebab, as the 1b design prescribes', () => {
    const { fixture, http } = setup(['geban'], 'geban');
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const kebab = root.querySelector<HTMLButtonElement>('button.kebab')!;
    expect(kebab).toBeTruthy();
    expect(root.querySelector('.menu-azioni')).toBeNull();
    kebab.click();
    fixture.detectChanges();
    const menu = root.querySelector('.menu-azioni')!;
    expect(menu.textContent).toContain('Invia in revisione');
    expect(menu.textContent).toContain('Elimina');
    http.verify();
  });

  it('confirms each transition and displays state only after the backend reload', () => {
    const { fixture, http } = setup(['geban']);
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelector('dialog') as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    apriKebab(fixture);
    const button = Array.from(
      fixture.nativeElement.querySelectorAll(
        '.menu-azioni button',
      ) as NodeListOf<HTMLButtonElement>,
    ).find((b) => b.textContent?.includes('Invia in revisione'))!;
    button.click();
    fixture.detectChanges();
    expect(dialog.showModal).toHaveBeenCalled();
    http.expectNone((r) => r.method === 'POST');
    Array.from(dialog.querySelectorAll('button'))
      .find((b) => b.textContent?.includes('Conferma'))!
      .click();
    const request = http.expectOne(
      '/api/v1/builder/modelli/model/versioni/version/invia-revisione',
    );
    fixture.detectChanges();
    // La colonna Stato mostra ancora BOZZA: la scrittura non e' confermata dal backend.
    const stato = () =>
      (fixture.nativeElement as HTMLElement).querySelector('.badge-stato')!.textContent!.trim();
    expect(stato()).toBe('BOZZA');
    request.flush({ ...version, stato: 'IN_REVISIONE' });
    http
      .expectOne((r) => r.url === '/api/v1/builder/modelli')
      .flush([{ ...model, versioni: [{ ...version, stato: 'IN_REVISIONE' }] }]);
    fixture.detectChanges();
    expect(stato()).toBe('IN_REVISIONE');
    http.verify();
  });
  it('distinguishes read failures from an empty registry and permits retry', () => {
    const { fixture, http } = setup(['geban']);
    http
      .expectOne((r) => r.url === '/api/v1/builder/modelli')
      .flush({ messaggio: 'Servizio indisponibile' }, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Servizio indisponibile');
    expect(fixture.nativeElement.textContent).not.toContain('Nessun modello presente');
    Array.from(fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>)
      .find((b) => b.textContent?.includes('Riprova'))!
      .click();
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([]);
    http.verify();
  });
  it('shows an explicit empty authorization state without querying models', () => {
    const { fixture, http } = setup([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Nessun contesto autorizzato');
    http.verify();
  });
  it('reloads a conflicting transition without retrying the write', () => {
    const { fixture, http } = setup(['geban']);
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelector('dialog') as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    apriKebab(fixture);
    Array.from(
      fixture.nativeElement.querySelectorAll(
        '.menu-azioni button',
      ) as NodeListOf<HTMLButtonElement>,
    )
      .find((b) => b.textContent?.includes('Invia in revisione'))!
      .click();
    fixture.detectChanges();
    Array.from(dialog.querySelectorAll('button'))
      .find((b) => b.textContent?.includes('Conferma'))!
      .click();
    http
      .expectOne('/api/v1/builder/modelli/model/versioni/version/invia-revisione')
      .flush({ messaggio: 'Stato modificato' }, { status: 409, statusText: 'Conflict' });
    http
      .expectOne((r) => r.url === '/api/v1/builder/modelli')
      .flush([{ ...model, versioni: [{ ...version, stato: 'IN_REVISIONE' }] }]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Stato modificato');
    http.expectNone((r) => r.method === 'POST');
    http.verify();
  });
});
