import { Component, inject, signal } from '@angular/core';
import Keycloak from 'keycloak-js';
import { tokenContexts } from './auth/roles';
@Component({
  standalone: true,
  template: `<h1>Profilo</h1>
    <dl>
      <dt>Nome</dt>
      <dd>{{ name }}</dd>
      <dt>Username</dt>
      <dd>{{ username }}</dd>
      <dt>Contesti</dt>
      <dd>{{ contexts.join(', ') || 'Nessun contesto' }}</dd>
    </dl>
    <button
      type="button"
      class="btn btn-outline-primary me-3"
      (click)="showToken.set(!showToken())"
      [attr.aria-expanded]="showToken()"
    >
      {{ showToken() ? 'Nascondi token' : 'Mostra token' }}
    </button>
    <button type="button" class="btn btn-primary" (click)="logout()">Logout</button>
    @if (showToken()) {
      <pre class="token mt-4">{{ keycloak.token }}</pre>
    }`,
  styles: `
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
  protected readonly name =
    this.keycloak.tokenParsed?.['name'] ||
    this.keycloak.tokenParsed?.['preferred_username'] ||
    'Utente';
  protected readonly username = this.keycloak.tokenParsed?.['preferred_username'];
  protected readonly contexts = tokenContexts(this.keycloak);
  protected readonly showToken = signal(false);
  protected logout(): void {
    void this.keycloak.logout({ redirectUri: window.location.origin });
  }
}
