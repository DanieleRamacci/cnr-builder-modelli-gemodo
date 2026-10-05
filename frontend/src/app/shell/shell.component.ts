import { Component, computed, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import Keycloak from 'keycloak-js';

import { ProfiloService } from '../auth/profilo.service';
import { RUNTIME_CONFIG } from '../runtime-config';

/**
 * Application shell (007 tasks.md T010): layout + navigation only. No feature
 * logic lives here - configurazione/builder route to their own feature areas.
 */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent {
  private readonly router = inject(Router);
  private readonly keycloak = inject(Keycloak);
  protected readonly userName =
    this.keycloak.tokenParsed?.['name'] ||
    this.keycloak.tokenParsed?.['preferred_username'] ||
    'Utente';
  protected readonly userInitials = this.initials(this.userName);
  private readonly profili = inject(ProfiloService);
  // Il menu segue il profilo calcolato dal backend (007 T115): mostra cio' che
  // le rotte autorizzeranno davvero, non una regola ricostruita dal token.
  protected readonly isManager = computed(() => this.profili.ha('GEMODO_MODELLI_GESTORE'));
  // Undefined until the separately-deployed docs (deploy/coolify-test/) have a
  // real URL - see GEMODO_EXTERNAL_DOCS_URL in scripts/genera-runtime-config.sh.
  protected readonly externalDocsUrl = inject(RUNTIME_CONFIG).externalDocsUrl;

  // UI-only (spec.md FR-023): hides the link, never the real authorization -
  // adminGuard + the backend's require_admin are what actually protect the route.
  protected readonly isAdmin = computed(() => this.profili.ha('GEMODO_ADMIN'));

  constructor() {
    // Senza profilo il menu resta vuoto: e' il caso sicuro, non un errore da mostrare qui.
    this.profili.carica().subscribe({ error: () => undefined });
  }

  /** Impostazioni, ma non il registro attivita' che ha la sua voce (013). */
  protected inImpostazioni(): boolean {
    return /^\/configurazione(?!\/attivita)/.test(this.router.url);
  }

  protected isEditorFullscreen(): boolean {
    return /^\/modelli\/[^/]+\/builder(?:[?#].*)?$/.test(this.router.url);
  }

  private initials(name: string): string {
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('');
  }
}
