import { describe, expect, it } from 'vitest';
import { EditorState, TextSelection, type Command } from 'prosemirror-state';

import {
  STILI,
  blocchiDaDocumento,
  comandoElenco,
  comandoEnfasi,
  comandoInterruzione,
  comandoLivello,
  comandoStile,
  comandoTesto,
  comandoUnisciRighe,
  creaStato,
  documentoDaBlocchi,
  impronta,
  porzioneDaIncollare,
  type BloccoDocumento,
} from './documento-editor';
import type { FrammentoTesto } from './frammenti';

function blocco(
  id: string,
  frammenti: FrammentoTesto[],
  extra: Partial<BloccoDocumento> = {},
): BloccoDocumento {
  return {
    id,
    tipo: 'PARAGRAFO',
    frammenti,
    allineamento: null,
    elementi: [],
    posizionamento: 'BODY',
    ordine: 0,
    stile: null,
    placeholder_usati: [],
    regole_layout: {},
    asset_ref: null,
    colonne: [],
    ...extra,
  };
}

const NESSUNA_CRONOLOGIA = { annulla: () => undefined, ripeti: () => undefined };

function stato(blocchi: BloccoDocumento[]): EditorState {
  return creaStato(blocchi, () => 'art', NESSUNA_CRONOLOGIA);
}

function esegui(iniziale: EditorState, comando: Command): EditorState {
  let risultato = iniziale;
  comando(iniziale, (tr) => {
    risultato = iniziale.apply(tr);
  });
  return risultato;
}

/** Il testo cercato, come posizioni del documento: per selezionare come col mouse. */
function posizioneDi(s: EditorState, testo: string): { da: number; a: number } {
  let trovato: { da: number; a: number } | null = null;
  s.doc.descendants((nodo, pos) => {
    if (trovato || !nodo.isText) return;
    const indice = nodo.text!.indexOf(testo);
    if (indice >= 0) trovato = { da: pos + indice, a: pos + indice + testo.length };
  });
  if (!trovato) throw new Error(`"${testo}" non c'e'`);
  return trovato;
}

function seleziona(s: EditorState, da: string, a: string): EditorState {
  return s.apply(
    s.tr.setSelection(TextSelection.create(s.doc, posizioneDi(s, da).da, posizioneDi(s, a).a)),
  );
}

const ARTICOLO: BloccoDocumento[] = [
  blocco('t', [{ testo: 'Art. 3 - Requisiti' }], {
    tipo: 'TITOLO',
    allineamento: 'CENTRO',
    ordine: 0,
  }),
  blocco('p', [{ testo: 'VISTO', grassetto: true }, { testo: ' il decreto\nn. 127;' }], {
    allineamento: 'GIUSTIFICATO',
    ordine: 1,
  }),
  blocco('e', [], {
    tipo: 'ELENCO',
    ordine: 2,
    elementi: [
      { livello: 0, marcatore: 'NUMERICO', frammenti: [{ testo: 'Requisiti:' }] },
      {
        livello: 1,
        marcatore: 'ALFABETICO',
        frammenti: [{ testo: 'cittadinanza ' }, { testo: '{{nazione}}', corsivo: true }],
      },
    ],
  }),
  blocco('i', [], { tipo: 'INTERRUZIONE_PAGINA', ordine: 3 }),
  blocco('f', [{ testo: 'Il Presidente' }], {
    tipo: 'FIRMA',
    posizionamento: 'BOTTOM_RIGHT',
    ordine: 4,
  }),
];

