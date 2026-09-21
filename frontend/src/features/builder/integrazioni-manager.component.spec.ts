import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
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
  it('deletes only after confirmation and reloads the list', () => {
    const { fixture, http } = setup(['geban']);
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelectorAll('dialog')[2] as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    fixture.nativeElement.querySelector('button[aria-label="Elimina modello"]').click();
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
  function setup(contexts = ['geban', 'altro']) {
    TestBed.configureTestingModule({
      providers: [
        provideDesignAngularKit(),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
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
  it('uses backend-authorized context tabs and reloads the list on selection', () => {
    const { fixture, http } = setup();
    const first = http.expectOne((r) => r.url === '/api/v1/builder/modelli');
    expect(first.request.params.get('codice_contesto')).toBe('geban');
    first.flush([model]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('select')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Modello CTER');
    expect(fixture.nativeElement.textContent).toContain('Italiano');
    expect(fixture.nativeElement.textContent).toContain('VI');
    expect(fixture.nativeElement.textContent).toContain('Crea versione inglese');
    const tabs = fixture.nativeElement.querySelectorAll('nav button');
    tabs[1].click();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Modello CTER');
    const next = http.expectOne((r) => r.url === '/api/v1/builder/modelli');
    expect(next.request.params.get('codice_contesto')).toBe('altro');
    next.flush([]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Nessun modello presente');
    http.verify();
  });
  it('creates the English derived model only after confirmation', () => {
    const { fixture, http } = setup(['geban']);
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelectorAll('dialog')[1] as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    Array.from(fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>)
      .find((button) => button.textContent?.includes('Crea versione inglese'))!
      .click();
    fixture.detectChanges();
    expect(dialog.showModal).toHaveBeenCalled();
    http.expectNone((request) => request.method === 'POST');
    Array.from(dialog.querySelectorAll('button'))
      .find((button) => button.textContent?.trim() === 'Crea')!
      .click();
    const request = http.expectOne('/api/v1/builder/modelli/model/edizioni-derivate');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ lingua: 'EN' });
    request.flush({ ...model, id: 'english', lingua: 'EN', derivato_da_modello_id: 'model' });
    http
      .expectOne((candidate) => candidate.url === '/api/v1/builder/modelli')
      .flush([
        model,
        { ...model, id: 'english', lingua: 'EN', derivato_da_modello_id: 'model' },
      ]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent.match(/Crea versione inglese/g)?.length ?? 0).toBe(0);
    http.verify();
  });
  it('confirms each transition and displays state only after the backend reload', () => {
    const { fixture, http } = setup(['geban']);
    http.expectOne((r) => r.url === '/api/v1/builder/modelli').flush([model]);
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelector('dialog') as HTMLDialogElement;
    dialog.showModal = vi.fn();
    dialog.close = vi.fn();
    const button = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
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
    expect(button.disabled).toBe(true);
    request.flush({ ...version, stato: 'IN_REVISIONE' });
    http
      .expectOne((r) => r.url === '/api/v1/builder/modelli')
      .flush([{ ...model, versioni: [{ ...version, stato: 'IN_REVISIONE' }] }]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Approva');
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
    Array.from(fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>)
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
