import { Component, ElementRef, input, output, viewChild } from '@angular/core';
import type { SafeResourceUrl } from '@angular/platform-browser';

/**
 * Finestra dell'anteprima PDF della bozza (012 US4, T040).
 *
 * Solo presentazione: chiedere l'anteprima, salvare prima se serve e liberare
 * la memoria del PDF restano all'editor, che sa quando il documento e'
 * salvato. Separata dall'editor anche per una ragione concreta: il suo stile
 * aveva portato quello dell'editor oltre il limite di dimensione della build
 * di produzione (deploy fallito del 2026-10-01).
 */
@Component({
  selector: 'app-anteprima-pdf',
  standalone: true,
  styleUrl: './anteprima-pdf.component.scss',
  template: `
    <dialog
      #finestra
      class="preview-dialog"
      aria-labelledby="anteprima-titolo"
      data-preview-dialog
      (close)="chiusa.emit()"
    >
      <header class="preview-header">
        <div>
          <h2 id="anteprima-titolo" class="h5 mb-1">Anteprima della bozza</h2>
          <p class="mb-0">
            Lo stesso PDF che verra' generato, con «etichetta del campo» al posto dei segnaposto.
            Non e' un documento: non viene registrato.
          </p>
        </div>
        <div class="d-flex gap-2">
          @if (indirizzo(); as href) {
            <a class="btn btn-sm btn-outline-primary" [href]="href" [download]="nome()">Scarica</a>
          }
          <button type="button" class="btn btn-sm btn-outline-secondary" (click)="finestra.close()">
            Chiudi
          </button>
        </div>
      </header>
      @if (caricando()) {
        <p role="status" class="preview-state">Preparazione dell'anteprima...</p>
      }
      @if (errore(); as messaggio) {
        <div class="alert alert-danger m-3" role="alert" data-preview-error>
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
      @if (documento(); as pdf) {
        <iframe
          class="preview-frame"
          title="Anteprima PDF della bozza"
          data-preview-frame
          [src]="pdf"
        ></iframe>
      }
    </dialog>
  `,
})
export class AnteprimaPdfComponent {
  readonly caricando = input(false);
  readonly errore = input<string | null>(null);
  readonly violazioni = input<string[]>([]);
  readonly documento = input<SafeResourceUrl | null>(null);
  readonly indirizzo = input<string | null>(null);
  readonly nome = input('anteprima.pdf');
  readonly chiusa = output<void>();

  private readonly finestra = viewChild.required<ElementRef<HTMLDialogElement>>('finestra');

  /** L'elemento `<dialog>`, che l'editor apre quando chiede l'anteprima. */
  elemento(): HTMLDialogElement {
    return this.finestra().nativeElement;
  }
}