describe('documento ProseMirror <-> blocchi (T074)', () => {
  it('un articolo torna uguale dopo andata e ritorno', () => {
    const ritorno = blocchiDaDocumento(documentoDaBlocchi(ARTICOLO));
    expect(impronta(ritorno)).toBe(impronta(ARTICOLO));
    expect(ritorno.map((b) => b.ordine)).toEqual([0, 1, 2, 3, 4]);
    expect(ritorno[2].placeholder_usati).toEqual(['nazione']);
  });

  it('un blocco che l editor non gestisce resta intatto', () => {
    const tabella = blocco('tab', [], { tipo: 'TABELLA', colonne: ['a', 'b'] });
    const ritorno = blocchiDaDocumento(documentoDaBlocchi([tabella]));
    expect(ritorno[0]).toEqual({ ...tabella, ordine: 0 });
  });

  it('una sezione vuota diventa una riga su cui scrivere', () => {
    const documento = documentoDaBlocchi([]);
    expect(documento.childCount).toBe(1);
    expect(documento.firstChild!.type.name).toBe('paragrafo');
  });

  it('i campi del formato che l editor non tocca non si perdono', () => {
    const conRegole = blocco('r', [{ testo: 'x' }], { regole_layout: { margine: 'ampio' } });
    expect(blocchiDaDocumento(documentoDaBlocchi([conRegole]))[0].regole_layout).toEqual({
      margine: 'ampio',
    });
  });
});

