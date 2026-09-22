import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../../shared/api-client';
import type { components as discoveryComponents } from '../../shared/api-types/integrazioni';

export type NodoLive = discoveryComponents['schemas']['NodoCategorizzazione'];
export type PolicyDimensione = discoveryComponents['schemas']['PolicyDimensione'];
export type PolicyDimensioni = discoveryComponents['schemas']['PolicyDimensioni'];
export type PolicyDimensioneRequest = discoveryComponents['schemas']['PolicyDimensioneRequest'];

export interface StrutturaLive {
  codice_tipo_documento: string;
  validita: string;
  nodi: NodoLive[];
}

@Injectable({ providedIn: 'root' })
export class PolicyDimensioniService {
  private readonly api = inject(ApiClient);

  tipiDocumento(integrazioneId: string): Observable<string[]> {
    return this.api.get<string[]>(
      `/api/v1/configurazione/integrazioni/${integrazioneId}/tipi-documento`,
    );
  }

  struttura(integrazioneId: string, codice: string): Observable<StrutturaLive> {
    return this.api.get<StrutturaLive>(
      `/api/v1/configurazione/integrazioni/${integrazioneId}/tipi-documento/${encodeURIComponent(codice)}/struttura`,
    );
  }

  policy(integrazioneId: string, codice: string): Observable<PolicyDimensioni> {
    return this.api.get<PolicyDimensioni>(
      `/api/v1/configurazione/integrazioni/${integrazioneId}/tipi-documento/${encodeURIComponent(codice)}/policy-dimensioni`,
    );
  }

  salvaPolicy(
    integrazioneId: string,
    codice: string,
    request: PolicyDimensioneRequest,
  ): Observable<PolicyDimensione> {
    return this.api.put<PolicyDimensione>(
      `/api/v1/configurazione/integrazioni/${integrazioneId}/tipi-documento/${encodeURIComponent(codice)}/policy-dimensioni`,
      request,
    );
  }
}
