import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { createAuthGuard, type AuthGuardData } from 'keycloak-angular';

import { hasClientRole } from './roles';

/**
 * UI-only route guard (spec.md FR-023): keeps a non-admin from landing on a
 * screen whose every API call would 403 anyway. The backend's require_admin
 * remains the real authorization boundary regardless of this guard.
 */
const isAdmin = async (_route: unknown, _state: unknown, authData: AuthGuardData) => {
  if (
    authData.authenticated &&
    hasClientRole(authData.keycloak, 'gemodo-backend', 'GEMODO_ADMIN')
  ) {
    return true;
  }
  return inject(Router).parseUrl('/');
};

export const adminGuard = createAuthGuard(isAdmin);
