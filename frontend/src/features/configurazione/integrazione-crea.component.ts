import { Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { IntegrazioniAdminService } from './integrazioni-admin.service';
import type { ApiError } from '../../shared/api-error';

/**
 * Integration creation form (007 tasks.md T017, spec.md FR-021 Acceptance
 * Scenario 1/2). Client-side validation is length/presence only (UX); the
 * backend remains the authority (e.g. INTEGRAZIONE_DUPLICATA - data-model.md).
 */
@Component({
  selector: 'app-integrazione-crea',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './integrazione-crea.component.html',
})
export class IntegrazioneCreaComponent {
  private readonly service = inject(IntegrazioniAdminService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  protected readonly esempioJson = JSON.stringify(
    {
      contesto: 'geban',
      tipi_documento: [
        {
          codice: 'BANDO_CONCORSO',
          nome: 'Bando di concorso',
          albero: [
            {
              codice: 'CP',
              descrizione: 'Concorsi pubblici',
              figli: [
                {
                  codice: 'RICERCATORE',
                  descrizione: 'Ricercatore',
                  dimensioni: {
                    livello: ['I', 'II', 'III'],
                    lingua: ['IT', 'EN'],
                  },
                  campi: [
                    { codice: 'ente.denominazione', tipo: 'testo', obbligatorio: true },
                    { codice: 'bando.scadenza', tipo: 'data', obbligatorio: true },
                    { codice: 'profilo.codice', tipo: 'testo', obbligatorio: false },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
    null,
    2,
  );

  protected readonly form = this.fb.nonNullable.group({
    codice: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(100)]],
    nome: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(200)]],
    codiceContesto: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(64)]],
  });

  protected readonly inviando = signal(false);
  protected readonly erroreServer = signal<string | null>(null);

  protected invia(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.erroreServer.set(null);
    this.inviando.set(true);
    const { codice, nome, codiceContesto } = this.form.getRawValue();
    this.service.crea({ codice, nome, codice_contesto: codiceContesto }).subscribe({
      next: (integrazione) =>
        this.router.navigate(['/configurazione/contesti', integrazione.id, 'integrazione']),
      error: (error: ApiError) => {
        this.inviando.set(false);
        this.erroreServer.set(error.messaggio);
      },
    });
  }
}
