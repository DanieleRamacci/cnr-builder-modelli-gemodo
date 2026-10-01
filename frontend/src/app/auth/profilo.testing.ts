import { signal } from '@angular/core';
import { of } from 'rxjs';

import type { Profilo, ProfiloService } from './profilo.service';

/** Un profilo gia' caricato con questi permessi: per i test dei componenti che lo leggono. */
export function profiloFinto(
  permessi: string[],
  contesti: Profilo['contesti'] = [],
): ProfiloService {
  const profilo: Profilo = {
    soggetto: 'utente-test',
    client_id: 'gemodo-frontend',
    permessi_diretti: [],
    contesti,
    permessi,
  };
  return {
    profilo: signal<Profilo | null>(profilo),
    carica: () => of(profilo),
    ha: (permesso: string) => permessi.includes(permesso),
  } as unknown as ProfiloService;
}
