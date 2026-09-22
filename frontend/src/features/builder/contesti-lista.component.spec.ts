import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import Keycloak from 'keycloak-js';
import { ContestiListaComponent } from './contesti-lista.component';

const integrazioni = [
  { id: 'a', codice: 'GEBAN', nome: 'Software GEBAN', codice_contesto: 'geban' },
  { id: 'b', codice: 'ALTRO', nome: 'Secondo software', codice_contesto: 'geban' },
];

describe('1a contexts list', () => {
  function setup(roles: string[] = []) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Keycloak,
          useValue: { tokenParsed: { resource_access: { 'gemodo-backend': { roles } } } },
        },
      ],
    });
    const fixture = TestBed.createComponent(ContestiListaComponent);
    const http = TestBed.inject(HttpTestingController);
    return { fixture, http };
  }
  const load = (http: HttpTestingController, contexts: string[], sources = integrazioni) => {
    http.expectOne('/api/v1/builder/contesti').flush(contexts);
    http.expectOne('/api/v1/builder/integrazioni').flush(sources);
  };

  it('shows one card per authorized context with its real integration count and a link to its models', () => {
    const { fixture, http } = setup();
    load(http, ['geban', 'altro']);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const cards = root.querySelectorAll('article.card-contesto');
    expect(cards.length).toBe(2);
    expect(cards[0].textContent).toContain('geban');
    expect(cards[0].textContent).toContain('2 integrazioni');
    expect(cards[0].textContent).toContain('Software GEBAN');
    expect(cards[1].textContent).toContain('0 integrazioni');
    expect(root.querySelector('a[href="/contesti/geban/modelli"]')).not.toBeNull();
    http.verify();
  });

  it('filters by search text and by chip', () => {
    const { fixture, http } = setup();
    load(http, ['geban', 'altro']);
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const search = root.querySelector<HTMLInputElement>('input[type=search]')!;
    search.value = 'alt';
    search.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(root.querySelectorAll('article.card-contesto').length).toBe(1);
    expect(root.querySelector('article.card-contesto')?.textContent).toContain('altro');
    search.value = '';
    search.dispatchEvent(new Event('input'));
    const chip = Array.from(root.querySelectorAll('button.chip')).find((b) =>
      b.textContent?.includes('Con integrazioni'),
    ) as HTMLButtonElement;
    chip.click();
    fixture.detectChanges();
    expect(root.querySelectorAll('article.card-contesto').length).toBe(1);
    expect(root.querySelector('article.card-contesto')?.textContent).toContain('geban');
    http.verify();
  });

  it('shows explicit empty, error and no-match states', () => {
    const empty = setup();
    load(empty.http, []);
    empty.fixture.detectChanges();
    expect(empty.fixture.nativeElement.textContent).toContain('Nessun contesto autorizzato');
    empty.http.verify();
    TestBed.resetTestingModule();
    const failed = setup();
    failed.http
      .expectOne('/api/v1/builder/contesti')
      .flush({ messaggio: 'Servizio indisponibile' }, { status: 503, statusText: 'Unavailable' });
    failed.http.match('/api/v1/builder/integrazioni');
    failed.fixture.detectChanges();
    expect(failed.fixture.nativeElement.querySelector('[role=alert]')?.textContent).toContain(
      'Servizio indisponibile',
    );
    expect(failed.fixture.nativeElement.textContent).not.toContain('Nessun contesto autorizzato');
  });

  it('offers "Nuovo contesto" only to an admin (UI enablement, never authorization)', () => {
    const manager = setup(['GEMODO_MODELLI_GESTORE']);
    load(manager.http, ['geban']);
    manager.fixture.detectChanges();
    expect(
      manager.fixture.nativeElement.querySelector('a[href="/configurazione/contesti/nuovo"]'),
    ).toBeNull();
    TestBed.resetTestingModule();
    const admin = setup(['GEMODO_ADMIN']);
    load(admin.http, ['geban']);
    admin.fixture.detectChanges();
    expect(
      admin.fixture.nativeElement.querySelector('a[href="/configurazione/contesti/nuovo"]'),
    ).not.toBeNull();
  });
});
