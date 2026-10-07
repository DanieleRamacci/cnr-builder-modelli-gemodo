import {
  Component,
  DestroyRef,
  ElementRef,
  SecurityContext,
  afterNextRender,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DomSanitizer } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { combineLatest } from 'rxjs';

import {
  BASE_MANUALE,
  ROTTA_MANUALE,
  type IndiceManuale,
  type PaginaManuale,
  rendiPagina,
} from './manuale';

/**
 * Voce "Documentazione" dell'header: la guida per gli utenti e la documentazione
 * per gli sviluppatori, lette da public/manuale/ (copie di docs/ riallineate da
 * scripts/sync-documentazione.mjs). File statici: niente token, niente backend.
 */
@Component({
  selector: 'app-documentazione',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './documentazione.component.html',
  styleUrl: './documentazione.component.scss',
})
export class DocumentazioneComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly destroyRef = inject(DestroyRef);
  private readonly contenuto = viewChild<ElementRef<HTMLElement>>('contenuto');

  protected readonly indice = signal<IndiceManuale | null>(null);
  protected readonly pagina = signal<PaginaManuale | null>(null);
  protected readonly errore = signal<string | null>(null);
  protected readonly rotta = ROTTA_MANUALE;
  private richiesta = 0;

  constructor() {
    afterNextRender(() => {
      fetch(`${BASE_MANUALE}/indice.json`)
        .then((risposta) => {
          if (!risposta.ok) throw new Error(String(risposta.status));
          return risposta.json() as Promise<IndiceManuale>;
        })
        .then((indice) => {
          this.indice.set(indice);
          combineLatest([this.route.paramMap, this.route.fragment])
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(([parametri, ancora]) => this.apri(parametri.get('pagina'), ancora));
        })
        .catch(() => this.errore.set('Indice della documentazione non disponibile.'));
    });
  }

  private apri(slug: string | null, ancora: string | null): void {
    const indice = this.indice()!;
    const pagine = indice.sezioni.flatMap((sezione) => sezione.pagine);
    const pagina = pagine.find((p) => p.slug === slug) ?? (slug ? null : pagine[0]);
    if (!pagina) {
      this.pagina.set(null);
      this.errore.set('Pagina non trovata nella documentazione.');
      return;
    }
    if (pagina === this.pagina()) {
      this.scorri(ancora);
      return;
    }
    const numero = ++this.richiesta;
    this.errore.set(null);
    fetch(`${BASE_MANUALE}/${pagina.slug}.md`)
      .then((risposta) => {
        if (!risposta.ok) throw new Error(String(risposta.status));
        return risposta.text();
      })
      .then((md) => {
        if (numero !== this.richiesta) return;
        const html = rendiPagina(
          md,
          pagina,
          indice,
          (grezzo) => this.sanitizer.sanitize(SecurityContext.HTML, grezzo) ?? '',
        );
        this.pagina.set(pagina);
        const elemento = this.contenuto()?.nativeElement;
        if (elemento) elemento.innerHTML = html;
        if (ancora) this.scorri(ancora);
        else window.scrollTo?.({ top: 0 });
      })
      .catch(() => {
        if (numero === this.richiesta) this.errore.set('Pagina non disponibile.');
      });
  }

  private scorri(ancora: string | null): void {
    if (!ancora) return;
    const titoli = this.contenuto()?.nativeElement.querySelectorAll<HTMLElement>('[id]') ?? [];
    Array.from(titoli)
      .find((titolo) => titolo.id === ancora)
      ?.scrollIntoView?.();
  }

  /** I link del manuale restano veri href (si aprono in una nuova scheda), ma il clic resta nell'app. */
  protected naviga(evento: MouseEvent): void {
    const link = (evento.target as HTMLElement).closest('a');
    const href = link?.getAttribute('href');
    if (
      !href?.startsWith(`${ROTTA_MANUALE}/`) ||
      evento.ctrlKey ||
      evento.metaKey ||
      evento.shiftKey
    ) {
      return;
    }
    evento.preventDefault();
    void this.router.navigateByUrl(href);
  }
}
