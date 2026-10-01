import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { FrammentoTesto } from '../builder/frammenti';

type CornicePagina = {
  logo_ref: string | null;
  intestazione: FrammentoTesto[];
  pie_pagina: FrammentoTesto[];
  numerazione_pagine: boolean;
};
type CorniceTipoDocumento = { cornice: CornicePagina | null; loghi_disponibili: string[] };

const RIGHE_MASSIME = 3;

/**
 * Cornice di pagina di un tipo documento (012 US3, T047): cio' che si ripete
 * su ogni pagina di ogni documento di quel tipo.
 *
 * E' dell'amministratore, non di chi compone il bando: il gestore non la vede
 * nell'editor e non la puo' sbagliare (FR-011). L'intestazione e' testo su
 * piu' righe con la prima, di solito il nome dell'ente, eventualmente in
 * grassetto: per tre righe fisse un editor completo sarebbe di troppo.
 */
@Component({
  selector: 'app-cornice',
  standalone: true,
  imports: [RouterLink],
  styleUrl: './cornice.component.scss',
  template: `
    <nav class="mm-breadcrumb" aria-label="Percorso">
      <a routerLink="/configurazione">Impostazioni</a><span>/</span>
      <a routerLink="/configurazione/tipi-documento">Tipi documento</a><span>/</span>
      <code>{{ codice }}</code
      ><span>/</span>
      Cornice di pagina
    </nav>

    <header class="cornice-header">
      <h1>Cornice di pagina</h1>
      <p>
        Logo, intestazione e piè di pagina compaiono su <strong>ogni pagina</strong> di ogni
        documento di tipo <code>{{ codice }}</code
        >, nell'anteprima e nei documenti generati. Chi compone i modelli non la modifica.
      </p>
    </header>

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

    @if (!caricamento()) {
      <form class="cornice-form" (submit)="$event.preventDefault(); salva()">
        <fieldset>
          <legend>Logo</legend>
          @if (loghi().length) {
            <label class="form-check">
              <input
                class="form-check-input"
                type="checkbox"
                data-cornice-logo
                [checked]="conLogo()"
                (change)="conLogo.set($any($event.target).checked)"
              />
              Logo dell'ente in alto a sinistra
            </label>
          } @else {
            <p class="nota" data-cornice-no-logo>
              Il file del logo dell'ente non è ancora stato fornito: la cornice esce senza logo.
            </p>
          }
        </fieldset>

        <label for="cornice-intestazione">Intestazione</label>
        <textarea
          id="cornice-intestazione"
          class="form-control"
          rows="3"
          data-cornice-intestazione
          [value]="intestazione()"
          (input)="intestazione.set($any($event.target).value)"
        ></textarea>
        <p class="nota" [class.troppe]="righeIntestazione() > righeMassime">
          {{ righeIntestazione() }} di {{ righeMassime }} righe, accanto al logo.
        </p>
        <label class="form-check">
          <input
            class="form-check-input"
            type="checkbox"
            data-cornice-grassetto
            [checked]="primaInGrassetto()"
            (change)="primaInGrassetto.set($any($event.target).checked)"
          />
          Prima riga in grassetto
        </label>

        <label for="cornice-piede">Piè di pagina</label>
        <input
          id="cornice-piede"
          class="form-control"
          type="text"
          data-cornice-piede
          [value]="piede()"
          (input)="piede.set($any($event.target).value)"
        />
        <label class="form-check">
          <input
            class="form-check-input"
            type="checkbox"
            data-cornice-numerazione
            [checked]="numerazione()"
            (change)="numerazione.set($any($event.target).checked)"
          />
          Numero di pagina ("Pagina 2 di 5") in basso a destra
        </label>

        <div class="azioni">
          <button
            type="submit"
            class="btn btn-primary"
            data-cornice-salva
            [disabled]="salvando() || righeIntestazione() > righeMassime"
          >
            {{ salvando() ? 'Salvataggio...' : 'Salva cornice' }}
          </button>
          @if (salvata()) {
            <span role="status" class="salvata" data-cornice-salvata
              >Salvata: vale da subito per tutti i documenti di questo tipo.</span
            >
          }
        </div>
      </form>
    }
  `,
})
export class CorniceComponent {
  private readonly api = inject(ApiClient);
  private readonly destroyRef = inject(DestroyRef);
  private readonly route = inject(ActivatedRoute);

