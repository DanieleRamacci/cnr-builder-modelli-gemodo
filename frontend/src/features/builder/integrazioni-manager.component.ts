import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ItIconComponent } from 'design-angular-kit';
import { forkJoin, Subscription } from 'rxjs';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components as Registry } from '../../shared/api-types/integrazioni';
import type { components } from '../../shared/api-types/builder-modelli';

type Model = components['schemas']['ModelloGestione'];
type Version = components['schemas']['Versione'];
type Action = { route: string; label: string };
type VociFiltri = {
  codici_tipo_documento: string[];
  codici_tipologia: string[];
  codici_categoria: string[];
  lingue: string[];
  livelli_professionali: string[];
  varianti: string[];
};
const ACTIONS: Record<string, Action> = {
  BOZZA: { route: 'invia-revisione', label: 'Invia in revisione' },
  IN_REVISIONE: { route: 'approva', label: 'Approva' },
  APPROVATO: { route: 'pubblica', label: 'Pubblica' },
};

@Component({
  standalone: true,
  imports: [DatePipe, NgTemplateOutlet, RouterLink, ItIconComponent],
  templateUrl: './integrazioni-manager.component.html',
  styleUrl: './integrazioni-manager.component.scss',
  styles: `
    :host {
      display: block;
    }
    td {
      overflow-wrap: anywhere;
      min-width: 9rem;
    }
    dialog {
      border: 1px solid #ccc;
      border-radius: 4px;
      padding: 24px;
      width: min(560px, calc(100% - 32px));
    }
    dialog::backdrop {
      background: rgb(0 0 0 / 40%);
    }
  `,
})
export class IntegrazioniManagerComponent {
  private readonly api = inject(ApiClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private listing?: Subscription;
  protected readonly pageSize = 50;
  protected readonly testo = signal('');
  protected readonly statoFiltro = signal('');
  protected readonly linguaFiltro = signal('');
  protected readonly tipologiaFiltro = signal('');
  protected readonly profiloFiltro = signal('');
  protected readonly livelloFiltro = signal('');
  /** Voci selezionabili, dai modelli esistenti nel contesto (007 FR-028). */
  protected readonly voci = signal<VociFiltri>({
    codici_tipo_documento: [],
    codici_tipologia: [],
    codici_categoria: [],
    lingue: [],
    livelli_professionali: [],
    varianti: [],
  });
  protected readonly view = signal<'table' | 'grid'>(
    this.route.snapshot.queryParamMap.get('view') === 'grid' ? 'grid' : 'table',
  );
  protected readonly contexts = signal<string[]>([]);
  protected readonly selected = signal('');
  protected readonly models = signal<Model[]>([]);
  protected readonly integrations = signal<Registry['schemas']['IntegrazioneVisibile'][]>([]);
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly offset = signal(0);
  protected readonly deleting = signal<Model | null>(null);
  protected readonly menuAperto = signal<string | null>(null);
  protected readonly pending = signal<{ model: Model; version: Version; action: Action } | null>(
    null,
  );
  constructor() {
    this.initialize();
  }
  /** Stato della versione piu recente: e quello che l'utente vede come stato del modello. */
  protected stato(model: Model): string {
    const versions = model.versioni ?? [];
    return (
      versions.reduce<Version | undefined>(
        (latest, v) => (!latest || v.numero_versione > latest.numero_versione ? v : latest),
        undefined,
      )?.stato ?? 'BOZZA'
    );
  }
  /**
   * Filtri e ricerca sono applicati dal server: qui non si rifiltra nulla.
   * Rifiltrare la pagina ricevuta darebbe risultati sbagliati dalla seconda
   * pagina in poi ed e' esattamente il difetto che 007 FR-028 vieta.
   */
  protected readonly visibili = computed(() => this.models());
  /** Solo conteggi sui modelli della pagina caricata: nessun totale o metrica inventata. */
  protected readonly metriche = computed(() => {
    const stati = this.models().map((m) => this.stato(m));
    const conta = (s: string) => stati.filter((x) => x === s).length;
    return [
      { etichetta: 'Modelli', valore: stati.length },
      { etichetta: 'Pubblicati', valore: conta('PUBBLICATO') },
      { etichetta: 'In revisione', valore: conta('IN_REVISIONE') },
      { etichetta: 'Bozze', valore: conta('BOZZA') },
    ];
  });
  protected toggleMenu(id: string): void {
    this.menuAperto.update((aperto) => (aperto === id ? null : id));
  }

  /** La versione su cui agisce la riga: la piu' recente. */
  protected versioneCorrente(model: Model): Version | undefined {
    return (model.versioni ?? []).reduce<Version | undefined>(
      (latest, v) => (!latest || v.numero_versione > latest.numero_versione ? v : latest),
      undefined,
    );
  }

  /** L'unica transizione proponibile dalla riga, sulla versione corrente. */
  protected azioneCorrente(model: Model): { version: Version; action: Action } | undefined {
    const version = this.versioneCorrente(model);
    const action = version && this.action(version);
    return version && action ? { version, action } : undefined;
  }

  protected setView(view: 'table' | 'grid'): void {
    this.view.set(view);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { view: view === 'grid' ? 'grid' : null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }
  protected sources() {
    return this.integrations().filter((s) => s.codice_contesto === this.selected());
  }
  protected action(version: Version): Action | undefined {
    return ACTIONS[version.stato];
  }
  private initialize(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({
      contexts: this.api.get<string[]>('/api/v1/builder/contesti'),
      integrations: this.api.get<Registry['schemas']['IntegrazioneVisibile'][]>(
        '/api/v1/builder/integrazioni',
      ),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ contexts, integrations }) => {
          this.contexts.set(contexts);
          this.integrations.set(integrations);
          // Schermata 1b: il contesto arriva dalla rotta /contesti/:ctxId/modelli
          // (query `contesto` solo per compatibilita'). Un contesto non autorizzato
          // non ricade mai su un altro in silenzio.
          const requested =
            this.route.snapshot.paramMap.get('ctxId') ??
            this.route.snapshot.queryParamMap.get('contesto');
          if (requested && !contexts.includes(requested)) {
            this.error.set('Contesto non autorizzato o inesistente');
            this.loading.set(false);
            return;
          }
          this.ripristinaFiltriDaUrl();
          const context = requested ?? contexts[0];
          if (context) this.select(context);
          else this.loading.set(false);
        },
        error: (e: ApiError) => {
          this.error.set(e.messaggio);
          this.loading.set(false);
        },
      });
  }
  protected select(context: string): void {
    if (this.saving() || !this.contexts().includes(context)) return;
    this.selected.set(context);
    this.offset.set(0);
    this.caricaVoci();
    this.load();
  }
  protected page(delta: number): void {
    this.offset.update((n) => Math.max(0, n + delta * this.pageSize));
    this.load();
  }
  protected retry(): void {
    if (this.contexts().length && this.selected()) this.load();
    else this.initialize();
  }
  /**
   * I filtri di dimensione vanno al server, non applicati sulla pagina ricevuta.
   * L'elenco e' paginato: filtrare dopo `limit` restituirebbe la pagina in mano
   * invece dell'insieme, con risultati sbagliati dalla seconda pagina in poi
   * (007 FR-028).
   */
  protected filtriAttivi(): Record<string, string> {
    const filtri: Record<string, string> = {};
    if (this.statoFiltro()) filtri['stato_versione'] = this.statoFiltro();
    if (this.linguaFiltro()) filtri['lingua'] = this.linguaFiltro();
    if (this.tipologiaFiltro()) filtri['codice_tipologia'] = this.tipologiaFiltro();
    if (this.profiloFiltro()) filtri['codice_categoria'] = this.profiloFiltro();
    if (this.livelloFiltro()) filtri['livello_professionale'] = this.livelloFiltro();
    if (this.testo().trim()) filtri['ricerca'] = this.testo().trim();
    return filtri;
  }

