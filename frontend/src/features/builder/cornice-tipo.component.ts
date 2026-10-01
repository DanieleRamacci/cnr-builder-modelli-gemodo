import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DomSanitizer, type SafeUrl } from '@angular/platform-browser';

import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import { CorniceAnteprimaComponent } from './cornice-anteprima.component';
import {
  NOMI_MASCHERE,
  urlCornice,
  type CornicePagina,
  type CorniceTipoDocumento,
} from './cornice.model';

const RIGHE_MASSIME = 3;

/**
 * Intestazione e pie' di pagina di un tipo documento (012 T069).
 *
 * Valgono per tutti i modelli del tipo. Li impostano il gestore del contesto,
 * da Contesti -> <contesto> -> Impostazioni modelli, e l'amministratore, da
 * Impostazioni: la pagina e' la stessa. Intestazione e pie' di pagina sono
 * indipendenti; si sceglie la maschera, poi si riempie. Il logo si carica
 * subito e il servizio lo conserva ricodificato.
 */
@Component({
  selector: 'app-cornice-tipo',
  standalone: true,
  imports: [RouterLink, CorniceAnteprimaComponent],
  styleUrl: './cornice-tipo.component.scss',
  template: `
    <nav class="mb-2" aria-label="Percorso">
      @if (contesto) {
        <a routerLink="/contesti">Contesti</a> /
        <a [routerLink]="['/contesti', contesto, 'modelli']">{{ contesto }}</a> /
        <a [routerLink]="['/contesti', contesto, 'impostazioni']">Impostazioni modelli</a> /
      } @else {
        <a routerLink="/configurazione/tipi-documento">Tipi documento</a> /
      }
      <strong>{{ codice }}</strong>
    </nav>
    <h1>Intestazione e piè di pagina</h1>
    <p class="nota">
      Valgono per <strong>tutti i modelli</strong> di tipo <code>{{ codice }}</code
      >, nell'anteprima e nei documenti generati.
    </p>

    @if (caricamento()) {
      <p role="status">Caricamento...</p>
    }
    @if (errore(); as messaggio) {
      <div class="alert alert-danger" role="alert" data-cornice-error>
        {{ messaggio }}
        @if (violazioni().length) {
          <ul class="mb-0">
            @for (violazione of violazioni(); track violazione) {
              <li>{{ violazione }}</li>
            }
          </ul>
        }
      </div>
    }

    @if (!caricamento() && stato()) {
      <section class="parte" data-parte="intestazione">
        <h2>Intestazione</h2>
        @if (!conIntestazione()) {
          @if (scegliMaschera()) {
            <p class="nota">Scegli come impaginarla:</p>
            <div class="maschere">
              @for (maschera of stato()!.maschere_intestazione; track maschera) {
                <button
                  type="button"
                  class="maschera"
                  [attr.data-maschera]="maschera"
                  (click)="aggiungiIntestazione(maschera)"
                >
                  <span class="schizzo" aria-hidden="true">
                    <span class="s-logo"></span><span class="s-riga"></span
                    ><span class="s-riga corta"></span>
                  </span>
                  {{ nome(maschera) }}
                </button>
              }
            </div>
          } @else {
            <p class="nota">Nessuna intestazione.</p>
            <button
              type="button"
              class="btn btn-outline-primary"
              data-aggiungi-intestazione
              (click)="scegliMaschera.set(true)"
            >
              Aggiungi intestazione
            </button>
          }
        } @else {
          <p class="nota">Maschera: {{ nome(mascheraIntestazione()) }}</p>
          <div class="logo-riga">
            <div class="form-check">
              <input
                id="spunta-con-logo"
                type="checkbox"
                data-con-logo
                [checked]="conLogo()"
                (change)="conLogo.set($any($event.target).checked)"
              />
              <label for="spunta-con-logo">Logo</label>
            </div>
            @if (conLogo()) {
              <label class="btn btn-sm btn-outline-primary mb-0">
                {{ stato()!.logo_presente ? 'Sostituisci logo' : 'Carica logo' }}
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  class="visually-hidden"
                  data-logo-file
                  (change)="caricaLogo($any($event.target))"
                />
              </label>
              @if (stato()!.logo_presente) {
                <button
                  type="button"
                  class="btn btn-sm btn-outline-danger"
                  data-rimuovi-logo
                  (click)="rimuoviLogo()"
                >
                  Rimuovi logo
                </button>
              }
              <span class="nota">PNG o JPEG, al massimo 1 MB.</span>
            }
          </div>
          <label for="testo-intestazione">Testo sotto il logo</label>
          <textarea
            id="testo-intestazione"
            class="form-control"
            rows="3"
            data-testo-intestazione
            [value]="testoIntestazione()"
            (input)="testoIntestazione.set($any($event.target).value)"
          ></textarea>
          <p class="nota" [class.troppe]="righe() > righeMassime">
            {{ righe() }} di {{ righeMassime }} righe.
          </p>
          <div class="form-check">
            <input
              id="spunta-prima-grassetto"
              type="checkbox"
              data-prima-grassetto
              [checked]="primaInGrassetto()"
              (change)="primaInGrassetto.set($any($event.target).checked)"
            />
            <label for="spunta-prima-grassetto">Prima riga in grassetto</label>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-link px-0"
            data-rimuovi-intestazione
            (click)="conIntestazione.set(false)"
          >
            Togli l'intestazione
          </button>
        }
      </section>

      <section class="parte" data-parte="piede">
        <h2>Piè di pagina</h2>
        @if (!conPiede()) {
          <p class="nota">Nessun piè di pagina.</p>
          <button
            type="button"
            class="btn btn-outline-primary"
            data-aggiungi-piede
            (click)="conPiede.set(true)"
          >
            Aggiungi piè di pagina
          </button>
        } @else {
          <p class="nota">Maschera: {{ nome('TESTO_SINISTRA_NUMERO_DESTRA') }}</p>
          <label for="testo-piede">Testo</label>
          <input
            id="testo-piede"
            class="form-control"
            type="text"
            data-testo-piede
            [value]="testoPiede()"
            (input)="testoPiede.set($any($event.target).value)"
          />
          <div class="form-check">
            <input
              id="spunta-numerazione"
              type="checkbox"
              data-numerazione
              [checked]="numerazione()"
              (change)="numerazione.set($any($event.target).checked)"
            />
            <label for="spunta-numerazione">Numero di pagina ("Pagina 2 di 5")</label>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-link px-0"
            data-rimuovi-piede
            (click)="conPiede.set(false)"
          >
            Togli il piè di pagina
          </button>
        }
      </section>

      <section class="foglio-prova" aria-label="Anteprima della cornice">
        <app-cornice-anteprima [cornice]="cornice()" parte="intestazione" [logoUrl]="logoUrl()" />
        <p class="corpo-finto">Il testo del documento.</p>
        <app-cornice-anteprima [cornice]="cornice()" parte="piede" />
      </section>

      <div class="azioni">
        <button
          type="button"
          class="btn btn-primary"
          data-salva-cornice
          [disabled]="salvando() || righe() > righeMassime"
          (click)="salva()"
        >
          {{ salvando() ? 'Salvataggio...' : 'Salva' }}
        </button>
        @if (salvata()) {
          <span role="status" class="salvata" data-cornice-salvata
            >Salvata: vale da subito per tutti i modelli di questo tipo.</span
          >
        }
      </div>
    }
  `,
})
export class CorniceTipoComponent {
  private readonly api = inject(ApiClient);
  private readonly destroyRef = inject(DestroyRef);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly route = inject(ActivatedRoute);

