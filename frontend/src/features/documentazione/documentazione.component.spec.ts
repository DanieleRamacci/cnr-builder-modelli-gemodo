import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { DocumentazioneComponent } from './documentazione.component';
import type { IndiceManuale } from './manuale';

const indice: IndiceManuale = {
  sezioni: [
    {
      codice: 'utenti',
      titolo: 'Per gli utenti',
      pagine: [
        { slug: 'utenti-introduzione', titolo: 'Introduzione', sorgente: 'utenti/introduzione.md' },
      ],
    },
    {
      codice: 'sviluppatori',
      titolo: 'Per gli sviluppatori',
      pagine: [{ slug: 'contratto-dati', titolo: 'Contratto dati', sorgente: 'contratto-dati.md' }],
    },
  ],
};
const pagine: Record<string, string> = {
  '/manuale/indice.json': JSON.stringify(indice),
  '/manuale/utenti-introduzione.md':
    '# Introduzione\n\nVedi il [contratto](../contratto-dati.md#regole).\n',
  '/manuale/contratto-dati.md': '# Contratto dati\n\n## Regole\n\nTesto.\n',
};

async function apri(url: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (percorso: string) =>
      percorso in pagine
        ? new Response(pagine[percorso], { status: 200 })
        : new Response('', { status: 404 }),
    ),
  );
  TestBed.configureTestingModule({
    providers: [
      provideRouter([
        { path: 'documentazione', component: DocumentazioneComponent },
        { path: 'documentazione/:pagina', component: DocumentazioneComponent },
      ]),
    ],
  });
  const harness = await RouterTestingHarness.create();
  const router = TestBed.inject(Router);
  await harness.navigateByUrl(url, DocumentazioneComponent);
  const attendi = async () => {
    for (let i = 0; i < 5; i++) {
      harness.detectChanges();
      await harness.fixture.whenStable();
      await new Promise((r) => setTimeout(r));
    }
  };
  await attendi();
  return { root: harness.routeNativeElement as HTMLElement, router, attendi };
}

describe('Documentazione', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('splits the index into user and developer sections', async () => {
    const { root } = await apri('/documentazione');
    const titoli = [...root.querySelectorAll('.manuale-sezione-titolo')].map((h) => h.textContent);
    expect(titoli).toEqual(['Per gli utenti', 'Per gli sviluppatori']);
    expect(root.querySelector('.manuale-sezione a[href="/docs"]')).not.toBeNull();
  });

  it('opens the first user page by default and rewrites its links to the app', async () => {
    const { root } = await apri('/documentazione');
    const contenuto = root.querySelector('.manuale-contenuto')!;
    expect(contenuto.querySelector('h1')!.textContent).toBe('Introduzione');
    expect(contenuto.querySelector('a')!.getAttribute('href')).toBe(
      '/documentazione/contratto-dati#regole',
    );
  });

  it('follows an in-manual link without leaving the app', async () => {
    const { root, router, attendi } = await apri('/documentazione');
    const naviga = vi.spyOn(router, 'navigateByUrl');
    (root.querySelector('.manuale-contenuto a') as HTMLAnchorElement).click();
    await attendi();
    expect(naviga).toHaveBeenCalledWith('/documentazione/contratto-dati#regole');
  });

  it('shows the requested page and says so when a page does not exist', async () => {
    const { root, router, attendi } = await apri('/documentazione/contratto-dati');
    expect(root.querySelector('.manuale-contenuto h2')!.id).toBe('regole');
    await router.navigateByUrl('/documentazione/non-esiste');
    await attendi();
    expect(root.querySelector('.alert')!.textContent).toContain('Pagina non trovata');
  });
});
