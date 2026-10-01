import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, from, switchMap, throwError } from 'rxjs';

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

  /** POST che risponde con un file (l'anteprima PDF della 012). */
  postBlob(path: string, body: unknown): Observable<Blob> {
    return this.http
      .post(path, body, { responseType: 'blob' })
      .pipe(catchError(mapBlobError));
  }

  /** GET di un file (il logo della cornice, 012 T069). */
  getBlob(path: string): Observable<Blob> {
    return this.http.get(path, { responseType: 'blob' }).pipe(catchError(mapBlobError));
  }

  /** PUT di un file come corpo della richiesta, con il suo tipo (il logo, 012 T066). */
  putFile(path: string, file: Blob): Observable<void> {
    return this.http
      .put<void>(path, file, { headers: { 'Content-Type': file.type || 'application/octet-stream' } })
      .pipe(catchError(mapError));
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(path, body).pipe(catchError(mapError));
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<T>(path).pipe(catchError(mapError));
  }
}

/**
 * Con `responseType: 'blob'` anche il corpo di un errore arriva come Blob: lo
 * si rilegge come JSON, altrimenti codice e messaggio del servizio andrebbero
 * persi e l'utente vedrebbe solo un errore generico.
 */
function mapBlobError(error: HttpErrorResponse): Observable<never> {
  if (!(error.error instanceof Blob)) return mapError(error);
  return from(error.error.text()).pipe(
    switchMap((testo) => {
      let corpo: unknown = null;
      try {
        corpo = JSON.parse(testo);
      } catch {
        // Non era JSON: resta l'errore generico.
      }
      return mapError(new HttpErrorResponse({ error: corpo, status: error.status }));
    }),
  );
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
