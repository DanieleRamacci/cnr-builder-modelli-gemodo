import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import type { ApiError } from '../../shared/api-error';
import { DISCOVERY_EXAMPLE_JSON } from './discovery-example';
import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';

@Component({
  selector: 'app-integrazione-struttura-json',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './integrazione-struttura-json.component.html',
  styleUrl: './integrazione-struttura-json.component.scss',
})
export class IntegrazioneStrutturaJsonComponent {
  private readonly service = inject(IntegrazioniAdminService);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('id')!;

  protected readonly integrazione = signal<IntegrazioneAdmin | null>(null);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);
  protected readonly copiaCompletata = signal(false);
  protected readonly esempioJson = DISCOVERY_EXAMPLE_JSON;
  protected readonly nomeFile = computed(() => {
    const codice =
      this.integrazione()
        ?.codice.toLowerCase()
        .replace(/[^a-z0-9_-]+/g, '-') ?? 'discovery';
    return `${codice}-discovery.example.json`;
  });

  constructor() {
    this.service.ottieni(this.id).subscribe({
      next: (integrazione) => {
        this.integrazione.set(integrazione);
        this.caricamento.set(false);
      },
      error: (error: ApiError) => {
        this.errore.set(error.messaggio);
        this.caricamento.set(false);
      },
    });
  }

  protected copia(): void {
    if (!navigator.clipboard) return;
    void navigator.clipboard.writeText(this.esempioJson).then(() => {
      this.copiaCompletata.set(true);
      setTimeout(() => this.copiaCompletata.set(false), 2000);
    });
  }

  protected scarica(): void {
    const url = URL.createObjectURL(new Blob([this.esempioJson], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = this.nomeFile();
    link.click();
    URL.revokeObjectURL(url);
  }
}