  // Dalla rotta del contesto (/contesti/:ctxId/impostazioni/:integrazioneId/:codice)
  // o da quella dell'amministratore (/configurazione/tipi-documento/:codice/cornice?integrazioneId=).
  protected readonly contesto = this.route.snapshot.paramMap.get('ctxId');
  protected readonly codice = this.route.snapshot.paramMap.get('codice') ?? '';
  private readonly integrazioneId =
    this.route.snapshot.paramMap.get('integrazioneId') ??
    this.route.snapshot.queryParamMap.get('integrazioneId') ??
    '';
  protected readonly righeMassime = RIGHE_MASSIME;

  protected readonly caricamento = signal(true);
  protected readonly salvando = signal(false);
  protected readonly salvata = signal(false);
  protected readonly errore = signal<string | null>(null);
  protected readonly violazioni = signal<string[]>([]);
  protected readonly stato = signal<CorniceTipoDocumento | null>(null);
  protected readonly scegliMaschera = signal(false);
  protected readonly conIntestazione = signal(false);
  protected readonly mascheraIntestazione = signal('LOGO_CENTRO_TESTO_SOTTO');
  protected readonly conLogo = signal(true);
  protected readonly testoIntestazione = signal('');
  protected readonly primaInGrassetto = signal(true);
  protected readonly conPiede = signal(false);
  protected readonly testoPiede = signal('');
  protected readonly numerazione = signal(true);
  protected readonly logoUrl = signal<SafeUrl | null>(null);
  private indirizzoLogo: string | null = null;

