import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';

/** Un evento del registro, come lo restituisce `GET /api/v1/admin/attivita` (013). */
export type EventoAttivita = {
  quando: string;
  categoria: string;
  azione: string;
  esito: string;
  soggetto: string | null;
  username: string | null;
  client_id: string | null;
  contesto: string | null;
  oggetto_tipo: string | null;
  oggetto_id: string | null;
  oggetto_nome: string | null;
  dettaglio: Record<string, unknown>;
};

type Pagina = { eventi: EventoAttivita[]; altri: boolean };

type Filtri = {
  da: string;
  a: string;
  categoria: string;
  esito: string;
  utente: string;
  testo: string;
};

const PAGINA = 50;

export const CATEGORIE: { valore: string; etichetta: string }[] = [
  { valore: 'GENERAZIONE', etichetta: 'Generazioni' },
  { valore: 'VALIDAZIONE', etichetta: 'Validazioni' },
  { valore: 'ACCESSO', etichetta: 'Accessi negati' },
  { valore: 'MODELLO', etichetta: 'Modelli' },
  { valore: 'CONFIGURAZIONE', etichetta: 'Configurazione' },
  { valore: 'INTEGRAZIONE', etichetta: 'Integrazioni' },
];

const ESITI: Record<string, { etichetta: string; tono: 'ok' | 'avviso' | 'errore' }> = {
  COMPLETATO: { etichetta: 'Generato', tono: 'ok' },
  VALIDO: { etichetta: 'Valido', tono: 'ok' },
  OK: { etichetta: 'Fatto', tono: 'ok' },
  DATI_NON_VALIDI: { etichetta: 'Dati non validi', tono: 'avviso' },
  FALLITO: { etichetta: 'Errore', tono: 'errore' },
  '401': { etichetta: 'Non autenticato', tono: 'errore' },
  '403': { etichetta: 'Non autorizzato', tono: 'errore' },
};

/**
 * Registro attivita' (013 US4): chi ha fatto cosa, in un solo elenco. Solo per
 * gli amministratori - lo garantiscono la guardia della rotta e il backend.
 */
@Component({
  selector: 'app-registro-attivita',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './registro-attivita.component.html',
  styleUrl: './registro-attivita.component.scss',
})
export class RegistroAttivitaComponent {
  private readonly api = inject(ApiClient);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly categorie = CATEGORIE;
  protected readonly esiti = Object.entries(ESITI).map(([valore, esito]) => ({
    valore,
    etichetta: esito.etichetta,
  }));
  protected filtri: Filtri = { da: '', a: '', categoria: '', esito: '', utente: '', testo: '' };
  /** I filtri dell'elenco mostrato: "Carica altri" e l'esportazione usano questi. */
  private applicati: Filtri = { ...this.filtri };

  protected readonly eventi = signal<EventoAttivita[]>([]);
  protected readonly altri = signal(false);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);
  protected readonly aperto = signal<number | null>(null);
  protected readonly esportando = signal(false);

  constructor() {
    this.carica();
  }

  protected applica(): void {
    this.applicati = { ...this.filtri };
    this.carica();
  }

  protected azzera(): void {
    this.filtri = { da: '', a: '', categoria: '', esito: '', utente: '', testo: '' };
    this.applica();
  }

  protected carica(seguito = false): void {
    this.caricamento.set(true);
    this.errore.set(null);
    const salto = seguito ? this.eventi().length : 0;
    this.api
      .get<Pagina>('/api/v1/admin/attivita', { ...this.parametri(), limite: PAGINA, salto })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (pagina) => {
          this.eventi.set(seguito ? [...this.eventi(), ...pagina.eventi] : pagina.eventi);
          this.altri.set(pagina.altri);
          if (!seguito) this.aperto.set(null);
          this.caricamento.set(false);
        },
        error: (e: ApiError) => {
          this.caricamento.set(false);
          this.errore.set(e.messaggio || "Il registro non si e' potuto caricare.");
        },
      });
  }

  protected esporta(): void {
    this.esportando.set(true);
    const query = new URLSearchParams(
      Object.entries(this.parametri()).map(([k, v]) => [k, String(v)]),
    ).toString();
    this.api
      .getBlob(`/api/v1/admin/attivita.csv${query ? '?' + query : ''}`)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (file) => {
          this.esportando.set(false);
          const indirizzo = URL.createObjectURL(file);
          const link = document.createElement('a');
          link.href = indirizzo;
          link.download = 'registro-attivita.csv';
          link.click();
          URL.revokeObjectURL(indirizzo);
        },
        error: (e: ApiError) => {
          this.esportando.set(false);
          this.errore.set(e.messaggio || "L'esportazione non e' riuscita.");
        },
      });
  }

  protected alterna(indice: number): void {
    this.aperto.set(this.aperto() === indice ? null : indice);
  }

  protected quando(evento: EventoAttivita): string {
    return new Date(evento.quando).toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  protected chi(evento: EventoAttivita): string {
    return evento.username || evento.soggetto || 'sconosciuto';
  }

  protected categoria(evento: EventoAttivita): string {
    return CATEGORIE.find((c) => c.valore === evento.categoria)?.etichetta ?? evento.categoria;
  }

  /** `MODELLO_CREATO` -> "Modello creato": l'azione si legge, non si decifra. */
  protected azione(evento: EventoAttivita): string {
    const testo = evento.azione.replaceAll('_', ' ').toLowerCase();
    return testo.charAt(0).toUpperCase() + testo.slice(1);
  }

  protected oggetto(evento: EventoAttivita): string {
    return evento.oggetto_nome || evento.oggetto_id || '';
  }

  protected esito(evento: EventoAttivita): { etichetta: string; tono: string } {
    return ESITI[evento.esito] ?? { etichetta: evento.esito, tono: 'neutro' };
  }

  protected dettaglio(evento: EventoAttivita): string {
    return JSON.stringify(evento.dettaglio, null, 2);
  }

  private parametri(): Record<string, string> {
    return Object.fromEntries(
      Object.entries(this.applicati).filter(([, valore]) => valore.trim() !== ''),
    );
  }
}
