import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import type { ApiError } from '../../shared/api-error';
import { IntegrazioniAdminService, type IntegrazioneAdmin } from './integrazioni-admin.service';
import {
  PolicyDimensioniService,
  type NodoLive,
  type PolicyDimensione,
  type PolicyDimensioni,
  type StrutturaLive,
} from './policy-dimensioni.service';

/** Un modello pubblicato che la dimensione non la valorizza (011 FR-010b). */
interface ModelloImpattato {
  modello_id: string;
  codice: string;
  nome: string;
}

interface ConfermaImpatto {
  nome: string;
  messaggio: string;
  modelli: ModelloImpattato[];
}

interface DimensioneFoglia {
  nome: string;
  valori: string[];
  policy: PolicyDimensione | null;
  modelliPubblicati: number;
}

const PROPRIETA_NODO = new Set([
  'codice',
  'descrizione',
  'tipo_livello',
  'figli',
  'campi',
  'livelli_possibili',
  'livello_base',
  'lingue_possibili',
]);

@Component({
  selector: 'app-dimensioni',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './dimensioni.component.html',
  styleUrl: './dimensioni.component.scss',
})
export class DimensioniComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly integrations = inject(IntegrazioniAdminService);
  private readonly service = inject(PolicyDimensioniService);

  protected readonly codice = this.route.snapshot.paramMap.get('codice') ?? '';
  protected readonly integrazioneId = this.route.snapshot.queryParamMap.get('integrazioneId') ?? '';
  protected readonly integrazione = signal<IntegrazioneAdmin | null>(null);
  protected readonly struttura = signal<StrutturaLive | null>(null);
  protected readonly policy = signal<PolicyDimensioni | null>(null);
  protected readonly percorso = signal<NodoLive[]>([]);
  protected readonly caricamento = signal(true);
  protected readonly errore = signal<string | null>(null);
  protected readonly salvando = signal<string | null>(null);
  protected readonly erroreSalvataggio = signal<string | null>(null);
  protected readonly confermaRichiesta = signal<ConfermaImpatto | null>(null);
  protected readonly inModifica = signal<string[]>([]);
  protected readonly scelte = signal<Record<string, boolean | null>>({});
  protected readonly defaultScelti = signal<Record<string, string | null>>({});

  protected readonly foglia = computed(() => {
    const ultimo = this.percorso().at(-1);
    return ultimo?.campi ? ultimo : null;
  });

  protected readonly nodiVisibili = computed(() => {
    const struttura = this.struttura();
    if (!struttura) return [];
    const path = this.percorso();
    if (!path.length) return struttura.nodi;
    const ultimo = path.at(-1)!;
    if (ultimo.figli?.length) return ultimo.figli;
    if (path.length === 1) return struttura.nodi;
    return path.at(-2)?.figli ?? [];
  });

  protected readonly fogliePerDimensione = computed(() => {
    const conteggi = new Map<string, number>();
    const visita = (nodi: NodoLive[]) => {
      for (const nodo of nodi) {
        if (nodo.campi) {
          for (const nome of this.dimensioniDaNodo(nodo).keys()) {
            conteggi.set(nome, (conteggi.get(nome) ?? 0) + 1);
          }
          continue;
        }
        if (nodo.figli?.length) visita(nodo.figli);
      }
    };
    visita(this.struttura()?.nodi ?? []);
    return conteggi;
  });

  protected readonly dimensioni = computed<DimensioneFoglia[]>(() => {
    const foglia = this.foglia();
    if (!foglia) return [];
    const valori = this.dimensioniDaNodo(foglia);
    const configurate = new Map(
      (this.policy()?.policy ?? []).map((item) => [item.nome_dimensione, item]),
    );
    const nonConfigurate = new Map(
      (this.policy()?.dimensioni_non_configurate ?? []).map((item) => [item.nome_dimensione, item]),
    );
    return [...valori.entries()].map(([nome, opzioni]) => ({
      nome,
      valori: opzioni,
      policy: configurate.get(nome) ?? null,
      modelliPubblicati:
        configurate.get(nome)?.modelli_pubblicati_che_la_valorizzano ??
        nonConfigurate.get(nome)?.modelli_pubblicati_che_la_valorizzano ??
        0,
    }));
  });

  protected readonly jsonLive = computed(() => JSON.stringify(this.struttura(), null, 2));
  protected readonly host = computed(() => {
    const url = this.integrazione()?.url;
    if (!url) return '';
    try {
      return new URL(url).host;
    } catch {
      return url;
    }
  });

  constructor() {
    this.carica();
  }

  protected carica(): void {
    if (!this.integrazioneId || !this.codice) {
      this.caricamento.set(false);
      this.errore.set("Manca l'integrazione da cui leggere l'albero.");
      return;
    }
    this.caricamento.set(true);
    this.errore.set(null);
    this.percorso.set([]);
    forkJoin({
      integrazione: this.integrations.ottieni(this.integrazioneId),
      struttura: this.service.struttura(this.integrazioneId, this.codice),
      policy: this.service.policy(this.integrazioneId, this.codice),
    }).subscribe({
      next: ({ integrazione, struttura, policy }) => {
        this.integrazione.set(integrazione);
        this.struttura.set(struttura);
        this.policy.set(policy);
        this.caricamento.set(false);
      },
      error: (error: ApiError) => {
        this.caricamento.set(false);
        this.errore.set(error.messaggio);
      },
    });
  }

  protected seleziona(nodo: NodoLive): void {
    const path = this.percorso();
    if (path.at(-1)?.campi) {
      this.percorso.set([...path.slice(0, -1), nodo]);
    } else {
      this.percorso.set([...path, nodo]);
    }
  }

  protected risali(indice: number): void {
    this.percorso.set(indice < 0 ? [] : this.percorso().slice(0, indice + 1));
  }

  protected configurata(dimensione: DimensioneFoglia): boolean {
    return dimensione.policy !== null;
  }

  protected foglieToccate(nome: string): number {
    return this.fogliePerDimensione().get(nome) ?? 0;
  }

  protected defaultNonDisponibile(dimensione: DimensioneFoglia): boolean {
    const valore = dimensione.policy?.valore_default;
    return !!valore && !dimensione.valori.includes(valore);
  }

  protected modifica(nome: string): void {
    const corrente = this.policy()?.policy.find((item) => item.nome_dimensione === nome);
    this.scelte.update((scelte) => ({
      ...scelte,
      [nome]: corrente?.consente_valore_generico ?? null,
    }));
    this.defaultScelti.update((defaults) => ({
      ...defaults,
      [nome]: corrente?.valore_default ?? null,
    }));
    this.inModifica.update((nomi) => (nomi.includes(nome) ? nomi : [...nomi, nome]));
  }

  protected modificabile(dimensione: DimensioneFoglia): boolean {
    return !dimensione.policy || this.inModifica().includes(dimensione.nome);
  }

  protected scelta(nome: string): boolean | null {
    return this.scelte()[nome] ?? null;
  }

  protected scegli(nome: string, generico: boolean): void {
    this.scelte.update((scelte) => ({ ...scelte, [nome]: generico }));
  }

  protected defaultScelto(nome: string): string | null {
    return this.defaultScelti()[nome] ?? null;
  }

  protected scegliDefault(nome: string, valore: string): void {
    this.defaultScelti.update((defaults) => ({ ...defaults, [nome]: valore || null }));
  }

  protected annullaConferma(): void {
    this.confermaRichiesta.set(null);
  }

  protected annulla(nome: string): void {
    this.inModifica.update((nomi) => nomi.filter((item) => item !== nome));
    this.scelte.update((scelte) => ({ ...scelte, [nome]: null }));
    this.defaultScelti.update((defaults) => ({ ...defaults, [nome]: null }));
  }

  protected salva(nome: string, confermaImpatto = false): void {
    const consenteValoreGenerico = this.scelta(nome);
    if (consenteValoreGenerico === null || this.salvando()) return;
    this.salvando.set(nome);
    this.erroreSalvataggio.set(null);
    if (!confermaImpatto) this.confermaRichiesta.set(null);
    this.service
      .salvaPolicy(this.integrazioneId, this.codice, {
        nome_dimensione: nome,
        consente_valore_generico: consenteValoreGenerico,
        ...(confermaImpatto ? { conferma_impatto: true } : {}),
        valore_default: this.defaultScelto(nome),
      })
      .subscribe({
        next: (salvata) => {
          this.policy.update((corrente) => {
            if (!corrente) return corrente;
            return {
              ...corrente,
              policy: [...corrente.policy.filter((item) => item.nome_dimensione !== nome), salvata],
              dimensioni_non_configurate: corrente.dimensioni_non_configurate.filter(
                (item) => item.nome_dimensione !== nome,
              ),
            };
          });
          this.inModifica.update((nomi) => nomi.filter((item) => item !== nome));
          this.confermaRichiesta.set(null);
          this.salvando.set(null);
        },
        error: (error: ApiError) => {
          this.salvando.set(null);
          // Chiudere il generico lascia senza un valore ammesso i modelli
          // pubblicati che non lo valorizzano. Non e' un errore: e' la
          // conseguenza da leggere prima di procedere (011 FR-010b).
          if (error.codice === 'CONFERMA_IMPATTO_RICHIESTA') {
            this.confermaRichiesta.set({
              nome,
              messaggio: error.messaggio,
              modelli: (error.dettagli ?? []).map((dettaglio) => ({
                modello_id: dettaglio['modello_id'] ?? '',
                codice: dettaglio['codice'] ?? '',
                nome: dettaglio['nome'] ?? '',
              })),
            });
            return;
          }
          this.erroreSalvataggio.set(error.messaggio);
        },
      });
  }

  private dimensioniDaNodo(nodo: NodoLive): Map<string, string[]> {
    const valori = new Map<string, string[]>();
    if (nodo.lingue_possibili?.length) valori.set('lingua', [...nodo.lingue_possibili]);
    if (nodo.livelli_possibili?.length) {
      valori.set('livello_professionale', [...nodo.livelli_possibili]);
    }
    for (const [nome, value] of Object.entries(nodo as unknown as Record<string, unknown>)) {
      if (!PROPRIETA_NODO.has(nome) && Array.isArray(value) && value.length) {
        valori.set(nome, value.map(String));
      }
    }
    return valori;
  }
}
