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
    path: 'contesti',
    pathMatch: 'full',
    loadComponent: () =>
      import('../features/builder/contesti-lista.component').then((m) => m.ContestiListaComponent),
  },
  {
    path: 'contesti/:ctxId/modelli',
    loadComponent: () =>
      import('../features/builder/integrazioni-manager.component').then(
        (m) => m.IntegrazioniManagerComponent,
      ),
  },
  { path: 'builder', pathMatch: 'full', redirectTo: 'contesti' },
  {
    path: 'modelli/:modelId/builder',
    loadComponent: () =>
      import('../features/builder/modello-anteprima.component').then(
        (m) => m.ModelloAnteprimaComponent,
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
        path: 'contesti/nuovo',
        loadComponent: () =>
          import('../features/configurazione/integrazione-crea.component').then(
            (m) => m.IntegrazioneCreaComponent,
          ),
      },
      {
        path: 'contesti/:id/integrazione',
        loadComponent: () =>
          import('../features/configurazione/integrazione-configura.component').then(
            (m) => m.IntegrazioneConfiguraComponent,
          ),
      },
      {
        path: 'tipi-documento',
        loadComponent: () =>
          import('../features/configurazione/tipi-documento-lista.component').then(
            (m) => m.TipiDocumentoListaComponent,
          ),
      },
      {
        path: 'tipi-documento/nuovo',
        pathMatch: 'full',
        redirectTo: 'tipi-documento',
      },
      {
        path: 'tipi-documento/:codice/dimensioni',
        loadComponent: () =>
          import('../features/configurazione/dimensioni.component').then(
            (m) => m.DimensioniComponent,
          ),
      },
      {
        path: 'tipi-documento/:codice',
        loadComponent: () =>
          import('../features/configurazione/tipo-documento-struttura.component').then(
            (m) => m.TipoDocumentoStrutturaComponent,
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
