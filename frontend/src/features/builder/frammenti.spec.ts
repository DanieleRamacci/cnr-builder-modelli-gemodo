import {
  applicaEnfasi,
  convertiAppunti,
  leggiFrammentiDalDom,
  normalizzaFrammenti,
  offsetNelTesto,
  placeholderNeiFrammenti,
  puntoDaOffset,
  scriviFrammentiNelDom,
  type FrammentoTesto,
} from './frammenti';

const VISTO: FrammentoTesto[] = [
  { testo: 'VISTO', grassetto: true },
  { testo: ' il Decreto Legislativo 4 giugno 2003, n. 127, recante ' },
  { testo: '“Riordino del Consiglio Nazionale delle Ricerche”', corsivo: true },
  { testo: ';' },
];

function editor(): HTMLElement {
  const elemento = document.createElement('div');
  document.body.appendChild(elemento);
  return elemento;
}

describe('frammenti: forma del testo nell editor (012 T021-T022)', () => {
  it('rilegge dal DOM esattamente i frammenti che vi ha scritto', () => {
    const elemento = editor();
    scriviFrammentiNelDom(elemento, VISTO);
    expect(elemento.innerHTML).toContain('<strong>VISTO</strong>');
    expect(leggiFrammentiDalDom(elemento)).toEqual(VISTO);
  });

  it('unisce i frammenti adiacenti uguali invece di accumularli', () => {
    expect(
      normalizzaFrammenti([
        { testo: 'Art. ', grassetto: true },
        { testo: '1', grassetto: true, corsivo: false },
        { testo: '' },
        { testo: ' - Indizione' },
      ]),
    ).toEqual([{ testo: 'Art. 1', grassetto: true }, { testo: ' - Indizione' }]);
  });

  it('legge anche il markup che produce il browser, compreso lo stile in linea', () => {
    const elemento = editor();
    elemento.innerHTML =
      'a <b>b <i>c</i></b> <span style="font-weight: 700">d</span> <u>e</u><br>f<div>g</div>';
    expect(leggiFrammentiDalDom(elemento)).toEqual([
      { testo: 'a ' },
      { testo: 'b ', grassetto: true },
      { testo: 'c', grassetto: true, corsivo: true },
      { testo: ' ' },
      { testo: 'd', grassetto: true },
      { testo: ' ' },
      { testo: 'e', sottolineato: true },
      { testo: '\nf\ng' },
    ]);
  });

  it('conta le posizioni nel DOM come conta il testo, a capo compresi', () => {
    const elemento = editor();
    scriviFrammentiNelDom(elemento, [{ testo: 'uno\n' }, { testo: 'due', grassetto: true }]);
    const due = elemento.querySelector('strong')!.firstChild!;
    expect(offsetNelTesto(elemento, due, 1)).toBe(5);
    const punto = puntoDaOffset(elemento, 5);
    expect(punto.nodo).toBe(due);
    expect(punto.offset).toBe(1);
  });

  it('cerca i segnaposto dentro ciascun frammento, come li sostituisce il servizio', () => {
    expect(
      placeholderNeiFrammenti([
        { testo: 'Bando n. ' },
        { testo: '{{numero_bando}}', grassetto: true },
        { testo: ' del {{da' },
        { testo: 'ta}}', corsivo: true },
      ]),
    ).toEqual(['numero_bando']);
  });
});

