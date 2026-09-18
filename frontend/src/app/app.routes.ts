import { Routes } from '@angular/router';

import { adminGuard } from './auth/admin.guard';

export const routes: Routes = [
  {
    path: 'configurazione',
    canActivate: [adminGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('../features/configurazione/integrazioni-lista.component').then(
            (m) => m.IntegrazioniListaComponent,
          ),
      },
      {
        path: 'nuova',
        loadComponent: () =>
          import('../features/configurazione/integrazione-crea.component').then(
            (m) => m.IntegrazioneCreaComponent,
          ),
      },
      {
        path: ':id',
        loadComponent: () =>
          import('../features/configurazione/integrazione-configura.component').then(
            (m) => m.IntegrazioneConfiguraComponent,
          ),
      },
    ],
  },
];
