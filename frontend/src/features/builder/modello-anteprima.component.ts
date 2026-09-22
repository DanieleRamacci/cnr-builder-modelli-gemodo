import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/builder-modelli';

type Dettaglio = components['schemas']['ModelloDettaglio'];
type Versione = Dettaglio['versioni'][number];

/**
 * Schermata 2b (builder-editor) in versione ridotta, decisa il 2026-09-22.
 *
 * Oggi mostra solo cio' che l'API rende davvero disponibile: il contratto dati
 * della versione, gli stati e il percorso di categorizzazione. L'outline delle
 * sezioni e il foglio centrale restano dichiaratamente vuoti finche' `003` non
 * introduce sezioni e segnaposto: meglio uno stato esplicito che un contenuto
 * finto. La stessa pagina diventera' l'editor vero.
 */
@Component({
  standalone: true,
  imports: [RouterLink],
  styleUrl: './modello-anteprima.component.scss',
  template: `
    <header class="topbar">
      <a [routerLink]="['/contesti', contesto(), 'modelli']">&larr; Modelli</a>
      <span class="divisore" aria-hidden="true"></span>
      @if (modello(); as m) {
        <span class="titolo">{{ m.nome }}</span>
        <span class="meta"
          >{{ m.codice }} · v{{ corrente()?.numero_versione }} · {{ corrente()?.stato }}</span
        >
      }
      <div class="azioni">
        @if (puoDerivare()) {
          <button
            type="button"
            class="btn btn-sm"
            [disabled]="salvando()"
            (click)="derivazione.showModal()"
          >
            Crea versione inglese
          </button>
        }
      </div>
    </header>

    @if (errore()) {
      <div class="alert alert-danger" role="alert">{{ errore() }}</div>
    }
    @if (caricamento()) {
      <p role="status">Caricamento...</p>
    }

    @if (modello(); as m) {
      <div class="corpo">
        <aside class="outline">
          <h2>Sezioni</h2>
          <p class="vuoto-sezioni">
            Nessuna sezione: i contenuti del documento e i segnaposto arrivano con la spec 003, non
            ancora implementata.
          </p>
        </aside>

        <section class="foglio">
          <div class="pagina">
            <p class="vuoto-sezioni">
              L'anteprima del documento comparira' qui quando il modello avra' contenuti (spec 003).
              Oggi il modello definisce solo il contratto dati qui a destra.
            </p>
          </div>
        </section>

        <aside class="pannello">
          <h2>Campi del contratto</h2>
          @if (!corrente()?.campi?.length) {
            <p class="vuoto-sezioni">Questa versione non ha campi.</p>
          }
          @for (campo of corrente()?.campi ?? []; track campo.codice + campo.lingua) {
            <div class="campo">
              <div class="riga">
                <span class="token">{{ campo.codice }}</span>
                <span class="tipo">{{ campo.tipo }}</span>
              </div>
              <div class="etichetta">{{ campo.etichetta }}</div>
              <div class="riga">
                <span class="lingua">{{ campo.lingua }}</span>
                @if (campo.obbligatorio) {
                  <span class="pill">obbligatorio</span>
                }
              </div>
            </div>
          }

          <h2>Versioni</h2>
          @for (versione of m.versioni; track versione.id) {
            <div class="versione">
              v{{ versione.numero_versione }} · {{ versione.stato }}
              <span class="api">ID API: {{ versione.public_id ?? '-' }}</span>
            </div>
          }

          <footer>
            Categoria: <strong>{{ m.percorso_categorizzazione.join(' / ') }}</strong>
          </footer>
        </aside>
      </div>
    }

    <dialog #derivazione aria-labelledby="derivazione-titolo">
      <h2 id="derivazione-titolo" class="h4">Creare la versione inglese?</h2>
      <p>
        Viene creato un modello collegato con una nuova versione in bozza. Struttura e campi sono
        copiati dalla versione piu' recente; il modello italiano non viene modificato.
      </p>
      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" (click)="derivazione.close()">Annulla</button>
        <button class="btn btn-primary" (click)="creaEdizioneInglese(derivazione)">Crea</button>
      </div>
    </dialog>
  `,
})
export class ModelloAnteprimaComponent {
  private readonly api = inject(ApiClient);
  private readonly destroyRef = inject(DestroyRef);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('modelId')!;
  protected readonly modello = signal<Dettaglio | null>(null);
  protected readonly caricamento = signal(false);
  protected readonly salvando = signal(false);
  protected readonly errore = signal<string | null>(null);

  constructor() {
    this.carica();
  }

  protected contesto(): string {
    return this.modello()?.codice_contesto ?? '';
  }

  /** La versione piu' recente: e' quella che l'utente considera "il modello". */
  protected corrente(): Versione | undefined {
    return this.modello()?.versioni?.[0];
  }

  // Un'edizione inglese si crea solo da un originale italiano non derivato.
  // Il backend resta l'autorita': risponde EDIZIONE_DERIVATA_DUPLICATA.
  protected puoDerivare(): boolean {
    const m = this.modello();
    return !!m && m.lingua === 'IT' && !m.derivato_da_modello_id;
  }

  protected carica(): void {
    this.caricamento.set(true);
    this.errore.set(null);
    this.api
      .get<Dettaglio>(`/api/v1/builder/modelli/${this.id}`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (dettaglio) => {
          this.modello.set(dettaglio);
          this.caricamento.set(false);
        },
        error: (e: ApiError) => {
          this.errore.set(e.messaggio);
          this.caricamento.set(false);
        },
      });
  }

  protected creaEdizioneInglese(dialog: HTMLDialogElement): void {
    if (this.salvando()) return;
    dialog.close();
    this.salvando.set(true);
    this.errore.set(null);
    this.api
      .post<Dettaglio>(`/api/v1/builder/modelli/${this.id}/edizioni-derivate`, { lingua: 'EN' })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.salvando.set(false);
          this.carica();
        },
        error: (e: ApiError) => {
          this.salvando.set(false);
          this.errore.set(e.messaggio);
        },
      });
  }
}
