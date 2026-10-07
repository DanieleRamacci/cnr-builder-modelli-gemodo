import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, map, of, switchMap } from 'rxjs';

import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';

type IntegrazioneVisibile = { id: string; codice: string; nome: string; codice_contesto: string };
type TipoDelContesto = { integrazione: IntegrazioneVisibile; codice: string };

/**
 * Contesti -> <contesto> -> Impostazioni modelli (012 T069).
 *
 * Cio' che vale per tutti i modelli di un tipo documento, impostato da chi li
 * gestisce nel contesto: oggi intestazione e pie' di pagina. I tipi documento
 * sono quelli che le integrazioni del contesto dichiarano davvero.
 */
@Component({
  selector: 'app-impostazioni-modelli',
  standalone: true,
  imports: [RouterLink],
  styles: `
    :host {
      display: block;
      max-width: 860px;
    }
    .nota {
      color: #5a6772;
      font-size: 14px;
    }
    td,
    th {
      vertical-align: middle;
    }
  `,
  template: `
    <header class="mm-testata mb-2">
      <h1>Impostazioni modelli</h1>
      <nav class="mm-breadcrumb" aria-label="Percorso">
        <a routerLink="/contesti">Contesti</a> /
        <a [routerLink]="['/contesti', contesto, 'modelli']">{{ contesto }}</a> /
        <strong>Impostazioni modelli</strong>
      </nav>
    </header>
    <p class="nota">
      Ciò che vale per tutti i modelli di un tipo documento nel contesto <code>{{ contesto }}</code
      >.
    </p>

    @if (caricamento()) {
      <p role="status">Caricamento...</p>
    } @else if (errore(); as messaggio) {
      <div class="alert alert-danger" role="alert">{{ messaggio }}</div>
    } @else if (!tipi().length) {
      <p class="nota" data-nessun-tipo>
        Nessun tipo documento: il contesto non ha integrazioni connesse che ne dichiarino.
      </p>
    } @else {
      <table class="table">
        <thead>
          <tr>
            <th scope="col">Tipo documento</th>
            <th scope="col">Integrazione</th>
            <th scope="col"></th>
          </tr>
        </thead>
        <tbody>
          @for (tipo of tipi(); track tipo.integrazione.id + tipo.codice) {
            <tr [attr.data-tipo]="tipo.codice">
              <td>
                <code>{{ tipo.codice }}</code>
              </td>
              <td>{{ tipo.integrazione.nome }}</td>
              <td class="text-end">
                <a
                  class="btn btn-sm btn-outline-primary"
                  data-imposta-cornice
                  [routerLink]="[
                    '/contesti',
                    contesto,
                    'impostazioni',
                    tipo.integrazione.id,
                    tipo.codice,
                  ]"
                  >Intestazione e piè di pagina</a
                >
              </td>
            </tr>
          }
        </tbody>
      </table>
    }
  `,
})
export class ImpostazioniModelliComponent {
  private readonly api = inject(ApiClient);
  protected readonly contesto = inject(ActivatedRoute).snapshot.paramMap.get('ctxId') ?? '';
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);
  protected readonly tipi = signal<TipoDelContesto[]>([]);

  constructor() {
    this.api
      .get<IntegrazioneVisibile[]>('/api/v1/builder/integrazioni')
      .pipe(
        map((integrazioni) => integrazioni.filter((i) => i.codice_contesto === this.contesto)),
        switchMap((integrazioni) =>
          integrazioni.length
            ? forkJoin(
                integrazioni.map((integrazione) =>
                  this.api
                    .get<string[]>(`/api/v1/builder/integrazioni/${integrazione.id}/tipi-documento`)
                    .pipe(map((codici) => codici.map((codice) => ({ integrazione, codice })))),
                ),
              )
            : of([]),
        ),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe({
        next: (gruppi) => {
          this.tipi.set(gruppi.flat());
          this.caricamento.set(false);
        },
        error: (e: ApiError) => {
          this.errore.set(e.messaggio);
          this.caricamento.set(false);
        },
      });
  }
}
