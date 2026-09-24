import { DOCUMENT } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  computed,
  effect,
  inject,
  signal,
  viewChildren,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/builder-modelli';
import { forkJoin } from 'rxjs';

type Dettaglio = components['schemas']['ModelloDettaglio'];
type Versione = Dettaglio['versioni'][number];
type CampoVersione = Versione['campi'][number];
type Nodo = {
  codice: string;
  figli?: Nodo[];
  lingue_possibili?: string[];
  livelli_possibili?: string[];
  [nome: string]: unknown;
};
type CandidatoDerivazione = { nome: string; valori: string[] };
type AzioneVersione = {
  route: string;
  label: string;
  conferma: string;
  /** `true` dove il backend valida il documento prima di accettare la transizione. */
  verificaDocumento: boolean;
};
type StatoSalvataggio = {
  codice: 'salvato' | 'modificato' | 'salvataggio' | 'errore';
  etichetta: string;
};
type PannelloBuilder = 'segnaposto' | 'blocchi' | 'proprieta';
type BloccoPredefinito = {
  codice: string;
  titolo: string;
  descrizione: string;
  contenuto: string;
  stile: 'H1' | 'H2' | null;
};
type PolicyResponse = {
  policy: { nome_dimensione: string; consente_valore_generico: boolean }[];
};
type BloccoDocumento = {
  id: string;
  tipo: 'PARAGRAFO';
  contenuto: string | null;
  posizionamento: 'BODY';
  ordine: number;
  stile?: string | null;
  placeholder_usati: string[];
  regole_layout?: Record<string, string>;
  asset_ref?: string | null;
  colonne?: string[];
};
type SezioneDocumento = {
  codice: string;
  ordine: number;
  contenuto: BloccoDocumento[];
};
type SezioniResponse = {
  modello_versione_id: string;
  stato_versione: string;
  modificabile: boolean;
  sezioni: SezioneDocumento[];
  documento: {
    blocchi: BloccoDocumento[];
    placeholder_usati: string[];
  };
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
const AZIONI_VERSIONE: Record<string, AzioneVersione> = {
  BOZZA: {
    route: 'invia-revisione',
    label: 'Invia in revisione',
    conferma:
      "La versione passa in revisione: da quel momento le sezioni non sono piu' modificabili.",
    verificaDocumento: false,
  },
  IN_REVISIONE: {
    route: 'approva',
    label: 'Approva',
    conferma: 'La versione viene approvata e resta pronta per la pubblicazione.',
    verificaDocumento: false,
  },
  APPROVATO: {
    route: 'pubblica',
    label: 'Pubblica',
    conferma:
      "La pubblicazione rende il modello utilizzabile e archivia la versione corrente: non e' reversibile.",
    verificaDocumento: true,
  },
};

/**
 * Schermata 2b (builder-editor) in versione ridotta, decisa il 2026-09-22.
 *
 * La `003` ora espone sezioni versionate: questa pagina e' diventata l'editor
 * minimo del documento, mantenendo il contratto dati accanto al foglio.
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
      <span
        class="save-state"
        data-save-state
        role="status"
        [attr.data-state]="statoSalvataggio().codice"
        >{{ statoSalvataggio().etichetta }}</span
      >
      <div class="azioni">
        @if (puoDerivare()) {
          <button
            type="button"
            class="btn btn-sm"
            [disabled]="salvando()"
            (click)="derivazione.showModal()"
          >
            Crea modello derivato
          </button>
        }
        <button type="button" class="btn btn-sm" (click)="scorriAnteprima()">Anteprima</button>
        <button
          type="button"
          class="btn btn-sm"
          data-export-docx
          disabled
          title="Il backend non espone ancora un export .docx del modello: vedi T123 in tasks.md"
        >
          Esporta .docx
        </button>
        @if (azioneVersione(); as azione) {
          <button
            type="button"
            class="btn btn-sm primary"
            data-version-action
            [disabled]="salvandoStato() || salvandoSezioni()"
            (click)="confermaAzione.showModal()"
          >
            {{ salvandoStato() ? 'Aggiornamento...' : azione.label }}
          </button>
        }
      </div>
    </header>

    @if (violazioniStato().length) {
      <div class="alert alert-danger" role="alert" data-transition-blocks>
        Il backend ha rifiutato la transizione:
        <ul class="mb-0">
          @for (violazione of violazioniStato(); track violazione) {
            <li>{{ violazione }}</li>
          }
        </ul>
      </div>
    }

    @if (errore()) {
      <div class="alert alert-danger" role="alert">{{ errore() }}</div>
    }
    @if (caricamento()) {
      <p role="status">Caricamento...</p>
    }

    @if (modello(); as m) {
      <div class="format-toolbar">
        <button
          type="button"
          class="tool strong"
          disabled
          title="Stile inline non ancora persistito"
        >
          B
        </button>
        <button
          type="button"
          class="tool italic"
          disabled
          title="Stile inline non ancora persistito"
        >
          I
        </button>
        <button
          type="button"
          class="tool underline"
          disabled
          title="Stile inline non ancora persistito"
        >
          U
        </button>
        <span class="separator"></span>
        <button type="button" class="tool" (click)="applicaStileBlocco('H1')">H1</button>
        <button type="button" class="tool" (click)="applicaStileBlocco('H2')">H2</button>
        <span class="separator"></span>
        <button type="button" class="tool" (click)="applicaLista('ordinata')">1.</button>
        <button type="button" class="tool" (click)="applicaLista('puntata')">•</button>
        <button type="button" class="tool" (click)="inserisciTab()">Tab</button>
        <span class="hint"
          >Clicca un segnaposto nel pannello laterale per inserirlo nella sezione selezionata</span
        >
      </div>

      <div class="corpo">
        <aside class="outline">
          <h2>Sezioni del modello</h2>
          @if (sezioniLocali().length === 0) {
            <p class="vuoto-sezioni">Nessuna sezione configurata.</p>
          }
          @for (sezione of sezioniLocali(); track sezione.codice; let i = $index) {
            <div class="outline-item" [class.selected]="sezione.codice === sezioneAttiva()">
              <button
                type="button"
                class="outline-select"
                (click)="selezionaSezione(sezione.codice)"
              >
                <span class="handle" aria-hidden="true">≡</span>
                <span class="outline-copy">
                  <strong>{{ sezione.codice }}</strong>
                  <small>modificabile · {{ placeholderSezione(sezione).length }} segnaposto</small>
                </span>
              </button>
              @if (sezioni()?.modificabile) {
                <div class="section-actions">
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-secondary"
                    [disabled]="i === 0 || salvandoSezioni()"
                    [attr.data-move-section]="sezione.codice"
                    data-direction="up"
                    (click)="spostaSezione(i, -1); $event.stopPropagation()"
                  >
                    Su
                  </button>
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-secondary"
                    [disabled]="i === sezioniLocali().length - 1 || salvandoSezioni()"
                    [attr.data-move-section]="sezione.codice"
                    data-direction="down"
                    (click)="spostaSezione(i, 1); $event.stopPropagation()"
                  >
                    Giu
                  </button>
                  <button
                    type="button"
                    class="btn btn-sm btn-outline-danger"
                    [disabled]="salvandoSezioni()"
                    [attr.data-remove-section]="sezione.codice"
                    (click)="rimuoviSezione(sezione.codice); $event.stopPropagation()"
                  >
                    Rimuovi
                  </button>
                </div>
              }
            </div>
          }
          @if (sezioni()?.modificabile) {
            <button
              type="button"
              class="btn btn-sm btn-outline-primary w-100 mt-2"
              data-add-section
              [disabled]="salvandoSezioni()"
              (click)="aggiungiSezione()"
            >
              Aggiungi sezione
            </button>
            <button
              type="button"
              class="btn btn-sm btn-primary w-100 mt-2"
              data-save-sections
              [disabled]="salvandoSezioni()"
              (click)="salvaSezioni()"
            >
              {{ salvandoSezioni() ? 'Salvataggio...' : 'Salva documento' }}
            </button>
          } @else if (sezioni()) {
            <p class="vuoto-sezioni">
              Versione in sola lettura: le sezioni pubblicate restano consultabili.
            </p>
          }

          @if (sezioni()) {
            <section class="readiness" data-readiness>
              <h3>Pronto per la pubblicazione</h3>
              @if (blocchiDocumento().length === 0) {
                <p class="readiness-ok">Nessun blocco: il documento rispetta il contratto dati.</p>
              } @else {
                <ul class="readiness-elenco">
                  @for (blocco of blocchiDocumento(); track blocco) {
                    <li data-readiness-block>{{ blocco }}</li>
                  }
                </ul>
              }
            </section>
          }
        </aside>

        <section class="foglio">
          <div class="pagina" id="anteprima-documento" data-document-preview>
            <div class="document-header">
              <div class="logo-box" aria-hidden="true"></div>
              <div class="document-heading">
                <strong
                  >Comune di
                  <span class="inline-token">{{ tokenDocumento(['ente', 'comune'], 'ente') }}</span>
                </strong>
                <span>Area appalti e contratti</span>
              </div>
              <div class="document-meta">
                Det. n.
                <span class="inline-token">{{
                  tokenDocumento(['numero', 'determina'], 'numero_atto')
                }}</span>
                <br />
                del
                <span class="inline-token">{{ tokenDocumento(['data'], 'data_atto') }}</span>
              </div>
            </div>

            <div class="document-body">
              @if (erroreSezioni()) {
                <div class="alert alert-danger" role="alert">
                  {{ erroreSezioni() }}
                  @if (violazioniSezioni().length) {
                    <ul class="mb-0">
                      @for (violazione of violazioniSezioni(); track violazione) {
                        <li>{{ violazione }}</li>
                      }
                    </ul>
                  }
                </div>
              }

              @if (sezioni()?.modificabile) {
                @for (sezione of sezioniLocali(); track sezione.codice) {
                  <article
                    class="section-editor"
                    [class.selected]="sezione.codice === sezioneAttiva()"
                    [class.style-h1]="stileSezione(sezione) === 'H1'"
                    [class.style-h2]="stileSezione(sezione) === 'H2'"
                  >
                    <span class="section-tag">{{ etichettaStile(stileSezione(sezione)) }}</span>
                    <h3>{{ sezione.codice }}</h3>
                    <div
                      #editor
                      class="editor-text"
                      contenteditable="plaintext-only"
                      role="textbox"
                      tabindex="0"
                      spellcheck="true"
                      [attr.aria-label]="'Testo sezione ' + sezione.codice"
                      [attr.data-section-text]="sezione.codice"
                      (focus)="selezionaSezione(sezione.codice, editor)"
                      (blur)="autosalva()"
                      (input)="aggiornaTestoDaEditor(sezione.codice, editor)"
                      (keydown)="gestisciTastoEditor($event, sezione.codice, editor)"
                      (dragover)="consentiDrop($event)"
                      (drop)="rilasciaSegnaposto($event, sezione.codice, editor)"
                    ></div>
                  </article>
                }
              } @else {
                @if ((sezioni()?.documento?.blocchi?.length ?? 0) === 0) {
                  <p class="vuoto-sezioni">L'anteprima del documento composto comparira' qui.</p>
                }
                @for (blocco of sezioni()?.documento?.blocchi ?? []; track blocco.id) {
                  <article
                    class="section-editor readonly"
                    [class.style-h1]="blocco.stile === 'H1'"
                    [class.style-h2]="blocco.stile === 'H2'"
                  >
                    <span class="section-tag">{{ etichettaStile(blocco.stile ?? '') }}</span>
                    <div class="editor-text">{{ blocco.contenuto || 'Blocco senza testo' }}</div>
                  </article>
                }
              }

              <div class="document-signature">
                <div>
                  <strong>Il Responsabile del procedimento</strong>
                  <span class="inline-token">{{
                    tokenDocumento(['rup', 'responsabile'], 'rup')
                  }}</span>
                </div>
              </div>

              @if (sezioni()?.modificabile) {
                <button
                  type="button"
                  class="add-section-inline"
                  data-add-section-inline
                  [disabled]="salvandoSezioni()"
                  (click)="aggiungiSezione()"
                >
                  Inserisci una nuova sezione di testo
                </button>
              }
            </div>
          </div>
        </section>

        <aside class="pannello">
          <div class="panel-tabs" role="tablist" aria-label="Pannello builder">
            <button
              type="button"
              role="tab"
              [class.active]="pannelloAttivo() === 'segnaposto'"
              [attr.aria-selected]="pannelloAttivo() === 'segnaposto'"
              (click)="pannelloAttivo.set('segnaposto')"
            >
              Segnaposto
            </button>
            <button
              type="button"
              role="tab"
              [class.active]="pannelloAttivo() === 'blocchi'"
              [attr.aria-selected]="pannelloAttivo() === 'blocchi'"
              (click)="pannelloAttivo.set('blocchi')"
            >
              Blocchi
            </button>
            <button
              type="button"
              role="tab"
              [class.active]="pannelloAttivo() === 'proprieta'"
              [attr.aria-selected]="pannelloAttivo() === 'proprieta'"
              (click)="pannelloAttivo.set('proprieta')"
            >
              Proprietà
            </button>
          </div>
          <div class="panel-body">
            @if (pannelloAttivo() === 'segnaposto') {
              <label class="visually-hidden" for="cerca-segnaposto">Cerca segnaposto</label>
              <input
                id="cerca-segnaposto"
                class="form-control"
                type="text"
                placeholder="Cerca segnaposto"
                [value]="ricercaSegnaposto()"
                (input)="ricercaSegnaposto.set($any($event.target).value)"
              />
              <p class="panel-hint">
                Clicca per inserire nella sezione selezionata. I segnaposto derivano dai campi della
                versione.
              </p>

              <h2>Segnaposto</h2>
              @if (!corrente()?.campi?.length) {
                <p class="vuoto-sezioni">Questa versione non ha campi.</p>
              } @else if (campiSegnaposto().length === 0) {
                <p class="vuoto-sezioni">Nessun segnaposto trovato.</p>
              }
              @for (campo of campiSegnaposto(); track campo.codice + campo.lingua) {
                <button
                  type="button"
                  class="campo"
                  [attr.data-placeholder]="campo.codice"
                  draggable="true"
                  [disabled]="!sezioni()?.modificabile || !sezioneAttiva() || salvandoSezioni()"
                  (dragstart)="iniziaTrascinamento($event, campo)"
                  (click)="inserisciPlaceholderAttivo(campo)"
                >
                  <span class="drag-handle" aria-hidden="true">⠿</span>
                  <span class="campo-copy">
                    <span class="riga">
                      <span class="token">{{ campo.codice }}</span>
                      <span class="tipo">{{ campo.tipo }}</span>
                    </span>
                    <span class="etichetta">{{ campo.etichetta }}</span>
                    <span class="riga">
                      @if (campo.lingua) {
                        <span class="lingua">{{ campo.lingua }}</span>
                      }
                      @if (campo.obbligatorio) {
                        <span class="pill">obbligatorio</span>
                      }
                    </span>
                  </span>
                </button>
              }
            } @else if (pannelloAttivo() === 'blocchi') {
              <p class="panel-hint">
                Blocchi di testo predefiniti per la categoria scelta. Clicca per inserirli come
                nuova sezione.
              </p>
              @for (blocco of blocchiPredefiniti(); track blocco.codice) {
                <button
                  type="button"
                  class="snippet"
                  [attr.data-block-template]="blocco.codice"
                  [disabled]="!sezioni()?.modificabile || salvandoSezioni()"
                  (click)="inserisciBloccoPredefinito(blocco)"
                >
                  <strong>{{ blocco.titolo }}</strong>
                  <span>{{ blocco.descrizione }}</span>
                </button>
              }
            } @else {
              @if (sezioneCorrente(); as sezione) {
                <h2>Proprietà</h2>
                <label for="proprieta-codice">Titolo sezione</label>
                <input
                  id="proprieta-codice"
                  class="form-control"
                  type="text"
                  [value]="sezione.codice"
                  readonly
                />
                <label for="proprieta-stile">Stile blocco</label>
                <select
                  id="proprieta-stile"
                  class="form-select"
                  [value]="stileSezione(sezione)"
                  [disabled]="!sezioni()?.modificabile || salvandoSezioni()"
                  (change)="impostaStileSezione($any($event.target).value)"
                >
                  <option value="">Paragrafo</option>
                  <option value="H1">Titolo H1</option>
                  <option value="H2">Titolo H2</option>
                </select>
                <div class="property-note">
                  <strong>{{ placeholderSezione(sezione).length }}</strong>
                  segnaposto usati in questa sezione.
                </div>
                <div class="property-note">
                  Ripetibile: <strong>No</strong><br />
                  Obbligatorietà: <strong>gestita dal contratto dati</strong>
                </div>
              } @else {
                <p class="vuoto-sezioni">Seleziona una sezione per modificarne le proprietà.</p>
              }
            }

            <h2>Versioni</h2>
            @for (versione of m.versioni; track versione.id) {
              <div class="versione">
                v{{ versione.numero_versione }} · {{ versione.stato }}
                <span class="api">ID API: {{ versione.public_id ?? '-' }}</span>
              </div>
            }
          </div>

          <footer>
            Categoria: <strong>{{ m.percorso_categorizzazione.join(' / ') }}</strong>
          </footer>
        </aside>
      </div>
    }

    <dialog #confermaAzione aria-labelledby="conferma-azione-titolo" data-confirm-transition>
      @if (azioneVersione(); as azione) {
        <h2 id="conferma-azione-titolo" class="h4">{{ azione.label }}?</h2>
        <p>{{ azione.conferma }}</p>
        @if (bloccoModificheNonSalvate()) {
          <p class="blocco-pubblicazione" data-readiness-block>
            Ci sono modifiche non salvate: salva il documento prima di cambiare stato.
          </p>
        }
        @if (azione.verificaDocumento && blocchiDocumento().length) {
          <p class="blocco-pubblicazione">Il documento non e' pubblicabile:</p>
          <ul class="blocco-pubblicazione-elenco">
            @for (blocco of blocchiDocumento(); track blocco) {
              <li data-readiness-block>{{ blocco }}</li>
            }
          </ul>
        }
        <div class="d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary" (click)="confermaAzione.close()">
            Annulla
          </button>
          <button
            class="btn btn-primary"
            data-confirm-transition-submit
            [disabled]="transizioneBloccata()"
            (click)="cambiaStatoVersione(azione, confermaAzione)"
          >
            Conferma
          </button>
        </div>
      }
    </dialog>

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
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('modelId')!;
  private editorAttivo: HTMLElement | null = null;
  protected readonly modello = signal<Dettaglio | null>(null);
  protected readonly caricamento = signal(false);
  protected readonly salvando = signal(false);
  protected readonly salvandoStato = signal(false);
  protected readonly errore = signal<string | null>(null);
  protected readonly sezioni = signal<SezioniResponse | null>(null);
  protected readonly sezioniLocali = signal<SezioneDocumento[]>([]);
  protected readonly salvandoSezioni = signal(false);
  protected readonly erroreSezioni = signal<string | null>(null);
  protected readonly violazioniSezioni = signal<string[]>([]);
  protected readonly sezioneAttiva = signal<string | null>(null);
  protected readonly documentoModificato = signal(false);
  protected readonly violazioniStato = signal<string[]>([]);
  protected readonly pannelloAttivo = signal<PannelloBuilder>('segnaposto');
  protected readonly ricercaSegnaposto = signal('');
  protected readonly candidatiDerivazione = signal<CandidatoDerivazione[]>([]);
  protected readonly dimensioneScelta = signal('');
  protected readonly valoreScelto = signal('');
  protected readonly candidatoScelto = computed(() =>
    this.candidatiDerivazione().find((item) => item.nome === this.dimensioneScelta()),
  );
  protected readonly campiSegnaposto = computed(() => {
    const query = this.ricercaSegnaposto().trim().toLocaleLowerCase();
    const campi = this.corrente()?.campi ?? [];
    if (!query) return campi;
    return campi.filter((campo) =>
      [campo.codice, campo.etichetta, campo.tipo, campo.lingua ?? '']
        .join(' ')
        .toLocaleLowerCase()
        .includes(query),
    );
  });
  protected readonly azioneVersione = computed(() => {
    const stato = this.corrente()?.stato;
    return stato ? (AZIONI_VERSIONE[stato] ?? null) : null;
  });
  protected readonly statoSalvataggio = computed<StatoSalvataggio>(() => {
    if (this.salvandoSezioni()) return { codice: 'salvataggio', etichetta: 'Salvataggio...' };
    if (this.erroreSezioni()) return { codice: 'errore', etichetta: 'Salvataggio non riuscito' };
    if (!this.sezioni()?.modificabile) {
      return { codice: 'salvato', etichetta: 'Versione in sola lettura' };
    }
    return this.documentoModificato()
      ? { codice: 'modificato', etichetta: 'Modifiche non salvate' }
      : { codice: 'salvato', etichetta: 'Tutte le modifiche salvate' };
  });
  /** I codici che il backend accetta come segnaposto: sono i campi della versione. */
  protected readonly placeholderAmmessi = computed(
    () => new Set((this.corrente()?.campi ?? []).map((campo) => campo.codice)),
  );
  /**
   * Gli stessi blocchi che `pubblica` applicherebbe lato backend
   * (`_valida_documento`), anticipati qui per non far scoprire il problema
   * con un 400 a transizione gia' tentata.
   */
  protected readonly blocchiDocumento = computed<string[]>(() => {
    const sezioni = this.sezioniLocali();
    if (sezioni.length === 0) return ['Il documento non ha sezioni.'];
    const blocchi: string[] = [];
    const ammessi = this.placeholderAmmessi();
    for (const sezione of sezioni) {
      if (!this.testoSezione(sezione).trim()) {
        blocchi.push(`La sezione "${sezione.codice}" non ha testo.`);
      }
      for (const placeholder of this.placeholderSezione(sezione)) {
        if (!ammessi.has(placeholder)) {
          blocchi.push(
            `Il segnaposto {{${placeholder}}} della sezione "${sezione.codice}" non esiste fra i campi della versione.`,
          );
        }
      }
    }
    return blocchi;
  });
  protected readonly bloccoModificheNonSalvate = computed(
    () => !!this.sezioni()?.modificabile && this.documentoModificato(),
  );
  protected readonly transizioneBloccata = computed(() => {
    if (this.salvandoStato() || this.salvandoSezioni()) return true;
    if (this.bloccoModificheNonSalvate()) return true;
    return !!this.azioneVersione()?.verificaDocumento && this.blocchiDocumento().length > 0;
  });
  protected readonly sezioneCorrente = computed(() => {
    const codice = this.sezioneAttiva();
    return this.sezioniLocali().find((sezione) => sezione.codice === codice) ?? null;
  });
  protected readonly blocchiPredefiniti = computed<BloccoPredefinito[]>(() => [
    {
      codice: 'oggetto',
      titolo: 'Oggetto',
      descrizione: 'Titolo sintetico con il segnaposto principale del modello.',
      contenuto: `Oggetto: ${this.tokenDocumento(['titolo', 'oggetto'], 'titolo')}`,
      stile: 'H1',
    },
    {
      codice: 'premesse',
      titolo: 'Premesse',
      descrizione: "Paragrafo introduttivo per motivare l'atto.",
      contenuto: 'Premesso che il procedimento richiede la predisposizione del presente atto.',
      stile: 'H2',
    },
    {
      codice: 'dettaglio',
      titolo: 'Dettaglio',
      descrizione: 'Blocco di testo operativo con i dati disponibili dal contratto.',
      contenuto: `Sono disponibili ${this.tokenDocumento(['numero', 'posti'], 'numero_posti')} elementi secondo il contratto dati associato.`,
      stile: null,
    },
  ]);

  private readonly editors = viewChildren<ElementRef<HTMLElement>>('editor');

  constructor() {
    // Il testo dell'editor NON e' un binding: `[textContent]` riscriveva il
    // nodo a ogni battuta e il caret tornava a inizio blocco, restituendo il
    // testo mescolato (visto sullo screenshot e2e del 2026-09-24). Qui il DOM
    // si allinea al modello solo quando la modifica arriva da fuori, cioe'
    // quando quell'editor non e' quello su cui si sta scrivendo.
    effect(() => {
      const sezioni = this.sezioniLocali();
      for (const riferimento of this.editors()) {
        const elemento = riferimento.nativeElement;
        if (elemento === this.document.activeElement) continue;
        const sezione = sezioni.find(
          (item) => item.codice === elemento.getAttribute('data-section-text'),
        );
        if (!sezione) continue;
        const testo = this.testoSezione(sezione);
        if (elemento.textContent !== testo) elemento.textContent = testo;
      }
    });
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
          this.caricaSezioni();
          this.caricaCandidati(dettaglio);
        },
        error: (e: ApiError) => {
          this.errore.set(e.messaggio);
          this.caricamento.set(false);
        },
      });
  }

  protected testoSezione(sezione: SezioneDocumento): string {
    return sezione.contenuto[0]?.contenuto ?? '';
  }

  protected stileSezione(sezione: SezioneDocumento): string {
    return sezione.contenuto[0]?.stile ?? '';
  }

  protected placeholderSezione(sezione: SezioneDocumento): string[] {
    return sezione.contenuto.flatMap((blocco) => blocco.placeholder_usati);
  }

  protected selezionaSezione(codice: string, editor?: HTMLElement): void {
    this.sezioneAttiva.set(codice);
    if (editor) this.editorAttivo = editor;
  }

  protected aggiungiSezione(
    contenuto = '',
    codiceBase = 'sezione',
    stile: 'H1' | 'H2' | null = null,
    apriProprieta = false,
  ): void {
    const codice =
      codiceBase === 'sezione'
        ? this.codiceSezioneLibero(`sezione-${this.sezioniLocali().length + 1}`)
        : this.codiceSezioneLibero(codiceBase);
    this.sezioniLocali.update((sezioni) => [
      ...sezioni,
      {
        codice,
        ordine: sezioni.length,
        contenuto: [{ ...this.nuovoBlocco(codice, contenuto), stile }],
      },
    ]);
    this.sezioneAttiva.set(codice);
    this.documentoModificato.set(true);
    if (apriProprieta) this.pannelloAttivo.set('proprieta');
  }

  protected inserisciBloccoPredefinito(blocco: BloccoPredefinito): void {
    this.aggiungiSezione(blocco.contenuto, blocco.codice, blocco.stile, true);
  }

  protected rimuoviSezione(codice: string): void {
    const aggiornate = this.riordina(
      this.sezioniLocali().filter((sezione) => sezione.codice !== codice),
    );
    this.sezioniLocali.set(aggiornate);
    this.documentoModificato.set(true);
    if (this.sezioneAttiva() === codice) {
      this.sezioneAttiva.set(aggiornate[0]?.codice ?? null);
    }
  }

  protected spostaSezione(indice: number, direzione: -1 | 1): void {
    this.sezioniLocali.update((sezioni) => {
      const destinazione = indice + direzione;
      if (destinazione < 0 || destinazione >= sezioni.length) return sezioni;
      const aggiornate = [...sezioni];
      [aggiornate[indice], aggiornate[destinazione]] = [
        aggiornate[destinazione],
        aggiornate[indice],
      ];
      this.documentoModificato.set(true);
      return this.riordina(aggiornate);
    });
  }

  protected aggiornaTesto(codice: string, testo: string): void {
    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) =>
        sezione.codice === codice ? this.sezioneConTesto(sezione, testo) : sezione,
      ),
    );
  }

  protected aggiornaTestoDaEditor(codice: string, editor: HTMLElement): void {
    this.aggiornaTesto(codice, this.testoEditor(editor));
  }

  protected gestisciTastoEditor(event: KeyboardEvent, codice: string, editor: HTMLElement): void {
    if (event.key !== 'Tab') return;
    event.preventDefault();
    this.inserisciTestoNelEditor(codice, '  ', editor);
  }

  protected inserisciPlaceholder(codiceSezione: string, campo: CampoVersione): void {
    const token = `{{${campo.codice}}}`;
    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) => {
        if (sezione.codice !== codiceSezione) return sezione;
        const testo = this.testoSezione(sezione);
        return this.sezioneConTesto(sezione, `${testo}${testo ? ' ' : ''}${token}`);
      }),
    );
  }

  protected inserisciPlaceholderAttivo(campo: CampoVersione): void {
    const codice = this.sezioneAttiva();
    if (!codice) return;
    this.inserisciTestoNelEditor(codice, `{{${campo.codice}}}`);
  }

  protected iniziaTrascinamento(event: DragEvent, campo: CampoVersione): void {
    event.dataTransfer?.setData('application/x-gemodo-placeholder', campo.codice);
    event.dataTransfer?.setData('text/plain', `{{${campo.codice}}}`);
  }

  protected consentiDrop(event: DragEvent): void {
    if (!this.sezioni()?.modificabile || this.salvandoSezioni()) return;
    event.preventDefault();
  }

  protected rilasciaSegnaposto(event: DragEvent, codiceSezione: string, editor: HTMLElement): void {
    event.preventDefault();
    this.selezionaSezione(codiceSezione, editor);
    const codiceCampo = event.dataTransfer?.getData('application/x-gemodo-placeholder');
    if (codiceCampo) {
      const campo = this.corrente()?.campi.find((item) => item.codice === codiceCampo);
      if (campo) {
        this.inserisciTestoNelEditor(codiceSezione, `{{${campo.codice}}}`, editor);
        return;
      }
    }
    const testo = event.dataTransfer?.getData('text/plain');
    if (testo) this.inserisciTestoNelEditor(codiceSezione, testo, editor);
  }

  protected applicaStileBlocco(stile: 'H1' | 'H2'): void {
    const codice = this.sezioneAttiva();
    if (!codice || !this.sezioni()?.modificabile) return;
    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) => {
        if (sezione.codice !== codice) return sezione;
        const blocco = sezione.contenuto[0] ?? this.nuovoBlocco(sezione.codice, '');
        return {
          ...sezione,
          contenuto: [
            {
              ...blocco,
              stile: blocco.stile === stile ? null : stile,
            },
            ...sezione.contenuto.slice(1),
          ],
        };
      }),
    );
  }

  protected impostaStileSezione(stile: string): void {
    const codice = this.sezioneAttiva();
    if (!codice || !this.sezioni()?.modificabile) return;
    const normalizzato = stile === 'H1' || stile === 'H2' ? stile : null;
    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) => {
        if (sezione.codice !== codice) return sezione;
        const blocco = sezione.contenuto[0] ?? this.nuovoBlocco(sezione.codice, '');
        return {
          ...sezione,
          contenuto: [{ ...blocco, stile: normalizzato }, ...sezione.contenuto.slice(1)],
        };
      }),
    );
  }

  protected applicaLista(tipo: 'ordinata' | 'puntata'): void {
    const codice = this.sezioneAttiva();
    if (!codice || !this.sezioni()?.modificabile) return;
    const sezione = this.sezioniLocali().find((item) => item.codice === codice);
    if (!sezione) return;
    const righe = this.testoSezione(sezione)
      .split('\n')
      .map((riga, indice) => {
        const pulita = riga.replace(/^(\d+\.|-)\s+/, '');
        return tipo === 'ordinata' ? `${indice + 1}. ${pulita}` : `- ${pulita}`;
      });
    this.aggiornaTesto(codice, righe.join('\n'));
    this.sincronizzaEditorAttivo(codice);
  }

  protected inserisciTab(): void {
    const codice = this.sezioneAttiva();
    if (!codice) return;
    this.inserisciTestoNelEditor(codice, '  ');
  }

  protected scorriAnteprima(): void {
    this.document.getElementById('anteprima-documento')?.scrollIntoView({ block: 'center' });
  }

  protected cambiaStatoVersione(azione: AzioneVersione, dialog?: HTMLDialogElement): void {
    const versione = this.corrente();
    if (!versione || this.salvandoStato() || this.transizioneBloccata()) return;
    dialog?.close();
    this.salvandoStato.set(true);
    this.errore.set(null);
    this.violazioniStato.set([]);
    this.api
      .post<Versione>(
        `/api/v1/builder/modelli/${this.id}/versioni/${versione.id}/${azione.route}`,
        {},
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.salvandoStato.set(false);
          this.carica();
        },
        error: (e: ApiError) => {
          this.salvandoStato.set(false);
          this.errore.set(e.messaggio);
          // Su `pubblica` il backend risponde 400 PLACEHOLDER_NON_VALIDO con
          // tutte le violazioni: perderle lascerebbe l'utente col solo
          // messaggio generico.
          this.violazioniStato.set((e.dettagli ?? []).flatMap((d) => d['violazione'] ?? []));
        },
      });
  }

  /**
   * Salvataggio automatico all'uscita dal blocco.
   *
   * Non e' un autosave a timer: il PUT sostituisce l'intero insieme di
   * sezioni, quindi salvare a meta' di una frase manderebbe al backend un
   * documento che l'utente non ha ancora finito di scrivere. L'uscita dal
   * blocco e' il primo momento in cui il testo e' una versione completa.
   */
  protected autosalva(): void {
    if (!this.documentoModificato() || !this.sezioni()?.modificabile) return;
    this.salvaSezioni();
  }

  protected salvaSezioni(): void {
    const versione = this.corrente();
    if (!versione || !this.sezioni()?.modificabile || this.salvandoSezioni()) return;
    this.salvandoSezioni.set(true);
    this.erroreSezioni.set(null);
    this.violazioniSezioni.set([]);
    // Da qui in poi "modificato" significa "modificato dopo l'invio": e' il
    // segnale che la risposta del PUT e' piu' vecchia di quello che l'utente
    // ha in mano, e quindi non deve sovrascriverlo.
    this.documentoModificato.set(false);
    const sezioni = this.riordina(this.sezioniLocali());
    this.api
      .put<SezioniResponse>(`/api/v1/builder/modelli/${this.id}/versioni/${versione.id}/sezioni`, {
        sezioni,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.salvandoSezioni.set(false);
          this.applicaSezioni(response, this.documentoModificato());
        },
        error: (e: ApiError) => {
          this.salvandoSezioni.set(false);
          this.documentoModificato.set(true);
          this.erroreSezioni.set(e.messaggio);
          this.violazioniSezioni.set((e.dettagli ?? []).flatMap((d) => d['violazione'] ?? []));
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

  protected etichettaStile(stile: string): string {
    if (stile === 'H1') return 'titolo';
    if (stile === 'H2') return 'sottotitolo';
    return 'paragrafo';
  }

  protected tokenDocumento(indizi: string[], fallback: string): string {
    const campo = this.corrente()?.campi.find((item) => {
      const testo = `${item.codice} ${item.etichetta}`.toLocaleLowerCase();
      return indizi.some((indizio) => testo.includes(indizio));
    });
    return `{{${campo?.codice ?? fallback}}}`;
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

  private inserisciTestoNelEditor(
    codiceSezione: string,
    testo: string,
    editor?: HTMLElement,
  ): void {
    const target = editor ?? this.editorAttivo;
    if (
      target &&
      target.getAttribute('data-section-text') === codiceSezione &&
      this.editorHaSelezione(target)
    ) {
      target.focus();
      const selection = this.document.getSelection();
      const range = selection?.getRangeAt(0);
      if (selection && range) {
        range.deleteContents();
        range.insertNode(this.document.createTextNode(testo));
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
        this.aggiornaTesto(codiceSezione, this.testoEditor(target));
        return;
      }
    }

    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) => {
        if (sezione.codice !== codiceSezione) return sezione;
        const corrente = this.testoSezione(sezione);
        return this.sezioneConTesto(sezione, `${corrente}${corrente ? ' ' : ''}${testo}`);
      }),
    );
    this.sincronizzaEditorAttivo(codiceSezione);
  }

  private editorHaSelezione(editor: HTMLElement): boolean {
    const selection = this.document.getSelection();
    if (!selection || selection.rangeCount === 0) return false;
    const range = selection.getRangeAt(0);
    const contenitore = range.commonAncestorContainer;
    return contenitore === editor || editor.contains(contenitore);
  }

  private testoEditor(editor: HTMLElement): string {
    return editor.textContent ?? '';
  }

  private sincronizzaEditorAttivo(codiceSezione: string): void {
    if (this.editorAttivo?.getAttribute('data-section-text') !== codiceSezione) return;
    const sezione = this.sezioniLocali().find((item) => item.codice === codiceSezione);
    if (sezione && this.editorAttivo.textContent !== this.testoSezione(sezione)) {
      this.editorAttivo.textContent = this.testoSezione(sezione);
    }
  }

  private codiceSezioneLibero(base: string): string {
    const usati = new Set(this.sezioniLocali().map((sezione) => sezione.codice));
    if (!usati.has(base)) return base;
    let progressivo = 2;
    while (usati.has(`${base}-${progressivo}`)) progressivo += 1;
    return `${base}-${progressivo}`;
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

  private caricaSezioni(): void {
    const versione = this.corrente();
    if (!versione) return;
    this.erroreSezioni.set(null);
    this.api
      .get<SezioniResponse>(`/api/v1/builder/modelli/${this.id}/versioni/${versione.id}/sezioni`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => this.applicaSezioni(response),
        error: (e: ApiError) => this.erroreSezioni.set(e.messaggio),
      });
  }

  private applicaSezioni(response: SezioniResponse, mantieniLocali = false): void {
    this.sezioni.set(response);
    if (mantieniLocali) return;
    const locali = this.riordina(response.sezioni.map((sezione) => this.clonaSezione(sezione)));
    this.sezioniLocali.set(locali);
    this.sezioneAttiva.set(locali[0]?.codice ?? null);
    this.documentoModificato.set(false);
  }

  private clonaSezione(sezione: SezioneDocumento): SezioneDocumento {
    return {
      codice: sezione.codice,
      ordine: sezione.ordine,
      contenuto: sezione.contenuto.map((blocco) => ({
        ...blocco,
        placeholder_usati: [...blocco.placeholder_usati],
      })),
    };
  }

  private riordina(sezioni: SezioneDocumento[]): SezioneDocumento[] {
    return sezioni.map((sezione, ordine) => ({ ...this.clonaSezione(sezione), ordine }));
  }

  private sezioneConTesto(sezione: SezioneDocumento, testo: string): SezioneDocumento {
    const blocco = sezione.contenuto[0] ?? this.nuovoBlocco(sezione.codice, '');
    return {
      ...sezione,
      contenuto: [
        {
          ...blocco,
          contenuto: testo,
          placeholder_usati: this.placeholderNelTesto(testo),
        },
        ...sezione.contenuto.slice(1),
      ],
    };
  }

  private nuovoBlocco(codiceSezione: string, contenuto: string): BloccoDocumento {
    return {
      id: `${codiceSezione}-paragrafo`,
      tipo: 'PARAGRAFO',
      contenuto,
      posizionamento: 'BODY',
      ordine: 0,
      stile: null,
      placeholder_usati: this.placeholderNelTesto(contenuto),
      regole_layout: {},
      asset_ref: null,
      colonne: [],
    };
  }

  private placeholderNelTesto(testo: string): string[] {
    const trovati: string[] = [];
    for (const match of testo.matchAll(/{{\s*([A-Za-z0-9_.-]+)\s*}}/g)) {
      const nome = match[1];
      if (!trovati.includes(nome)) trovati.push(nome);
    }
    return trovati;
  }
}
