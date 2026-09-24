import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiClient } from '../../shared/api-client';
import type { ApiError } from '../../shared/api-error';
import type { components } from '../../shared/api-types/integrazioni';
type Nodo = components['schemas']['NodoCategorizzazione'];
/** Un blocco-livello della schermata 2a (design_handoff_modellario): badge L#, select, nota opzioni. */
interface Livello {
  readonly indice: number;
  readonly nome: string;
  readonly opzioni: readonly { readonly codice: string; readonly descrizione: string }[];
  readonly scelto: string;
  readonly abilitato: boolean;
}
interface PolicyDimensione {
  readonly nome_dimensione: string;
  readonly consente_valore_generico: boolean;
  readonly valore_default: string | null;
}
interface DimensioneFoglia {
  readonly nome: string;
  readonly valori: readonly string[];
}
const TITOLI_LIVELLO: Record<string, string> = { tipologia: 'Tipologia', profilo: 'Profilo' };
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
  standalone: true,
  imports: [FormsModule, RouterLink],
  styleUrl: './modello-crea.component.scss',
  template: `
    <nav class="breadcrumb-2a" aria-label="Percorso">
      <a [routerLink]="backLink()">Contesti</a>
      <span aria-hidden="true">/</span>
      <span>{{ contesto || 'Contesto' }}</span>
      <span aria-hidden="true">/</span>
      <strong>Nuovo modello</strong>
    </nav>
    <ol class="stepper-2a" aria-label="Fasi di creazione">
      <li class="step attivo" aria-current="step"><span class="dot">1</span>Categorizzazione</li>
      <li class="connettore" aria-hidden="true"></li>
      <li class="step"><span class="dot">2</span>Generazione struttura</li>
      <li class="connettore" aria-hidden="true"></li>
      <li class="step"><span class="dot">3</span>Editor documento</li>
    </ol>
    <div class="corpo-2a">
      <section>
        <h1>Categorizzazione del modello</h1>
        <p class="lead-2a">
          Scegli il tipo documento e i livelli restituiti dal servizio di categorizzazione
          dell'integrazione. Da una foglia in poi puoi generare il modello.
        </p>
        @if (error()) {
          <div class="alert alert-danger" role="alert">{{ error() }}</div>
        }
        @if (loading()) {
          <p role="status">Caricamento...</p>
        }
        @if (!success()) {
          <div class="livelli">
            <div class="livello" [class.valorizzato]="!!tipo">
              <div class="livello-testa">
                <span class="badge-livello">L1</span>
                <label for="tipo">Tipo documento</label>
                <span class="hint">servizio: discovery dell'integrazione</span>
              </div>
              <select
                id="tipo"
                class="form-select"
                [disabled]="loading() || saving() || !!modelId"
                [ngModel]="tipo"
                (ngModelChange)="loadTree($event)"
              >
                <option value="">Seleziona tipo documento</option>
                @for (code of types(); track code) {
                  <option [value]="code">{{ code }}</option>
                }
              </select>
              @if (!tipo && types().length) {
                <p class="nota">{{ types().length }} opzioni restituite dal servizio</p>
              }
            </div>
            @for (livello of levels(); track livello.indice) {
              <div
                class="livello"
                [class.valorizzato]="!!livello.scelto"
                [class.disabilitato]="!livello.abilitato"
              >
                <div class="livello-testa">
                  <span class="badge-livello">L{{ livello.indice + 2 }}</span>
                  <label [for]="'livello-' + livello.indice">{{ livello.nome }}</label>
                  <span class="hint">suggerito dal livello precedente</span>
                </div>
                <select
                  [id]="'livello-' + livello.indice"
                  class="form-select"
                  [disabled]="!livello.abilitato || saving() || !!modelId"
                  [ngModel]="livello.scelto"
                  (ngModelChange)="chooseAt(livello.indice, $event)"
                >
                  <option value="">Seleziona {{ livello.nome.toLowerCase() }}</option>
                  @for (opzione of livello.opzioni; track opzione.codice) {
                    <option [value]="opzione.codice">{{ opzione.descrizione }}</option>
                  }
                </select>
                @if (livello.abilitato && !livello.scelto) {
                  <p class="nota">{{ livello.opzioni.length }} opzioni restituite dal servizio</p>
                }
              </div>
            }
            @if (leaf(); as selected) {
              <form #form="ngForm" (ngSubmit)="create()" class="livello valorizzato attributi">
                <div class="livello-testa">
                  <span class="badge-livello">+</span>
                  <span class="titolo-attributi">Attributi del modello</span>
                  <span class="hint">dimensioni dichiarate dalla foglia</span>
                </div>
                @for (dimensione of dimensioniFoglia(); track dimensione.nome) {
                  <label [for]="'dimensione-' + dimensione.nome" class="form-label">
                    {{ etichettaDimensione(dimensione.nome) }}
                  </label>
                  <select
                    [id]="'dimensione-' + dimensione.nome"
                    [name]="'dimensione-' + dimensione.nome"
                    class="form-select mb-3"
                    [ngModel]="valoreDimensione(dimensione.nome)"
                    (ngModelChange)="scegliDimensione(dimensione.nome, $event)"
                    [required]="!genericoAmmesso(dimensione.nome)"
                    [disabled]="saving() || !!modelId"
                  >
                    <option value="" [disabled]="!genericoAmmesso(dimensione.nome)">
                      {{
                        genericoAmmesso(dimensione.nome)
                          ? 'Nessun valore specifico'
                          : 'Seleziona un valore'
                      }}
                    </option>
                    @for (valore of dimensione.valori; track valore) {
                      <option [value]="valore">{{ valore }}</option>
                    }
                  </select>
                }
                <div class="azioni-2a">
                  <button
                    type="submit"
                    class="btn btn-primary"
                    [disabled]="form.invalid || saving()"
                  >
                    Genera modello
                  </button>
                  <a
                    class="btn btn-outline-primary"
                    routerLink="/builder"
                    [queryParams]="{ contesto: contesto }"
                    >Annulla</a
                  >
                  <span class="contatore"
                    >{{ scelti() }} di {{ totaleLivelli() }} livelli selezionati</span
                  >
                </div>
              </form>
            } @else {
              <div class="azioni-2a">
                <button type="button" class="btn btn-primary" disabled>Genera modello</button>
                <a class="btn btn-outline-primary" [routerLink]="backLink()">Annulla</a>
                <span class="contatore"
                  >{{ scelti() }} di {{ totaleLivelli() }} livelli selezionati</span
                >
              </div>
            }
          </div>
        } @else {
          <div class="alert alert-success" role="status">
            Modello {{ createdModel?.nome }} ({{ createdModel?.codice }}) creato - {{ success() }}
          </div>
          <a [routerLink]="backLink()">Torna ai modelli</a>
        }
      </section>
      <aside class="riepilogo">
        <h2>Categorizzazione corrente</h2>
        @if (!path().length && !tipo) {
          <p class="vuoto">Nessuna scelta effettuata. Inizia dal livello L1.</p>
        } @else {
          <ul class="scelte">
            @if (tipo) {
              <li>
                <span class="sigla">L1</span><strong>{{ tipo }}</strong
                ><small>Tipo documento</small>
              </li>
            }
            @for (voce of riepilogo(); track voce.sigla) {
              <li>
                <span class="sigla">{{ voce.sigla }}</span
                ><strong>{{ voce.valore }}</strong>
                <small>{{ voce.nome }}</small>
              </li>
            }
          </ul>
        }
        <h2>Codice assegnato</h2>
        <p class="codice">{{ createdModel?.codice ?? 'assegnato alla generazione' }}</p>
        <h2>Campi del contratto</h2>
        @if (leaf(); as selected) {
          <ul class="campi">
            @for (field of selected.campi; track field.codice + field.lingua) {
              <li>
                {{ field.etichetta }} - {{ field.tipo }}
                @if (field.obbligatorio) {
                  <span class="pill-obbligatorio">obbligatorio</span>
                }
              </li>
            }
          </ul>
          <p class="nota">
            I campi derivano dalla foglia scelta e restano quelli del contratto dell'integrazione.
          </p>
        } @else {
          <p class="vuoto">Scegli una foglia per vedere i campi.</p>
        }
      </aside>
    </div>
  `,
})
export class ModelloCreaComponent {
  private readonly api = inject(ApiClient);
  private readonly route = inject(ActivatedRoute);
  private readonly id = this.route.snapshot.paramMap.get('id')!;
  private readonly presetTipo = this.route.snapshot.queryParamMap?.get('tipo') ?? '';
  private readonly presetPath =
    this.route.snapshot.queryParamMap?.get('percorso')?.split('|') ?? [];
  private readonly presetDimensioni = Object.fromEntries(
    (this.route.snapshot.queryParamMap?.keys ?? [])
      .filter((key: string) => key.startsWith('dimensione.'))
      .map((key: string) => [
        key.slice('dimensione.'.length),
        this.route.snapshot.queryParamMap?.get(key) ?? '',
      ]),
  );
  protected readonly contesto = this.route.snapshot.queryParamMap?.get('contesto') ?? '';
  protected readonly types = signal<string[]>([]);
  private readonly tree = signal<Nodo[]>([]);
  protected readonly path = signal<string[]>([]);
  protected readonly leaf = signal<Nodo | null>(null);
  protected readonly error = signal<string | null>(null);
  /**
   * Policy del tipo documento: quali dimensioni ammettono un valore generico.
   * Senza questa lettura il form offriva sempre "Tutti i livelli" e il backend
   * rifiutava l'invio con DIMENSIONE_RICHIEDE_VALORE (007 FR-031).
   */
  private readonly policy = signal<Record<string, PolicyDimensione>>({});
  protected readonly dimensioni = signal<Record<string, string>>({});
  protected genericoAmmesso(dimensione: string): boolean {
    return this.policy()[dimensione]?.consente_valore_generico ?? false;
  }
  protected readonly dimensioniFoglia = computed<DimensioneFoglia[]>(() => {
    const foglia = this.leaf();
    if (!foglia) return [];
    const valori = new Map<string, readonly string[]>();
    if (foglia.lingue_possibili?.length) valori.set('lingua', foglia.lingue_possibili);
    if (foglia.livelli_possibili?.length) {
      valori.set('livello_professionale', foglia.livelli_possibili);
    }
    for (const [nome, value] of Object.entries(foglia as unknown as Record<string, unknown>)) {
      if (!PROPRIETA_NODO.has(nome) && Array.isArray(value) && value.length) {
        valori.set(nome, value.map(String));
      }
    }
    return [...valori].map(([nome, opzioni]) => ({ nome, valori: opzioni }));
  });
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly success = signal<string | null>(null);
  protected tipo = '';
  protected modelId: string | null = null;
  protected createdModel: { codice: string; nome: string } | null = null;
  constructor() {
    this.loading.set(true);
    this.api.get<string[]>(`/api/v1/builder/integrazioni/${this.id}/tipi-documento`).subscribe({
      next: (types) => {
        this.types.set(types);
        this.loading.set(false);
        if (this.presetTipo && types.includes(this.presetTipo)) this.loadTree(this.presetTipo);
      },
      error: (error: ApiError) => this.failed(error),
    });
  }
  /** Blocchi-livello L2..: uno per profondita' dell'albero raggiunta, senza assumere una forma fissa. */
  protected readonly levels = computed<Livello[]>(() => {
    const path = this.path();
    let nodes = this.tree();
    const out: Livello[] = [];
    for (let indice = 0; nodes.length > 0; indice++) {
      const scelto = path[indice] ?? '';
      const tipoLivello = nodes[0].tipo_livello;
      out.push({
        indice,
        nome:
          TITOLI_LIVELLO[tipoLivello ?? ''] ??
          (tipoLivello
            ? tipoLivello.charAt(0).toUpperCase() + tipoLivello.slice(1)
            : `Livello ${indice + 2}`),
        opzioni: nodes.map((n) => ({ codice: n.codice, descrizione: n.descrizione })),
        scelto,
        abilitato: true,
      });
      const picked = nodes.find((n) => n.codice === scelto);
      if (!picked) break;
      nodes = picked.figli ?? [];
    }
    return out;
  });

