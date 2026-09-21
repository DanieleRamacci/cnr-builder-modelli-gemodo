import { Component, computed, inject, signal } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import type { ApiError } from '../../shared/api-error';

import {
  TipiDocumentoService,
  type StrutturaTipoDocumento,
} from './tipi-documento.service';

const TIPI_CAMPO = ['string', 'number', 'boolean', 'date', 'object', 'array'] as const;
const LINGUE = ['IT', 'EN'] as const;

/**
 * Editor struttura tipo documento (spec 010 User Story 1, FR-001..FR-005):
 * tipologie, profili (con attributi profilo-dipendenti), combinazioni ammesse,
 * lingue possibili e campi del contratto dati con obbligatorio/opzionale
 * esplicito. Crea (POST) se il tipo non esiste ancora, altrimenti legge e
 * sostituisce la struttura corrente (PUT) - ogni submit e' una definizione
 * completa, non una modifica incrementale (coerente con come il backend
 * versiona la definizione).
 */
@Component({
  selector: 'app-tipo-documento-struttura',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './tipo-documento-struttura.component.html',
  styleUrl: './tipo-documento-struttura.component.scss',
})
export class TipoDocumentoStrutturaComponent {
  private readonly service = inject(TipiDocumentoService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  protected readonly tipiCampo = TIPI_CAMPO;
  protected readonly lingue = LINGUE;

  protected readonly codiceEsistente = this.route.snapshot.paramMap.get('codice');
  protected readonly modalitaModifica = this.codiceEsistente !== null;

  protected readonly caricamento = signal(this.modalitaModifica);
  protected readonly salvataggio = signal(false);
  protected readonly errore = signal<string | null>(null);
  protected readonly salvatoOra = signal(false);

  protected readonly identita = this.fb.nonNullable.group({
    codice: [{ value: this.codiceEsistente ?? '', disabled: this.modalitaModifica }, [Validators.required, Validators.maxLength(128)]],
    nome: ['', [Validators.required, Validators.maxLength(200)]],
    codiceContesto: ['', [Validators.required, Validators.maxLength(64)]],
  });

  protected readonly tipologie = this.fb.array<FormGroup>([]);
  protected readonly profili = this.fb.array<FormGroup>([]);
  protected readonly combinazioni = this.fb.array<FormGroup>([]);
  protected readonly linguePossibili = this.fb.nonNullable.group({
    IT: [true],
    EN: [false],
  });
  protected readonly campi = this.fb.array<FormGroup>([]);

  protected readonly codiciTipologie = computed(() =>
    this.tipologie.controls.map((c) => c.get('codice')?.value as string).filter(Boolean),
  );
  protected readonly codiciProfili = computed(() =>
    this.profili.controls.map((c) => c.get('codice')?.value as string).filter(Boolean),
  );

  constructor() {
    if (this.modalitaModifica && this.codiceEsistente) {
      this.service.leggiStruttura(this.codiceEsistente).subscribe({
        next: (struttura) => {
          this.applicaStruttura(struttura);
          this.caricamento.set(false);
        },
        error: (error: ApiError) => {
          this.caricamento.set(false);
          this.errore.set(error.messaggio);
        },
      });
    } else {
      this.aggiungiTipologia();
      this.aggiungiProfilo();
      this.aggiungiCampo();
    }
  }

  private nuovaTipologia(valore?: { codice: string; descrizione: string; riferimento_esterno?: string | null }) {
    return this.fb.nonNullable.group({
      codice: [valore?.codice ?? '', Validators.required],
      descrizione: [valore?.descrizione ?? '', Validators.required],
      riferimentoEsterno: [valore?.riferimento_esterno ?? ''],
    });
  }

  private nuovoAttributo(valore?: { nome: string; valori_ammessi: string[]; valore_default?: string | null }) {
    return this.fb.nonNullable.group({
      nome: [valore?.nome ?? '', Validators.required],
      valoriAmmessi: [(valore?.valori_ammessi ?? []).join(', '), Validators.required],
      valoreDefault: [valore?.valore_default ?? ''],
    });
  }

  private nuovoProfilo(valore?: {
    codice: string;
    descrizione: string;
    attributi?: { nome: string; valori_ammessi: string[]; valore_default?: string | null }[];
  }) {
    const attributi = this.fb.array<FormGroup>((valore?.attributi ?? []).map((a) => this.nuovoAttributo(a)));
    return this.fb.group({
      codice: this.fb.nonNullable.control(valore?.codice ?? '', Validators.required),
      descrizione: this.fb.nonNullable.control(valore?.descrizione ?? '', Validators.required),
      attributi,
    });
  }

  private nuovaCombinazione(valore?: { codice_tipologia: string; codice_profilo: string }) {
    return this.fb.nonNullable.group({
      codiceTipologia: [valore?.codice_tipologia ?? '', Validators.required],
      codiceProfilo: [valore?.codice_profilo ?? '', Validators.required],
    });
  }

  private nuovoCampo(valore?: {
    codice: string;
    etichetta: string;
    tipo: string;
    lingua: string;
    obbligatorio: boolean;
    ordine: number;
    dipende_da_attributo_profilo?: string | null;
  }) {
    return this.fb.nonNullable.group({
      codice: [valore?.codice ?? '', Validators.required],
      etichetta: [valore?.etichetta ?? '', Validators.required],
      tipo: [valore?.tipo ?? 'string', Validators.required],
      lingua: [valore?.lingua ?? 'IT', Validators.required],
      obbligatorio: [valore?.obbligatorio ?? true],
      ordine: [valore?.ordine ?? this.campi.length + 1, [Validators.required, Validators.min(1)]],
      dipendeDaAttributoProfilo: [valore?.dipende_da_attributo_profilo ?? ''],
    });
  }

  protected aggiungiTipologia(): void {
    this.tipologie.push(this.nuovaTipologia());
  }
  protected rimuoviTipologia(i: number): void {
    this.tipologie.removeAt(i);
  }

  protected aggiungiProfilo(): void {
    this.profili.push(this.nuovoProfilo());
  }
  protected rimuoviProfilo(i: number): void {
    this.profili.removeAt(i);
  }
  protected attributiDi(profilo: FormGroup): FormArray<FormGroup> {
    return profilo.get('attributi') as FormArray<FormGroup>;
  }
  protected aggiungiAttributo(profilo: FormGroup): void {
    this.attributiDi(profilo).push(this.nuovoAttributo());
  }
  protected rimuoviAttributo(profilo: FormGroup, i: number): void {
    this.attributiDi(profilo).removeAt(i);
  }

  protected aggiungiCombinazione(): void {
    this.combinazioni.push(this.nuovaCombinazione());
  }
  protected rimuoviCombinazione(i: number): void {
    this.combinazioni.removeAt(i);
  }

  protected aggiungiCampo(): void {
    this.campi.push(this.nuovoCampo());
  }
  protected rimuoviCampo(i: number): void {
    this.campi.removeAt(i);
  }

  private applicaStruttura(struttura: StrutturaTipoDocumento): void {
    this.tipologie.clear();
    (struttura.tipologie ?? []).forEach((t) => this.tipologie.push(this.nuovaTipologia(t)));
    this.profili.clear();
    (struttura.profili ?? []).forEach((p) => this.profili.push(this.nuovoProfilo(p)));
    this.combinazioni.clear();
    (struttura.combinazioni ?? []).forEach((c) => this.combinazioni.push(this.nuovaCombinazione(c)));
    this.linguePossibili.setValue({
      IT: (struttura.lingue_possibili ?? []).includes('IT'),
      EN: (struttura.lingue_possibili ?? []).includes('EN'),
    });
    this.campi.clear();
    (struttura.campi ?? []).forEach((c) => this.campi.push(this.nuovoCampo(c)));
    if (this.tipologie.length === 0) this.aggiungiTipologia();
    if (this.profili.length === 0) this.aggiungiProfilo();
    if (this.campi.length === 0) this.aggiungiCampo();
  }

  private costruisciStruttura(): StrutturaTipoDocumento {
    const lingue = this.linguePossibili.getRawValue();
    return {
      tipologie: this.tipologie.controls.map((c) => ({
        codice: c.value.codice,
        descrizione: c.value.descrizione,
        riferimento_esterno: c.value.riferimentoEsterno || null,
      })),
      profili: this.profili.controls.map((c) => ({
        codice: c.value.codice,
        descrizione: c.value.descrizione,
        attributi: this.attributiDi(c).controls.map((a) => ({
          nome: a.value.nome,
          valori_ammessi: String(a.value.valoriAmmessi)
            .split(',')
            .map((v: string) => v.trim())
            .filter(Boolean),
          valore_default: a.value.valoreDefault || null,
        })),
      })),
      combinazioni: this.combinazioni.controls.map((c) => ({
        codice_tipologia: c.value.codiceTipologia,
        codice_profilo: c.value.codiceProfilo,
      })),
      lingue_possibili: (['IT', 'EN'] as const).filter((l) => lingue[l]),
      campi: this.campi.controls.map((c) => ({
        codice: c.value.codice,
        etichetta: c.value.etichetta,
        tipo: c.value.tipo,
        lingua: c.value.lingua,
        obbligatorio: c.value.obbligatorio,
        ordine: c.value.ordine,
        dipende_da_attributo_profilo: c.value.dipendeDaAttributoProfilo || null,
      })),
    };
  }

  protected salva(): void {
    if (this.identita.invalid && !this.modalitaModifica) {
      this.identita.markAllAsTouched();
      return;
    }
    this.errore.set(null);
    this.salvatoOra.set(false);
    this.salvataggio.set(true);
    const struttura = this.costruisciStruttura();

    if (this.modalitaModifica && this.codiceEsistente) {
      this.service.aggiornaStruttura(this.codiceEsistente, struttura).subscribe({
        next: () => {
          this.salvataggio.set(false);
          this.salvatoOra.set(true);
        },
        error: (error: ApiError) => {
          this.salvataggio.set(false);
          this.errore.set(error.messaggio);
        },
      });
      return;
    }

    const { codice, nome, codiceContesto } = this.identita.getRawValue();
    this.service
      .crea({ codice, nome, codice_contesto: codiceContesto, struttura })
      .subscribe({
        next: () => this.router.navigate(['/configurazione/tipi-documento', codice]),
        error: (error: ApiError) => {
          this.salvataggio.set(false);
          this.errore.set(error.messaggio);
        },
      });
  }
}
