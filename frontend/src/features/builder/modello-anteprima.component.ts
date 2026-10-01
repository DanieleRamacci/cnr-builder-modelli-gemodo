import { DOCUMENT } from '@angular/common';
import {
  Component,
  DestroyRef,
  ElementRef,
  computed,
  Injector,
  afterNextRender,
  effect,
  inject,
  signal,
  viewChildren,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/builder-modelli';
import { forkJoin } from 'rxjs';
import {
  applicaEnfasi,
  convertiAppunti,
  dividiPerRighe,
  leggiFrammentiDalDom,
  normalizzaFrammenti,
  offsetNelTesto,
  placeholderNeiFrammenti,
  puntoDaOffset,
  scriviFrammentiNelDom,
  sostituisci,
  taglia,
  testoDiFrammenti,
  unisciRighe,
  type AttributoEnfasi,
  type BloccoIncollato,
  type ElementoElenco,
  type FrammentoTesto,
  type TipoMarcatore,
} from './frammenti';

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
type Allineamento = 'SINISTRA' | 'CENTRO' | 'DESTRA' | 'GIUSTIFICATO';
/**
 * Forma del blocco di `GEMODO_DOCUMENT_V1` dalla 012: il testo e' in
 * `frammenti` (o negli `elementi` di un `ELENCO`), mai in una stringa.
 */
type BloccoDocumento = {
  id: string;
  tipo: string;
  frammenti: FrammentoTesto[];
  allineamento?: Allineamento | null;
  elementi?: ElementoElenco[];
  posizionamento: string;
  ordine: number;
  stile?: string | null;
  placeholder_usati: string[];
  regole_layout?: Record<string, string>;
  asset_ref?: string | null;
  colonne?: string[];
};
/** Dove sta il cursore: un blocco, ed eventualmente una voce del suo elenco. */
type PosizioneEditor = { sezione: string; blocco: string; voce: number | null };
// Allineamento implicito del renderer per un blocco nel corpo (`_ALLINEAMENTO`
// in `renderer.py`): l'editor deve mostrare lo stesso, non un giustificato
// che il PDF poi non produce (FR-008).
const ALLINEAMENTO_CSS: Record<Allineamento, string> = {
  SINISTRA: 'left',
  CENTRO: 'center',
  DESTRA: 'right',
  GIUSTIFICATO: 'justify',
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
        @if (derivazioneNonDisponibile(); as motivo) {
          <span class="derivazione-ko" data-derivazione-ko [title]="motivo">
            Derivazione non disponibile
          </span>
        }
        @if (modello()) {
          <button
            type="button"
            class="btn btn-sm"
            data-create-variant-open
            [disabled]="salvando()"
            (click)="variante.showModal()"
          >
            Crea variante
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
        <!-- mousedown senza default: il clic non deve togliere il fuoco
             all'editor, o la selezione da enfatizzare e' gia' persa. -->
        <button
          type="button"
          class="tool strong"
          data-emphasis="grassetto"
          title="Grassetto (Ctrl+B)"
          [disabled]="!sezioni()?.modificabile"
          (mousedown)="$event.preventDefault()"
          (click)="applicaEnfasiSelezione('grassetto')"
        >
          B
        </button>
        <button
          type="button"
          class="tool italic"
          data-emphasis="corsivo"
          title="Corsivo (Ctrl+I)"
          [disabled]="!sezioni()?.modificabile"
          (mousedown)="$event.preventDefault()"
          (click)="applicaEnfasiSelezione('corsivo')"
        >
          I
        </button>
        <button
          type="button"
          class="tool underline"
          data-emphasis="sottolineato"
          title="Sottolineato (Ctrl+U)"
          [disabled]="!sezioni()?.modificabile"
          (mousedown)="$event.preventDefault()"
          (click)="applicaEnfasiSelezione('sottolineato')"
        >
          U
        </button>
        <span class="separator"></span>
        <button
          type="button"
          class="tool"
          (mousedown)="$event.preventDefault()"
          (click)="applicaStileBlocco('H1')"
        >
          H1
        </button>
        <button
          type="button"
          class="tool"
          (mousedown)="$event.preventDefault()"
          (click)="applicaStileBlocco('H2')"
        >
          H2
        </button>
        <span class="separator"></span>
        <button
          type="button"
          class="tool"
          data-list="NUMERICO"
          (mousedown)="$event.preventDefault()"
          (click)="applicaLista('NUMERICO')"
        >
          1.
        </button>
        <button
          type="button"
          class="tool"
          data-list="PUNTATO"
          (mousedown)="$event.preventDefault()"
          (click)="applicaLista('PUNTATO')"
        >
          •
        </button>
        <button
          type="button"
          class="tool"
          title="In un elenco: sposta la voce al secondo livello"
          (mousedown)="$event.preventDefault()"
          (click)="inserisciTab()"
        >
          Tab
        </button>
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
                  >
                    <span class="section-tag">{{ etichettaStile(stileSezione(sezione)) }}</span>
                    <h3>{{ sezione.codice }}</h3>
                    @for (blocco of sezione.contenuto; track blocco.id) {
                      @if (blocco.tipo === 'ELENCO') {
                        <div
                          class="editor-list"
                          [attr.data-block-id]="blocco.id"
                          [class.block-active]="bloccoAttivo(sezione.codice, blocco.id)"
                        >
                          @for (
                            elemento of blocco.elementi ?? [];
                            track $index;
                            let indice = $index
                          ) {
                            <div class="editor-item" [class.level-1]="elemento.livello === 1">
                              <span class="item-marker" aria-hidden="true">{{
                                marcatoreVoce(sezione, blocco, indice)
                              }}</span>
                              <div
                                #editor
                                class="editor-text"
                                contenteditable="true"
                                role="textbox"
                                tabindex="0"
                                spellcheck="true"
                                [style.text-align]="allineamentoCss(blocco)"
                                [attr.aria-label]="
                                  'Voce ' + (indice + 1) + ' sezione ' + sezione.codice
                                "
                                [attr.data-section-text]="sezione.codice"
                                [attr.data-block-id]="blocco.id"
                                [attr.data-item-index]="indice"
                                (focus)="selezionaEditor(editor)"
                                (blur)="autosalva()"
                                (input)="aggiornaDaEditor(editor)"
                                (keydown)="gestisciTastoEditor($event, editor)"
                                (paste)="incolla($event, editor)"
                                (dragover)="consentiDrop($event)"
                                (drop)="rilasciaSegnaposto($event, editor)"
                              ></div>
                            </div>
                          }
                        </div>
                      } @else {
                        <div
                          #editor
                          class="editor-text"
                          contenteditable="true"
                          role="textbox"
                          tabindex="0"
                          spellcheck="true"
                          [class.style-h1]="blocco.stile === 'H1'"
                          [class.style-h2]="blocco.stile === 'H2'"
                          [class.block-active]="bloccoAttivo(sezione.codice, blocco.id)"
                          [style.text-align]="allineamentoCss(blocco)"
                          [attr.aria-label]="'Testo sezione ' + sezione.codice"
                          [attr.data-section-text]="sezione.codice"
                          [attr.data-block-id]="blocco.id"
                          (focus)="selezionaEditor(editor)"
                          (blur)="autosalva()"
                          (input)="aggiornaDaEditor(editor)"
                          (keydown)="gestisciTastoEditor($event, editor)"
                          (paste)="incolla($event, editor)"
                          (dragover)="consentiDrop($event)"
                          (drop)="rilasciaSegnaposto($event, editor)"
                        ></div>
                      }
                    }
                  </article>
                }
              } @else {
                @if ((sezioni()?.documento?.blocchi?.length ?? 0) === 0) {
                  <p class="vuoto-sezioni">L'anteprima del documento composto comparira' qui.</p>
                }
                @for (blocco of sezioni()?.documento?.blocchi ?? []; track blocco.id) {
                  <article class="section-editor readonly">
                    <span class="section-tag">{{ etichettaStile(blocco.stile ?? '') }}</span>
                    @if (blocco.tipo === 'ELENCO') {
                      @for (elemento of blocco.elementi ?? []; track $index; let indice = $index) {
                        <div class="editor-item" [class.level-1]="elemento.livello === 1">
                          <span class="item-marker">{{ marcatoreInBlocco(blocco, indice) }}</span>
                          <div class="editor-text" [style.text-align]="allineamentoCss(blocco)">
                            @for (frammento of elemento.frammenti; track $index) {
                              <span
                                class="frammento"
                                [class.fr-b]="frammento.grassetto"
                                [class.fr-i]="frammento.corsivo"
                                [class.fr-u]="frammento.sottolineato"
                                >{{ frammento.testo }}</span
                              >
                            }
                          </div>
                        </div>
                      }
                    } @else {
                      <div
                        class="editor-text"
                        [class.style-h1]="blocco.stile === 'H1'"
                        [class.style-h2]="blocco.stile === 'H2'"
                        [style.text-align]="allineamentoCss(blocco)"
                      >
                        @for (frammento of blocco.frammenti; track $index) {
                          <span
                            class="frammento"
                            [class.fr-b]="frammento.grassetto"
                            [class.fr-i]="frammento.corsivo"
                            [class.fr-u]="frammento.sottolineato"
                            >{{ frammento.testo }}</span
                          >
                        } @empty {
                          Blocco senza testo
                        }
                      </div>
                    }
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

    <dialog #variante aria-labelledby="variante-titolo" data-create-variant-dialog>
      <h2 id="variante-titolo" class="h4">Creare una variante?</h2>
      <p>
        Viene creato un modello sulla stessa categorizzazione, con una descrizione che lo distingue
        dalle altre varianti.
      </p>
      <label for="nota-variante">In cosa differisce</label>
      <input
        id="nota-variante"
        class="form-control mb-3"
        type="text"
        maxlength="500"
        data-variant-note
        [value]="notaVariante()"
        (input)="notaVariante.set($any($event.target).value)"
      />
      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" (click)="variante.close()">Annulla</button>
        <button
          class="btn btn-primary"
          data-create-variant-submit
          [disabled]="salvando() || !notaVariante().trim()"
          (click)="creaVariante(variante)"
        >
          Crea variante
        </button>
      </div>
    </dialog>
  `,
})
export class ModelloAnteprimaComponent {
  private readonly api = inject(ApiClient);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
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
  /** Perche' la derivazione non e' proponibile ora, quando la causa e' un errore. */
  protected readonly derivazioneNonDisponibile = signal<string | null>(null);
  protected readonly dimensioneScelta = signal('');
  protected readonly valoreScelto = signal('');
  protected readonly notaVariante = signal('');
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
  /**
   * I marcatori del documento composto. Il servizio lo restituisce come
   * sequenza piatta, e i confini di sezione si ricostruiscono dalle sezioni,
   * come fa la resa (`inizi_sezione` in `builder/repository.py`).
   */
  protected readonly marcatoriDocumento = computed(() => {
    const risposta = this.sezioni();
    if (!risposta) return new Map<BloccoDocumento, string[]>();
    const inizi = new Set<number>();
    let progressivo = 0;
    for (const sezione of [...risposta.sezioni].sort((a, b) => a.ordine - b.ordine)) {
      if (sezione.contenuto.length) inizi.add(progressivo);
      progressivo += sezione.contenuto.length;
    }
    return numeraElenchi(risposta.documento.blocchi, inizi);
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
  private readonly injector = inject(Injector);
  /** Il blocco (e la voce) su cui sta lavorando il gestore. */
  protected readonly posizioneAttiva = signal<PosizioneEditor | null>(null);

  constructor() {
    // Il testo dell'editor NON e' un binding: riscrivere il DOM a ogni battuta
    // riporta il caret a inizio blocco e mescola il testo (screenshot e2e del
    // 2026-09-24). Il DOM si allinea al modello solo quando la modifica arriva
    // da fuori, cioe' quando quell'editor non e' quello su cui si scrive; per
    // l'editor attivo lo fa chi modifica (`riscriviEditor`).
    effect(() => {
      const sezioni = this.sezioniLocali();
      for (const riferimento of this.editors()) {
        const elemento = riferimento.nativeElement;
        if (elemento === this.document.activeElement) continue;
        const posizione = this.posizioneDi(elemento);
        const frammenti = posizione && this.frammentiIn(sezioni, posizione);
        if (!frammenti) continue;
        if (JSON.stringify(leggiFrammentiDalDom(elemento)) !== JSON.stringify(frammenti)) {
          scriviFrammentiNelDom(elemento, frammenti);
        }
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

  /** Tutto il testo della sezione, elenchi compresi: serve a dire se e' vuota. */
  protected testoSezione(sezione: SezioneDocumento): string {
    return sezione.contenuto
      .map((blocco) =>
        [blocco.frammenti, ...(blocco.elementi ?? []).map((elemento) => elemento.frammenti)]
          .map(testoDiFrammenti)
          .join('\n'),
      )
      .join('\n');
  }

  /** Lo stile del blocco su cui si lavora, o del primo blocco della sezione. */
  protected stileSezione(sezione: SezioneDocumento): string {
    return this.bloccoBersaglio(sezione)?.stile ?? '';
  }

  protected placeholderSezione(sezione: SezioneDocumento): string[] {
    return [...new Set(sezione.contenuto.flatMap((blocco) => blocco.placeholder_usati))];
  }

  protected bloccoAttivo(codiceSezione: string, idBlocco: string): boolean {
    const posizione = this.posizioneAttiva();
    return posizione?.sezione === codiceSezione && posizione.blocco === idBlocco;
  }

  protected allineamentoCss(blocco: BloccoDocumento): string {
    return ALLINEAMENTO_CSS[blocco.allineamento ?? 'SINISTRA'];
  }

  /**
   * Il marcatore di una voce, calcolato e mai scritto nel testo (FR-015). I
   * contatori proseguono fra elenchi della stessa sezione e si azzerano a ogni
   * sezione e a ogni `TITOLO` (contracts/formato-documentale.md).
   */
  protected marcatoreVoce(
    sezione: SezioneDocumento,
    blocco: BloccoDocumento,
    indice: number,
  ): string {
    return numeraElenchi(sezione.contenuto).get(blocco)?.[indice] ?? '';
  }

  /** In sola lettura: il documento composto, con le sezioni dove ripartire. */
  protected marcatoreInBlocco(blocco: BloccoDocumento, indice: number): string {
    return this.marcatoriDocumento().get(blocco)?.[indice] ?? '';
  }

  protected selezionaSezione(codice: string): void {
    this.sezioneAttiva.set(codice);
    if (this.posizioneAttiva()?.sezione === codice) return;
    const primo = this.sezioniLocali().find((sezione) => sezione.codice === codice)?.contenuto[0];
    this.posizioneAttiva.set(
      primo
        ? { sezione: codice, blocco: primo.id, voce: primo.tipo === 'ELENCO' ? 0 : null }
        : null,
    );
    this.editorAttivo = null;
  }

  protected selezionaEditor(editor: HTMLElement): void {
    const posizione = this.posizioneDi(editor);
    if (!posizione) return;
    this.editorAttivo = editor;
    this.sezioneAttiva.set(posizione.sezione);
    this.posizioneAttiva.set(posizione);
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
    const blocco = {
      ...this.nuovoBlocco(`${codice}-paragrafo`, contenuto ? [{ testo: contenuto }] : []),
      stile,
    };
    this.sezioniLocali.update((sezioni) => [
      ...sezioni,
      { codice, ordine: sezioni.length, contenuto: [blocco] },
    ]);
    this.sezioneAttiva.set(codice);
    this.posizioneAttiva.set({ sezione: codice, blocco: blocco.id, voce: null });
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
      this.posizioneAttiva.set(null);
      this.sezioneAttiva.set(null);
      if (aggiornate[0]) this.selezionaSezione(aggiornate[0].codice);
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

  /** Ogni battuta: il DOM dell'editor torna frammenti, e i frammenti nel modello. */
  protected aggiornaDaEditor(editor: HTMLElement): void {
    const posizione = this.posizioneDi(editor);
    if (posizione) this.scriviFrammenti(posizione, leggiFrammentiDalDom(editor));
  }

  protected gestisciTastoEditor(event: KeyboardEvent, editor: HTMLElement): void {
    const posizione = this.posizioneDi(editor);
    if (!posizione) return;
    if (event.ctrlKey || event.metaKey) {
      const attributo = SCORCIATOIE_ENFASI[event.key.toLowerCase()];
      if (attributo && !event.altKey) {
        event.preventDefault();
        this.selezionaEditor(editor);
        this.applicaEnfasiSelezione(attributo);
      }
      return;
    }
    if (event.key === 'Tab') {
      event.preventDefault();
      if (posizione.voce !== null) this.cambiaLivelloVoce(posizione, event.shiftKey ? 0 : 1);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (posizione.voce !== null && !event.shiftKey) {
        this.dividiVoce(editor, posizione);
      } else {
        this.inserisciNelEditor(editor, '\n');
      }
      return;
    }
    if (event.key === 'Backspace' && posizione.voce !== null) {
      const selezione = this.selezioneIn(editor);
      if (selezione && selezione.inizio === 0 && selezione.fine === 0) {
        event.preventDefault();
        this.rimuoviVoce(posizione);
      }
    }
  }

  /** Grassetto, corsivo, sottolineato sulla porzione selezionata (FR-006). */
  protected applicaEnfasiSelezione(attributo: AttributoEnfasi): void {
    const editor = this.editorAttivo;
    if (!editor || !this.sezioni()?.modificabile) return;
    const selezione = this.selezioneIn(editor);
    if (!selezione || selezione.fine <= selezione.inizio) return;
    const frammenti = applicaEnfasi(
      leggiFrammentiDalDom(editor),
      selezione.inizio,
      selezione.fine,
      attributo,
    );
    this.riscriviEditor(editor, frammenti, selezione.inizio, selezione.fine);
  }

  /**
   * Incolla da un elaboratore di testi (FR-017). L'HTML degli appunti viene
   * convertito qui e non arriva mai al servizio: l'editor riceve frammenti e
   * blocchi, come se il gestore li avesse scritti.
   */
  protected incolla(event: ClipboardEvent, editor: HTMLElement): void {
    event.preventDefault();
    const posizione = this.posizioneDi(editor);
    const appunti = event.clipboardData;
    if (!posizione || !appunti || !this.sezioni()?.modificabile) return;
    const incollati = convertiAppunti(appunti.getData('text/html'), appunti.getData('text/plain'));
    if (incollati.length === 0) return;
    const frammenti = leggiFrammentiDalDom(editor);
    const fine = testoDiFrammenti(frammenti).length;
    const selezione = this.selezioneIn(editor) ?? { inizio: fine, fine };

    if (incollati.length === 1 && incollati[0].tipo === 'PARAGRAFO') {
      const nuovi = incollati[0].frammenti;
      this.riscriviEditor(
        editor,
        sostituisci(frammenti, selezione.inizio, selezione.fine, nuovi),
        selezione.inizio + testoDiFrammenti(nuovi).length,
      );
      return;
    }

    const prima = taglia(frammenti, 0, selezione.inizio);
    const dopo = taglia(frammenti, selezione.fine);
    if (posizione.voce !== null) {
      this.incollaInElenco(posizione, incollati, prima, dopo);
    } else {
      this.incollaFraBlocchi(posizione, incollati, prima, dopo);
    }
    this.editorAttivo = null;
    editor.blur();
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

  protected rilasciaSegnaposto(event: DragEvent, editor: HTMLElement): void {
    event.preventDefault();
    this.selezionaEditor(editor);
    const posizione = this.posizioneDi(editor);
    if (!posizione) return;
    const codiceCampo = event.dataTransfer?.getData('application/x-gemodo-placeholder');
    if (codiceCampo) {
      const campo = this.corrente()?.campi.find((item) => item.codice === codiceCampo);
      if (campo) {
        this.inserisciTestoNelEditor(posizione.sezione, `{{${campo.codice}}}`, editor);
        return;
      }
    }
    const testo = event.dataTransfer?.getData('text/plain');
    if (testo) this.inserisciTestoNelEditor(posizione.sezione, testo, editor);
  }

  protected applicaStileBlocco(stile: 'H1' | 'H2'): void {
    this.modificaBloccoBersaglio((blocco) => ({
      ...blocco,
      stile: blocco.stile === stile ? null : stile,
    }));
  }

  protected impostaStileSezione(stile: string): void {
    const normalizzato = stile === 'H1' || stile === 'H2' ? stile : null;
    this.modificaBloccoBersaglio((blocco) => ({ ...blocco, stile: normalizzato }));
  }

  /**
   * Il paragrafo diventa un `ELENCO`, una voce per riga; su un elenco cambia
   * il marcatore, e lo stesso marcatore lo riporta a paragrafo. Mai `1.`
   * scritto nel testo: si sommerebbe alla numerazione calcolata (FR-015).
   */
  protected applicaLista(marcatore: TipoMarcatore): void {
    this.modificaBloccoBersaglio((blocco) => {
      if (blocco.tipo !== 'ELENCO') {
        const righe = dividiPerRighe(blocco.frammenti);
        return {
          ...blocco,
          tipo: 'ELENCO',
          stile: null,
          frammenti: [],
          elementi: (righe.length ? righe : [[]]).map((frammenti) => ({
            livello: 0,
            marcatore,
            frammenti,
          })),
        };
      }
      const elementi = blocco.elementi ?? [];
      if (
        elementi.every((elemento) => elemento.livello === 1 || elemento.marcatore === marcatore)
      ) {
        return {
          ...blocco,
          tipo: 'PARAGRAFO',
          frammenti: unisciRighe(elementi.map((elemento) => elemento.frammenti)),
          elementi: [],
        };
      }
      return {
        ...blocco,
        elementi: elementi.map((elemento) => ({
          ...elemento,
          marcatore: elemento.livello === 0 ? marcatore : sottoMarcatore(marcatore),
        })),
      };
    }, true);
  }

  protected inserisciTab(): void {
    const posizione = this.posizioneAttiva();
    if (!posizione || posizione.voce === null) return;
    const voce = this.voceIn(posizione);
    this.cambiaLivelloVoce(posizione, voce?.livello === 1 ? 0 : 1);
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

  protected creaVariante(dialog: HTMLDialogElement): void {
    const nota = this.notaVariante().trim();
    if (this.salvando() || !nota) return;
    dialog.close();
    this.salvando.set(true);
    this.errore.set(null);
    this.api
      .post<{ id: string }>(`/api/v1/builder/modelli/${this.id}/varianti`, { nota })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (modello) => {
          this.salvando.set(false);
          this.notaVariante.set('');
          void this.router.navigate(['/modelli', modello.id, 'builder']);
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
      this.selezioneIn(target)
    ) {
      target.focus();
      this.inserisciNelEditor(target, testo);
      return;
    }

    // Nessun cursore nella sezione: il testo va in coda all'ultimo blocco di testo.
    const sezione = this.sezioniLocali().find((item) => item.codice === codiceSezione);
    if (!sezione) return;
    const blocco = [...sezione.contenuto].reverse().find((item) => item.tipo !== 'ELENCO');
    if (!blocco) {
      this.modificaSezione(codiceSezione, (blocchi) => [
        ...blocchi,
        this.nuovoBlocco(this.idBloccoLibero(sezione), [{ testo }]),
      ]);
      return;
    }
    const corrente = testoDiFrammenti(blocco.frammenti);
    this.scriviFrammenti({ sezione: codiceSezione, blocco: blocco.id, voce: null }, [
      ...blocco.frammenti,
      { testo: `${corrente ? ' ' : ''}${testo}` },
    ]);
  }

  /**
   * Inserisce testo al cursore con l'enfasi di cio' che lo precede: un
   * segnaposto scritto dentro un grassetto e' in grassetto (FR-005).
   */
  private inserisciNelEditor(editor: HTMLElement, testo: string): void {
    const frammenti = leggiFrammentiDalDom(editor);
    const fine = testoDiFrammenti(frammenti).length;
    const selezione = this.selezioneIn(editor) ?? { inizio: fine, fine };
    const enfasi = taglia(
      frammenti,
      Math.max(selezione.inizio - 1, 0),
      Math.max(selezione.inizio, 1),
    )[0];
    const nuovo: FrammentoTesto = { ...(enfasi ?? {}), testo };
    this.riscriviEditor(
      editor,
      sostituisci(frammenti, selezione.inizio, selezione.fine, [nuovo]),
      selezione.inizio + testo.length,
    );
  }

  /** Riscrive l'editor attivo dai frammenti e rimette la selezione dov'era. */
  private riscriviEditor(
    editor: HTMLElement,
    frammenti: FrammentoTesto[],
    inizio: number,
    fine = inizio,
  ): void {
    scriviFrammentiNelDom(editor, frammenti);
    const selezione = this.document.getSelection();
    if (selezione && editor.isConnected) {
      const da = puntoDaOffset(editor, inizio);
      const a = puntoDaOffset(editor, fine);
      const range = this.document.createRange();
      range.setStart(da.nodo, da.offset);
      range.setEnd(a.nodo, a.offset);
      selezione.removeAllRanges();
      selezione.addRange(range);
    }
    const posizione = this.posizioneDi(editor);
    if (posizione) this.scriviFrammenti(posizione, frammenti);
  }

  /** La selezione come posizioni nel testo dell'editor, se sta dentro l'editor. */
  private selezioneIn(editor: HTMLElement): { inizio: number; fine: number } | null {
    const selezione = this.document.getSelection();
    if (!selezione || selezione.rangeCount === 0) return null;
    const range = selezione.getRangeAt(0);
    const contenitore = range.commonAncestorContainer;
    if (contenitore !== editor && !editor.contains(contenitore)) return null;
    return {
      inizio: offsetNelTesto(editor, range.startContainer, range.startOffset),
      fine: offsetNelTesto(editor, range.endContainer, range.endOffset),
    };
  }

  private posizioneDi(editor: HTMLElement): PosizioneEditor | null {
    const sezione = editor.getAttribute('data-section-text');
    const blocco = editor.getAttribute('data-block-id');
    if (!sezione || !blocco) return null;
    const voce = editor.getAttribute('data-item-index');
    return { sezione, blocco, voce: voce === null ? null : Number(voce) };
  }

  private frammentiIn(
    sezioni: SezioneDocumento[],
    posizione: PosizioneEditor,
  ): FrammentoTesto[] | null {
    const blocco = sezioni
      .find((sezione) => sezione.codice === posizione.sezione)
      ?.contenuto.find((item) => item.id === posizione.blocco);
    if (!blocco) return null;
    if (posizione.voce === null) return blocco.frammenti;
    return blocco.elementi?.[posizione.voce]?.frammenti ?? null;
  }

  private voceIn(posizione: PosizioneEditor): ElementoElenco | null {
    if (posizione.voce === null) return null;
    const blocco = this.sezioniLocali()
      .find((sezione) => sezione.codice === posizione.sezione)
      ?.contenuto.find((item) => item.id === posizione.blocco);
    return blocco?.elementi?.[posizione.voce] ?? null;
  }

  private scriviFrammenti(posizione: PosizioneEditor, frammenti: FrammentoTesto[]): void {
    this.modificaSezione(posizione.sezione, (blocchi) =>
      blocchi.map((blocco) => {
        if (blocco.id !== posizione.blocco) return blocco;
        if (posizione.voce === null) return { ...blocco, frammenti };
        return {
          ...blocco,
          elementi: (blocco.elementi ?? []).map((elemento, indice) =>
            indice === posizione.voce ? { ...elemento, frammenti } : elemento,
          ),
        };
      }),
    );
  }

  /**
   * Il solo punto in cui cambiano i blocchi di una sezione: dopo ogni modifica
   * `ordine` e `placeholder_usati` sono ricalcolati, cosi' che non possano
   * divergere dal testo.
   */
  private modificaSezione(
    codice: string,
    trasforma: (blocchi: BloccoDocumento[]) => BloccoDocumento[],
  ): void {
    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) =>
        sezione.codice !== codice
          ? sezione
          : {
              ...sezione,
              contenuto: trasforma(sezione.contenuto).map((blocco, ordine) => ({
                ...blocco,
                ordine,
                placeholder_usati: placeholderNeiFrammenti([
                  ...blocco.frammenti,
                  ...(blocco.elementi ?? []).flatMap((elemento) => elemento.frammenti),
                ]),
              })),
            },
      ),
    );
  }

  /** Il blocco su cui agiscono i comandi della toolbar e del pannello proprieta'. */
  private bloccoBersaglio(sezione: SezioneDocumento): BloccoDocumento | undefined {
    const posizione = this.posizioneAttiva();
    return (
      (posizione?.sezione === sezione.codice
        ? sezione.contenuto.find((blocco) => blocco.id === posizione.blocco)
        : undefined) ?? sezione.contenuto[0]
    );
  }

  private modificaBloccoBersaglio(
    trasforma: (blocco: BloccoDocumento) => BloccoDocumento,
    rimettiCursore = false,
  ): void {
    const sezione = this.sezioneCorrente();
    if (!sezione || !this.sezioni()?.modificabile) return;
    const bersaglio =
      this.bloccoBersaglio(sezione) ?? this.nuovoBlocco(`${sezione.codice}-paragrafo`, []);
    const trasformato = trasforma(bersaglio);
    this.modificaSezione(sezione.codice, (blocchi) =>
      blocchi.length
        ? blocchi.map((blocco) => (blocco.id === bersaglio.id ? trasformato : blocco))
        : [trasformato],
    );
    const voce = trasformato.tipo === 'ELENCO' ? 0 : null;
    this.posizioneAttiva.set({ sezione: sezione.codice, blocco: trasformato.id, voce });
    if (rimettiCursore)
      this.mettiCursore({ sezione: sezione.codice, blocco: trasformato.id, voce }, 0);
  }

  private cambiaLivelloVoce(posizione: PosizioneEditor, livello: 0 | 1): void {
    this.modificaSezione(posizione.sezione, (blocchi) =>
      blocchi.map((blocco) => {
        if (blocco.id !== posizione.blocco) return blocco;
        const elementi = blocco.elementi ?? [];
        const radice = elementi.find((elemento) => elemento.livello === 0)?.marcatore ?? 'NUMERICO';
        return {
          ...blocco,
          elementi: elementi.map((elemento, indice) =>
            indice !== posizione.voce || indice === 0
              ? elemento
              : {
                  ...elemento,
                  livello,
                  marcatore: livello === 1 ? sottoMarcatore(radice) : radice,
                },
          ),
        };
      }),
    );
  }

  /** Invio in una voce: la voce si divide al cursore. Su una voce vuota si esce dall'elenco. */
  private dividiVoce(editor: HTMLElement, posizione: PosizioneEditor): void {
    const frammenti = leggiFrammentiDalDom(editor);
    const voce = this.voceIn(posizione);
    if (!voce || posizione.voce === null) return;
    const indice = posizione.voce;
    if (!testoDiFrammenti(frammenti)) {
      this.esciDallElenco(posizione);
      return;
    }
    const selezione = this.selezioneIn(editor) ?? { inizio: 0, fine: 0 };
    const prima = taglia(frammenti, 0, selezione.inizio);
    const dopo = taglia(frammenti, selezione.fine);
    this.modificaSezione(posizione.sezione, (blocchi) =>
      blocchi.map((blocco) => {
        if (blocco.id !== posizione.blocco) return blocco;
        const elementi = [...(blocco.elementi ?? [])];
        elementi.splice(indice, 1, { ...voce, frammenti: prima }, { ...voce, frammenti: dopo });
        return { ...blocco, elementi };
      }),
    );
    scriviFrammentiNelDom(editor, prima);
    this.mettiCursore({ ...posizione, voce: indice + 1 }, 0);
  }

  /** L'ultima voce vuota diventa un paragrafo dopo l'elenco, come in Word. */
  private esciDallElenco(posizione: PosizioneEditor): void {
    const sezione = this.sezioniLocali().find((item) => item.codice === posizione.sezione);
    if (!sezione) return;
    const nuovo = this.nuovoBlocco(this.idBloccoLibero(sezione), []);
    this.modificaSezione(posizione.sezione, (blocchi) =>
      blocchi.flatMap((blocco) => {
        if (blocco.id !== posizione.blocco) return [blocco];
        const elementi = (blocco.elementi ?? []).filter((_, indice) => indice !== posizione.voce);
        return elementi.length ? [{ ...blocco, elementi }, nuovo] : [nuovo];
      }),
    );
    this.mettiCursore({ sezione: posizione.sezione, blocco: nuovo.id, voce: null }, 0);
  }

  /** Backspace all'inizio di una voce: la voce si unisce alla precedente. */
  private rimuoviVoce(posizione: PosizioneEditor): void {
    const voce = this.voceIn(posizione);
    if (!voce || posizione.voce === null) return;
    const indice = posizione.voce;
    if (indice === 0) {
      // Dalla prima voce si torna a un paragrafo con lo stesso testo.
      this.modificaSezione(posizione.sezione, (blocchi) =>
        blocchi.flatMap((blocco) => {
          if (blocco.id !== posizione.blocco) return [blocco];
          const resto = (blocco.elementi ?? []).slice(1);
          const paragrafo = this.nuovoBlocco(`${blocco.id}-p`, voce.frammenti);
          return resto.length
            ? [paragrafo, { ...blocco, elementi: resto }]
            : [{ ...paragrafo, id: blocco.id }];
        }),
      );
      const rimasto = this.voceIn({ ...posizione, voce: 0 }) !== null;
      this.mettiCursore(
        {
          sezione: posizione.sezione,
          blocco: rimasto ? `${posizione.blocco}-p` : posizione.blocco,
          voce: null,
        },
        0,
      );
      return;
    }
    const precedente = this.voceIn({ ...posizione, voce: indice - 1 })!;
    const lunghezza = testoDiFrammenti(precedente.frammenti).length;
    this.modificaSezione(posizione.sezione, (blocchi) =>
      blocchi.map((blocco) => {
        if (blocco.id !== posizione.blocco) return blocco;
        const elementi = [...(blocco.elementi ?? [])];
        elementi.splice(indice - 1, 2, {
          ...precedente,
          frammenti: [...precedente.frammenti, ...voce.frammenti],
        });
        return { ...blocco, elementi };
      }),
    );
    this.mettiCursore({ ...posizione, voce: indice - 1 }, lunghezza);
  }

  /** Incolla piu' capoversi in un paragrafo: il paragrafo si divide al cursore. */
  private incollaFraBlocchi(
    posizione: PosizioneEditor,
    incollati: BloccoIncollato[],
    prima: FrammentoTesto[],
    dopo: FrammentoTesto[],
  ): void {
    const sezione = this.sezioniLocali().find((item) => item.codice === posizione.sezione);
    if (!sezione) return;
    const usati = new Set(sezione.contenuto.map((blocco) => blocco.id));
    const libero = (): string => {
      const id = this.idBloccoLibero(sezione, usati);
      usati.add(id);
      return id;
    };
    this.modificaSezione(posizione.sezione, (blocchi) =>
      blocchi.flatMap((blocco) => {
        if (blocco.id !== posizione.blocco) return [blocco];
        const nuovi = incollati.map((incollato) =>
          incollato.tipo === 'ELENCO'
            ? { ...this.nuovoBlocco(libero(), []), tipo: 'ELENCO', elementi: incollato.elementi }
            : {
                ...this.nuovoBlocco(libero(), incollato.frammenti),
                allineamento: blocco.allineamento,
              },
        );
        const coda = dopo.length
          ? [{ ...this.nuovoBlocco(libero(), dopo), allineamento: blocco.allineamento }]
          : [];
        return [...(prima.length ? [{ ...blocco, frammenti: prima }] : []), ...nuovi, ...coda];
      }),
    );
  }

  /** Incolla in una voce: i capoversi diventano voci dopo quella corrente. */
  private incollaInElenco(
    posizione: PosizioneEditor,
    incollati: BloccoIncollato[],
    prima: FrammentoTesto[],
    dopo: FrammentoTesto[],
  ): void {
    const voce = this.voceIn(posizione);
    if (!voce || posizione.voce === null) return;
    const indice = posizione.voce;
    const voci = incollati.flatMap((incollato): ElementoElenco[] =>
      incollato.tipo === 'ELENCO'
        ? incollato.elementi
        : [{ livello: voce.livello, marcatore: voce.marcatore, frammenti: incollato.frammenti }],
    );
    this.modificaSezione(posizione.sezione, (blocchi) =>
      blocchi.map((blocco) => {
        if (blocco.id !== posizione.blocco) return blocco;
        const elementi = [...(blocco.elementi ?? [])];
        const sostitute = [
          ...(prima.length ? [{ ...voce, frammenti: prima }] : []),
          ...voci,
          ...(dopo.length ? [{ ...voce, frammenti: dopo }] : []),
        ];
        elementi.splice(indice, 1, ...sostitute);
        return { ...blocco, elementi };
      }),
    );
  }

  /** Dopo il prossimo disegno, il cursore in un editor che forse ancora non esiste. */
  private mettiCursore(posizione: PosizioneEditor, offset: number): void {
    this.posizioneAttiva.set(posizione);
    afterNextRender(
      () => {
        const selettore =
          `[data-section-text="${CSS.escape(posizione.sezione)}"][data-block-id="${CSS.escape(posizione.blocco)}"]` +
          (posizione.voce === null
            ? ':not([data-item-index])'
            : `[data-item-index="${posizione.voce}"]`);
        const editor = this.document.querySelector<HTMLElement>(`.editor-text${selettore}`);
        if (!editor) return;
        editor.focus();
        this.selezionaEditor(editor);
        const punto = puntoDaOffset(editor, offset);
        const range = this.document.createRange();
        range.setStart(punto.nodo, punto.offset);
        range.collapse(true);
        const selezione = this.document.getSelection();
        selezione?.removeAllRanges();
        selezione?.addRange(range);
      },
      { injector: this.injector },
    );
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
          this.derivazioneNonDisponibile.set(null);
          this.scegliDimensione(candidati[0]?.nome ?? '');
        },
        error: (e: ApiError) => {
          // Prima qui il pulsante spariva e basta: se discovery o policy non
          // rispondono, la derivazione sembra non esistere invece di essere
          // temporaneamente indisponibile. Sono due cose diverse e vanno dette.
          this.candidatiDerivazione.set([]);
          this.derivazioneNonDisponibile.set(e.messaggio);
        },
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
        // Il servizio rimanda gli attributi falsi per esteso: qui si tiene la
        // forma compatta, la stessa che produce l'editor, cosi' che il
        // confronto fra DOM e modello non veda differenze che non ci sono.
        frammenti: normalizzaFrammenti(blocco.frammenti ?? []),
        elementi: (blocco.elementi ?? []).map((elemento) => ({
          ...elemento,
          frammenti: normalizzaFrammenti(elemento.frammenti),
        })),
        placeholder_usati: [...blocco.placeholder_usati],
      })),
    };
  }

  private riordina(sezioni: SezioneDocumento[]): SezioneDocumento[] {
    return sezioni.map((sezione, ordine) => ({ ...this.clonaSezione(sezione), ordine }));
  }

  private nuovoBlocco(id: string, frammenti: FrammentoTesto[]): BloccoDocumento {
    return {
      id,
      tipo: 'PARAGRAFO',
      frammenti,
      allineamento: null,
      elementi: [],
      posizionamento: 'BODY',
      ordine: 0,
      stile: null,
      placeholder_usati: placeholderNeiFrammenti(frammenti),
      regole_layout: {},
      asset_ref: null,
      colonne: [],
    };
  }

  private idBloccoLibero(sezione: SezioneDocumento, usati?: Set<string>): string {
    const occupati = usati ?? new Set(sezione.contenuto.map((blocco) => blocco.id));
    let progressivo = occupati.size + 1;
    while (occupati.has(`${sezione.codice}-b${progressivo}`)) progressivo += 1;
    return `${sezione.codice}-b${progressivo}`;
  }
}

const SCORCIATOIE_ENFASI: Record<string, AttributoEnfasi> = {
  b: 'grassetto',
  i: 'corsivo',
  u: 'sottolineato',
};

/** Sotto un elenco numerato si va per lettere (`a)`), sotto uno puntato si resta puntati. */
function sottoMarcatore(radice: TipoMarcatore): TipoMarcatore {
  return radice === 'NUMERICO' ? 'ALFABETICO' : 'PUNTATO';
}

/**
 * I marcatori di ogni voce degli elenchi di una sequenza di blocchi. Il
 * contatore del primo livello prosegue fra elenchi e si azzera a ogni `TITOLO`
 * e a ogni blocco il cui `ordine` apre una sezione (`inizi`); quello del
 * secondo si azzera a ogni voce di primo livello. E' la regola di
 * `marcatori_elenchi` nel renderer: l'editor mostra cio' che il PDF scrive.
 */
function numeraElenchi(
  blocchi: BloccoDocumento[],
  inizi: Set<number> = new Set(),
): Map<BloccoDocumento, string[]> {
  const marcatori = new Map<BloccoDocumento, string[]>();
  let primo = 0;
  let secondo = 0;
  for (const blocco of blocchi) {
    if (blocco.tipo === 'TITOLO' || inizi.has(blocco.ordine)) {
      primo = 0;
      secondo = 0;
    }
    if (blocco.tipo !== 'ELENCO') continue;
    marcatori.set(
      blocco,
      (blocco.elementi ?? []).map((elemento) => {
        if (elemento.livello === 0) {
          secondo = 0;
          primo += 1;
          return formattaMarcatore(elemento.marcatore, primo, 0);
        }
        secondo += 1;
        return formattaMarcatore(elemento.marcatore, secondo, 1);
      }),
    );
  }
  return marcatori;
}

function formattaMarcatore(marcatore: TipoMarcatore, numero: number, livello: 0 | 1): string {
  if (marcatore === 'NUMERICO') return `${numero}.`;
  if (marcatore === 'ALFABETICO') return `${String.fromCharCode(96 + ((numero - 1) % 26) + 1)})`;
  return livello === 0 ? '•' : '–';
}