  /** Un filtro cambiato riporta alla prima pagina: restare sull'offset corrente
   * mostrerebbe una pagina vuota di un insieme piu' piccolo. */
  protected applicaFiltri(): void {
    this.offset.set(0);
    this.sincronizzaUrl();
    this.load();
  }

  protected azzeraFiltri(): void {
    this.statoFiltro.set('');
    this.linguaFiltro.set('');
    this.tipologiaFiltro.set('');
    this.profiloFiltro.set('');
    this.livelloFiltro.set('');
    this.testo.set('');
    this.applicaFiltri();
  }

  private sincronizzaUrl(): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { ...this.filtriAttivi(), contesto: this.selected() },
      replaceUrl: true,
    });
  }

  private ripristinaFiltriDaUrl(): void {
    const params = this.route.snapshot.queryParamMap;
    this.statoFiltro.set(params.get('stato_versione') ?? '');
    this.linguaFiltro.set(params.get('lingua') ?? '');
    this.tipologiaFiltro.set(params.get('codice_tipologia') ?? '');
    this.profiloFiltro.set(params.get('codice_categoria') ?? '');
    this.livelloFiltro.set(params.get('livello_professionale') ?? '');
    this.testo.set(params.get('ricerca') ?? '');
  }

  /** Le voci dipendono dai modelli del contesto: si rileggono al cambio contesto. */
  private caricaVoci(): void {
    this.api
      .get<VociFiltri>('/api/v1/builder/modelli/filtri', { codice_contesto: this.selected() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (voci) => this.voci.set(voci) });
  }

  private load(clearError = true): void {
    this.listing?.unsubscribe();
    this.loading.set(true);
    this.models.set([]);
    if (clearError) this.error.set(null);
    this.listing = this.api
      .get<Model[]>('/api/v1/builder/modelli', {
        codice_contesto: this.selected(),
        offset: this.offset(),
        limit: this.pageSize,
        ...this.filtriAttivi(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (models) => {
          this.models.set(models);
          this.loading.set(false);
        },
        error: (e: ApiError) => {
          this.error.set(e.messaggio);
          this.loading.set(false);
        },
      });
  }
  protected request(model: Model, version: Version, dialog: HTMLDialogElement): void {
    const action = this.action(version);
    if (!action || this.saving()) return;
    this.pending.set({ model, version, action });
    dialog.showModal();
  }
  protected requestDelete(model: Model, dialog: HTMLDialogElement): void {
    if (this.saving()) return;
    this.deleting.set(model);
    dialog.showModal();
  }
  protected confirmDelete(dialog: HTMLDialogElement): void {
    const model = this.deleting();
    if (!model || this.saving()) return;
    dialog.close();
    this.deleting.set(null);
    this.saving.set(true);
    this.error.set(null);
    this.api
      .delete<void>(`/api/v1/builder/modelli/${model.id}`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.offset.set(0);
          this.load();
        },
        error: (e: ApiError) => {
          this.saving.set(false);
          this.error.set(e.messaggio);
        },
      });
  }
  protected confirm(dialog: HTMLDialogElement): void {
    const item = this.pending();
    if (!item || this.saving()) return;
    dialog.close();
    this.pending.set(null);
    this.saving.set(true);
    this.error.set(null);
    this.api
      .post<Version>(
        `/api/v1/builder/modelli/${item.model.id}/versioni/${item.version.id}/${item.action.route}`,
        {},
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.load();
        },
        error: (e: ApiError) => {
          this.saving.set(false);
          this.error.set(e.messaggio);
          if (e.status === 409) this.load(false);
        },
      });
  }
}
