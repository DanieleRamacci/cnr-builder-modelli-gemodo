import { DOCUMENT } from '@angular/common';
import {
  Component,
  DestroyRef,
  computed,
  effect,
  ChangeDetectorRef,
  Injector,
  afterNextRender,
  inject,
  signal,
  viewChildren,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DomSanitizer, type SafeResourceUrl, type SafeUrl } from '@angular/platform-browser';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiClient } from '../../shared/api-client';
import { AnteprimaPdfComponent } from './anteprima-pdf.component';
import type { VoceSegnaposto } from './menu-segnaposto.component';
import { CorniceAnteprimaComponent } from './cornice-anteprima.component';
import { NOMI_MASCHERE, urlCornice, type CorniceModello } from './cornice.model';
import {
  EditorSezioneComponent,
  type InizioPaginaSezione,
  type Intervallo,
  type ModificaSezione,
} from './editor-sezione.component';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/builder-modelli';
import { Subject, debounceTime, forkJoin, of, switchMap, catchError } from 'rxjs';
import {
  normalizzaFrammenti,
  normalizzaIndirizzo,
  placeholderNeiFrammenti,
  testoDiFrammenti,
  type FrammentoTesto,
  type TipoMarcatore,
} from './frammenti';
import {
  ALLINEAMENTO_CSS,
  STILI,
  allineamentoEffettivo,
  collegamentoIn,
  comandoAllineamento,
  comandoCollegamento,
  comandoElenco,
  comandoEnfasi,
  comandoInterruzione,
  comandoLivello,
  comandoStile,
  comandoUnisciRighe,
  numeraElenchi,
  statoSelezione,
  type Allineamento,
  type AttributoEnfasi,
  type BloccoDocumento,
  type StatoSelezione,
} from './documento-editor';

