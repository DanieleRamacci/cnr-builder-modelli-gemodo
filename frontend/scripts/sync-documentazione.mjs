#!/usr/bin/env node
// Copia in public/manuale/ le pagine di docs/ mostrate dalla voce "Documentazione"
// e ne scrive l'indice. La fonte resta docs/ (anche per mkdocs): il frontend si
// costruisce con contesto Docker `frontend/`, che non vede ../docs, quindi le
// copie sono versionate e questo script le riallinea.
//
//   node scripts/sync-documentazione.mjs           riallinea
//   node scripts/sync-documentazione.mjs --check   esce con 1 se le copie sono vecchie

import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const qui = dirname(fileURLToPath(import.meta.url));
const DOCS = resolve(qui, '../../docs');
const USCITA = resolve(qui, '../public/manuale');

// Ordine e titoli del menu. `sorgente` e' relativo a docs/; lo slug e' il nome
// del file pubblicato e l'ultimo pezzo dell'indirizzo /documentazione/<slug>.
const CONTRATTI = [
  ['geban-catalog', 'Catalogo e generazione (sistemi esterni)'],
  ['generazione-documenti', 'Generazione documenti'],
  ['storage-documenti', 'Registro di una generazione'],
  ['geban-discovery-endpoint', 'Discovery da esporre (sistema esterno)'],
  ['builder-modelli', 'Builder: modelli e versioni'],
  ['builder-discovery', 'Builder: struttura dal discovery'],
  ['integrazioni', 'Amministrazione integrazioni'],
  ['configurazione-cataloghi', 'Struttura attesa e contratto'],
  ['registro-attivita-admin', 'Registro attivita'],
];

const SEZIONI = [
  {
    codice: 'utenti',
    titolo: 'Per gli utenti',
    pagine: [
      ['utenti/introduzione.md', 'Introduzione a GEMODO'],
      ['utenti/modelli.md', 'Creare e pubblicare un modello'],
      ['utenti/amministrazione.md', 'Amministrare integrazioni e contesti'],
    ],
  },
  {
    codice: 'architettura',
    titolo: 'Architettura e integrazione',
    pagine: [
      ['architettura.md', 'Architettura e modularita'],
      ['integrazione-sistema-esterno.md', 'Integrare un sistema esterno'],
      ['contratto-dati.md', 'Contratto dati'],
      ['matrice-flussi-integrazione.md', 'Matrice flussi integrazione'],
      ['formato-documentale.md', 'Formato documentale'],
    ],
  },
  {
    codice: 'casi',
    titolo: 'Casi di integrazione',
    pagine: [
      ['casi/geban.md', 'GEBAN: bandi di concorso'],
      ['presa-atto-geban-dimensioni-catalogo.md', 'GEBAN: dimensioni nel catalogo'],
    ],
  },
  {
    codice: 'api',
    titolo: 'API',
    pagine: [['riferimento-api.md', 'Riferimento API']],
    collegamenti: [
      { titolo: 'Indice dei contratti', href: '/docs' },
      ...CONTRATTI.map(([codice, titolo]) => ({ titolo: `Swagger: ${titolo}`, href: `/docs/${codice}` })),
    ],
  },
  {
    codice: 'progetto',
    titolo: 'Progetto',
    pagine: [
      ['project-map.md', 'Mappa del progetto'],
      ['adr/0001-ownership-dati-esterni-e-onboarding-contesti.md', 'ADR 0001: dati esterni e contesti'],
      ['adr/0002-integrazioni-contesti-modelli-test.md', 'ADR 0002: integrazioni e contesti'],
      ['adr/0003-accesso-utenti-contesti-ace.md', 'ADR 0003: accesso tramite ACE'],
      ['api-documentation.md', 'Regole per documentare le API'],
      ['frontend-server-test.md', 'Collaudo sul server di test'],
      ['pulizia-modelli.md', 'Demo ed eliminazione modelli'],
      ['decision-workflow.md', 'Aggiornare le decisioni aperte'],
      ['open-source-pa-readiness.md', 'Riuso PA e open source'],
    ],
  },
  {
    codice: 'archivio',
    titolo: 'Archivio',
    pagine: [
      ['flusso-integrazione-geban.md', 'Flusso integrazione GEBAN (storico)'],
      ['discovery-per-nodi-esempio.md', 'Discovery per nodi (proposta)'],
    ],
  },
];

