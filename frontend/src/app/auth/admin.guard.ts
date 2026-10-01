import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { createAuthGuard, type AuthGuardData } from 'keycloak-angular';
import { firstValueFrom } from 'rxjs';

import { ProfiloService } from './profilo.service';

/**
 * UI-only route guard (spec.md FR-023): keeps a non-admin from landing on a
 * screen whose every API call would 403 anyway. Decide dal profilo calcolato
 * dal backend (007 T115), cioe' con la stessa regola di `require_admin`, che
 * resta comunque il confine vero.
 */
const isAdmin = async (_route: unknown, _state: unknown, authData: AuthGuardData) => {
  // Le dipendenze si prendono prima di qualunque `await`: dopo, il contesto
  // di iniezione non c'e' piu'.
  const router = inject(Router);
  const profili = inject(ProfiloService);
  if (!authData.authenticated) return router.parseUrl('/');
  const profilo = await firstValueFrom(profili.carica()).catch(() => null);
  return profilo?.permessi.includes('GEMODO_ADMIN') ? true : router.parseUrl('/');
};

export const adminGuard = createAuthGuard(isAdmin);
