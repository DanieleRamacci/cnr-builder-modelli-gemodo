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
          <label for="codice" class="form-label">Codice modello</label
          ><input
            id="codice"
            name="codice"
            class="form-control mb-3"
            [(ngModel)]="codice"
            required
            maxlength="128"
            [disabled]="saving() || !!modelId"
          />
          <label for="nome" class="form-label">Nome</label
          ><input
            id="nome"
            name="nome"
            class="form-control mb-3"
            [(ngModel)]="nome"
            required
            maxlength="255"
            [disabled]="saving() || !!modelId"
          />
          <label for="variante" class="form-label">Variante</label
          ><input
            id="variante"
            name="variante"
            class="form-control mb-3"
            [(ngModel)]="variante"
            required
            maxlength="64"
            [disabled]="saving() || !!modelId"
          />
          <button type="submit" class="btn btn-primary" [disabled]="form.invalid || saving()">
            Crea modello in bozza
          </button>
        </form>
      }
    } @else {
      <div class="alert alert-success" role="status">
        Modello {{ codice }} creato - {{ success() }}
      </div>
    } `,
})
export class ModelloCreaComponent {
  private readonly api = inject(ApiClient);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('id')!;
  protected readonly contesto =
    inject(ActivatedRoute).snapshot.queryParamMap?.get('contesto') ?? '';
  protected readonly types = signal<string[]>([]);
  protected readonly nodes = signal<Nodo[]>([]);
  protected readonly path = signal<string[]>([]);
  protected readonly leaf = signal<Nodo | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly success = signal<string | null>(null);
  protected tipo = '';
  protected codice = '';
  protected nome = '';
  protected variante = 'STANDARD';
  private root: Nodo[] = [];
  protected modelId: string | null = null;
  constructor() {
    this.loading.set(true);
    this.api.get<string[]>(`/api/v1/builder/integrazioni/${this.id}/tipi-documento`).subscribe({
      next: (types) => {
        this.types.set(types);
        this.loading.set(false);
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
        },
        error: (error: ApiError) => this.failed(error),
      });
  }
  protected choose(node: Nodo): void {
    this.path.update((path) => [...path, node.codice]);
    this.nodes.set(node.figli ?? []);
    this.leaf.set(node.campi ? node : null);
    this.modelId = null;
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
      !this.codice.trim() ||
      !this.nome.trim() ||
      !this.variante.trim()
    )
      return;
    this.saving.set(true);
    this.error.set(null);
    if (this.modelId) {
      this.createVersion(this.modelId);
      return;
    }
    this.api
      .post<{ id: string }>('/api/v1/builder/modelli', {
        codice: this.codice,
        nome: this.nome,
        variante: this.variante,
        codice_tipo_documento: this.tipo,
        integrazione_id: this.id,
        percorso_categorizzazione: this.path(),
      })
      .subscribe({
        next: (model) => {
          this.modelId = model.id;
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
