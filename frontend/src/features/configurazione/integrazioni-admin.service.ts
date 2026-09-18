import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../../shared/api-client';
import type { components } from '../../shared/api-types/integrazioni';

export type IntegrazioneAdmin = components['schemas']['IntegrazioneAdmin'];
export type IntegrazioneCreate = components['schemas']['IntegrazioneCreate'];
export type IntegrazioneUpdate = components['schemas']['IntegrazioneUpdate'];

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

  verifica(id: string, revisioneAttesa: number): Observable<IntegrazioneAdmin> {
    return this.api.post<IntegrazioneAdmin>(`${BASE}/${id}/verifica`, {
      revisione_attesa: revisioneAttesa,
    });
  }
}
