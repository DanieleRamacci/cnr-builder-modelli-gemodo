# Presa d'atto GEBAN: dimensioni generiche nel catalogo

Oggetto: aggiornamento additivo del catalogo modelli GEMODO

Con la feature "dimensioni generiche del modello" GEMODO smette di trattare
`lingua` e `livello_professionale` come colonne speciali interne e salva i
valori che distinguono un modello in una mappa normalizzata chiamata
`dimensioni`.

Questo non cambia il discovery che GEBAN espone a GEMODO: GEBAN continua a
dichiarare le dimensioni come attributi della foglia, per esempio
`lingue_possibili`, `livelli_possibili` o eventuali nuove chiavi come
`area_geografica`. GEBAN non deve inviare una proprieta' chiamata `dimensioni`
nel discovery.

La modifica riguarda il catalogo restituito da GEMODO a GEBAN:

- `ModelloCatalogoSchema.dimensioni` viene aggiunto come campo additivo;
- `ModelloCatalogoSchema.lingua` diventa nullable nello schema;
- per le richieste GEBAN attuali sui bandi, `lingua` resta valorizzata come
  oggi, perche' il tipo documento BANDO dichiara ancora la dimensione lingua;
- per futuri tipi documento senza lingua, il catalogo potra' restituire
  `lingua: null` e riportare la categorizzazione specifica in `dimensioni`.

Esempio bando, comportamento attuale conservato:

```json
{
  "lingua": "IT",
  "livello_professionale": "VI",
  "dimensioni": {
    "lingua": "IT",
    "livello_professionale": "VI"
  }
}
```

Esempio futuro tipo documento senza lingua:

```json
{
  "lingua": null,
  "livello_professionale": null,
  "dimensioni": {
    "area_geografica": "NORD"
  }
}
```

Impatto atteso per GEBAN:

- nessun cambiamento funzionale nelle risposte che GEBAN riceve oggi per
  `BANDO_CONCORSO`;
- eventuale rigenerazione del client OpenAPI, se il client tratta `lingua` come
  obbligatoria/non nullable a livello di schema;
- nessuna modifica richiesta al discovery esistente, salvo prendere atto che dal
  contratto discovery 0.6.0 `lingue_possibili` e' opzionale sulle foglie che non
  hanno una dimensione linguistica.

