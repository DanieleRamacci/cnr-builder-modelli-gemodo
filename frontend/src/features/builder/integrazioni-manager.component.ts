import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import Keycloak from 'keycloak-js';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/integrazioni';
import { hasManagerAccess, tokenContexts } from '../../app/auth/roles';
@Component({
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `<h1>Crea modello</h1>
    @if (!manager) {
      <div class="alert alert-warning" role="alert">Non sei autorizzato a creare modelli.</div>
    } @else {
      <label for="contesto" class="form-label">Contesto</label>
      <select
        id="contesto"
        class="form-select mb-4"
        [ngModel]="selected()"
        (ngModelChange)="selected.set($event)"
      >
        <option value="">Seleziona contesto</option>
        @for (code of contexts(); track code) {
          <option [value]="code">{{ code }}</option>
        }
      </select>
      @if (loading()) {
        <p role="status">Caricamento...</p>
      }
      @if (error()) {
        <div class="alert alert-danger" role="alert">{{ error() }}</div>
      }
      @if (!loading() && !error() && selected()) {
        <h2 class="h4">Integrazioni disponibili</h2>
        @for (item of integrations(); track item.id) {
          @if (item.codice_contesto === selected()) {
            <p>
              <a [routerLink]="['/builder', item.id]">{{ item.nome }}</a>
            </p>
          }
        }
        @if (!available()) {
          <p>Nessuna integrazione connessa e autorizzata in questo contesto.</p>
        }
      }
    }`,
})
export class IntegrazioniManagerComponent {
  private readonly keycloak = inject(Keycloak);
  protected readonly manager = hasManagerAccess(this.keycloak);
  protected readonly contexts = signal(tokenContexts(this.keycloak));
  protected readonly selected = signal('');
  protected readonly integrations = signal<components['schemas']['IntegrazioneVisibile'][]>([]);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected available(): boolean {
    return this.integrations().some((item) => item.codice_contesto === this.selected());
  }
  constructor() {
    if (!this.manager) return;
    this.loading.set(true);
    inject(ApiClient)
      .get<components['schemas']['IntegrazioneVisibile'][]>('/api/v1/builder/integrazioni')
      .subscribe({
        next: (items) => {
          this.integrations.set(items);
          this.contexts.set(
            [...new Set([...this.contexts(), ...items.map((item) => item.codice_contesto)])].sort(),
          );
          this.loading.set(false);
        },
        error: (error: ApiError) => {
          this.error.set(error.messaggio);
          this.loading.set(false);
        },
      });
  }
}
