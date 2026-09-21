import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import type { ApiError } from '../../shared/api-error';

import { TipiDocumentoService, type TipoDocumentoDashboard } from './tipi-documento.service';

type BadgeVariant = 'neutro' | 'positivo' | 'errore';

const BADGE: Record<TipoDocumentoDashboard['stato_integrazione'], { label: string; variant: BadgeVariant }> = {
  INCOMPLETO: { label: 'Struttura incompleta', variant: 'neutro' },
  DEFINITO: { label: 'Definito, non connesso', variant: 'neutro' },
  CONNESSO: { label: 'Connesso', variant: 'positivo' },
  ERRORE: { label: 'Errore', variant: 'errore' },
};

/**
 * Dashboard tipi documento (spec 010 User Story 1, FR-001/FR-002/FR-013).
 * Elenca cio' che il backend ha gia' persistito - nessuno stato dedotto qui.
 */
@Component({
  selector: 'app-tipi-documento-lista',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './tipi-documento-lista.component.html',
})
export class TipiDocumentoListaComponent {
  private readonly service = inject(TipiDocumentoService);

  protected readonly tipi = signal<TipoDocumentoDashboard[]>([]);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);

  constructor() {
    this.carica();
  }

  protected carica(): void {
    this.caricamento.set(true);
    this.errore.set(null);
    this.service.dashboard().subscribe({
      next: (tipi) => {
        this.tipi.set(tipi);
        this.caricamento.set(false);
      },
      error: (error: ApiError) => {
        this.caricamento.set(false);
        this.errore.set(error.messaggio);
      },
    });
  }

  protected badge(stato: TipoDocumentoDashboard['stato_integrazione']) {
    return BADGE[stato];
  }
}
