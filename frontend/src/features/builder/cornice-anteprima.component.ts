import { Component, computed, input } from '@angular/core';
import type { SafeUrl } from '@angular/platform-browser';

import { righeIntestazione, type CornicePagina } from './cornice.model';

/**
 * Intestazione o pie' di pagina come li disegna il PDF (012 T070, FR-008):
 * logo al centro e righe centrate sotto; testo a sinistra e numero a destra.
 * Solo presentazione; lo usano il foglio dell'editor e la pagina che imposta
 * la cornice, per vedere il risultato mentre si scrive.
 */
@Component({
  selector: 'app-cornice-anteprima',
  standalone: true,
  styles: `
    :host {
      display: block;
    }
    .testata {
      display: grid;
      justify-items: center;
      gap: 2px;
      padding-bottom: 10px;
      border-bottom: 1px solid #a0a0a0;
      text-align: center;
      font-size: 12px;
    }
    .logo {
      height: 44px;
      max-width: 60%;
      object-fit: contain;
      margin-bottom: 4px;
    }
    .logo-mancante {
      display: grid;
      place-items: center;
      height: 44px;
      width: 88px;
      margin-bottom: 4px;
      border: 1px dashed #a0a8b0;
      color: #6b7884;
      font-size: 10px;
    }
    .piede {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding-top: 8px;
      color: #333;
      font-size: 10.5px;
    }
    .b {
      font-weight: 700;
    }
    .i {
      font-style: italic;
    }
  `,
  template: `
    @if (parte() === 'intestazione') {
      @if (cornice()?.intestazione; as testa) {
        <div class="testata" data-cornice-testata>
          @if (testa.con_logo) {
            @if (logoUrl(); as url) {
              <img class="logo" [src]="url" alt="Logo dell'intestazione" />
            } @else {
              <span class="logo-mancante">logo da caricare</span>
            }
          }
          @for (riga of righe(); track $index) {
            <span [class.b]="riga.grassetto" [class.i]="riga.corsivo">{{ riga.testo }}</span>
          }
        </div>
      }
    } @else {
      @if (cornice()?.pie_pagina; as piede) {
        <div class="piede" data-cornice-piede>
          <span>{{ testoPiede() }}</span>
          @if (piede.numerazione_pagine) {
            <span>Pagina {{ pagina() }} di {{ pagine() ?? 'N' }}</span>
          }
        </div>
      }
    }
  `,
})
export class CorniceAnteprimaComponent {
  readonly cornice = input<CornicePagina | null>(null);
  readonly parte = input<'intestazione' | 'piede'>('intestazione');
  readonly logoUrl = input<SafeUrl | string | null>(null);
  /** Il numero che il pie' di pagina scrive, e il totale se e' noto. */
  readonly pagina = input(1);
  readonly pagine = input<number | null>(null);

  protected readonly righe = computed(() =>
    righeIntestazione(this.cornice()?.intestazione?.testo ?? []),
  );
  protected readonly testoPiede = computed(() =>
    (this.cornice()?.pie_pagina?.testo ?? []).map((f) => f.testo).join(''),
  );
}
