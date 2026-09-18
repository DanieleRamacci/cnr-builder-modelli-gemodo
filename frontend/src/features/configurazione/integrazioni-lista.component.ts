import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import Keycloak from 'keycloak-js';
import type { ApiError } from '../../shared/api-error';

import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';

type BadgeVariant = 'neutro' | 'positivo' | 'errore';

const BADGE: Record<IntegrazioneAdmin['stato'], { label: string; variant: BadgeVariant }> = {
  DEFINITO: { label: 'Non verificato', variant: 'neutro' },
  CONNESSO: { label: 'Connesso', variant: 'positivo' },
  ERRORE: { label: 'Errore', variant: 'errore' },
};

/**
 * Integration list (007 tasks.md T016, spec.md User Story 4 Acceptance Scenario 1/2).
 * Status badge reflects only what the backend returned - never derived locally
 * (data-model.md "Stato UI derivato da stato").
 */
@Component({
  selector: 'app-integrazioni-lista',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './integrazioni-lista.component.html',
})
export class IntegrazioniListaComponent {
  private readonly service = inject(IntegrazioniAdminService);

  protected readonly integrazioni = signal<IntegrazioneAdmin[]>([]);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);
  protected readonly sessioneScaduta = signal(false);
  private readonly keycloak = inject(Keycloak, { optional: true });

  constructor() {
    this.carica();
  }

  protected accedi(): void {
    void this.keycloak?.login({ redirectUri: window.location.origin + '/configurazione' });
  }
  protected carica(): void {
    this.caricamento.set(true);
    this.errore.set(null);
    this.sessioneScaduta.set(false);
    this.service.lista().subscribe({
      next: (integrazioni) => {
        this.integrazioni.set(integrazioni);
        this.caricamento.set(false);
      },
      error: (error: ApiError) => {
        this.caricamento.set(false);
        this.sessioneScaduta.set(error.status === 401);
        this.errore.set(
          error.status === 401
            ? 'Sessione non valida. Accedi nuovamente: le integrazioni salvate restano disponibili.'
            : error.messaggio,
        );
      },
    });
  }

  protected badge(stato: IntegrazioneAdmin['stato']) {
    return BADGE[stato];
  }
}
