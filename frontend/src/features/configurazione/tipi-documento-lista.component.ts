import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, forkJoin, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../shared/api-error';
import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';
import { PolicyDimensioniService } from './policy-dimensioni.service';

interface TipoLive {
  codice: string;
  integrazione: IntegrazioneAdmin;
}

interface ErroreSorgente {
  integrazione: IntegrazioneAdmin;
  messaggio: string;
}

@Component({
  selector: 'app-tipi-documento-lista',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './tipi-documento-lista.component.html',
})
export class TipiDocumentoListaComponent {
  private readonly integrations = inject(IntegrazioniAdminService);
  private readonly policyService = inject(PolicyDimensioniService);
  private readonly filtroIntegrazione =
    inject(ActivatedRoute).snapshot.queryParamMap.get('integrazioneId');

  protected readonly tipi = signal<TipoLive[]>([]);
  protected readonly erroriSorgente = signal<ErroreSorgente[]>([]);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);

  constructor() {
    this.carica();
  }

  protected carica(): void {
    this.caricamento.set(true);
    this.errore.set(null);
    this.integrations
      .lista()
      .pipe(
        switchMap((integrazioni) => {
          const connesse = integrazioni.filter(
            (item) =>
              item.stato === 'CONNESSO' &&
              (!this.filtroIntegrazione || item.id === this.filtroIntegrazione),
          );
          if (!connesse.length) return of([]);
          return forkJoin(
            connesse.map((integrazione) =>
              this.policyService.tipiDocumento(integrazione.id).pipe(
                map((codici) => ({ integrazione, codici, errore: null as string | null })),
                catchError((error: ApiError) =>
                  of({ integrazione, codici: [] as string[], errore: error.messaggio }),
                ),
              ),
            ),
          );
        }),
      )
      .subscribe({
        next: (risultati) => {
          this.tipi.set(
            risultati.flatMap(({ integrazione, codici }) =>
              codici.map((codice) => ({ codice, integrazione })),
            ),
          );
          this.erroriSorgente.set(
            risultati
              .filter((item) => item.errore)
              .map((item) => ({ integrazione: item.integrazione, messaggio: item.errore! })),
          );
          this.caricamento.set(false);
        },
        error: (error: ApiError) => {
          this.errore.set(error.messaggio);
          this.caricamento.set(false);
        },
      });
  }
}
