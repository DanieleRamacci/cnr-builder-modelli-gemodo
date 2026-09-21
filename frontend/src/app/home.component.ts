import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import Keycloak from 'keycloak-js';
import { hasClientRole, hasManagerAccess } from './auth/roles';
@Component({
  standalone: true,
  imports: [RouterLink],
  template: `<h1>GEMODO</h1>
    @if (!admin && !manager) {
      <div class="alert alert-warning" role="alert">
        Non sei autorizzato ad accedere alle funzioni di GEMODO.
      </div>
    }
    <div class="list-group">
      @if (admin) {
        <a routerLink="/configurazione" class="list-group-item list-group-item-action"
          >Integrazione servizi</a
        >
      }
      @if (manager) {
        <a routerLink="/contesti" class="list-group-item list-group-item-action">Contesti</a>
      }
    </div>`,
})
export class HomeComponent {
  private readonly keycloak = inject(Keycloak);
  protected readonly admin = hasClientRole(this.keycloak, 'gemodo-backend', 'GEMODO_ADMIN');
  protected readonly manager = hasManagerAccess(this.keycloak);
}
