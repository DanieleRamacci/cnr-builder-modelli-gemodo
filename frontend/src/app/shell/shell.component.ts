import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import {
  ItFooterComponent,
  ItHeaderComponent,
  ItNavBarComponent,
  ItNavBarItemComponent,
} from 'design-angular-kit';

import { RUNTIME_CONFIG } from '../runtime-config';

/**
 * Application shell (007 tasks.md T010): layout + navigation only. No feature
 * logic lives here - configurazione/builder route to their own feature areas.
 */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    ItHeaderComponent,
    ItNavBarComponent,
    ItNavBarItemComponent,
    ItFooterComponent,
  ],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent {
  // Undefined until the separately-deployed docs (deploy/coolify-test/) have a
  // real URL - see GEMODO_EXTERNAL_DOCS_URL in scripts/genera-runtime-config.sh.
  protected readonly externalDocsUrl = inject(RUNTIME_CONFIG).externalDocsUrl;
}
