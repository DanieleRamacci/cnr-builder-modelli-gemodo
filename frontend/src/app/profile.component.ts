import { Component, inject, signal } from '@angular/core';
import Keycloak from 'keycloak-js';

import type { ApiError } from '../shared/api-error';
import { ProfiloService } from './auth/profilo.service';

/**
 * Profilo (007 FR-034, T114): per ogni contesto del token, i ruoli posseduti e
 * cosa consentono. Le descrizioni vengono dal backend, che applica la
 * mappatura ruoli -> permessi: un elenco scritto qui divergerebbe.
 */
@Component({
  standalone: true,
  template: `<h1>Profilo</h1>
    <dl>
      <dt>Nome</dt>
      <dd>{{ name }}</dd>
      <dt>Username</dt>
      <dd>{{ username }}</dd>
    </dl>

    <h2 class="h4 mt-4">Cosa puoi fare in GEMODO</h2>
    @if (errore(); as messaggio) {
      <div class="alert alert-danger" role="alert">{{ messaggio }}</div>
    }
    @if (profili.profilo(); as profilo) {
      @if (profilo.permessi_diretti.length) {
        <section class="contesto" data-permessi-diretti>
          <h3 class="h6">Permessi assegnati direttamente</h3>
          <ul>
            @for (permesso of profilo.permessi_diretti; track permesso.codice) {
              <li>
                <code>{{ permesso.codice }}</code> - {{ permesso.descrizione }}
              </li>
            }
          </ul>
        </section>
      }
      @for (contesto of profilo.contesti; track contesto.codice) {
        <section class="contesto" [attr.data-contesto]="contesto.codice">
          <h3 class="h6">
            Contesto <code>{{ contesto.codice }}</code>
          </h3>
          <p class="ruoli">Ruoli: {{ contesto.ruoli.join(', ') || 'nessuno' }}</p>
          @if (contesto.permessi.length) {
            <ul>
              @for (permesso of contesto.permessi; track permesso.codice) {
                <li>
                  <code>{{ permesso.codice }}</code> - {{ permesso.descrizione }}
                </li>
              }
            </ul>
          } @else {
            <p class="nessuno" data-nessun-permesso>
              Questi ruoli non concedono permessi in GEMODO: le sue funzioni non sono disponibili in
              questo contesto.
            </p>
          }
        </section>
      } @empty {
        @if (!profilo.permessi_diretti.length) {
          <p>Il token non porta contesti né permessi per GEMODO.</p>
        }
      }
    } @else if (!errore()) {
      <p role="status">Caricamento dei permessi...</p>
    }

    <button
      type="button"
      class="btn btn-outline-primary me-3 mt-3"
      (click)="showToken.set(!showToken())"
      [attr.aria-expanded]="showToken()"
    >
      {{ showToken() ? 'Nascondi token' : 'Mostra token' }}
    </button>
    <button type="button" class="btn btn-primary mt-3" (click)="logout()">Logout</button>
    @if (showToken()) {
      <pre class="token mt-4">{{ keycloak.token }}</pre>
    }`,
  styles: `
    .contesto {
      margin-top: 16px;
      padding: 12px 16px;
      border: 1px solid #dbe2e8;
      border-radius: 4px;
    }
    .ruoli,
    .nessuno {
      color: #5a6772;
      font-size: 14px;
    }
    .token {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      padding: 16px;
      background: #f0f3f2;
      max-width: 100%;
    }
  `,
})
export class ProfileComponent {
  protected readonly keycloak = inject(Keycloak);
  protected readonly profili = inject(ProfiloService);
  protected readonly name =
    this.keycloak.tokenParsed?.['name'] ||
    this.keycloak.tokenParsed?.['preferred_username'] ||
    'Utente';
  protected readonly username = this.keycloak.tokenParsed?.['preferred_username'];
  protected readonly showToken = signal(false);
  protected readonly errore = signal<string | null>(null);

  constructor() {
    this.profili.carica().subscribe({ error: (e: ApiError) => this.errore.set(e.messaggio) });
  }

  protected logout(): void {
    void this.keycloak.logout({ redirectUri: window.location.origin });
  }
}
