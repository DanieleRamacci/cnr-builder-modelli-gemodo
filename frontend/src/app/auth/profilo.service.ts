import { Injectable, inject, signal } from '@angular/core';
import { Observable, catchError, shareReplay, tap, throwError } from 'rxjs';

import { ApiClient } from '../../shared/api-client';

export type PermessoProfilo = { codice: string; descrizione: string };
export type ContestoProfilo = { codice: string; ruoli: string[]; permessi: PermessoProfilo[] };
export type Profilo = {
  soggetto: string;
  client_id: string;
  permessi_diretti: PermessoProfilo[];
  contesti: ContestoProfilo[];
  permessi: string[];
};

/**
 * Cosa l'utente puo' fare, chiesto al backend (007 FR-034, T115).
 *
 * Prima l'interfaccia lo ricostruiva dal token con regole proprie
 * (`ROLE_MANAGER#<contesto>` = gestore): per un contesto non mappato mostrava
 * funzioni che il backend poi rifiutava, e non avrebbe seguito un cambio della
 * mappatura. Ora la fonte e' una sola, la stessa che autorizza le chiamate.
 * Resta una comodita' dell'interfaccia: chi decide e' sempre il backend.
 */
@Injectable({ providedIn: 'root' })
export class ProfiloService {
  private readonly api = inject(ApiClient);
  private richiesta?: Observable<Profilo>;

  /** Il profilo, una volta caricato; `null` prima (e se la chiamata fallisce). */
  readonly profilo = signal<Profilo | null>(null);

  carica(): Observable<Profilo> {
    this.richiesta ??= this.api.get<Profilo>('/api/v1/builder/profilo').pipe(
      tap((profilo) => this.profilo.set(profilo)),
      // Un errore non resta in memoria: la prossima richiesta riprova.
      catchError((errore) => {
        this.richiesta = undefined;
        return throwError(() => errore);
      }),
      shareReplay(1),
    );
    return this.richiesta;
  }

  ha(permesso: string): boolean {
    return this.profilo()?.permessi.includes(permesso) ?? false;
  }
}