const slug = (sorgente) => sorgente.replace(/\.md$/, '').replaceAll('/', '-');

function attesi() {
  const file = new Map();
  const indice = {
    sezioni: SEZIONI.map((sezione) => ({
      codice: sezione.codice,
      titolo: sezione.titolo,
      pagine: sezione.pagine.map(([sorgente, titolo]) => {
        file.set(`${slug(sorgente)}.md`, readFileSync(join(DOCS, sorgente), 'utf8'));
        return { slug: slug(sorgente), titolo, sorgente };
      }),
      ...(sezione.collegamenti ? { collegamenti: sezione.collegamenti } : {}),
    })),
  };
  file.set('indice.json', JSON.stringify(indice, null, 2) + '\n');
  return file;
}

// Stesso slug di mkdocs e di src/features/documentazione/manuale.ts.
const slugTitolo = (testo) =>
  testo
    .normalize('NFKD')
    .replace(/[^\x00-\x7F]/g, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .toLowerCase()
    .replace(/[-\s]+/g, '-');

function ancore(md) {
  const senzaCodice = md.replace(/^```[\s\S]*?^```/gm, '');
  const usati = new Map();
  const ids = new Set();
  for (const [, titolo] of senzaCodice.matchAll(/^#{1,6} +(.+?) *#*$/gm)) {
    const base = slugTitolo(titolo.replace(/[`*_]/g, ''));
    const volte = usati.get(base) ?? 0;
    usati.set(base, volte + 1);
    ids.add(volte ? `${base}_${volte}` : base);
  }
  return ids;
}

// Un link fra pagine del manuale verso un'ancora che non esiste e' un errore:
// lo si scopre qui, non navigando l'app.
function linkRotti() {
  const pagine = SEZIONI.flatMap((sezione) => sezione.pagine.map(([sorgente]) => sorgente));
  const testi = new Map(pagine.map((sorgente) => [sorgente, readFileSync(join(DOCS, sorgente), 'utf8')]));
  const rotti = [];
  for (const [sorgente, md] of testi) {
    const senzaCodice = md.replace(/^```[\s\S]*?^```/gm, '').replace(/`[^`\n]*`/g, '');
    for (const [, href] of senzaCodice.matchAll(/\]\(([^)\s]+)\)/g)) {
      if (/^[a-z]+:/i.test(href) || href.startsWith('/')) continue;
      const [percorso, ancora] = href.split('#');
      const destinazione = percorso ? join(dirname(sorgente), percorso).replaceAll('\\', '/') : sorgente;
      if (!testi.has(destinazione)) continue; // fuori dal manuale: diventa testo
      if (ancora && !ancore(testi.get(destinazione)).has(ancora)) rotti.push(`${sorgente}: ${href}`);
    }
  }
  return rotti;
}

const rotti = linkRotti();
if (rotti.length) {
  for (const link of rotti) console.error(`ancora inesistente: ${link}`);
  process.exit(1);
}

const voluti = attesi();
if (process.argv.includes('--check')) {
  const presenti = existsSync(USCITA) ? readdirSync(USCITA) : [];
  const diversi = [...voluti].filter(
    ([nome, testo]) => !existsSync(join(USCITA, nome)) || readFileSync(join(USCITA, nome), 'utf8') !== testo,
  );
  const superflui = presenti.filter((nome) => !voluti.has(nome));
  if (diversi.length || superflui.length) {
    for (const [nome] of diversi) console.error(`non allineato: public/manuale/${nome}`);
    for (const nome of superflui) console.error(`superfluo: public/manuale/${nome}`);
    console.error('Eseguire: node scripts/sync-documentazione.mjs');
    process.exit(1);
  }
  console.log(`public/manuale allineato (${voluti.size} file)`);
} else {
  rmSync(USCITA, { recursive: true, force: true });
  mkdirSync(USCITA, { recursive: true });
  for (const [nome, testo] of voluti) writeFileSync(join(USCITA, nome), testo);
  console.log(`public/manuale riallineato (${voluti.size} file)`);
}
