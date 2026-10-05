import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import type { ApiError } from '../../shared/api-error';
import {
  IntegrazioniAdminService,
  type AccessiIntegrazione,
  type IntegrazioneAdmin,
  type PermessoRuolo,
} from './integrazioni-admin.service';

/** Una riga della griglia: il ruolo ACE e i permessi che concede. */
interface RigaRuolo {
  ruolo: string;
  permessi: PermessoRuolo[];
}

/**
 * Il profilo di accesso dell'integrazione (001 T091): quali ruoli ACE del suo
 * contesto concedono quali permessi GEMODO. Si modifica sullo schermo e si
 * salva per intero; il backend lo applica dalla richiesta successiva.
 */
@Component({
  selector: 'app-integrazione-accessi',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './integrazione-accessi.component.html',
})
export class IntegrazioneAccessiComponent {
  private readonly service = inject(IntegrazioniAdminService);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('id')!;

  protected readonly integrazione = signal<IntegrazioneAdmin | null>(null);
  protected readonly salvati = signal<AccessiIntegrazione | null>(null);
  protected readonly ruoli = signal<RigaRuolo[]>([]);
  protected readonly client = signal<string[]>([]);
  protected readonly altre = signal<IntegrazioneAdmin[]>([]);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);
  protected readonly salvando = signal(false);
  protected readonly erroreSalvataggio = signal<ApiError | null>(null);
  protected readonly salvato = signal(false);

  protected readonly permessi = computed(() => this.salvati()?.permessi_disponibili ?? []);
  protected readonly modificato = computed(() => {
    const salvati = this.salvati();
    if (!salvati) return false;
    return (
      JSON.stringify(this.normalizza(this.ruoli(), this.client())) !==
      JSON.stringify(this.normalizza(salvati.ruoli, salvati.client))
    );
  });
  /** Un ruolo vuoto, ripetuto o senza permessi: il backend lo rifiuterebbe. */
  protected readonly problemi = computed(() => {
    const nomi = this.ruoli().map((r) => r.ruolo.trim());
    const problemi: string[] = [];
    if (nomi.some((n) => !n)) problemi.push('Ogni riga deve avere il nome del ruolo.');
    if (nomi.some((n) => /[\s#]/.test(n)))
      problemi.push('Il ruolo si scrive senza spazi e senza "#contesto".');
    if (new Set(nomi).size !== nomi.length) problemi.push('Un ruolo compare due volte.');
    if (this.ruoli().some((r) => r.permessi.length === 0))
      problemi.push('Ogni ruolo deve concedere almeno un permesso.');
    return problemi;
  });

  constructor() {
    this.service.ottieni(this.id).subscribe({
      next: (integrazione) => this.integrazione.set(integrazione),
      error: (error: ApiError) => this.errore.set(error.messaggio),
    });
    this.service.accessi(this.id).subscribe({
      next: (accessi) => {
        this.applica(accessi);
        this.caricamento.set(false);
      },
      error: (error: ApiError) => {
        this.errore.set(error.messaggio);
        this.caricamento.set(false);
      },
    });
    this.service.lista().subscribe({
      next: (tutte) => this.altre.set(tutte.filter((i) => i.id !== this.id)),
      error: () => this.altre.set([]),
    });
  }

  protected concede(riga: RigaRuolo, permesso: PermessoRuolo): boolean {
    return riga.permessi.includes(permesso);
  }

  protected rinomina(indice: number, valore: string): void {
    this.ruoli.update((righe) => righe.map((r, i) => (i === indice ? { ...r, ruolo: valore } : r)));
    this.salvato.set(false);
  }

  protected commuta(indice: number, permesso: PermessoRuolo): void {
    this.ruoli.update((righe) =>
      righe.map((r, i) =>
        i !== indice
          ? r
          : {
              ...r,
              permessi: r.permessi.includes(permesso)
                ? r.permessi.filter((p) => p !== permesso)
                : [...r.permessi, permesso],
            },
      ),
    );
    this.salvato.set(false);
  }

  protected aggiungiRuolo(): void {
    this.ruoli.update((righe) => [...righe, { ruolo: '', permessi: [] }]);
    this.salvato.set(false);
  }

  protected togliRuolo(indice: number): void {
    this.ruoli.update((righe) => righe.filter((_, i) => i !== indice));
    this.salvato.set(false);
  }

  protected aggiungiClient(campo: HTMLInputElement): void {
    const valore = campo.value.trim();
    if (!valore || this.client().includes(valore)) return;
    this.client.update((elenco) => [...elenco, valore]);
    campo.value = '';
    this.salvato.set(false);
  }

  protected togliClient(clientId: string): void {
    this.client.update((elenco) => elenco.filter((c) => c !== clientId));
    this.salvato.set(false);
  }

  /** Riempie la griglia col profilo di un'altra integrazione; si salva a parte. */
  protected copiaDa(integrazioneId: string): void {
    if (!integrazioneId) return;
    this.service.accessi(integrazioneId).subscribe({
      next: (accessi) => {
        this.ruoli.set(accessi.ruoli.map((r) => ({ ruolo: r.ruolo, permessi: [...r.permessi] })));
        this.client.set([...accessi.client]);
        this.salvato.set(false);
      },
      error: (error: ApiError) => this.erroreSalvataggio.set(error),
    });
  }

  protected annulla(): void {
    const salvati = this.salvati();
    if (salvati) this.applica(salvati);
  }

  protected salva(): void {
    if (this.salvando() || this.problemi().length) return;
    this.salvando.set(true);
    this.erroreSalvataggio.set(null);
    const { ruoli, client } = this.normalizza(this.ruoli(), this.client());
    this.service.impostaAccessi(this.id, { ruoli, client }).subscribe({
      next: (accessi) => {
        this.salvando.set(false);
        this.applica(accessi);
        this.salvato.set(true);
      },
      error: (error: ApiError) => {
        this.salvando.set(false);
        this.erroreSalvataggio.set(error);
      },
    });
  }

  private applica(accessi: AccessiIntegrazione): void {
    this.salvati.set(accessi);
    this.ruoli.set(accessi.ruoli.map((r) => ({ ruolo: r.ruolo, permessi: [...r.permessi] })));
    this.client.set([...accessi.client]);
  }

  /** Lo stesso profilo scritto sempre allo stesso modo, per confrontarlo e per inviarlo. */
  private normalizza(ruoli: readonly RigaRuolo[], client: readonly string[]) {
    return {
      ruoli: [...ruoli]
        .map((r) => ({ ruolo: r.ruolo.trim(), permessi: [...r.permessi].sort() }))
        .sort((a, b) => a.ruolo.localeCompare(b.ruolo)),
      client: [...client].sort(),
    };
  }
}