describe('comandi su piu capoversi (T076)', () => {
  it('il grassetto si applica a una selezione che attraversa tre blocchi', () => {
    const iniziale = seleziona(stato(ARTICOLO), 'Requisiti', 'Requisiti:');
    const blocchi = blocchiDaDocumento(esegui(iniziale, comandoEnfasi('grassetto')).doc);
    expect(blocchi[0].frammenti).toEqual([
      { testo: 'Art. 3 - ' },
      { testo: 'Requisiti', grassetto: true },
    ]);
    expect(blocchi[1].frammenti.every((f) => f.grassetto)).toBe(true);
    expect(blocchi[2].elementi![0].frammenti).toEqual([{ testo: 'Requisiti:', grassetto: true }]);
    expect(blocchi[2].elementi![1].frammenti[0].grassetto).toBeUndefined();
  });

  it('come in Word: l enfasi si toglie solo se tutta la selezione ce l ha gia', () => {
    const parziale = seleziona(stato(ARTICOLO), 'VISTO', 'il decreto');
    const dopo = esegui(parziale, comandoEnfasi('grassetto'));
    expect(blocchiDaDocumento(dopo.doc)[1].frammenti[0]).toEqual({
      testo: 'VISTO il decreto',
      grassetto: true,
    });
    const tolto = esegui(seleziona(dopo, 'VISTO', 'il decreto'), comandoEnfasi('grassetto'));
    expect(blocchiDaDocumento(tolto.doc)[1].frammenti[0]).toEqual({
      testo: 'VISTO il decreto\nn. 127;',
    });
  });

  it('un segnaposto in grassetto resta un frammento unico e sostituibile', () => {
    const iniziale = seleziona(stato(ARTICOLO), '{{nazione}}', '{{nazione}}');
    const blocchi = blocchiDaDocumento(esegui(iniziale, comandoEnfasi('grassetto')).doc);
    expect(blocchi[2].elementi![1].frammenti[1]).toEqual({
      testo: '{{nazione}}',
      grassetto: true,
      corsivo: true,
    });
    expect(blocchi[2].placeholder_usati).toEqual(['nazione']);
  });

  it('lo stile si applica a tutti i blocchi selezionati', () => {
    const iniziale = seleziona(stato(ARTICOLO), 'VISTO', 'Requisiti:');
    const h2 = STILI.find((s) => s.valore === 'H2')!;
    const blocchi = blocchiDaDocumento(esegui(iniziale, comandoStile(h2)).doc);
    expect(blocchi.map((b) => [b.tipo, b.stile])).toEqual([
      ['TITOLO', null],
      ['PARAGRAFO', 'H2'],
      ['PARAGRAFO', 'H2'],
      ['ELENCO', null],
      ['INTERRUZIONE_PAGINA', null],
      ['FIRMA', null],
    ]);
    // Il capoverso staccato dall'elenco ha un id suo: il formato li vuole unici.
    expect(new Set(blocchi.map((b) => b.id)).size).toBe(blocchi.length);
  });

  it('due capoversi diventano due voci dello stesso elenco, e tornano capoversi', () => {
    const due = [blocco('a', [{ testo: 'uno' }]), blocco('b', [{ testo: 'due' }], { ordine: 1 })];
    const selezionati = seleziona(stato(due), 'uno', 'due');
    const elenco = esegui(selezionati, comandoElenco('NUMERICO'));
    const blocchi = blocchiDaDocumento(elenco.doc);
    expect(blocchi).toHaveLength(1);
    expect(blocchi[0].elementi!.map((e) => e.marcatore)).toEqual(['NUMERICO', 'NUMERICO']);
    const ritorno = blocchiDaDocumento(esegui(elenco, comandoElenco('NUMERICO')).doc);
    expect(ritorno.map((b) => b.tipo)).toEqual(['PARAGRAFO', 'PARAGRAFO']);
    expect(new Set(ritorno.map((b) => b.id)).size).toBe(2);
  });

  it('il marcatore scelto col solo cursore cambia tutto l elenco', () => {
    const iniziale = stato(ARTICOLO);
    const pos = posizioneDi(iniziale, 'Requisiti:').da;
    const cursore = iniziale.apply(
      iniziale.tr.setSelection(TextSelection.create(iniziale.doc, pos)),
    );
    const blocchi = blocchiDaDocumento(esegui(cursore, comandoElenco('PUNTATO')).doc);
    expect(blocchi[2].elementi!.map((e) => e.marcatore)).toEqual(['PUNTATO', 'PUNTATO']);
  });

  it('Tab non porta al secondo livello la prima voce di un elenco', () => {
    const iniziale = stato(ARTICOLO);
    const pos = posizioneDi(iniziale, 'Requisiti:').da;
    const cursore = iniziale.apply(
      iniziale.tr.setSelection(TextSelection.create(iniziale.doc, pos)),
    );
    const dopo = esegui(cursore, comandoLivello(1));
    expect(blocchiDaDocumento(dopo.doc)[2].elementi![0].livello).toBe(0);
  });

  it('l interruzione su una riga vuota va prima della riga', () => {
    const vuota = stato([blocco('a', [{ testo: 'testo' }]), blocco('b', [], { ordine: 1 })]);
    const fine = vuota.apply(
      vuota.tr.setSelection(TextSelection.create(vuota.doc, vuota.doc.content.size - 1)),
    );
    const blocchi = blocchiDaDocumento(esegui(fine, comandoInterruzione).doc);
    expect(blocchi.map((b) => b.tipo)).toEqual(['PARAGRAFO', 'INTERRUZIONE_PAGINA', 'PARAGRAFO']);
  });

  it('un segnaposto inserito in un grassetto e in grassetto', () => {
    const iniziale = stato([blocco('a', [{ testo: 'VISTO', grassetto: true }])]);
    const pos = posizioneDi(iniziale, 'VISTO').a;
    const cursore = iniziale.apply(
      iniziale.tr.setSelection(TextSelection.create(iniziale.doc, pos)),
    );
    const blocchi = blocchiDaDocumento(esegui(cursore, comandoTesto(' {{campo}}')).doc);
    expect(blocchi[0].frammenti).toEqual([{ testo: 'VISTO {{campo}}', grassetto: true }]);
    expect(blocchi[0].placeholder_usati).toEqual(['campo']);
  });
});

describe('incolla (T075)', () => {
  it('capoversi incollati a meta di un capoverso lo dividono, aperti ai due capi', () => {
    const iniziale = stato([blocco('a', [{ testo: 'prima dopo' }])]);
    const pos = posizioneDi(iniziale, ' dopo').da;
    const cursore = iniziale.apply(
      iniziale.tr.setSelection(TextSelection.create(iniziale.doc, pos)),
    );
    const porzione = porzioneDaIncollare([
      { tipo: 'PARAGRAFO', frammenti: [{ testo: ' uno' }] },
      { tipo: 'PARAGRAFO', frammenti: [{ testo: 'due' }] },
    ]);
    const dopo = cursore.apply(cursore.tr.replaceSelection(porzione));
    const blocchi = blocchiDaDocumento(dopo.doc);
    expect(blocchi.map((b) => b.frammenti[0]?.testo)).toEqual(['prima uno', 'due dopo']);
    expect(new Set(blocchi.map((b) => b.id)).size).toBe(2);
  });
});