  protected backLink(): string[] {
    return this.contesto ? ['/contesti', this.contesto, 'modelli'] : ['/contesti'];
  }

  protected scelti(): number {
    return (this.tipo ? 1 : 0) + this.path().length;
  }

  protected totaleLivelli(): number {
    return 1 + this.levels().length;
  }

  protected riepilogo(): { sigla: string; valore: string; nome: string }[] {
    const levels = this.levels();
    return this.path().map((codice, indice) => ({
      sigla: `L${indice + 2}`,
      valore: levels[indice]?.opzioni.find((o) => o.codice === codice)?.descrizione ?? codice,
      nome: levels[indice]?.nome ?? '',
    }));
  }

  private nodesAt(depth: number): Nodo[] {
    let nodes = this.tree();
    for (const code of this.path().slice(0, depth)) {
      nodes = nodes.find((node) => node.codice === code)?.figli ?? [];
    }
    return nodes;
  }

  /** Scelta a cascata: cambiare un livello azzera quelli sottostanti. */
  protected chooseAt(indice: number, code: string): void {
    const node = this.nodesAt(indice).find((candidate) => candidate.codice === code);
    this.path.update((path) => path.slice(0, indice));
    this.leaf.set(null);
    this.modelId = null;
    if (node) this.choose(node);
  }

