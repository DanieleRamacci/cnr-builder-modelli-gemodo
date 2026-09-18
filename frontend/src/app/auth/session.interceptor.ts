import { HttpErrorResponse, type HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import Keycloak from 'keycloak-js';
import { from, mergeMap } from 'rxjs';

export const sessionInterceptor: HttpInterceptorFn = (request, next) => {
  if (!request.url.startsWith('/api/')) return next(request);
  const keycloak = inject(Keycloak);
  const refresh = async () => {
    try {
      await keycloak.updateToken(30);
      if (!keycloak.authenticated || !keycloak.token || keycloak.isTokenExpired(0))
        throw new Error('Session expired');
      return keycloak.token;
    } catch {
      throw new HttpErrorResponse({
        status: 401,
        error: {
          codice: 'SESSIONE_SCADUTA',
          messaggio: 'Sessione scaduta o non disponibile. Accedi nuovamente per continuare.',
        },
      });
    }
  };
  return from(refresh()).pipe(
    mergeMap((token) => next(request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }))),
  );
};