describe('unisci righe (riscontro del 2026-10-02)', () => {
  // I visti come li aveva salvati il vecchio editor: una riga del PDF per capoverso.
  const RIGHE: BloccoDocumento[] = [
    'IL VICEPRESIDENTE',
    'VISTO il D.Lgs 31 dicembre 2009 n. 213, “Riordino degli Enti di ricerca in attuazione dell’art. 1 della',
    'legge 27 settembre 2007, n. 165”;',
    'VISTO lo Statuto del CNR, emanato con provvedimento del Presidente del CNR n. 93 prot.',
    '0051080/2018 del 19/07/2018, di cui è stato dato l’avviso di pubbli-',
    'cazione sul sito del Ministero;',
  ].map((testo, i) =>
    blocco(
      `r${i}`,
      i === 1 ? [{ testo: 'VISTO', grassetto: true }, { testo: testo.slice(5) }] : [{ testo }],
      {
        ordine: i,
        allineamento: 'GIUSTIFICATO',
      },
    ),
  );

  it('ricompone i visti in capoversi interi, tenendo l enfasi e ricucendo le parole spezzate', () => {
    const tutto = stato(RIGHE);
    const selezione = tutto.apply(
      tutto.tr.setSelection(TextSelection.create(tutto.doc, 1, tutto.doc.content.size - 1)),
    );
    const blocchi = blocchiDaDocumento(esegui(selezione, comandoUnisciRighe).doc);
    expect(blocchi.map((b) => b.frammenti.map((f) => f.testo).join(''))).toEqual([
      'IL VICEPRESIDENTE',
      'VISTO il D.Lgs 31 dicembre 2009 n. 213, “Riordino degli Enti di ricerca in attuazione dell’art. 1 della legge 27 settembre 2007, n. 165”;',
      'VISTO lo Statuto del CNR, emanato con provvedimento del Presidente del CNR n. 93 prot. 0051080/2018 del 19/07/2018, di cui è stato dato l’avviso di pubblicazione sul sito del Ministero;',
    ]);
    expect(blocchi[1].frammenti[0]).toEqual({ testo: 'VISTO', grassetto: true });
    expect(blocchi.every((b) => b.allineamento === 'GIUSTIFICATO')).toBe(true);
    expect(new Set(blocchi.map((b) => b.id)).size).toBe(3);
  });

  it('il seguito di una voce si unisce alla voce, e una voce nuova resta una voce', () => {
    const conVoci = [
      {
        ...blocco('e', [], {
          tipo: 'ELENCO',
          ordine: 0,
          elementi: [
            {
              livello: 0 as const,
              marcatore: 'NUMERICO' as const,
              frammenti: [{ testo: 'ai sensi del' }],
            },
          ],
        }),
      },
      blocco('p', [{ testo: 'D.P.R. 487/1994;' }], { ordine: 1 }),
      {
        ...blocco('e2', [], {
          tipo: 'ELENCO',
          ordine: 2,
          elementi: [
            {
              livello: 0 as const,
              marcatore: 'NUMERICO' as const,
              frammenti: [{ testo: 'secondo comma' }],
            },
          ],
        }),
      },
    ];
    const tutto = stato(conVoci);
    const selezione = tutto.apply(
      tutto.tr.setSelection(TextSelection.create(tutto.doc, 1, tutto.doc.content.size - 1)),
    );
    const blocchi = blocchiDaDocumento(esegui(selezione, comandoUnisciRighe).doc);
    expect(blocchi.map((b) => b.tipo)).toEqual(['ELENCO', 'ELENCO']);
    expect(blocchi[0].elementi![0].frammenti).toEqual([{ testo: 'ai sensi del D.P.R. 487/1994;' }]);
  });
});
