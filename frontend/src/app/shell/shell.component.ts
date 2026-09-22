import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import Keycloak from 'keycloak-js';

import { hasClientRole, hasManagerAccess } from '../auth/roles';
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
  private readonly keycloak = inject(Keycloak);
  protected readonly userName =
    this.keycloak.tokenParsed?.['name'] ||
    this.keycloak.tokenParsed?.['preferred_username'] ||
    'Utente';
  protected readonly userInitials = this.initials(this.userName);
  protected readonly isManager = hasManagerAccess(this.keycloak);
  // Undefined until the separately-deployed docs (deploy/coolify-test/) have a
  // real URL - see GEMODO_EXTERNAL_DOCS_URL in scripts/genera-runtime-config.sh.
  protected readonly externalDocsUrl = inject(RUNTIME_CONFIG).externalDocsUrl;

  // UI-only (spec.md FR-023): hides the link, never the real authorization -
  // adminGuard + the backend's require_admin are what actually protect the route.
  protected readonly isAdmin = hasClientRole(inject(Keycloak), 'gemodo-backend', 'GEMODO_ADMIN');

  private initials(name: string): string {
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('');
  }
}