  /** La cornice come la vedra' il PDF, ricostruita dal form a ogni battuta. */
  protected readonly cornice = computed<CornicePagina>(() => {
    const [prima = '', ...resto] = this.testoIntestazione().trim().split('\n');
    const testo = [];
    if (prima) testo.push({ testo: prima, grassetto: this.primaInGrassetto() });
    if (resto.length) testo.push({ testo: `\n${resto.join('\n')}` });
    const piede = this.testoPiede().trim();
    return {
      intestazione: this.conIntestazione()
        ? { maschera: this.mascheraIntestazione(), con_logo: this.conLogo(), testo }
        : null,
      pie_pagina: this.conPiede()
        ? {
            maschera: 'TESTO_SINISTRA_NUMERO_DESTRA',
            testo: piede ? [{ testo: piede }] : [],
            numerazione_pagine: this.numerazione(),
          }
        : null,
    };
  });

  constructor() {
    this.destroyRef.onDestroy(() => this.liberaLogo());
    if (!this.integrazioneId) {
      this.caricamento.set(false);
      this.errore.set("Manca l'integrazione a cui appartiene il tipo documento.");
      return;
    }
    this.api
      .get<CorniceTipoDocumento>(urlCornice(this.integrazioneId, this.codice))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (stato) => {
          this.caricamento.set(false);
          this.applica(stato);
        },
        error: (e: ApiError) => {
          this.caricamento.set(false);
          this.errore.set(e.messaggio);
        },
      });
  }

  protected nome(maschera: string): string {
    return NOMI_MASCHERE[maschera] ?? maschera;
  }

  protected righe(): number {
    const testo = this.testoIntestazione().trim();
    return testo ? testo.split('\n').length : 0;
  }

  protected aggiungiIntestazione(maschera: string): void {
    this.mascheraIntestazione.set(maschera);
    this.conIntestazione.set(true);
    this.scegliMaschera.set(false);
  }

  protected salva(): void {
    this.salvando.set(true);
    this.salvata.set(false);
    this.errore.set(null);
    this.violazioni.set([]);
    this.api
      .put<CorniceTipoDocumento>(urlCornice(this.integrazioneId, this.codice), this.cornice())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (stato) => {
          this.salvando.set(false);
          this.salvata.set(true);
          this.applica(stato);
        },
        error: (e: ApiError) => this.mostraErrore(e),
      });
  }

  protected caricaLogo(campo: HTMLInputElement): void {
    const file = campo.files?.[0];
    campo.value = '';
    if (!file) return;
    this.errore.set(null);
    this.violazioni.set([]);
    this.api
      .putFile(`${urlCornice(this.integrazioneId, this.codice)}/logo`, file)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.stato.update((stato) => (stato ? { ...stato, logo_presente: true } : stato));
          this.caricaAnteprimaLogo();
        },
        error: (e: ApiError) => this.mostraErrore(e),
      });
  }

  protected rimuoviLogo(): void {
    this.api
      .delete<void>(`${urlCornice(this.integrazioneId, this.codice)}/logo`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.stato.update((stato) => (stato ? { ...stato, logo_presente: false } : stato));
          this.liberaLogo();
        },
        error: (e: ApiError) => this.mostraErrore(e),
      });
  }

  private applica(stato: CorniceTipoDocumento): void {
    this.stato.set(stato);
    const testa = stato.cornice?.intestazione;
    this.conIntestazione.set(!!testa);
    if (testa) {
      this.mascheraIntestazione.set(testa.maschera);
      this.conLogo.set(testa.con_logo);
      this.testoIntestazione.set(testa.testo.map((f) => f.testo).join(''));
      this.primaInGrassetto.set(!!testa.testo[0]?.grassetto);
    }
    const piede = stato.cornice?.pie_pagina;
    this.conPiede.set(!!piede);
    if (piede) {
      this.testoPiede.set(piede.testo.map((f) => f.testo).join(''));
      this.numerazione.set(piede.numerazione_pagine);
    }
    if (stato.logo_presente) this.caricaAnteprimaLogo();
  }

  private caricaAnteprimaLogo(): void {
    this.api
      .getBlob(`${urlCornice(this.integrazioneId, this.codice)}/logo`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (immagine) => {
          this.liberaLogo();
          this.indirizzoLogo = URL.createObjectURL(immagine);
          this.logoUrl.set(this.sanitizer.bypassSecurityTrustUrl(this.indirizzoLogo));
        },
        error: () => this.liberaLogo(),
      });
  }

  private liberaLogo(): void {
    if (this.indirizzoLogo) URL.revokeObjectURL(this.indirizzoLogo);
    this.indirizzoLogo = null;
    this.logoUrl.set(null);
  }

  private mostraErrore(e: ApiError): void {
    this.salvando.set(false);
    this.errore.set(e.messaggio);
    this.violazioni.set((e.dettagli ?? []).flatMap((d) => d['violazione'] ?? []));
  }
}
