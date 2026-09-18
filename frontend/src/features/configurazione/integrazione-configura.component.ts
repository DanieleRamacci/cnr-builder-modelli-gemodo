import { Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import Keycloak from 'keycloak-js';

import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';
import type { ApiError } from '../../shared/api-error';

const BADGE: Record<
  IntegrazioneAdmin['stato'],
  { label: string; variant: 'neutro' | 'positivo' | 'errore' }
> = {
  DEFINITO: { label: 'Non verificato', variant: 'neutro' },
  CONNESSO: { label: 'Connesso', variant: 'positivo' },
  ERRORE: { label: 'Errore', variant: 'errore' },
};

/**
 * Configure URL/timeout + trigger verification (007 tasks.md T018, spec.md
 * User Story 4 Acceptance Scenario 3/4/5). REVISIONE_SUPERATA always reloads
 * the current server state rather than retrying the stale write - data-model.md
 * "mai un retry automatico silenzioso".
 */
@Component({
  selector: 'app-integrazione-configura',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './integrazione-configura.component.html',
})
export class IntegrazioneConfiguraComponent {
  private readonly service = inject(IntegrazioniAdminService);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  private readonly keycloak = inject(Keycloak, { optional: true });
  protected readonly sessioneScaduta = signal(false);
  protected accedi(): void {
    void this.keycloak?.login({
      redirectUri: window.location.origin + '/configurazione/' + this.id,
    });
  }
  private readonly id = this.route.snapshot.paramMap.get('id')!;

  protected readonly form = this.fb.nonNullable.group({
    nome: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(200)]],
    url: [''],
    timeoutMs: [5000, [Validators.min(1000), Validators.max(10000)]],
  });

  protected readonly integrazione = signal<IntegrazioneAdmin | null>(null);
  protected readonly caricando = signal(false);
  protected readonly erroreCaricamento = signal<string | null>(null);
  protected readonly salvando = signal(false);
  protected readonly verificando = signal(false);
  protected readonly erroreServer = signal<string | null>(null);
  protected readonly infoServer = signal<string | null>(null);

  constructor() {
    this.caricaStatoCorrente();
  }

  protected caricaStatoCorrente(): void {
    this.caricando.set(true);
    this.erroreCaricamento.set(null);
    this.service.ottieni(this.id).subscribe({
      next: (integrazione) => {
        this.caricando.set(false);
        this.integrazione.set(integrazione);
        this.form.patchValue({
          nome: integrazione.nome,
          url: integrazione.url ?? '',
          timeoutMs: integrazione.timeout_ms,
        });
      },
      error: (error: ApiError) => {
        this.sessioneScaduta.set(error.status === 401);
        this.caricando.set(false);
        this.erroreCaricamento.set(error.messaggio);
      },
    });
  }

  protected badge(stato: IntegrazioneAdmin['stato']) {
    return BADGE[stato];
  }

  protected salvaConfigurazione(): void {
    const current = this.integrazione();
    if (!current || this.form.invalid || this.salvando() || this.verificando()) {
      this.form.markAllAsTouched();
      return;
    }
    this.erroreServer.set(null);
    this.infoServer.set(null);
    this.salvando.set(true);
    const { nome, url, timeoutMs } = this.form.getRawValue();
    this.service
      .configura(this.id, {
        revisione_attesa: current.revisione,
        nome,
        url: url || null,
        timeout_ms: timeoutMs,
      })
      .subscribe({
        next: (integrazione) => {
          this.salvando.set(false);
          this.integrazione.set(integrazione);
        },
        error: (error: ApiError) => {
          this.sessioneScaduta.set(error.status === 401);
          this.salvando.set(false);
          this.erroreServer.set(
            error.codice === 'DESTINAZIONE_NON_APPROVATA'
              ? "URL discovery non autorizzato dal deployment. L'integrazione resta salvata; la configurazione dell'URL non e' stata applicata."
              : error.messaggio,
          );
          if (error.codice === 'REVISIONE_SUPERATA') {
            this.caricaStatoCorrente();
          }
        },
      });
  }

  protected avviaVerifica(): void {
    const current = this.integrazione();
    if (!current || !current.url || this.salvando() || this.verificando()) {
      return;
    }
    this.erroreServer.set(null);
    this.infoServer.set(null);
    this.verificando.set(true);
    this.service.verifica(this.id, current.revisione).subscribe({
      next: (integrazione) => {
        this.verificando.set(false);
        this.integrazione.set(integrazione);
      },
      error: (error: ApiError) => {
        this.sessioneScaduta.set(error.status === 401);
        this.verificando.set(false);
        if (error.codice === 'VERIFICA_IN_CORSO') {
          this.infoServer.set(error.messaggio);
          return;
        }
        this.erroreServer.set(error.messaggio);
        if (error.codice === 'REVISIONE_SUPERATA') {
          this.caricaStatoCorrente();
        }
      },
    });
  }
}
