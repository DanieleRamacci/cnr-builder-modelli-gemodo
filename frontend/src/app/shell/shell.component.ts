import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import {
  ItFooterComponent,
  ItHeaderComponent,
  ItNavBarComponent,
  ItNavBarItemComponent,
} from 'design-angular-kit';

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
export class ShellComponent {}
