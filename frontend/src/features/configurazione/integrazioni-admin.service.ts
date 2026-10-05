import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../../shared/api-client';
import type { components } from '../../shared/api-types/integrazioni';

export type IntegrazioneAdmin = components['schemas']['IntegrazioneAdmin'];
export type IntegrazioneCreate = components['schemas']['IntegrazioneCreate'];
export type IntegrazioneUpdate = components['schemas']['IntegrazioneUpdate'];
export type AccessiIntegrazione = components['schemas']['AccessiIntegrazione'];
export type AccessiIntegrazioneInput = components['schemas']['AccessiIntegrazioneInput'];
export type PermessoRuolo = components['schemas']['PermessoRuolo'];

const BASE = '/api/v1/configurazione/integrazioni';

/** Typed calls to /api/v1/configurazione/integrazioni* (spec.md User Story 4, FR-021). */
@Injectable({ providedIn: 'root' })
export class IntegrazioniAdminService {
  private readonly api = inject(ApiClient);

  lista(): Observable<IntegrazioneAdmin[]> {
    return this.api.get<IntegrazioneAdmin[]>(BASE);
  }

  ottieni(id: string): Observable<IntegrazioneAdmin> {
    return this.api.get<IntegrazioneAdmin>(`${BASE}/${id}`);
  }

  crea(request: IntegrazioneCreate): Observable<IntegrazioneAdmin> {
    return this.api.post<IntegrazioneAdmin>(BASE, request);
  }

  configura(id: string, request: IntegrazioneUpdate): Observable<IntegrazioneAdmin> {
    return this.api.put<IntegrazioneAdmin>(`${BASE}/${id}`, request);
  }

  /** 001 T090: quali ruoli ACE del contesto concedono quali permessi GEMODO. */
  accessi(id: string): Observable<AccessiIntegrazione> {
    return this.api.get<AccessiIntegrazione>(`${BASE}/${id}/accessi`);
  }

  /** Sostituisce il profilo intero; vale dalla richiesta successiva. */
  impostaAccessi(id: string, accessi: AccessiIntegrazioneInput): Observable<AccessiIntegrazione> {
    return this.api.put<AccessiIntegrazione>(`${BASE}/${id}/accessi`, accessi);
  }

  /** 010 T103: rifiutata (409) se l'integrazione ha modelli o documenti generati. */
  elimina(id: string): Observable<void> {
    return this.api.delete<void>(`${BASE}/${id}`);
  }

  verifica(id: string, revisioneAttesa: number): Observable<IntegrazioneAdmin> {
    return this.api.post<IntegrazioneAdmin>(`${BASE}/${id}/verifica`, {
      revisione_attesa: revisioneAttesa,
    });
  }
}