  protected loadTree(tipo: string): void {
    this.tipo = tipo;
    this.path.set([]);
    this.leaf.set(null);
    this.tree.set([]);
    this.error.set(null);
    this.modelId = null;
    if (!tipo) return;
    this.loading.set(true);
    this.api
      .get<{ nodi: Nodo[] }>(
        `/api/v1/builder/integrazioni/${this.id}/tipi-documento/${encodeURIComponent(tipo)}/struttura`,
      )
      .subscribe({
        next: (tree) => {
          this.tree.set(tree.nodi);
          this.loading.set(false);
          this.caricaPolicy(tipo);
          if (tipo === this.presetTipo && this.presetPath.length) this.applyPresetPath();
        },
        error: (error: ApiError) => this.failed(error),
      });
  }
  /** Una policy non leggibile non deve impedire la creazione: il backend resta
   * l'autorita' e rifiutera' comunque una scelta non ammessa. */
  private caricaPolicy(tipo: string): void {
    this.api
      .get<{ policy: PolicyDimensione[] }>(
        `/api/v1/builder/tipi-documento/${encodeURIComponent(tipo)}/policy-dimensioni`,
      )
      .subscribe({
        next: (risposta) => {
          this.policy.set(Object.fromEntries(risposta.policy.map((p) => [p.nome_dimensione, p])));
          if (this.leaf()) this.inizializzaDimensioni({ mantieniScelte: true });
        },
        error: () => this.policy.set({}),
      });
  }
  protected choose(node: Nodo): void {
    this.path.update((path) => [...path, node.codice]);
    this.leaf.set(node.campi ? node : null);
    if (node.campi) this.inizializzaDimensioni();
    this.modelId = null;
  }
  /**
   * Riempie le dimensioni con preset e default della policy.
   *
   * `mantieniScelte` serve quando la policy arriva **dopo** che la foglia e'
   * gia' scelta: senza, la risposta cancellava il valore che l'utente aveva
   * appena selezionato, e il bottone tornava disabilitato senza spiegazione
   * (visto dall'e2e della 011, T041). Cambiando foglia invece si riparte da
   * zero, perche' i valori della foglia precedente non c'entrano piu'.
   */
  private inizializzaDimensioni(opzioni: { mantieniScelte?: boolean } = {}): void {
    const scelte = opzioni.mantieniScelte ? this.dimensioni() : {};
    const valori = Object.fromEntries(
      this.dimensioniFoglia().flatMap((dimensione) => {
        const gia = scelte[dimensione.nome];
        if (gia && dimensione.valori.includes(gia)) return [[dimensione.nome, gia]];
        const preset = this.presetDimensioni[dimensione.nome];
        const valoreDefault = this.policy()[dimensione.nome]?.valore_default;
        const scelto = dimensione.valori.includes(preset)
          ? preset
          : dimensione.valori.includes(valoreDefault ?? '')
            ? valoreDefault
            : '';
        return scelto ? [[dimensione.nome, scelto]] : [];
      }),
    );
    this.dimensioni.set(valori);
  }
  private applyPresetPath(): void {
    for (const code of this.presetPath) {
      const node = this.nodesAt(this.path().length).find((candidate) => candidate.codice === code);
      if (!node) return;
      this.choose(node);
    }
  }
  private failed(error: ApiError): void {
    this.loading.set(false);
    this.saving.set(false);
    this.error.set(
      this.modelId
        ? `Modello salvato, versione non confermata: ${error.messaggio}`
        : error.messaggio,
    );
  }
  protected valoreDimensione(nome: string): string {
    return this.dimensioni()[nome] ?? '';
  }
  protected scegliDimensione(nome: string, valore: string): void {
    this.dimensioni.update((dimensioni) => {
      const aggiornate = { ...dimensioni };
      if (valore) aggiornate[nome] = valore;
      else delete aggiornate[nome];
      return aggiornate;
    });
  }
  protected etichettaDimensione(nome: string): string {
    return nome.replaceAll('_', ' ').replace(/^./, (iniziale) => iniziale.toUpperCase());
  }
  protected create(): void {
    if (
      this.saving() ||
      !this.leaf() ||
      this.dimensioniFoglia().some(
        (dimensione) =>
          !this.genericoAmmesso(dimensione.nome) && !this.dimensioni()[dimensione.nome],
      )
    )
      return;
    this.saving.set(true);
    this.error.set(null);
    if (this.modelId) {
      this.createVersion(this.modelId);
      return;
    }
    this.api
      .post<{ id: string; codice: string; nome: string }>('/api/v1/builder/modelli', {
        codice_tipo_documento: this.tipo,
        integrazione_id: this.id,
        percorso_categorizzazione: this.path(),
        dimensioni: this.dimensioni(),
      })
      .subscribe({
        next: (model) => {
          this.modelId = model.id;
          this.createdModel = model;
          this.createVersion(model.id);
        },
        error: (error: ApiError) => this.failed(error),
      });
  }
  private createVersion(id: string): void {
    this.api
      .post<{ stato: string }>(`/api/v1/builder/modelli/${id}/versioni`, {
        campi: this.leaf()!.campi!.map((field) => ({ codice: field.codice, lingua: field.lingua })),
      })
      .subscribe({
        next: (version) => {
          this.success.set(version.stato);
          this.saving.set(false);
        },
        error: (error: ApiError) => this.failed(error),
      });
  }
}