describe('frammenti: enfasi su selezione (012 T020, T024)', () => {
  it('mette il grassetto su una selezione parziale di un frammento', () => {
    expect(applicaEnfasi([{ testo: 'VISTO il decreto' }], 0, 5, 'grassetto')).toEqual([
      { testo: 'VISTO', grassetto: true },
      { testo: ' il decreto' },
    ]);
  });

  it('annida corsivo e grassetto sulla stessa porzione', () => {
    const grassetto = applicaEnfasi([{ testo: 'uno due tre' }], 4, 11, 'grassetto');
    expect(applicaEnfasi(grassetto, 0, 7, 'corsivo')).toEqual([
      { testo: 'uno ', corsivo: true },
      { testo: 'due', grassetto: true, corsivo: true },
      { testo: ' tre', grassetto: true },
    ]);
  });

  it('toglie l enfasi se tutta la selezione ce l ha gia, la mette se ce l ha solo in parte', () => {
    const tutto = applicaEnfasi(VISTO, 0, 5, 'grassetto');
    expect(tutto[0]).toEqual({
      testo: 'VISTO il Decreto Legislativo 4 giugno 2003, n. 127, recante ',
    });

    const parziale = applicaEnfasi(VISTO, 3, 9, 'grassetto');
    expect(parziale[0]).toEqual({ testo: 'VISTO il ', grassetto: true });
  });

  it('un segnaposto in grassetto resta un frammento unico e sostituibile', () => {
    const frammenti = applicaEnfasi([{ testo: 'Posti: {{numero_posti}}.' }], 7, 23, 'grassetto');
    expect(frammenti[1]).toEqual({ testo: '{{numero_posti}}', grassetto: true });
    expect(placeholderNeiFrammenti(frammenti)).toEqual(['numero_posti']);
  });
});