  protected readonly codice = this.route.snapshot.paramMap.get('codice') ?? '';
  private readonly integrazioneId = this.route.snapshot.queryParamMap.get('integrazioneId') ?? '';
  protected readonly righeMassime = RIGHE_MASSIME;

  protected readonly caricamento = signal(true);
  protected readonly salvando = signal(false);
  protected readonly salvata = signal(false);
  protected readonly errore = signal<string | null>(null);
  protected readonly violazioni = signal<string[]>([]);
  protected readonly loghi = signal<string[]>([]);
  protected readonly conLogo = signal(true);
  protected readonly intestazione = signal('');
  protected readonly primaInGrassetto = signal(true);
  protected readonly piede = signal('');
  protected readonly numerazione = signal(true);

  constructor() {
    if (!this.integrazioneId) {
      this.caricamento.set(false);
      this.errore.set("Manca l'integrazione a cui appartiene il tipo documento.");
      return;
    }
    this.api
      .get<CorniceTipoDocumento>(this.url())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (risposta) => {
          this.caricamento.set(false);
          this.applica(risposta);
        },
        error: (e: ApiError) => {
          this.caricamento.set(false);
          this.errore.set(e.messaggio);
        },
      });
  }

  protected righeIntestazione(): number {
    const testo = this.intestazione().trim();
    return testo ? testo.split('\n').length : 0;
  }

  protected salva(): void {
    this.salvando.set(true);
    this.salvata.set(false);
    this.errore.set(null);
    this.violazioni.set([]);
    this.api
      .put<CorniceTipoDocumento>(this.url(), this.cornice())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (risposta) => {
          this.salvando.set(false);
          this.salvata.set(true);
          this.applica(risposta);
        },
        error: (e: ApiError) => {
          this.salvando.set(false);
          this.errore.set(e.messaggio);
          this.violazioni.set((e.dettagli ?? []).flatMap((d) => d['violazione'] ?? []));
        },
      });
  }

  private url(): string {
    return `/api/v1/configurazione/integrazioni/${this.integrazioneId}/tipi-documento/${encodeURIComponent(this.codice)}/cornice`;
  }

  /** Dal form ai frammenti: la prima riga, se richiesto, in grassetto. */
  private cornice(): CornicePagina {
    const [prima = '', ...resto] = this.intestazione().trim().split('\n');
    const intestazione: FrammentoTesto[] = [];
    if (prima) intestazione.push({ testo: prima, grassetto: this.primaInGrassetto() });
    if (resto.length) intestazione.push({ testo: `\n${resto.join('\n')}` });
    const piede = this.piede().trim();
    return {
      logo_ref: this.conLogo() && this.loghi().length ? this.loghi()[0] : null,
      intestazione,
      pie_pagina: piede ? [{ testo: piede }] : [],
      numerazione_pagine: this.numerazione(),
    };
  }

  private applica(risposta: CorniceTipoDocumento): void {
    this.loghi.set(risposta.loghi_disponibili);
    const cornice = risposta.cornice;
    if (!cornice) return;
    this.conLogo.set(!!cornice.logo_ref);
    this.intestazione.set(cornice.intestazione.map((f) => f.testo).join(''));
    this.primaInGrassetto.set(!!cornice.intestazione[0]?.grassetto);
    this.piede.set(cornice.pie_pagina.map((f) => f.testo).join(''));
    this.numerazione.set(cornice.numerazione_pagine);
  }
}
