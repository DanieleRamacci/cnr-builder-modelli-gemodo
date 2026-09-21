import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ItIconComponent } from 'design-angular-kit';
import { forkJoin, Subscription } from 'rxjs';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components as Registry } from '../../shared/api-types/integrazioni';
import type { components } from '../../shared/api-types/builder-modelli';

type Model = components['schemas']['ModelloGestione'];
type Version = components['schemas']['Versione'];
type Action = { route: string; label: string };
const ACTIONS: Record<string, Action> = {
  BOZZA: { route: 'invia-revisione', label: 'Invia in revisione' },
  IN_REVISIONE: { route: 'approva', label: 'Approva' },
  APPROVATO: { route: 'pubblica', label: 'Pubblica' },
};

@Component({
  standalone: true,
  imports: [DatePipe, RouterLink, ItIconComponent],
  templateUrl: './integrazioni-manager.component.html',
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
  private readonly destroyRef = inject(DestroyRef);
  private listing?: Subscription;
  protected readonly pageSize = 50;
  protected readonly contexts = signal<string[]>([]);
  protected readonly selected = signal('');
  protected readonly models = signal<Model[]>([]);
  protected readonly integrations = signal<Registry['schemas']['IntegrazioneVisibile'][]>([]);
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly offset = signal(0);
  protected readonly deleting = signal<Model | null>(null);
  protected readonly deriving = signal<Model | null>(null);
  protected readonly pending = signal<{ model: Model; version: Version; action: Action } | null>(
    null,
  );
  constructor() {
    this.initialize();
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
  protected canCreateEnglishEdition(model: Model): boolean {
    return (
      model.lingua === 'IT' &&
      !model.derivato_da_modello_id &&
      !this.models().some(
        (candidate) => candidate.derivato_da_modello_id === model.id && candidate.lingua === 'EN',
      )
    );
  }
  protected requestDerived(model: Model, dialog: HTMLDialogElement): void {
    if (this.saving() || !this.canCreateEnglishEdition(model)) return;
    this.deriving.set(model);
    dialog.showModal();
  }
  protected confirmDerived(dialog: HTMLDialogElement): void {
    const model = this.deriving();
    if (!model || this.saving()) return;
    dialog.close();
    this.deriving.set(null);
    this.saving.set(true);
    this.error.set(null);
    this.api
      .post<Model>(`/api/v1/builder/modelli/${model.id}/edizioni-derivate`, { lingua: 'EN' })
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
