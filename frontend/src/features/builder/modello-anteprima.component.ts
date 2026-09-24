import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/builder-modelli';
import { forkJoin } from 'rxjs';

type Dettaglio = components['schemas']['ModelloDettaglio'];
type Versione = Dettaglio['versioni'][number];
type Nodo = {
  codice: string;
  figli?: Nodo[];
  lingue_possibili?: string[];
  livelli_possibili?: string[];
  [nome: string]: unknown;
};
type CandidatoDerivazione = { nome: string; valori: string[] };
type PolicyResponse = {
  policy: { nome_dimensione: string; consente_valore_generico: boolean }[];
};
const PROPRIETA_NODO = new Set([
  'codice',
  'descrizione',
  'tipo_livello',
  'figli',
  'campi',
  'lingue_possibili',
  'livelli_possibili',
  'livello_base',
]);

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
            Crea edizione collegata
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
                @if (campo.lingua) {
                  <span class="lingua">{{ campo.lingua }}</span>
                }
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
      <h2 id="derivazione-titolo" class="h4">Creare un'edizione collegata?</h2>
      <p>
        Viene creato un modello collegato con una nuova versione in bozza. Struttura e campi sono
        copiati dalla versione piu' recente; il modello di origine non viene modificato.
      </p>
      @if (candidatiDerivazione().length > 1) {
        <label for="dimensione-derivazione">Dimensione</label>
        <select
          id="dimensione-derivazione"
          class="form-select mb-3"
          [value]="dimensioneScelta()"
          (change)="scegliDimensione($any($event.target).value)"
        >
          @for (candidato of candidatiDerivazione(); track candidato.nome) {
            <option [value]="candidato.nome">{{ etichetta(candidato.nome) }}</option>
          }
        </select>
      }
      @if (candidatoScelto(); as candidato) {
        @if (candidato.valori.length > 1) {
          <label for="valore-derivazione">Nuovo valore</label>
          <select
            id="valore-derivazione"
            class="form-select mb-3"
            [value]="valoreScelto()"
            (change)="valoreScelto.set($any($event.target).value)"
          >
            @for (valore of candidato.valori; track valore) {
              <option [value]="valore">{{ valore }}</option>
            }
          </select>
        } @else {
          <p>
            <strong>{{ etichetta(candidato.nome) }}:</strong> {{ candidato.valori[0] }}
          </p>
        }
      }
      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" (click)="derivazione.close()">Annulla</button>
        <button class="btn btn-primary" (click)="creaEdizione(derivazione)">Crea</button>
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
  protected readonly candidatiDerivazione = signal<CandidatoDerivazione[]>([]);
  protected readonly dimensioneScelta = signal('');
  protected readonly valoreScelto = signal('');
  protected readonly candidatoScelto = computed(() =>
    this.candidatiDerivazione().find((item) => item.nome === this.dimensioneScelta()),
  );

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

  protected puoDerivare(): boolean {
    const m = this.modello();
    return !!m && !m.derivato_da_modello_id && this.candidatiDerivazione().length > 0;
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
          this.caricaCandidati(dettaglio);
        },
        error: (e: ApiError) => {
          this.errore.set(e.messaggio);
          this.caricamento.set(false);
        },
      });
  }

  protected scegliDimensione(nome: string): void {
    this.dimensioneScelta.set(nome);
    this.valoreScelto.set(this.candidatoScelto()?.valori[0] ?? '');
  }

  protected etichetta(nome: string): string {
    return nome.replaceAll('_', ' ').replace(/^./, (iniziale) => iniziale.toUpperCase());
  }

  protected creaEdizione(dialog: HTMLDialogElement): void {
    if (this.salvando() || !this.dimensioneScelta() || !this.valoreScelto()) return;
    dialog.close();
    this.salvando.set(true);
    this.errore.set(null);
    this.api
      .post<Dettaglio>(`/api/v1/builder/modelli/${this.id}/edizioni-derivate`, {
        nome_dimensione: this.dimensioneScelta(),
        valore: this.valoreScelto(),
      })
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

  private caricaCandidati(dettaglio: Dettaglio): void {
    if (dettaglio.derivato_da_modello_id) return;
    forkJoin({
      struttura: this.api.get<{ nodi: Nodo[] }>(
        `/api/v1/builder/tipi-documento/${encodeURIComponent(dettaglio.codice_tipo_documento)}/struttura-disponibile`,
      ),
      policy: this.api.get<PolicyResponse>(
        `/api/v1/builder/tipi-documento/${encodeURIComponent(dettaglio.codice_tipo_documento)}/policy-dimensioni`,
      ),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ struttura, policy }) => {
          let nodi = struttura.nodi;
          let foglia: Nodo | undefined;
          for (const codice of dettaglio.percorso_categorizzazione) {
            foglia = nodi.find((nodo) => nodo.codice === codice);
            if (!foglia) break;
            nodi = foglia.figli ?? [];
          }
          if (!foglia) return;
          const valori = new Map<string, string[]>();
          if (foglia.lingue_possibili?.length) valori.set('lingua', foglia.lingue_possibili);
          if (foglia.livelli_possibili?.length) {
            valori.set('livello_professionale', foglia.livelli_possibili);
          }
          for (const [nome, possibili] of Object.entries(foglia)) {
            if (!PROPRIETA_NODO.has(nome) && Array.isArray(possibili)) {
              valori.set(
                nome,
                possibili.filter((valore): valore is string => typeof valore === 'string'),
              );
            }
          }
          const obbligatorie = new Set(
            policy.policy
              .filter((item) => !item.consente_valore_generico)
              .map((item) => item.nome_dimensione),
          );
          const candidati = [...valori]
            .filter(([nome, possibili]) => obbligatorie.has(nome) && possibili.length >= 2)
            .map(([nome, possibili]) => ({
              nome,
              valori: possibili.filter((valore) => valore !== dettaglio.dimensioni[nome]),
            }))
            .filter((item) => item.valori.length > 0);
          this.candidatiDerivazione.set(candidati);
          this.scegliDimensione(candidati[0]?.nome ?? '');
        },
        error: () => this.candidatiDerivazione.set([]),
      });
  }
}
