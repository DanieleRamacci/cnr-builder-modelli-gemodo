/**
 * Forma documentale minima del discovery; i valori sono esempi, non dati runtime.
 *
 * Contratto 0.7.0: la lingua sta sulla **foglia** (`lingue`), non dentro ogni
 * campo. La foglia dichiara un contratto campi solo, valido per tutte le lingue
 * che dichiara. `lingua` su un campo resta ammessa e vale come restrizione a una
 * lingua sola: qui la usa `titolo_en`, che esiste solo in inglese.
 */
export const DISCOVERY_EXAMPLE = {
  BANDO_CONCORSO: {
    validita: '2026-09-15T00:00:00Z',
    nodi: [
      {
        codice: 'TD',
        descrizione: 'Tempo Determinato',
        tipo_livello: 'tipologia',
        figli: [
          {
            codice: 'COLLABORATORE_TECNICO_ER',
            descrizione: 'Collaboratore Tecnico E.R.',
            tipo_livello: 'profilo',
            livelli_possibili: ['IV', 'V', 'VI'],
            livello_base: 'VI',
            lingue: ['IT', 'ENG'],
            campi: [
              {
                codice: 'codice_bando',
                etichetta: 'Codice bando',
                tipo: 'string',
                obbligatorio: true,
                ordine: 1,
                descrizione: 'Identificativo funzionale del bando',
                validazione: { minLength: 1 },
              },
              {
                codice: 'titolo',
                etichetta: 'Titolo',
                tipo: 'string',
                obbligatorio: true,
                ordine: 2,
                descrizione: 'Titolo del bando',
                validazione: { minLength: 1 },
              },
              {
                codice: 'descrizione_ridotta',
                etichetta: 'Descrizione ridotta',
                tipo: 'string',
                obbligatorio: false,
                ordine: 3,
                descrizione: 'Sintesi del bando',
                validazione: null,
              },
              {
                codice: 'sede_prescelta',
                etichetta: 'Sede',
                tipo: 'string',
                obbligatorio: true,
                ordine: 4,
                descrizione: 'Sede associata alla procedura',
                validazione: { minLength: 1 },
              },
              {
                codice: 'numero_posti',
                etichetta: 'Numero posti',
                tipo: 'number',
                obbligatorio: true,
                ordine: 5,
                descrizione: 'Numero dei posti previsti',
                validazione: { minimum: 1 },
              },
              {
                codice: 'titolo_en',
                etichetta: 'Title',
                tipo: 'string',
                // Campo ristretto a una lingua sola: l'unico caso in cui
                // dichiarare `lingua` sul campo (contratto 0.7.0).
                lingua: 'EN',
                obbligatorio: true,
                ordine: 6,
                descrizione: 'Titolo inglese, per le sole edizioni EN',
                validazione: { minLength: 1 },
              },
              {
                codice: 'livello',
                etichetta: 'Livello',
                tipo: 'string',
                obbligatorio: true,
                ordine: 7,
                descrizione: 'Livello professionale del bando',
                validazione: {
                  fonte_opzioni: 'profilo.livelli_possibili',
                  default: 'profilo.livello_base',
                },
              },
            ],
          },
        ],
      },
    ],
  },
} as const;

export const DISCOVERY_EXAMPLE_JSON = JSON.stringify(DISCOVERY_EXAMPLE, null, 2);
