import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import Keycloak from 'keycloak-js';
import { hasClientRole, hasManagerAccess } from './auth/roles';

@Component({
  standalone: true,
  imports: [RouterLink],
  template: `
    @if (!admin && !manager) {
      <div class="alert alert-warning" role="alert">
        Non sei autorizzato ad accedere alle funzioni di Modellario.
      </div>
    } @else {
      <section class="home-hero">
        <div>
          <h1>{{ greeting }}</h1>
          <p>
            Un unico ingresso per amministrare le integrazioni e gestire i modelli dei contesti
            autorizzati.
          </p>
        </div>
        <span>22/09/2026</span>
      </section>

      <section class="home-actions" aria-labelledby="home-actions-title">
        <h2 id="home-actions-title">Cosa vuoi fare</h2>
        <div class="home-action-grid">
          @if (admin) {
            <a routerLink="/configurazione" class="home-action featured">
              <span>01</span>
              <strong>Integrazione servizi</strong>
              <small>Apri GEBAN, verifica endpoint e struttura API.</small>
            </a>
            <a routerLink="/configurazione/contesti/nuovo" class="home-action">
              <span>02</span>
              <strong>Nuovo contesto</strong>
              <small>Registra una integrazione e genera l'esempio JSON.</small>
            </a>
          }
          @if (manager) {
            <a routerLink="/contesti" class="home-action" [class.featured]="!admin">
              <span>{{ admin ? '03' : '01' }}</span>
              <strong>Contesti</strong>
              <small>Scegli un contesto e consulta i modelli disponibili.</small>
            </a>
            <a routerLink="/contesti" class="home-action">
              <span>{{ admin ? '04' : '02' }}</span>
              <strong>Nuovo modello</strong>
              <small>Parti dal contesto e dalla categorizzazione live.</small>
            </a>
          }
        </div>
      </section>

      <div class="home-layout">
        <section>
          <div class="section-title-row">
            <div>
              <h2>{{ admin ? 'Integrazioni servizi' : 'Contesti assegnati' }}</h2>
              <p>
                {{
                  admin ? 'Verifica endpoint, JSON e policy dati.' : 'Apri i modelli del contesto.'
                }}
              </p>
            </div>
            <a [routerLink]="admin ? '/configurazione' : '/contesti'">vedi tutti</a>
          </div>

          @if (admin) {
            <div class="home-list">
              <article>
                <span class="context-mark">GE</span>
                <div>
                  <h3><a routerLink="/configurazione">GEBAN - Bandi di concorso</a></h3>
                  <p><code>geban</code> · endpoint e struttura di esempio da completare</p>
                </div>
                <span class="status-pill warning">Da verificare</span>
                <a routerLink="/configurazione">Apri</a>
              </article>
              <article>
                <span class="context-mark">SI</span>
                <div>
                  <h3>SIGLA</h3>
                  <p><code>sigla</code> · ultima scansione non conforme</p>
                </div>
                <span class="status-pill error">Errore</span>
                <a routerLink="/configurazione">Apri</a>
              </article>
            </div>
          }

          @if (manager) {
            <div class="home-list">
              <article>
                <span class="context-mark">AC</span>
                <div>
                  <h3>Appalti e contratti</h3>
                  <p><code>CTX-APP</code> · modelli e bozze del contesto</p>
                </div>
                <a class="btn btn-outline-primary btn-sm" routerLink="/contesti">Vedi modelli</a>
                <a routerLink="/contesti">+ nuovo modello</a>
              </article>
              <article>
                <span class="context-mark">GE</span>
                <div>
                  <h3>GEBAN</h3>
                  <p><code>geban</code> · bandi e avvisi di concorso</p>
                </div>
                <a class="btn btn-outline-primary btn-sm" routerLink="/contesti">Vedi modelli</a>
                <a routerLink="/contesti">+ nuovo modello</a>
              </article>
            </div>
          }
        </section>

        <aside class="screen-aside">
          <h2>Tutte le schermate</h2>
          <p>Un solo ingresso per ciascuna. Le voci fuori dal tuo ruolo non compaiono.</p>
          @if (admin) {
            <a routerLink="/configurazione"><code>5b</code><span>Verifica endpoint</span></a>
            <a routerLink="/configurazione/contesti/nuovo"
              ><code>5a</code><span>Nuovo contesto</span></a
            >
            <a routerLink="/configurazione/tipi-documento/nuovo"
              ><code>4a</code><span>Policy dati</span></a
            >
          }
          @if (manager) {
            <a routerLink="/contesti"><code>1a</code><span>Contesti</span></a>
            <a routerLink="/contesti"><code>1b</code><span>Modelli</span></a>
          }
        </aside>
      </div>
    }
  `,
})
export class HomeComponent {
  private readonly keycloak = inject(Keycloak);
  protected readonly admin = hasClientRole(this.keycloak, 'gemodo-backend', 'GEMODO_ADMIN');
  protected readonly manager = hasManagerAccess(this.keycloak);
  protected readonly greeting = this.admin
    ? 'Ciao, configura le integrazioni'
    : 'Ciao, scegli un contesto';
}