type Dettaglio = components['schemas']['ModelloDettaglio'];
type Impaginazione = components['schemas']['Impaginazione'];
const NESSUN_INIZIO: readonly InizioPaginaSezione[] = [];
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
type PannelloBuilder = 'segnaposto' | 'pagina' | 'proprieta';
type PolicyResponse = {
  policy: { nome_dimensione: string; consente_valore_generico: boolean }[];
};
/** Uno stato del documento a cui annulla e ripeti possono tornare. */
type Istantanea = {
  sezioni: SezioneDocumento[];
  sezione: string | null;
  selezione: Intervallo;
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
  imports: [RouterLink, AnteprimaPdfComponent, EditorSezioneComponent, CorniceAnteprimaComponent],
  host: {
    // Annulla e ripeti anche quando il fuoco e' su un pulsante della toolbar.
    '(document:keydown)': 'tastoDocumento($event)',
  },
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
        <button
          type="button"
          class="btn btn-sm"
          data-preview-open
          [disabled]="!sezioni()?.modificabile || caricandoAnteprima()"
          [title]="
            sezioni()?.modificabile
              ? 'Il PDF della bozza, con valori fac-simile al posto dei segnaposto'
              : 'Anteprima disponibile solo sulle bozze: questa versione genera documenti veri'
          "
          (click)="apriAnteprima(anteprimaPdf.elemento())"
        >
          Anteprima
        </button>
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
          class="tool"
          data-undo
          title="Annulla (Ctrl+Z)"
          aria-label="Annulla"
          [disabled]="!possoAnnullare()"
          (mousedown)="$event.preventDefault()"
          (click)="annulla()"
        >
          ↶
        </button>
        <button
          type="button"
          class="tool"
          data-redo
          title="Ripeti (Ctrl+Maiusc+Z)"
          aria-label="Ripeti"
          [disabled]="!possoRipetere()"
          (mousedown)="$event.preventDefault()"
          (click)="ripeti()"
        >
          ↷
        </button>
        <span class="separator"></span>
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
        <button
          type="button"
          class="tool"
          data-link-open
          title="Collegamento: seleziona il testo, poi scrivi l'indirizzo"
          aria-label="Collegamento"
          [disabled]="!sezioni()?.modificabile"
          (mousedown)="$event.preventDefault()"
          (click)="apriCollegamento()"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
            <path
              d="M6.5 9.5l3-3M7 4.5l1-1a2.5 2.5 0 013.5 3.5l-1 1M9 11.5l-1 1A2.5 2.5 0 014.5 9l1-1"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </button>
        <span class="separator"></span>
        <!-- Un solo comando per cio' che un blocco e', come il menu Stili di
             Word (012 T059): sostituisce H1/H2 e il "Tipo blocco" che stava
             nelle Proprieta' e sembrava valere per tutta la sezione. -->
        <label class="visually-hidden" for="stile-blocco">Stile del blocco</label>
        <select
          id="stile-blocco"
          class="form-select form-select-sm style-select"
          data-style-select
          [value]="stileCorrente()"
          [disabled]="!sezioni()?.modificabile || !editorAttivo() || stileCorrente() === ''"
          (change)="applicaStile($any($event.target).value)"
        >
          @for (stile of stili; track stile.valore) {
            <option [value]="stile.valore">{{ stile.etichetta }}</option>
          }
          @if (stileCorrente() === '') {
            <option value="">Non è testo</option>
          }
        </select>
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
          data-list="ALFABETICO"
          title="Elenco a lettere"
          (mousedown)="$event.preventDefault()"
          (click)="applicaLista('ALFABETICO')"
        >
          a)
        </button>
        <span class="separator"></span>
        @for (allineamento of allineamenti; track allineamento.valore) {
          <button
            type="button"
            class="tool"
            [attr.data-align]="allineamento.valore"
            [title]="allineamento.etichetta"
            [attr.aria-label]="allineamento.etichetta"
            [attr.aria-pressed]="allineamentoAttivo() === allineamento.valore"
            [class.pressed]="allineamentoAttivo() === allineamento.valore"
            [disabled]="!sezioni()?.modificabile"
            (mousedown)="$event.preventDefault()"
            (click)="applicaAllineamento(allineamento.valore)"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              @for (riga of allineamento.righe; track $index) {
                <rect
                  [attr.x]="riga[0]"
                  [attr.y]="2 + $index * 4"
                  [attr.width]="riga[1]"
                  height="1.6"
                />
              }
            </svg>
          </button>
        }
        <span class="separator"></span>
        <button
          type="button"
          class="tool"
          title="In un elenco: sposta la voce al secondo livello"
          (mousedown)="$event.preventDefault()"
          (click)="inserisciTab()"
        >
          Tab
        </button>
        <button
          type="button"
          class="tool"
          data-join-lines
          title="Unisci righe: ricompone in capoversi le righe selezionate di un testo incollato da PDF"
          aria-label="Unisci righe in capoversi"
          [disabled]="!sezioni()?.modificabile || !editorAttivo()"
          (mousedown)="$event.preventDefault()"
          (click)="unisciRighe()"
        >
          ¶
        </button>
        <button
          type="button"
          class="tool"
          data-insert-block="INTERRUZIONE_PAGINA"
          title="Interruzione di pagina: il testo dopo va sulla pagina seguente"
          aria-label="Inserisci interruzione di pagina"
          [disabled]="!sezioni()?.modificabile || !editorAttivo()"
          (mousedown)="$event.preventDefault()"
          (click)="inserisciInterruzione()"
        >
          ⤓
        </button>
        <span class="hint">Scrivi / nel testo per inserire un segnaposto</span>
        @if (collegamento(); as stato) {
          <div class="link-bar" data-link-bar>
            @if (stato.editor) {
              <label for="indirizzo-collegamento">Indirizzo</label>
              <input
                #indirizzo
                id="indirizzo-collegamento"
                class="form-control form-control-sm"
                type="text"
                placeholder="https://..., www.... o un indirizzo email"
                data-link-input
                [value]="stato.valore"
                (keydown.enter)="$event.preventDefault(); confermaCollegamento(indirizzo.value)"
                (keydown.escape)="chiudiCollegamento()"
              />
              <button
                type="button"
                class="btn btn-sm btn-primary"
                data-link-apply
                (click)="confermaCollegamento(indirizzo.value)"
              >
                Applica
              </button>
              @if (stato.valore) {
                <button
                  type="button"
                  class="btn btn-sm btn-outline-danger"
                  data-link-remove
                  (click)="confermaCollegamento(null)"
                >
                  Rimuovi
                </button>
              }
            }
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              (click)="chiudiCollegamento()"
            >
              Annulla
            </button>
            @if (stato.errore) {
              <span class="link-errore" role="alert" data-link-error>{{ stato.errore }}</span>
            }
          </div>
        }
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
          <!-- Un A4 in scala: le misure del foglio sono in millimetri del PDF
               (012 T078), cosi' che le righe vadano a capo dove ci vanno li'. -->
          <div class="scala">
            @if (impaginazione(); as pagine) {
              <p class="conta-pagine" data-pagine>
                {{ pagine.pagine === 1 ? '1 pagina' : pagine.pagine + ' pagine' }} nel PDF
              </p>
            }
            <div class="pagina" id="anteprima-documento" data-document-preview>
              <!-- La cornice vera del tipo documento, come nel PDF (012 T070, FR-008):
                 prima qui c'erano un'intestazione e una firma finte del prototipo. -->
              <div class="document-frame" data-sheet-intestazione>
                @if (cornice()?.cornice?.intestazione) {
                  <app-cornice-anteprima
                    [cornice]="cornice()!.cornice"
                    parte="intestazione"
                    [logoUrl]="logoCornice()"
                  />
                } @else if (linkCornice(); as link) {
                  <a class="frame-add" data-sheet-add-intestazione [routerLink]="link"
                    >+ Aggiungi intestazione</a
                  >
                }
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
                      <h3>{{ sezione.codice }}</h3>
                      <app-editor-sezione
                        [codice]="sezione.codice"
                        [blocchi]="sezione.contenuto"
                        [campi]="vociCampi()"
                        [inizi]="iniziPerSezione().get(sezione.codice) ?? nessunInizio"
                        (modificato)="aggiornaSezione(sezione.codice, $event)"
                        (attivato)="sezioneAttiva.set(sezione.codice)"
                        (uscito)="autosalva($event)"
                        (selezione)="statoEditor.set($event)"
                        (cronologia)="$event === 'annulla' ? annulla() : ripeti()"
                        (dragover)="consentiDrop($event)"
                      />
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
                        @for (
                          elemento of blocco.elementi ?? [];
                          track $index;
                          let indice = $index
                        ) {
                          <div class="editor-item" [class.level-1]="elemento.livello === 1">
                            <span
                              class="item-marker"
                              [class.marker-puntato]="elemento.marcatore === 'PUNTATO'"
                              >{{ marcatoreInBlocco(blocco, indice) }}</span
                            >
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
                      } @else if (blocco.tipo === 'INTERRUZIONE_PAGINA') {
                        <div class="page-break"><span>Interruzione di pagina</span></div>
                      } @else {
                        <div
                          class="editor-text"
                          [class.style-h1]="blocco.stile === 'H1'"
                          [class.style-h2]="blocco.stile === 'H2'"
                          [class.block-titolo]="blocco.tipo === 'TITOLO'"
                          [class.block-firma]="blocco.tipo === 'FIRMA'"
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
              <div class="document-frame" data-sheet-piede>
                @if (cornice()?.cornice?.pie_pagina) {
                  <app-cornice-anteprima [cornice]="cornice()!.cornice" parte="piede" />
                } @else if (linkCornice(); as link) {
                  <a class="frame-add" data-sheet-add-piede [routerLink]="link"
                    >+ Aggiungi piè di pagina</a
                  >
                }
              </div>
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
              data-tab-pagina
              [class.active]="pannelloAttivo() === 'pagina'"
              [attr.aria-selected]="pannelloAttivo() === 'pagina'"
              (click)="pannelloAttivo.set('pagina')"
            >
              Pagina
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
            } @else if (pannelloAttivo() === 'pagina') {
              <h2>Intestazione e piè di pagina</h2>
              @if (cornice(); as c) {
                <p class="panel-hint">
                  Valgono per tutti i modelli di tipo <code>{{ c.codice_tipo_documento }}</code
                  >: si impostano una volta e qui si vedono già pronte.
                </p>
                <div class="property-note" data-pagina-intestazione>
                  <strong>Intestazione</strong><br />
                  @if (c.cornice?.intestazione; as testa) {
                    {{ nomeMaschera(testa.maschera) }}{{ testa.con_logo ? '' : ', senza logo' }}
                    @if (testa.con_logo && !c.logo_presente) {
                      <br /><span class="text-danger">Logo non ancora caricato</span>
                    }
                  } @else {
                    Nessuna
                  }
                </div>
                <div class="property-note" data-pagina-piede>
                  <strong>Piè di pagina</strong><br />
                  @if (c.cornice?.pie_pagina; as piede) {
                    {{ piede.testo.length ? 'Testo' : 'Senza testo'
                    }}{{ piede.numerazione_pagine ? ' e numero di pagina' : '' }}
                  } @else {
                    Nessuno
                  }
                </div>
                @if (linkCornice(); as link) {
                  <div class="d-grid gap-2 mt-3">
                    @if (!c.cornice?.intestazione) {
                      <a
                        class="btn btn-sm btn-outline-primary"
                        data-aggiungi-intestazione
                        [routerLink]="link"
                        >Aggiungi intestazione</a
                      >
                    }
                    @if (!c.cornice?.pie_pagina) {
                      <a
                        class="btn btn-sm btn-outline-primary"
                        data-aggiungi-piede
                        [routerLink]="link"
                        >Aggiungi piè di pagina</a
                      >
                    }
                    @if (c.cornice?.intestazione || c.cornice?.pie_pagina) {
                      <a
                        class="btn btn-sm btn-outline-secondary"
                        data-modifica-cornice
                        [routerLink]="link"
                        >Modifica intestazione e piè di pagina</a
                      >
                    }
                  </div>
                } @else {
                  <p class="panel-hint">
                    Questo tipo documento non appartiene a un'integrazione: la cornice non si può
                    impostare da qui.
                  </p>
                }
              } @else if (erroreCornice(); as messaggio) {
                <p class="vuoto-sezioni">{{ messaggio }}</p>
              } @else {
                <p role="status">Caricamento...</p>
              }
            } @else {
              @if (sezioneCorrente(); as sezione) {
                <h2>Sezione</h2>
                <label for="proprieta-nome">Nome della sezione</label>
                <input
                  id="proprieta-nome"
                  class="form-control"
                  type="text"
                  maxlength="128"
                  data-section-name
                  [value]="sezione.codice"
                  [disabled]="!sezioni()?.modificabile || salvandoSezioni()"
                  (change)="rinominaSezione(sezione.codice, $any($event.target))"
                />
                @if (erroreNome(); as errore) {
                  <p class="nome-errore" role="alert" data-section-name-error>{{ errore }}</p>
                }
                <p class="panel-hint">
                  Il nome compare nella struttura a sinistra (per esempio "Premesse" o "Art. 1"). Lo
                  stile del testo si cambia dalla barra in alto, dove sta il cursore.
                </p>
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

    <app-anteprima-pdf
      #anteprimaPdf
      [caricando]="caricandoAnteprima()"
      [errore]="erroreAnteprima()"
      [violazioni]="violazioniAnteprima()"
      [documento]="documentoAnteprima()"
      [indirizzo]="indirizzoAnteprima()"
      [nome]="nomeAnteprima()"
      (chiusa)="chiudiAnteprima()"
    />

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
  protected readonly allineamenti = ALLINEAMENTI;
  protected readonly stili = STILI;
  /**
   * Annulla e ripeti del documento intero (T072): lo stato delle sezioni
   * prima di ogni modifica, con la selezione di allora. Una sola cronologia
   * per tutte le sezioni, cosi' che anche aggiungere, rinominare o spostare
   * una sezione si annulli; la digitazione si raggruppa, come in Word.
   */
  private readonly passato: Istantanea[] = [];
  private readonly futuro: Istantanea[] = [];
  private ultimaDigitazione = 0;
  protected readonly possoAnnullare = signal(false);
  protected readonly possoRipetere = signal(false);
  /** La cornice che il modello eredita dal suo tipo documento (012 T070). */
  protected readonly cornice = signal<CorniceModello | null>(null);
  protected readonly erroreCornice = signal<string | null>(null);
  protected readonly logoCornice = signal<SafeUrl | null>(null);
  private indirizzoLogoCornice: string | null = null;
  /** Dove si imposta la cornice: la pagina del contesto, per quel tipo documento. */
  protected readonly linkCornice = computed(() => {
    const c = this.cornice();
    return c?.integrazione_id
      ? ['/contesti', c.codice_contesto, 'impostazioni', c.integrazione_id, c.codice_tipo_documento]
      : null;
  });
  /**
   * Il collegamento che si sta inserendo (012 T050). La selezione si ricorda
   * qui: quando il fuoco passa al campo dell'indirizzo, quella dell'editor
   * non e' piu' visibile.
   */
  protected readonly collegamento = signal<{
    editor: EditorSezioneComponent | null;
    da: number;
    a: number;
    valore: string;
    errore: string | null;
  } | null>(null);
  /** I segnaposto che il comando `/` propone: i campi della versione, una volta sola. */
  protected readonly vociCampi = computed<VoceSegnaposto[]>(() =>
    (this.corrente()?.campi ?? [])
      .filter((campo, i, campi) => campi.findIndex((altro) => altro.codice === campo.codice) === i)
      .map(({ codice, etichetta, tipo }) => ({ codice, etichetta, tipo })),
  );
  /** Perche' il nome scritto nelle Proprieta' non e' stato accettato. */
  protected readonly erroreNome = signal<string | null>(null);
  /**
   * Le pagine dell'anteprima del testo sullo schermo (012 T080, T081): quante
   * sono e dove comincia ciascuna, per disegnare i fogli sul testo.
   */
  protected readonly impaginazione = signal<Impaginazione | null>(null);
  private readonly daMisurare = new Subject<SezioneDocumento[]>();
  protected readonly nessunInizio = NESSUN_INIZIO;
  protected readonly iniziPerSezione = computed(() => {
    const perSezione = new Map<string, InizioPaginaSezione[]>();
    for (const inizio of this.impaginazione()?.inizi_pagina ?? []) {
      if (!inizio.sezione) continue;
      perSezione.set(inizio.sezione, [...(perSezione.get(inizio.sezione) ?? []), inizio]);
    }
    return perSezione;
  });
  /** Cosa c'e' dove sta il cursore, come lo mostra la toolbar. */
  protected readonly statoEditor = signal<StatoSelezione | null>(null);
  /** Lo stile del blocco col cursore, come lo mostra il menu Stile. */
  protected readonly stileCorrente = computed(() => this.statoEditor()?.stile ?? 'PARAGRAFO');
  protected readonly allineamentoAttivo = computed(() => this.statoEditor()?.allineamento ?? null);
  protected readonly sezioneCorrente = computed(() => {
    const codice = this.sezioneAttiva();
    return this.sezioniLocali().find((sezione) => sezione.codice === codice) ?? null;
  });

  private readonly editori = viewChildren(EditorSezioneComponent);
  /** L'editor della sezione selezionata: e' quello su cui agisce la toolbar. */
  protected readonly editorAttivo = computed(
    () => this.editori().find((editor) => editor.codice() === this.sezioneAttiva()) ?? null,
  );
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly injector = inject(Injector);
  private readonly sanitizer = inject(DomSanitizer);
  /** Azioni che aspettano la fine del salvataggio in corso (l'anteprima). */
  private readonly dopoSalvataggio: (() => void)[] = [];
  protected readonly caricandoAnteprima = signal(false);
  protected readonly erroreAnteprima = signal<string | null>(null);
  protected readonly violazioniAnteprima = signal<string[]>([]);
  protected readonly indirizzoAnteprima = signal<string | null>(null);
  protected readonly nomeAnteprima = signal('anteprima.pdf');
  protected readonly documentoAnteprima = signal<SafeResourceUrl | null>(null);

  constructor() {
    // I fogli seguono cio' che si scrive (012 T081): a ogni modifica, dopo
    // una breve pausa, il renderer misura le sezioni come sono sullo schermo,
    // anche se non ancora salvate. Una misura vecchia arrivata tardi non
    // sostituisce mai quella nuova.
    this.daMisurare
      .pipe(
        debounceTime(400),
        switchMap((sezioni) => {
          const versione = this.corrente();
          if (!versione) return of(null);
          return this.api
            .post<Impaginazione>(
              `/api/v1/builder/modelli/${this.id}/versioni/${versione.id}/impaginazione`,
              { sezioni },
            )
            .pipe(catchError(() => of(null)));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((impaginazione) => this.impaginazione.set(impaginazione));
    effect(() => {
      const sezioni = this.sezioniLocali();
      if (this.sezioni()?.modificabile) this.daMisurare.next(this.riordina(sezioni));
    });
    this.carica();
    this.destroyRef.onDestroy(() => {
      if (this.indirizzoLogoCornice) URL.revokeObjectURL(this.indirizzoLogoCornice);
    });
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
          this.caricaCornice();
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

  protected placeholderSezione(sezione: SezioneDocumento): string[] {
    return [...new Set(sezione.contenuto.flatMap((blocco) => blocco.placeholder_usati))];
  }

  protected allineamentoCss(blocco: BloccoDocumento): string {
    return ALLINEAMENTO_CSS[allineamentoEffettivo(blocco)];
  }

  /** In sola lettura: il documento composto, con le sezioni dove ripartire. */
  protected marcatoreInBlocco(blocco: BloccoDocumento, indice: number): string {
    return this.marcatoriDocumento().get(blocco)?.[indice] ?? '';
  }

  protected selezionaSezione(codice: string): void {
    this.sezioneAttiva.set(codice);
    const stato = this.editorAttivo()?.stato;
    this.statoEditor.set(stato ? statoSelezione(stato) : null);
  }

  /**
   * Ogni modifica del testo di una sezione arriva qui dal suo editor, con i
   * blocchi gia' ricalcolati (`ordine`, `placeholder_usati`).
   */
  protected aggiornaSezione(codice: string, modifica: ModificaSezione): void {
    this.ricorda(modifica.digitazione, { sezione: codice, selezione: modifica.prima });
    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) =>
        sezione.codice === codice ? { ...sezione, contenuto: modifica.blocchi } : sezione,
      ),
    );
  }

  /**
   * Una sezione nuova con una riga vuota e il cursore dentro. La riga non ha
   * ancora un ruolo: diventa cio' che si sceglie dal menu Stile (012 T060).
   */
  protected aggiungiSezione(): void {
    this.ricorda();
    const codice = this.codiceSezioneLibero(`sezione-${this.sezioniLocali().length + 1}`);
    const blocco = this.nuovoBlocco(`${codice}-paragrafo`, []);
    this.sezioniLocali.update((sezioni) => [
      ...sezioni,
      { codice, ordine: sezioni.length, contenuto: [blocco] },
    ]);
    this.sezioneAttiva.set(codice);
    this.documentoModificato.set(true);
    this.cdr.detectChanges();
    this.editorAttivo()?.scriviInFondo();
  }

  /**
   * Il nome della sezione (012 T062). E' il suo `codice`, che il servizio
   * accetta libero fino a 128 caratteri e unico nella versione: nessun campo
   * nuovo e nessuna migrazione.
   */
  protected rinominaSezione(attuale: string, campo: HTMLInputElement): void {
    const nome = campo.value.trim();
    this.erroreNome.set(null);
    if (nome === attuale) return;
    const errore = !nome
      ? "Il nome della sezione non puo' essere vuoto."
      : this.sezioniLocali().some((sezione) => sezione.codice === nome)
        ? `Esiste gia' una sezione "${nome}".`
        : null;
    if (errore) {
      this.erroreNome.set(errore);
      campo.value = attuale;
      return;
    }
    this.ricorda();
    this.documentoModificato.set(true);
    this.sezioniLocali.update((sezioni) =>
      sezioni.map((sezione) =>
        sezione.codice === attuale ? { ...sezione, codice: nome } : sezione,
      ),
    );
    if (this.sezioneAttiva() === attuale) this.sezioneAttiva.set(nome);
  }

  protected rimuoviSezione(codice: string): void {
    this.ricorda();
    const aggiornate = this.riordina(
      this.sezioniLocali().filter((sezione) => sezione.codice !== codice),
    );
    this.sezioniLocali.set(aggiornate);
    this.documentoModificato.set(true);
    if (this.sezioneAttiva() === codice) {
      this.sezioneAttiva.set(aggiornate[0]?.codice ?? null);
      this.statoEditor.set(null);
    }
  }

  protected spostaSezione(indice: number, direzione: -1 | 1): void {
    this.ricorda();
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

  protected apriCollegamento(): void {
    const editor = this.editorAttivo();
    const intervallo = editor?.intervallo();
    if (!editor?.stato || !intervallo || intervallo.a <= intervallo.da) {
      this.collegamento.set({
        editor: null,
        da: 0,
        a: 0,
        valore: '',
        errore: 'Seleziona prima il testo da collegare.',
      });
      return;
    }
    this.collegamento.set({
      editor,
      ...intervallo,
      valore: collegamentoIn(editor.stato, intervallo.da, intervallo.a) ?? '',
      errore: null,
    });
    afterNextRender(
      () => this.document.querySelector<HTMLInputElement>('[data-link-input]')?.focus(),
      {
        injector: this.injector,
      },
    );
  }

  /** Applica l'indirizzo alla porzione ricordata; `null` toglie il collegamento. */
  protected confermaCollegamento(scritto: string | null): void {
    const stato = this.collegamento();
    if (!stato?.editor) return;
    const indirizzo = scritto === null ? null : normalizzaIndirizzo(scritto);
    if (scritto !== null && indirizzo === null) {
      this.collegamento.set({
        ...stato,
        valore: scritto,
        errore: 'Indirizzo non valido: usa https://..., www.... o un indirizzo email.',
      });
      return;
    }
    this.collegamento.set(null);
    stato.editor.esegui(comandoCollegamento(stato.da, stato.a, indirizzo));
  }

  protected chiudiCollegamento(): void {
    const stato = this.collegamento();
    this.collegamento.set(null);
    if (stato?.editor) stato.editor.seleziona(stato);
  }

  /**
   * Il menu Stile: cambia cio' che sono i blocchi selezionati, tenendone il
   * testo (T059, T076).
   */
  protected applicaStile(valore: string): void {
    const stile = STILI.find((voce) => voce.valore === valore);
    if (stile) this.editorAttivo()?.esegui(comandoStile(stile));
  }

  protected applicaAllineamento(allineamento: Allineamento): void {
    this.editorAttivo()?.esegui(comandoAllineamento(allineamento));
  }

  protected annulla(): void {
    const precedente = this.passato.pop();
    if (!precedente) return;
    this.futuro.push(this.istantanea());
    this.ripristina(precedente);
  }

  protected ripeti(): void {
    const successivo = this.futuro.pop();
    if (!successivo) return;
    this.passato.push(this.istantanea());
    this.ripristina(successivo);
  }

  /** Ctrl/Cmd+Z annulla, Ctrl/Cmd+Maiusc+Z o Ctrl+Y ripete; `true` se il tasto era suo. */
  private tastoCronologia(event: KeyboardEvent): boolean {
    const tasto = event.key.toLowerCase();
    if (tasto !== 'z' && tasto !== 'y') return false;
    if (!this.sezioni()?.modificabile) return false;
    event.preventDefault();
    if (tasto === 'y' || event.shiftKey) this.ripeti();
    else this.annulla();
    return true;
  }

  /** Fuori dagli editor (un pulsante della toolbar), ma non nei campi di testo propri. */
  protected tastoDocumento(event: KeyboardEvent): void {
    if (event.defaultPrevented || !(event.ctrlKey || event.metaKey)) return;
    const bersaglio = event.target as HTMLElement | null;
    if (bersaglio?.closest?.('input, textarea, select, [contenteditable="true"]')) return;
    this.tastoCronologia(event);
  }

  /**
   * Prima di una modifica, lo stato a cui si potra' tornare. La digitazione
   * continua (meno di un secondo fra due battute) resta un passo solo.
   */
  private ricorda(digitazione = false, dove?: { sezione: string; selezione: Intervallo }): void {
    const ora = Date.now();
    if (digitazione && this.ultimaDigitazione && ora - this.ultimaDigitazione < 1000) {
      this.ultimaDigitazione = ora;
      return;
    }
    this.ultimaDigitazione = digitazione ? ora : 0;
    this.passato.push(this.istantanea(dove));
    if (this.passato.length > 200) this.passato.shift();
    this.futuro.length = 0;
    this.aggiornaCronologia();
  }

  private istantanea(dove?: { sezione: string; selezione: Intervallo }): Istantanea {
    return {
      sezioni: structuredClone(this.sezioniLocali()),
      sezione: dove?.sezione ?? this.sezioneAttiva(),
      selezione: dove?.selezione ?? this.editorAttivo()?.intervallo() ?? { da: 0, a: 0 },
    };
  }

  /** Rimette lo stato, e la selezione nella sezione dove si stava scrivendo. */
  private ripristina(stato: Istantanea): void {
    this.ultimaDigitazione = 0;
    this.sezioniLocali.set(structuredClone(stato.sezioni));
    this.documentoModificato.set(true);
    this.aggiornaCronologia();
    if (stato.sezione && stato.sezioni.some((sezione) => sezione.codice === stato.sezione)) {
      this.sezioneAttiva.set(stato.sezione);
    }
    this.cdr.detectChanges();
    for (const editor of this.editori()) editor.sincronizza();
    this.editorAttivo()?.seleziona(stato.selezione);
  }

  private aggiornaCronologia(): void {
    this.possoAnnullare.set(this.passato.length > 0);
    this.possoRipetere.set(this.futuro.length > 0);
  }

  /** Le righe selezionate di un testo incollato da PDF, ricomposte in capoversi. */
  protected unisciRighe(): void {
    this.editorAttivo()?.esegui(comandoUnisciRighe);
  }

  /** Un'interruzione di pagina al cursore (FR-012, T060). */
  protected inserisciInterruzione(): void {
    this.editorAttivo()?.esegui(comandoInterruzione);
  }

  /** Grassetto, corsivo, sottolineato sulla selezione, anche su piu' capoversi (FR-006). */
  protected applicaEnfasiSelezione(attributo: AttributoEnfasi): void {
    this.editorAttivo()?.esegui(comandoEnfasi(attributo));
  }

  protected inserisciPlaceholderAttivo(campo: CampoVersione): void {
    this.editorAttivo()?.inserisciTesto(`{{${campo.codice}}}`);
  }

  protected iniziaTrascinamento(event: DragEvent, campo: CampoVersione): void {
    event.dataTransfer?.setData('application/x-gemodo-placeholder', campo.codice);
    event.dataTransfer?.setData('text/plain', `{{${campo.codice}}}`);
  }

  protected consentiDrop(event: DragEvent): void {
    if (!this.sezioni()?.modificabile || this.salvandoSezioni()) return;
    event.preventDefault();
  }

  protected applicaLista(marcatore: TipoMarcatore): void {
    this.editorAttivo()?.esegui(comandoElenco(marcatore));
  }

  protected inserisciTab(): void {
    this.editorAttivo()?.esegui(comandoLivello(null));
  }

  /**
   * Il PDF della bozza (012 US4). L'anteprima legge le sezioni **salvate**:
   * se ci sono modifiche, o un salvataggio automatico e' in corso (il clic sul
   * pulsante toglie il fuoco all'editor e lo fa partire), la si chiede dopo,
   * altrimenti mostrerebbe il testo di prima.
   */
  protected apriAnteprima(finestra: HTMLDialogElement): void {
    const versione = this.corrente();
    if (!versione || !this.sezioni()?.modificabile) return;
    this.liberaAnteprima();
    this.erroreAnteprima.set(null);
    this.violazioniAnteprima.set([]);
    this.caricandoAnteprima.set(true);
    if (!finestra.open) finestra.showModal();
    const richiedi = () => this.richiediAnteprima(versione.id);
    if (this.salvandoSezioni()) {
      this.dopoSalvataggio.push(richiedi);
    } else if (this.documentoModificato()) {
      this.dopoSalvataggio.push(richiedi);
      this.salvaSezioni();
    } else {
      richiedi();
    }
  }

  protected chiudiAnteprima(): void {
    this.liberaAnteprima();
    this.caricandoAnteprima.set(false);
  }

  private richiediAnteprima(versioneId: string): void {
    this.api
      .postBlob(`/api/v1/builder/modelli/${this.id}/versioni/${versioneId}/anteprima`, {})
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (pdf) => {
          this.caricandoAnteprima.set(false);
          const indirizzo = URL.createObjectURL(pdf);
          this.indirizzoAnteprima.set(indirizzo);
          this.nomeAnteprima.set(`anteprima-${this.modello()?.codice ?? 'modello'}.pdf`);
          this.documentoAnteprima.set(this.sanitizer.bypassSecurityTrustResourceUrl(indirizzo));
        },
        error: (e: ApiError) => {
          this.caricandoAnteprima.set(false);
          this.erroreAnteprima.set(e.messaggio);
          this.violazioniAnteprima.set((e.dettagli ?? []).flatMap((d) => d['violazione'] ?? []));
        },
      });
  }

  /** Il PDF resta in memoria finche' l'URL non viene revocato. */
  private liberaAnteprima(): void {
    const indirizzo = this.indirizzoAnteprima();
    if (indirizzo) URL.revokeObjectURL(indirizzo);
    this.indirizzoAnteprima.set(null);
    this.documentoAnteprima.set(null);
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
   * Salvataggio automatico quando il fuoco esce dal testo del documento.
   *
   * Non e' un autosave a timer: il PUT sostituisce l'intero insieme di
   * sezioni, quindi salvare a meta' di una frase manderebbe al backend un
   * documento che l'utente non ha ancora finito di scrivere. Uscire dal
   * testo e' il primo momento in cui e' una versione completa.
   */
  protected autosalva(event?: FocusEvent): void {
    // Passare da una sezione all'altra non e' uscire dal testo: salvare li'
    // manderebbe un PUT a ogni clic e bloccherebbe la toolbar a meta' di una
    // scrittura.
    const verso = event?.relatedTarget;
    if (verso instanceof HTMLElement && verso.closest('[data-section-text]')) return;
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
          for (const azione of this.dopoSalvataggio.splice(0)) azione();
        },
        error: (e: ApiError) => {
          this.salvandoSezioni.set(false);
          this.documentoModificato.set(true);
          this.erroreSezioni.set(e.messaggio);
          this.violazioniSezioni.set((e.dettagli ?? []).flatMap((d) => d['violazione'] ?? []));
          // Cio' che aspettava il salvataggio non ha piu' senso: l'anteprima
          // mostrerebbe un documento diverso da quello sullo schermo.
          if (this.dopoSalvataggio.splice(0).length) {
            this.caricandoAnteprima.set(false);
            this.erroreAnteprima.set(`Il documento non e' stato salvato: ${e.messaggio}`);
          }
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

  private caricaCornice(): void {
    this.api
      .get<CorniceModello>(`/api/v1/builder/modelli/${this.id}/cornice`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (cornice) => {
          this.cornice.set(cornice);
          if (cornice.logo_presente && cornice.integrazione_id) {
            this.api
              .getBlob(`${urlCornice(cornice.integrazione_id, cornice.codice_tipo_documento)}/logo`)
              .pipe(takeUntilDestroyed(this.destroyRef))
              .subscribe({
                next: (immagine) => {
                  this.indirizzoLogoCornice = URL.createObjectURL(immagine);
                  this.logoCornice.set(
                    this.sanitizer.bypassSecurityTrustUrl(this.indirizzoLogoCornice),
                  );
                },
                // Senza logo l'anteprima mostra il segnaposto: non e' un errore da bloccare.
                error: () => undefined,
              });
          }
        },
        error: (e: ApiError) => this.erroreCornice.set(e.messaggio),
      });
  }

  protected nomeMaschera(maschera: string): string {
    return NOMI_MASCHERE[maschera] ?? maschera;
  }

  private caricaSezioni(): void {
    const versione = this.corrente();
    if (!versione) return;
    this.erroreSezioni.set(null);
    this.api
      .get<SezioniResponse>(`/api/v1/builder/modelli/${this.id}/versioni/${versione.id}/sezioni`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.applicaSezioni(response);
          this.passato.length = 0;
          this.futuro.length = 0;
          this.aggiornaCronologia();
        },
        error: (e: ApiError) => this.erroreSezioni.set(e.messaggio),
      });
  }

  private applicaSezioni(response: SezioniResponse, mantieniLocali = false): void {
    this.sezioni.set(response);
    if (mantieniLocali) return;
    const locali = this.riordina(response.sezioni.map((sezione) => this.clonaSezione(sezione)));
    this.sezioniLocali.set(locali);
    this.documentoModificato.set(false);
    // Dopo un salvataggio la selezione resta dov'era: tornare alla prima
    // sezione farebbe applicare il comando successivo (un tipo, uno stile) al
    // blocco sbagliato. Si riparte dalla prima solo se quella scelta non c'e' piu'.
    if (!locali.some((sezione) => sezione.codice === this.sezioneAttiva())) {
      this.sezioneAttiva.set(locali[0]?.codice ?? null);
      this.statoEditor.set(null);
    }
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
}

const ALLINEAMENTI: { valore: Allineamento; etichetta: string; righe: [number, number][] }[] = [
  {
    valore: 'SINISTRA',
    etichetta: 'Allinea a sinistra',
    righe: [
      [1, 14],
      [1, 9],
      [1, 12],
    ],
  },
  {
    valore: 'CENTRO',
    etichetta: 'Centra',
    righe: [
      [1, 14],
      [3.5, 9],
      [2, 12],
    ],
  },
  {
    valore: 'DESTRA',
    etichetta: 'Allinea a destra',
    righe: [
      [1, 14],
      [6, 9],
      [3, 12],
    ],
  },
  {
    valore: 'GIUSTIFICATO',
    etichetta: 'Giustifica',
    righe: [
      [1, 14],
      [1, 14],
      [1, 14],
    ],
  },
];
