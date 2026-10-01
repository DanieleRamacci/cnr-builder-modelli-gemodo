import { Component, input, output } from '@angular/core';

export type VoceSegnaposto = { codice: string; etichetta: string; tipo: string };

/**
 * Il menu dei segnaposto che si apre scrivendo `/` nel testo (012 T064).
 *
 * Solo presentazione: quando aprirlo, come filtrarlo e dove inserire il
 * segnaposto lo decide l'editor, che conosce cursore e testo. Il menu non
 * prende mai il fuoco - `mousedown` senza default - cosi' che il cursore resti
 * nel testo e la tastiera continui a scrivere il filtro.
 */
@Component({
  selector: 'app-menu-segnaposto',
  standalone: true,
  styleUrl: './menu-segnaposto.component.scss',
  template: `
    <div
      class="slash-menu"
      role="listbox"
      aria-label="Segnaposto da inserire"
      data-slash-menu
      [style.left.px]="x()"
      [style.top.px]="y()"
    >
      <div class="slash-head">
        Segnaposto
        @if (filtro()) {
          <span class="slash-filtro">{{ filtro() }}</span>
        }
      </div>
      @for (voce of voci(); track voce.codice; let i = $index) {
        <div
          class="slash-item"
          role="option"
          [attr.aria-selected]="i === indice()"
          [class.active]="i === indice()"
          [attr.data-slash-item]="voce.codice"
          (mousedown)="$event.preventDefault(); scelto.emit(voce.codice)"
        >
          <span class="slash-codice">{{ voce.codice }}</span>
          <span class="slash-etichetta">{{ voce.etichetta }}</span>
        </div>
      } @empty {
        <div class="slash-vuoto">Nessun segnaposto corrisponde. Esc per scrivere una /.</div>
      }
      <div class="slash-aiuto">↑↓ per scegliere · Invio per inserire · Esc per chiudere</div>
    </div>
  `,
})
export class MenuSegnapostoComponent {
  readonly voci = input<VoceSegnaposto[]>([]);
  readonly indice = input(0);
  readonly filtro = input('');
  readonly x = input(0);
  readonly y = input(0);
  readonly scelto = output<string>();
}
