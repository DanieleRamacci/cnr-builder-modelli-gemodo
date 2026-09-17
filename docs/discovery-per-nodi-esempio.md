# Discovery GEBAN per nodi: chiamate e risposte

Questa e' una simulazione documentata, non una chiamata a GEBAN reale. Gli URL
usano il dominio dimostrativo `geban.example`: il collega puo' implementare le
stesse richieste sul proprio server e restituire i JSON qui mostrati.
I dati e le combinazioni sono demo; la modalita runtime GEMODO non e' ancora implementata.

Si registra un solo URL iniziale per BANDO_CONCORSO. Ogni risposta contiene il
collegamento successivo, completo dei parametri. Gli URL che iniziano con
`/discovery` sono relativi alla base API `https://geban.example/api`.

## 1. Recuperare le tipologie

Questa e' l'unica chiamata il cui URL proviene dalla configurazione iniziale.

Richiesta:

```http
GET https://geban.example/api/discovery/bando-concorso
Accept: application/json
```

Risposta attesa: HTTP 200, Content-Type application/json.

```json
{
  "codice_tipo_documento": "BANDO_CONCORSO",
  "versione_catalogo": "demo-2026-09-17.1",
  "validita": "2026-09-17T00:00:00Z",
  "nodi": [
    {
      "id": "TD",
      "codice": "TD",
      "descrizione": "Tempo Determinato",
      "tipo_livello": "tipologia",
      "foglia": false,
      "url_figli": "/discovery/bando-concorso/profili?tipologia=TD&versione_catalogo=demo-2026-09-17.1"
    },
    {
      "id": "CP",
      "codice": "CP",
      "descrizione": "Concorsi Pubblici",
      "tipo_livello": "tipologia",
      "foglia": false,
      "url_figli": "/discovery/bando-concorso/profili?tipologia=CP&versione_catalogo=demo-2026-09-17.1"
    }
  ]
}
```

## 2. Scegliere Tempo Determinato

L'utente sceglie TD. GEMODO prende `url_figli` dal nodo TD della risposta 1. Non inventa l'endpoint ne' il parametro.

Richiesta:

```http
GET https://geban.example/api/discovery/bando-concorso/profili?tipologia=TD&versione_catalogo=demo-2026-09-17.1
Accept: application/json
```

Risposta attesa: HTTP 200, Content-Type application/json.

```json
{
  "codice_tipo_documento": "BANDO_CONCORSO",
  "versione_catalogo": "demo-2026-09-17.1",
  "validita": "2026-09-17T00:00:00Z",
  "nodo_padre": "TD",
  "nodi": [
    {
      "id": "TD/COLLABORATORE_TECNICO_ER",
      "codice": "COLLABORATORE_TECNICO_ER",
      "descrizione": "Collaboratore Tecnico E.R.",
      "tipo_livello": "profilo",
      "livelli_possibili": [
        "IV",
        "V",
        "VI"
      ],
      "livello_base": "VI",
      "foglia": true,
      "url_campi": "/discovery/bando-concorso/campi?tipologia=TD&profilo=COLLABORATORE_TECNICO_ER&versione_catalogo=demo-2026-09-17.1"
    },
    {
      "id": "TD/RICERCATORE",
      "codice": "RICERCATORE",
      "descrizione": "Ricercatore",
      "tipo_livello": "profilo",
      "livelli_possibili": [
        "I",
        "II",
        "III"
      ],
      "livello_base": "III",
      "foglia": true,
      "url_campi": "/discovery/bando-concorso/campi?tipologia=TD&profilo=RICERCATORE&versione_catalogo=demo-2026-09-17.1"
    }
  ]
}
```

## 3. Scegliere Collaboratore Tecnico

L'utente sceglie COLLABORATORE_TECNICO_ER. Il nodo ha `foglia: true`: GEMODO segue il suo `url_campi` dalla risposta 2.

Richiesta:

