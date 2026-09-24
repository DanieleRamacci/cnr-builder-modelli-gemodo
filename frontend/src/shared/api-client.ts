import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import type { ApiError } from './api-error';

/**
 * Thin wrapper over HttpClient (research.md: types generated from the OpenAPI
 * contracts, not a full SDK client) - maps the backend's {codice, messaggio}
 * error envelope to ApiError. No automatic retry: an optimistic-lock conflict
 * (e.g. REVISIONE_SUPERATA) is a case the calling component must handle
 * explicitly (reload + inform the user), never silently retried here.
 */
@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);

  get<T>(path: string, params?: Record<string, string | number | boolean>): Observable<T> {
    return this.http
      .get<T>(path, { params: params ? new HttpParams({ fromObject: params }) : undefined })
      .pipe(catchError(mapError));
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(path, body).pipe(catchError(mapError));
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(path, body).pipe(catchError(mapError));
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(path).pipe(catchError(mapError));
  }
}

function mapError(error: HttpErrorResponse): Observable<never> {
  const body = error.error as {
    codice?: string;
    messaggio?: string;
    dettagli?: Record<string, string>[];
  } | null;
  const apiError: ApiError = {
    codice: body?.codice ?? 'ERRORE_SCONOSCIUTO',
    messaggio: body?.messaggio ?? 'Errore di comunicazione con il servizio',
    status: error.status,
    ...(body?.dettagli ? { dettagli: body.dettagli } : {}),
  };
  return throwError(() => apiError);
}