describe('frammenti: incolla da elaboratore di testi (012 T023, FR-017)', () => {
  // Forma reale degli appunti di Word desktop: le liste non sono <ul>/<ol>
  // ma paragrafi `mso-list`, con il marcatore in uno span `mso-list:Ignore`
  // racchiuso da commenti condizionali.
  const WORD = `<html xmlns:o="urn:schemas-microsoft-com:office:office"><head>
<meta charset="utf-8"><style><!-- p.MsoNormal {margin:0cm; font-family:"Calibri"} --></style></head>
<body lang=IT><!--StartFragment-->
<p class=MsoNormal style='text-align:justify'><b><span style='font-size:11.0pt;color:#1F3864'>VISTO</span></b><span
style='font-size:11.0pt'> il Decreto Legislativo 4 giugno 2003, n. 127, recante <i>“Riordino del
Consiglio Nazionale delle Ricerche”</i>;<o:p></o:p></span></p>
<p class=MsoNormal><o:p>&nbsp;</o:p></p>
<p class=MsoListParagraph style='margin-left:18pt;mso-list:l0 level1 lfo1'><![if !supportLists]><span
style='mso-list:Ignore'>1.<span style='font:7.0pt "Times New Roman"'>&nbsp;&nbsp;&nbsp; </span></span><![endif]>Sono
indetti i seguenti concorsi:<o:p></o:p></p>
<p class=MsoListParagraph style='margin-left:36pt;mso-list:l0 level2 lfo1'><![if !supportLists]><span
style='mso-list:Ignore'>a)<span>&nbsp;&nbsp; </span></span><![endif]>un posto presso la sede di <u>Roma</u>;<o:p></o:p></p>
<table><tr><td>tabella da scartare</td></tr></table>
<p class=MsoNormal><img src="file:///C:/logo.png">Il Presidente</p>
<!--EndFragment--></body></html>`;

  it('da Word conserva enfasi, capoversi ed elenchi e scarta il resto', () => {
    expect(convertiAppunti(WORD, '')).toEqual([
      {
        tipo: 'PARAGRAFO',
        frammenti: [
          { testo: 'VISTO', grassetto: true },
          { testo: ' il Decreto Legislativo 4 giugno 2003, n. 127, recante ' },
          { testo: '“Riordino del Consiglio Nazionale delle Ricerche”', corsivo: true },
          { testo: ';' },
        ],
      },
      {
        tipo: 'ELENCO',
        elementi: [
          {
            livello: 0,
            marcatore: 'NUMERICO',
            frammenti: [{ testo: 'Sono indetti i seguenti concorsi:' }],
          },
          {
            livello: 1,
            marcatore: 'ALFABETICO',
            frammenti: [
              { testo: 'un posto presso la sede di ' },
              { testo: 'Roma', sottolineato: true },
              { testo: ';' },
            ],
          },
        ],
      },
      { tipo: 'PARAGRAFO', frammenti: [{ testo: 'Il Presidente' }] },
    ]);
  });

  it('da Google Docs non scambia il <b> esterno per un grassetto', () => {
    const docs =
      '<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-1"><p dir="ltr">' +
      '<span style="font-weight:700;">Art. 2</span><span style="font-weight:400;"> - Requisiti</span></p>' +
      '<ul><li><p><span style="font-style:italic;">cittadinanza</span></p></li>' +
      '<li><p><span>eta</span></p><ul><li><p>sotto</p></li></ul></li></ul></b>';
    expect(convertiAppunti(docs, '')).toEqual([
      {
        tipo: 'PARAGRAFO',
        frammenti: [{ testo: 'Art. 2', grassetto: true }, { testo: ' - Requisiti' }],
      },
      {
        tipo: 'ELENCO',
        elementi: [
          {
            livello: 0,
            marcatore: 'PUNTATO',
            frammenti: [{ testo: 'cittadinanza', corsivo: true }],
          },
          { livello: 0, marcatore: 'PUNTATO', frammenti: [{ testo: 'eta' }] },
          { livello: 1, marcatore: 'PUNTATO', frammenti: [{ testo: 'sotto' }] },
        ],
      },
    ]);
  });

  it('toglie i marcatori scritti a mano, che si sommerebbero alla numerazione calcolata', () => {
    const html =
      '<p>1. Sono indetti i seguenti concorsi:</p><p>a) un posto a Roma;</p>' +
      '<p>b) un posto a Milano.</p><p>2. Le domande vanno presentate entro il 30.</p>';
    const [elenco] = convertiAppunti(html, '');
    expect(elenco).toEqual({
      tipo: 'ELENCO',
      elementi: [
        {
          livello: 0,
          marcatore: 'NUMERICO',
          frammenti: [{ testo: 'Sono indetti i seguenti concorsi:' }],
        },
        { livello: 1, marcatore: 'ALFABETICO', frammenti: [{ testo: 'un posto a Roma;' }] },
        { livello: 1, marcatore: 'ALFABETICO', frammenti: [{ testo: 'un posto a Milano.' }] },
        {
          livello: 0,
          marcatore: 'NUMERICO',
          frammenti: [{ testo: 'Le domande vanno presentate entro il 30.' }],
        },
      ],
    });
  });

  it('toglie il marcatore anche da una voce di lista vera che lo ripete nel testo', () => {
    const [elenco] = convertiAppunti('<ol><li>1. primo</li><li>2) secondo</li></ol>', '');
    expect(elenco).toEqual({
      tipo: 'ELENCO',
      elementi: [
        { livello: 0, marcatore: 'NUMERICO', frammenti: [{ testo: 'primo' }] },
        { livello: 0, marcatore: 'NUMERICO', frammenti: [{ testo: 'secondo' }] },
      ],
    });
  });

  it('non scambia per marcatore un numero o un simbolo dentro la frase', () => {
    expect(convertiAppunti('<p>Il 3 &lt; 5 e la legge 127. non sono elenchi</p>', '')).toEqual([
      { tipo: 'PARAGRAFO', frammenti: [{ testo: 'Il 3 < 5 e la legge 127. non sono elenchi' }] },
    ]);
  });

  it('senza HTML usa il testo semplice, una riga per capoverso', () => {
    expect(convertiAppunti('', 'VISTO il decreto;\r\n\r\n• primo\n• secondo\n')).toEqual([
      { tipo: 'PARAGRAFO', frammenti: [{ testo: 'VISTO il decreto;' }] },
      {
        tipo: 'ELENCO',
        elementi: [
          { livello: 0, marcatore: 'PUNTATO', frammenti: [{ testo: 'primo' }] },
          { livello: 0, marcatore: 'PUNTATO', frammenti: [{ testo: 'secondo' }] },
        ],
      },
    ]);
  });

  it('non lascia passare markup come testo: un collegamento non ammesso perde il link, non il testo', () => {
    expect(
      convertiAppunti(
        '<p><a href="javascript:alert(1)">clic</a> e <a href="https://cnr.it">CNR</a></p>',
        '',
      ),
    ).toEqual([
      {
        tipo: 'PARAGRAFO',
        frammenti: [{ testo: 'clic e ' }, { testo: 'CNR', collegamento: 'https://cnr.it' }],
      },
    ]);
  });
});
