import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/builder-modelli';

type Storico = components['schemas']['StoricoModello'];
type Evento = components['schemas']['EventoStorico'];

/** Gruppi di azioni per il filtro: il codice dell'evento resta nel dettaglio. */
const GRUPPI: Record<string, (azione: string) => boolean> = {
  documento: (a) => a === 'SEZIONI_AGGIORNATE',
  stato: (a) => a.startsWith('VERSIONE_'),
  modello: (a) => a.startsWith('MODELLO_'),
  generazioni: (a) => a.startsWith('DOCUMENTO_') || a.startsWith('GENERAZIONE_'),
};

type Persona = { utente: string; azioni: number; ultima: string; canali: string[] };

/**
 * Storico di un modello per l'amministratore: chi ha fatto cosa, quando, su
 * quale versione e da dove (interfaccia o API). Legge `GET .../storico`, che
 * unisce l'audit del modello e le generazioni dalle sue versioni.
 */
@Component({
  selector: 'app-storico-modello',
  standalone: true,
  imports: [DatePipe, RouterLink],
  styleUrl: './storico-modello.component.scss',
  template: `
    <header class="mm-testata mb-3">
      <h1>Storico del modello</h1>
      <nav class="mm-breadcrumb" aria-label="Percorso">
        <a routerLink="/contesti">Contesti</a> /
        @if (storico(); as s) {
          <a [routerLink]="['/contesti', s.codice_contesto, 'modelli']">{{ s.codice_contesto }}</a>
          / <a [routerLink]="['/modelli', s.modello_id, 'builder']">{{ s.nome }}</a> /
        }
        <strong>Storico</strong>
      </nav>
    </header>

    @if (caricamento()) {
      <p role="status">Caricamento...</p>
    } @else if (errore(); as messaggio) {
      <div class="alert alert-danger" role="alert">{{ messaggio }}</div>
    } @else if (storico(); as s) {
      <p class="modello" data-modello>
        <strong>{{ s.nome }}</strong>
        <span class="stato">{{ s.stato }}</span>
        <code [title]="s.codice">{{ s.codice }}</code>
      </p>

      <section class="persone" aria-labelledby="persone-titolo">
        <h2 id="persone-titolo" class="h6">Chi ci ha lavorato</h2>
        <div class="elenco-persone">
          @for (persona of persone(); track persona.utente) {
            <button
              type="button"
              class="persona"
              data-persona
              [class.attiva]="utente() === persona.utente"
              [attr.aria-pressed]="utente() === persona.utente"
              (click)="utente.set(utente() === persona.utente ? '' : persona.utente)"
            >
              <strong>{{ persona.utente }}</strong>
              <span>{{ persona.azioni }} {{ persona.azioni === 1 ? 'azione' : 'azioni' }}</span>
              <span class="small">ultima {{ persona.ultima | date: 'dd/MM/yyyy HH:mm' }}</span>
              <span class="small">{{ persona.canali.join(' · ') }}</span>
            </button>
          }
        </div>
      </section>

      <div class="filtri">
        <select
          class="form-select"
          aria-label="Filtra per utente"
          [value]="utente()"
          (change)="utente.set($any($event.target).value)"
        >
          <option value="">Tutti gli utenti</option>
          @for (persona of persone(); track persona.utente) {
            <option [value]="persona.utente">{{ persona.utente }}</option>
          }
        </select>
        <select
          class="form-select"
          aria-label="Filtra per tipo di azione"
          [value]="gruppo()"
          (change)="gruppo.set($any($event.target).value)"
        >
          <option value="">Tutte le azioni</option>
          <option value="documento">Modifiche al documento</option>
          <option value="stato">Versioni e stati</option>
          <option value="modello">Creazione ed eliminazione</option>
          <option value="generazioni">Generazioni</option>
        </select>
        <select
          class="form-select"
          aria-label="Filtra per canale"
          [value]="canale()"
          (change)="canale.set($any($event.target).value)"
        >
          <option value="">Interfaccia e API</option>
          <option value="INTERFACCIA">Solo interfaccia</option>
          <option value="API">Solo API</option>
        </select>
        <span class="conteggio">{{ eventi().length }} di {{ s.eventi.length }} eventi</span>
      </div>

      @if (eventi().length) {
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th scope="col">Quando</th>
                <th scope="col">Utente</th>
                <th scope="col">Azione</th>
                <th scope="col">Ver.</th>
                <th scope="col">Canale</th>
              </tr>
            </thead>
            <tbody>
              @for (evento of eventi(); track $index) {
                <tr data-evento [attr.data-azione]="evento.azione">
                  <td class="text-nowrap">{{ evento.quando | date: 'dd/MM/yyyy HH:mm:ss' }}</td>
                  <td>{{ evento.utente }}</td>
                  <td [title]="evento.azione">{{ evento.descrizione }}</td>
                  <td>{{ evento.versione ? 'v' + evento.versione : '-' }}</td>
                  <td>
                    <span
                      class="canale"
                      [attr.data-canale]="evento.canale"
                      [title]="evento.client_id ?? ''"
                      >{{ evento.canale === 'API' ? 'API' : 'Interfaccia' }}</span
                    >
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p>Nessun evento con questi filtri.</p>
      }
    }
  `,
})
export class StoricoModelloComponent {
  private readonly api = inject(ApiClient);
  private readonly id = inject(ActivatedRoute).snapshot.paramMap.get('modelId')!;

  protected readonly storico = signal<Storico | null>(null);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);
  protected readonly utente = signal('');
  protected readonly gruppo = signal('');
  protected readonly canale = signal('');

  protected readonly persone = computed<Persona[]>(() => {
    const perUtente = new Map<string, Persona>();
    // Gli eventi arrivano dal piu' recente: il primo visto e' l'ultima azione.
    for (const evento of this.storico()?.eventi ?? []) {
      const persona = perUtente.get(evento.utente) ?? {
        utente: evento.utente,
        azioni: 0,
        ultima: evento.quando,
        canali: [],
      };
      persona.azioni += 1;
      const canale = evento.canale === 'API' ? 'API' : 'Interfaccia';
      if (!persona.canali.includes(canale)) persona.canali.push(canale);
      perUtente.set(evento.utente, persona);
    }
    return [...perUtente.values()].sort((a, b) => b.azioni - a.azioni);
  });

  protected readonly eventi = computed<Evento[]>(() =>
    (this.storico()?.eventi ?? []).filter(
      (evento) =>
        (!this.utente() || evento.utente === this.utente()) &&
        (!this.canale() || evento.canale === this.canale()) &&
        (!this.gruppo() || GRUPPI[this.gruppo()](evento.azione)),
    ),
  );

  constructor() {
    this.api.get<Storico>(`/api/v1/builder/modelli/${this.id}/storico`).subscribe({
      next: (storico) => {
        this.storico.set(storico);
        this.caricamento.set(false);
      },
      error: (errore: ApiError) => {
        this.errore.set(
          errore.status === 403
            ? "Lo storico del modello e' visibile solo agli amministratori."
            : errore.messaggio || 'Storico non disponibile.',
        );
        this.caricamento.set(false);
      },
    });
  }
}
