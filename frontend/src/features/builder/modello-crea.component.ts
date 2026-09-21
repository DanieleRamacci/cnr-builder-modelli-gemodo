import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/integrazioni';
type Nodo = components['schemas']['NodoCategorizzazione'];
@Component({
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `<h1>Crea modello</h1>
    <a routerLink="/builder" [queryParams]="{ contesto: contesto }" class="d-inline-block mb-3"
      >Torna ai modelli</a
    >
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    @if (loading()) {
      <p role="status">Caricamento...</p>
    }
    @if (!success()) {
      <label for="tipo" class="form-label">Tipo documento</label>
      <select
        id="tipo"
        class="form-select mb-4"
        [disabled]="loading() || saving() || !!modelId"
        [ngModel]="tipo"
        (ngModelChange)="loadTree($event)"
      >
        <option value="">Seleziona tipo documento</option>
        @for (code of types(); track code) {
          <option [value]="code">{{ code }}</option>
        }
      </select>
      @if (path().length) {
        <p>{{ path().join(' / ') }}</p>
        <button
          type="button"
          class="btn btn-outline-primary mb-3"
          [disabled]="saving() || !!modelId"
          (click)="back()"
        >
          Indietro
        </button>
      }
      <div class="list-group mb-4">
        @for (node of nodes(); track node.codice) {
          <button
            type="button"
            class="list-group-item list-group-item-action"
            [disabled]="saving() || !!modelId"
            (click)="choose(node)"
          >
            {{ node.descrizione }}
          </button>
        }
      </div>
      @if (leaf(); as selected) {
        <h2 class="h4">Campi</h2>
        <ul>
          @for (field of selected.campi; track field.codice + field.lingua) {
            <li>
              {{ field.etichetta }} - {{ field.tipo }}
              @if (field.obbligatorio) {
                (obbligatorio)
              }
            </li>
          }
        </ul>
        <form #form="ngForm" (ngSubmit)="create()">
          <label for="lingua" class="form-label">Lingua</label>
          <select
            id="lingua"
            name="lingua"
            class="form-select mb-3"
            [(ngModel)]="lingua"
            required
            [disabled]="saving() || !!modelId"
          >
            <option value="">Seleziona lingua</option>
            @for (language of selected.lingue_possibili ?? []; track language) {
              <option [value]="language">{{ language === 'IT' ? 'Italiano' : 'Inglese' }}</option>
            }
          </select>
          <label for="livello" class="form-label">Livello professionale</label>
          <select
            id="livello"
            name="livello"
            class="form-select mb-3"
            [(ngModel)]="livelloProfessionale"
            [disabled]="saving() || !!modelId"
          >
            <option value="">Tutti i livelli</option>
            @for (level of selected.livelli_possibili ?? []; track level) {
              <option [value]="level">{{ level }}</option>
            }
          </select>
          <button type="submit" class="btn btn-primary" [disabled]="form.invalid || saving()">
            Crea modello in bozza
          </button>
        </form>
      }
    } @else {
      <div class="alert alert-success" role="status">
        Modello {{ createdModel?.nome }} ({{ createdModel?.codice }}) creato - {{ success() }}
      </div>
    } `,
})
export class ModelloCreaComponent {
  private readonly api = inject(ApiClient);
  private readonly route = inject(ActivatedRoute);
  private readonly id = this.route.snapshot.paramMap.get('id')!;
  private readonly presetTipo = this.route.snapshot.queryParamMap?.get('tipo') ?? '';
  private readonly presetPath = this.route.snapshot.queryParamMap?.get('percorso')?.split('|') ?? [];
  private readonly presetLingua = this.route.snapshot.queryParamMap?.get('lingua') ?? '';
  private readonly presetLivello = this.route.snapshot.queryParamMap?.get('livello') ?? '';
  protected readonly contesto =
    this.route.snapshot.queryParamMap?.get('contesto') ?? '';
  protected readonly types = signal<string[]>([]);
  protected readonly nodes = signal<Nodo[]>([]);
  protected readonly path = signal<string[]>([]);
  protected readonly leaf = signal<Nodo | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly success = signal<string | null>(null);
  protected tipo = '';
  protected lingua = '';
  protected livelloProfessionale = '';
  private root: Nodo[] = [];
  protected modelId: string | null = null;
  protected createdModel: { codice: string; nome: string } | null = null;
  constructor() {
    this.loading.set(true);
    this.api.get<string[]>(`/api/v1/builder/integrazioni/${this.id}/tipi-documento`).subscribe({
      next: (types) => {
        this.types.set(types);
        this.loading.set(false);
        if (this.presetTipo && types.includes(this.presetTipo)) this.loadTree(this.presetTipo);
      },
      error: (error: ApiError) => this.failed(error),
    });
  }
  protected loadTree(tipo: string): void {
    this.tipo = tipo;
    this.path.set([]);
    this.leaf.set(null);
    this.nodes.set([]);
    this.error.set(null);
    this.modelId = null;
    if (!tipo) return;
    this.loading.set(true);
    this.api
      .get<{ nodi: Nodo[] }>(
        `/api/v1/builder/integrazioni/${this.id}/tipi-documento/${encodeURIComponent(tipo)}/struttura`,
      )
      .subscribe({
        next: (tree) => {
          this.root = tree.nodi;
          this.nodes.set(this.root);
          this.loading.set(false);
          if (tipo === this.presetTipo && this.presetPath.length) this.applyPresetPath();
        },
        error: (error: ApiError) => this.failed(error),
      });
  }
  protected choose(node: Nodo): void {
    this.path.update((path) => [...path, node.codice]);
    this.nodes.set(node.figli ?? []);
    this.leaf.set(node.campi ? node : null);
    if (node.campi) {
      const languages = node.lingue_possibili ?? [];
      this.lingua = languages.includes(this.presetLingua as 'IT' | 'EN')
        ? this.presetLingua
        : (languages[0] ?? '');
      const levels = node.livelli_possibili ?? [];
      this.livelloProfessionale = levels.includes(this.presetLivello)
        ? this.presetLivello
        : '';
    }
    this.modelId = null;
  }
  private applyPresetPath(): void {
    for (const code of this.presetPath) {
      const node = this.nodes().find((candidate) => candidate.codice === code);
      if (!node) return;
      this.choose(node);
    }
  }
  protected back(): void {
    const path = this.path().slice(0, -1);
    let nodes = this.root;
    for (const code of path) nodes = nodes.find((node) => node.codice === code)?.figli ?? [];
    this.path.set(path);
    this.nodes.set(nodes);
    this.leaf.set(null);
    this.modelId = null;
  }
  private failed(error: ApiError): void {
    this.loading.set(false);
    this.saving.set(false);
    this.error.set(
      this.modelId
        ? `Modello salvato, versione non confermata: ${error.messaggio}`
        : error.messaggio,
    );
  }
  protected create(): void {
    if (
      this.saving() ||
      !this.leaf() ||
      !this.lingua
    )
      return;
    this.saving.set(true);
    this.error.set(null);
    if (this.modelId) {
      this.createVersion(this.modelId);
      return;
    }
    this.api
      .post<{ id: string; codice: string; nome: string }>('/api/v1/builder/modelli', {
        codice_tipo_documento: this.tipo,
        integrazione_id: this.id,
        percorso_categorizzazione: this.path(),
        lingua: this.lingua,
        livello_professionale: this.livelloProfessionale || null,
      })
      .subscribe({
        next: (model) => {
          this.modelId = model.id;
          this.createdModel = model;
          this.createVersion(model.id);
        },
        error: (error: ApiError) => this.failed(error),
      });
  }
  private createVersion(id: string): void {
    this.api
      .post<{ stato: string }>(`/api/v1/builder/modelli/${id}/versioni`, {
        campi: this.leaf()!.campi!.map((field) => ({ codice: field.codice, lingua: field.lingua })),
      })
      .subscribe({
        next: (version) => {
          this.success.set(version.stato);
          this.saving.set(false);
        },
        error: (error: ApiError) => this.failed(error),
      });
  }
}
