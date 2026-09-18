import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

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

  constructor() {
    this.service.lista().subscribe((integrazioni) => {
      this.integrazioni.set(integrazioni);
      this.caricamento.set(false);
    });
  }

  protected badge(stato: IntegrazioneAdmin['stato']) {
    return BADGE[stato];
  }
}
