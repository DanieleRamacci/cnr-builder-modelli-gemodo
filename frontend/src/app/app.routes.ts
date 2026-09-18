import { Routes } from '@angular/router';

import { adminGuard } from './auth/admin.guard';

export const routes: Routes = [
  {
    path: 'builder/:id',
    loadComponent: () =>
      import('../features/builder/modello-crea.component').then((m) => m.ModelloCreaComponent),
  },
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'profilo',
    loadComponent: () => import('./profile.component').then((m) => m.ProfileComponent),
  },
  {
    path: 'builder',
    loadComponent: () =>
      import('../features/builder/integrazioni-manager.component').then(
        (m) => m.IntegrazioniManagerComponent,
      ),
  },
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
  { path: '**', redirectTo: '' },
];