```http
GET https://geban.example/api/discovery/bando-concorso/campi?tipologia=TD&profilo=COLLABORATORE_TECNICO_ER&versione_catalogo=demo-2026-09-17.1
Accept: application/json
```

Risposta attesa: HTTP 200, Content-Type application/json.

```json
{
  "codice_tipo_documento": "BANDO_CONCORSO",
  "versione_catalogo": "demo-2026-09-17.1",
  "validita": "2026-09-17T00:00:00Z",
  "nodo_id": "TD/COLLABORATORE_TECNICO_ER",
  "percorso": [
    "TD",
    "COLLABORATORE_TECNICO_ER"
  ],
  "profilo": {
    "codice": "COLLABORATORE_TECNICO_ER",
    "livelli_possibili": [
      "IV",
      "V",
      "VI"
    ],
    "livello_base": "VI"
  },
  "campi": [
    {
      "codice": "codice_bando",
      "etichetta": "Codice bando",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 1,
      "descrizione": "Identificativo funzionale del bando",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "titolo_it",
      "etichetta": "Titolo",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 2,
      "descrizione": "Titolo italiano del bando",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "descrizione_ridotta_it",
      "etichetta": "Descrizione ridotta",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": false,
      "ordine": 3,
      "descrizione": "Sintesi italiana del bando",
      "validazione": null
    },
    {
      "codice": "sede_prescelta_it",
      "etichetta": "Sede",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 4,
      "descrizione": "Sede associata alla procedura",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "numero_posti",
      "etichetta": "Numero posti",
      "tipo": "number",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 5,
      "descrizione": "Numero dei posti previsti",
      "validazione": {
        "minimum": 1
      }
    },
    {
      "codice": "titolo_en",
      "etichetta": "Title",
      "tipo": "string",
      "lingua": "EN",
      "obbligatorio": true,
      "ordine": 6,
      "descrizione": "Titolo inglese del bando",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "livello",
      "etichetta": "Livello",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 7,
      "descrizione": "Livello professionale del bando",
      "validazione": {
        "fonte_opzioni": "profilo.livelli_possibili",
        "default": "profilo.livello_base"
      }
    }
  ]
}
```

La navigazione termina. Il modello usa il percorso TD / COLLABORATORE_TECNICO_ER
e i campi restituiti. Il campo `livello` ricava le opzioni IV, V, VI da
`profilo.livelli_possibili`, con default VI da `profilo.livello_base`.
Questi sono attributi del profilo, non altri livelli dell'albero di navigazione.

## 4. Provare un altro profilo

Si torna alla risposta 2 e si sceglie RICERCATORE: il collegamento da usare e' il suo `url_campi`. La risposta completa mostra opzioni I, II, III e default III.

Richiesta:

```http
GET https://geban.example/api/discovery/bando-concorso/campi?tipologia=TD&profilo=RICERCATORE&versione_catalogo=demo-2026-09-17.1
Accept: application/json
```

Risposta attesa: HTTP 200, Content-Type application/json.

```json
{
  "codice_tipo_documento": "BANDO_CONCORSO",
  "versione_catalogo": "demo-2026-09-17.1",
  "validita": "2026-09-17T00:00:00Z",
  "nodo_id": "TD/RICERCATORE",
  "percorso": [
    "TD",
    "RICERCATORE"
  ],
  "profilo": {
    "codice": "RICERCATORE",
    "livelli_possibili": [
      "I",
      "II",
      "III"
    ],
    "livello_base": "III"
  },
  "campi": [
    {
      "codice": "codice_bando",
      "etichetta": "Codice bando",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 1,
      "descrizione": "Identificativo funzionale del bando",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "titolo_it",
      "etichetta": "Titolo",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 2,
      "descrizione": "Titolo italiano del bando",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "descrizione_ridotta_it",
      "etichetta": "Descrizione ridotta",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": false,
      "ordine": 3,
      "descrizione": "Sintesi italiana del bando",
      "validazione": null
    },
    {
      "codice": "sede_prescelta_it",
      "etichetta": "Sede",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 4,
      "descrizione": "Sede associata alla procedura",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "numero_posti",
      "etichetta": "Numero posti",
      "tipo": "number",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 5,
      "descrizione": "Numero dei posti previsti",
      "validazione": {
        "minimum": 1
      }
    },
    {
      "codice": "titolo_en",
      "etichetta": "Title",
      "tipo": "string",
      "lingua": "EN",
      "obbligatorio": true,
      "ordine": 6,
      "descrizione": "Titolo inglese del bando",
      "validazione": {
        "minLength": 1
      }
    },
    {
      "codice": "livello",
      "etichetta": "Livello",
      "tipo": "string",
      "lingua": "IT",
      "obbligatorio": true,
      "ordine": 7,
      "descrizione": "Livello professionale del bando",
      "validazione": {
        "fonte_opzioni": "profilo.livelli_possibili",
        "default": "profilo.livello_base"
      }
    }
  ]
}
```

