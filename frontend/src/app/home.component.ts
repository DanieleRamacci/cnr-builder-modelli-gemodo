import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import Keycloak from 'keycloak-js';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { ApiClient } from '../shared/api-client';
import type { ApiError } from '../shared/api-error';
import type { components as Registry } from '../shared/api-types/integrazioni';
import { hasClientRole, hasManagerAccess } from './auth/roles';

type Integrazione = Registry['schemas']['IntegrazioneAdmin'];

const ETICHETTE_STATO: Record<string, string> = {
  CONNESSO: 'Connesso',
  DEFINITO: 'Da verificare',
  ERRORE: 'Errore',
};

@Component({
  standalone: true,
  imports: [DatePipe, RouterLink],
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
        <span>{{ oggi | date: 'dd/MM/yyyy' }}</span>
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

          @if (caricamento()) {
            <p class="home-stato" role="status">Lettura in corso...</p>
          } @else if (errore()) {
            <div class="alert alert-danger" role="alert">{{ errore() }}</div>
          } @else if (admin) {
            @if (integrazioni().length) {
              <div class="home-list">
                @for (fonte of integrazioni(); track fonte.id) {
                  <article>
                    <span class="context-mark">{{ sigla(fonte.codice) }}</span>
                    <div>
                      <h3>
                        <a [routerLink]="['/configurazione', fonte.id]">{{ fonte.nome }}</a>
                      </h3>
                      <p>
                        <code>{{ fonte.codice_contesto }}</code>
                        &middot; {{ descrizioneStato(fonte) }}
                      </p>
                    </div>
                    <span class="status-pill" [class]="classeStato(fonte.stato)">{{
                      etichettaStato(fonte.stato)
                    }}</span>
                    <a [routerLink]="['/configurazione', fonte.id]">Apri</a>
                  </article>
                }
              </div>
            } @else {
              <p class="home-stato">
                Nessuna integrazione registrata.
                <a routerLink="/configurazione/contesti/nuovo">Registrane una</a>.
              </p>
            }
          } @else if (manager) {
            @if (contesti().length) {
              <div class="home-list">
                @for (contesto of contesti(); track contesto) {
                  <article>
                    <span class="context-mark">{{ sigla(contesto) }}</span>
                    <div>
                      <h3>{{ contesto }}</h3>
                      <p><code>{{ contesto }}</code> &middot; modelli del contesto</p>
                    </div>
                    <a
                      class="btn btn-outline-primary btn-sm"
                      [routerLink]="['/contesti', contesto, 'modelli']"
                      >Vedi modelli</a
                    >
                  </article>
                }
              </div>
            } @else {
              <p class="home-stato">Nessun contesto assegnato.</p>
            }
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
            <a routerLink="/configurazione/tipi-documento"
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
  private readonly api = inject(ApiClient);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly admin = hasClientRole(this.keycloak, 'gemodo-backend', 'GEMODO_ADMIN');
  protected readonly manager = hasManagerAccess(this.keycloak);
  protected readonly greeting = this.admin
    ? 'Ciao, configura le integrazioni'
    : 'Ciao, scegli un contesto';
  protected readonly oggi = new Date();
  protected readonly integrazioni = signal<Integrazione[]>([]);
  protected readonly contesti = signal<string[]>([]);
  protected readonly caricamento = signal(false);
  protected readonly errore = signal<string | null>(null);

  constructor() {
    this.carica();
  }

  /**
   * Fino al 2026-09-23 questa schermata mostrava integrazioni e contesti
   * inventati nel template, senza eseguire alcuna chiamata: annunciava sistemi
   * inesistenti e nascondeva quelli davvero registrati (007 FR-030). Un elenco
   * vuoto e' preferibile a un elenco inventato.
   */
  private carica(): void {
    if (!this.admin && !this.manager) return;
    this.caricamento.set(true);
    forkJoin({
      integrazioni: this.admin
        ? this.api.get<Integrazione[]>('/api/v1/configurazione/integrazioni')
        : of<Integrazione[]>([]),
      contesti: this.manager
        ? this.api.get<string[]>('/api/v1/builder/contesti')
        : of<string[]>([]),
    })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((error: ApiError) => {
          this.errore.set(error.messaggio);
          return of({ integrazioni: [] as Integrazione[], contesti: [] as string[] });
        }),
      )
      .subscribe(({ integrazioni, contesti }) => {
        this.integrazioni.set(integrazioni);
        this.contesti.set(contesti);
        this.caricamento.set(false);
      });
  }

  protected sigla(codice: string): string {
    return codice.slice(0, 2).toUpperCase();
  }

  protected etichettaStato(stato: string): string {
    return ETICHETTE_STATO[stato] ?? stato;
  }

  protected classeStato(stato: string): string {
    if (stato === 'CONNESSO') return 'success';
    return stato === 'ERRORE' ? 'error' : 'warning';
  }

  /** Solo cio' che il registro dichiara davvero: nessun esito inventato. */
  protected descrizioneStato(fonte: Integrazione): string {
    if (!fonte.url) return 'endpoint non configurato';
    const verifica = fonte.ultima_verifica;
    if (!verifica) return 'mai verificata';
    return verifica.esito === 'CONFORME' ? 'ultima verifica conforme' : 'ultima verifica fallita';
  }
}
