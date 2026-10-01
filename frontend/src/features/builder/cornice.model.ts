import type { FrammentoTesto } from './frammenti';

/** La cornice di pagina di un tipo documento (012 FR-011, T065). */
export type IntestazionePagina = {
  maschera: string;
  con_logo: boolean;
  testo: FrammentoTesto[];
};
export type PiePagina = { maschera: string; testo: FrammentoTesto[]; numerazione_pagine: boolean };
export type CornicePagina = {
  intestazione: IntestazionePagina | null;
  pie_pagina: PiePagina | null;
};
export type CorniceTipoDocumento = {
  cornice: CornicePagina | null;
  logo_presente: boolean;
  maschere_intestazione: string[];
  maschere_pie_pagina: string[];
};
export type CorniceModello = CorniceTipoDocumento & {
  integrazione_id: string | null;
  codice_tipo_documento: string;
  codice_contesto: string;
};

/** Come si chiamano le maschere nell'interfaccia. */
export const NOMI_MASCHERE: Record<string, string> = {
  LOGO_CENTRO_TESTO_SOTTO: 'Logo al centro, testo sotto',
  TESTO_SINISTRA_NUMERO_DESTRA: 'Testo a sinistra, numero di pagina a destra',
};

export function urlCornice(integrazioneId: string, codice: string): string {
  return `/api/v1/builder/integrazioni/${integrazioneId}/tipi-documento/${encodeURIComponent(codice)}/cornice`;
}

/** Le righe dell'intestazione, ciascuna con la sua enfasi: come le disegna il renderer. */
export function righeIntestazione(
  testo: FrammentoTesto[],
): { testo: string; grassetto: boolean; corsivo: boolean }[] {
  const righe: FrammentoTesto[][] = [[]];
  for (const frammento of testo) {
    frammento.testo.split('\n').forEach((pezzo, i) => {
      if (i) righe.push([]);
      if (pezzo) righe[righe.length - 1].push({ ...frammento, testo: pezzo });
    });
  }
  return righe
    .filter((riga) => riga.length)
    .map((riga) => ({
      testo: riga.map((f) => f.testo).join(''),
      grassetto: riga.every((f) => f.grassetto),
      corsivo: riga.every((f) => f.corsivo),
    }));
}
