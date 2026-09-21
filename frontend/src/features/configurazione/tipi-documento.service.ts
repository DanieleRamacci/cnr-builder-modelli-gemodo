import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../../shared/api-client';
import type { components } from '../../shared/api-types/configurazione-cataloghi';

export type TipoDocumentoDashboard = components['schemas']['TipoDocumentoDashboard'];
export type TipoDocumentoCreate = components['schemas']['TipoDocumentoCreate'];
export type StrutturaTipoDocumento = components['schemas']['StrutturaTipoDocumento'];

const BASE = '/api/v1/configurazione/tipi-documento';

/** Typed calls a /api/v1/configurazione/tipi-documento* (spec 010, User Story 1). */
@Injectable({ providedIn: 'root' })
export class TipiDocumentoService {
  private readonly api = inject(ApiClient);

  dashboard(): Observable<TipoDocumentoDashboard[]> {
    return this.api.get<TipoDocumentoDashboard[]>(BASE);
  }

  crea(request: TipoDocumentoCreate): Observable<TipoDocumentoDashboard> {
    return this.api.post<TipoDocumentoDashboard>(BASE, request);
  }

  leggiStruttura(codice: string): Observable<StrutturaTipoDocumento> {
    return this.api.get<StrutturaTipoDocumento>(`${BASE}/${codice}/struttura`);
  }

  aggiornaStruttura(codice: string, struttura: StrutturaTipoDocumento): Observable<TipoDocumentoDashboard> {
    return this.api.put<TipoDocumentoDashboard>(`${BASE}/${codice}/struttura`, struttura);
  }
}