## 5. Provare Concorsi Pubblici

Si torna alla risposta 1 e si sceglie CP. Il collegamento e' `url_figli` del nodo CP. I profili possono avere gli stessi codici, ma ID e collegamenti conservano il ramo CP.

Richiesta:

```http
GET https://geban.example/api/discovery/bando-concorso/profili?tipologia=CP&versione_catalogo=demo-2026-09-17.1
Accept: application/json
```

Risposta attesa: HTTP 200, Content-Type application/json.

```json
{
  "codice_tipo_documento": "BANDO_CONCORSO",
  "versione_catalogo": "demo-2026-09-17.1",
  "validita": "2026-09-17T00:00:00Z",
  "nodo_padre": "CP",
  "nodi": [
    {
      "id": "CP/COLLABORATORE_TECNICO_ER",
      "codice": "COLLABORATORE_TECNICO_ER",
      "descrizione": "Collaboratore Tecnico E.R.",
      "tipo_livello": "profilo",
      "livelli_possibili": [
        "IV",
        "V",
        "VI"
      ],
      "livello_base": "VI",
      "foglia": true,
      "url_campi": "/discovery/bando-concorso/campi?tipologia=CP&profilo=COLLABORATORE_TECNICO_ER&versione_catalogo=demo-2026-09-17.1"
    },
    {
      "id": "CP/RICERCATORE",
      "codice": "RICERCATORE",
      "descrizione": "Ricercatore",
      "tipo_livello": "profilo",
      "livelli_possibili": [
        "I",
        "II",
        "III"
      ],
      "livello_base": "III",
      "foglia": true,
      "url_campi": "/discovery/bando-concorso/campi?tipologia=CP&profilo=RICERCATORE&versione_catalogo=demo-2026-09-17.1"
    }
  ]
}
```

Per terminare il ramo CP, seguire uno degli `url_campi` della risposta 5.
La risposta ha lo stesso schema del passo 3 o 4, con `percorso` che inizia con
CP e `nodo_id` CP/COLLABORATORE_TECNICO_ER oppure CP/RICERCATORE.

## Versione cambiata durante la navigazione

Ogni collegamento propaga `versione_catalogo`. Se GEBAN non puo' piu' servire
quella versione, restituisce HTTP 409:

```json
{
  "codice": "VERSIONE_CATALOGO_CAMBIATA",
  "messaggio": "Il catalogo e' cambiato. Ripetere la navigazione dall'ingresso"
}
```

Si riparte dalla chiamata 1, evitando di combinare nodi e campi di versioni diverse.
Un parametro mancante produce 400; un ramo inesistente 404; il catalogo
non disponibile 503. Non si usano elenchi vuoti per nascondere questi errori.

## Simulazione con il collega

Leggete insieme i passi 1, 2 e 3: tu scegli il nodo, gli passi la richiesta
indicata nel collegamento e lui restituisce il JSON del passo successivo.
I passi 4 e 5 permettono di verificare il cambio ramo.

