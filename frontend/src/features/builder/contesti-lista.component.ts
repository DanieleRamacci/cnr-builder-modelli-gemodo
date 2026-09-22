import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import Keycloak from 'keycloak-js';
import { forkJoin } from 'rxjs';
import { hasClientRole } from '../../app/auth/roles';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/integrazioni';

type Integrazione = components['schemas']['IntegrazioneVisibile'];
type Filtro = 'tutti' | 'con' | 'senza';

/**
 * Schermata 1a (contexts-list) di design_handoff_modellario: landing a card dei
 * contesti autorizzati. Le metriche sono solo quelle realmente disponibili dal
 * backend (integrazioni connesse per contesto), mai valori inventati.
 */
@Component({
  standalone: true,
  imports: [RouterLink],
  styleUrl: './contesti-lista.component.scss',
  template: `
    <nav class="breadcrumb-1a" aria-label="Percorso"><strong>Contesti</strong></nav>
    <header class="testata">
      <div>
        <h1>Contesti</h1>
        <p>Scegli il contesto applicativo di cui gestire i modelli di documento.</p>
      </div>
      @if (admin) {
        <a class="btn btn-primary" routerLink="/configurazione/contesti/nuovo">+ Nuovo contesto</a>
      }
    </header>
    <div class="filtri">
      <input
        type="search"
        class="form-control ricerca"
        placeholder="Cerca contesto o integrazione"
        aria-label="Cerca contesto o integrazione"
        [value]="testo()"
        (input)="testo.set($any($event.target).value)"
      />
      @for (chip of chips; track chip.valore) {
        <button
          type="button"
          class="chip"
          [class.attivo]="filtro() === chip.valore"
          [attr.aria-pressed]="filtro() === chip.valore"
          (click)="filtro.set(chip.valore)"
        >
          {{ chip.etichetta }}
        </button>
      }
    </div>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
      <button class="btn btn-outline-primary mb-3" (click)="carica()">Riprova</button>
    }
    @if (loading()) {
      <p role="status">Caricamento...</p>
    }
    @if (!loading() && !error() && !contexts().length) {
      <p>Nessun contesto autorizzato alla gestione dei modelli.</p>
    } @else if (!loading() && !error() && !visibili().length) {
      <p>Nessun contesto corrisponde ai filtri.</p>
    }
    <div class="griglia">
      @for (card of visibili(); track card.codice) {
        <article class="card-contesto">
          <div class="intestazione">
            <span class="sigla" aria-hidden="true">{{ card.sigla }}</span>
            <div>
              <h2>{{ card.codice }}</h2>
              <span class="codice">{{ card.codice }}</span>
            </div>
          </div>
          <p class="descrizione">
            @if (card.integrazioni.length) {
              {{ card.nomi }}
            } @else {
              Nessuna integrazione connessa.
            }
          </p>
          <footer>
            <span
              ><strong>{{ card.integrazioni.length }}</strong>
              {{ card.integrazioni.length === 1 ? 'integrazione' : 'integrazioni' }}</span
            >
            <a [routerLink]="['/contesti', card.codice, 'modelli']">Apri contesto ›</a>
          </footer>
        </article>
      }
      @if (admin && !loading() && !error()) {
        <a class="card-nuovo" routerLink="/configurazione/contesti/nuovo">+ Nuovo contesto</a>
      }
    </div>
  `,
})
export class ContestiListaComponent {
  private readonly api = inject(ApiClient);
  private readonly destroyRef = inject(DestroyRef);
  // UI-only (FR-023): il backend resta l'autorita' sull'accesso amministrativo.
  protected readonly admin = hasClientRole(inject(Keycloak), 'gemodo-backend', 'GEMODO_ADMIN');
  protected readonly chips: { valore: Filtro; etichetta: string }[] = [
    { valore: 'tutti', etichetta: 'Tutti' },
    { valore: 'con', etichetta: 'Con integrazioni' },
    { valore: 'senza', etichetta: 'Senza integrazioni' },
  ];
  protected readonly contexts = signal<string[]>([]);
  private readonly integrations = signal<Integrazione[]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly testo = signal('');
  protected readonly filtro = signal<Filtro>('tutti');

  protected readonly visibili = computed(() => {
    const query = this.testo().trim().toLowerCase();
    return this.contexts()
      .map((codice) => {
        const integrazioni = this.integrations().filter((i) => i.codice_contesto === codice);
        return {
          codice,
          sigla: codice.slice(0, 2).toUpperCase(),
          integrazioni,
          nomi: integrazioni.map((i) => i.nome).join(', '),
        };
      })
      .filter((card) => {
        if (this.filtro() === 'con' && !card.integrazioni.length) return false;
        if (this.filtro() === 'senza' && card.integrazioni.length) return false;
        return (
          !query ||
          card.codice.toLowerCase().includes(query) ||
          card.nomi.toLowerCase().includes(query)
        );
      });
  });

  constructor() {
    this.carica();
  }

  protected carica(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({
      contexts: this.api.get<string[]>('/api/v1/builder/contesti'),
      integrations: this.api.get<Integrazione[]>('/api/v1/builder/integrazioni'),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ contexts, integrations }) => {
          this.contexts.set(contexts);
          this.integrations.set(integrations);
          this.loading.set(false);
        },
        error: (e: ApiError) => {
          this.error.set(e.messaggio);
          this.loading.set(false);
        },
      });
  }
}
