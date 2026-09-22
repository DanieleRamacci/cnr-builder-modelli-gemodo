# API GEMODO per un sistema esterno

Questa pagina è il punto di partenza per chi deve integrare un sistema esterno
(GEBAN è il primo) con GEMODO. Descrive le sole rotte che vi servono, nell'ordine
in cui le userete, e cosa il vostro sistema deve esporre a sua volta.

I contratti OpenAPI sono la fonte autoritativa: quello che leggete qui è una
guida, non una seconda definizione. L'indice con Swagger UI, ReDoc e i file YAML
è pubblicato su **`/docs`**.

## In due righe

Voi ci dite come è organizzato il vostro dominio (endpoint di discovery); noi vi
diciamo quali modelli di documento esistono e quali dati servono; voi ci mandate
i dati e ricevete il PDF.

## 1. Quello che dovete esporre voi: l'endpoint di discovery

Un solo URL, che restituisce l'albero delle vostre categorie con, sulle foglie,
i campi del contratto dati.

Contratto: **`/docs/geban-discovery-endpoint`**

```json
{
  "BANDO_CONCORSO": {
    "validita": "2026-09-21T20:46:15Z",
    "nodi": [
      {
        "codice": "TI",
        "descrizione": "Tempo Indeterminato",
        "tipo_livello": "tipologia",
        "figli": [
          {
            "codice": "COLLABORATORE_TECNICO_ER",
            "descrizione": "Collaboratore Tecnico E.R.",
            "tipo_livello": "profilo",
            "livelli_possibili": ["IV", "V", "VI"],
            "lingue_possibili": ["IT", "EN"],
            "campi": [
              {
                "codice": "codice_bando",
                "etichetta": "Codice bando",
                "tipo": "string",
                "lingua": "IT",
                "obbligatorio": true,
                "ordine": 1
              }
            ]
          }
        ]
      }
    ]
  }
}
```

Regole che contano:

- **La profondità è libera.** GEMODO cammina l'albero seguendo `figli`; una foglia
  è un nodo con `campi`. Non assumiamo un numero fisso di livelli.
- **`tipo_livello` è informativo.** Non lo usiamo per decidere come camminare.
- **`lingue_possibili` è obbligatorio sulle foglie.** Sono le lingue per cui si
  possono creare modelli su quel nodo.
- **Alias accettati per compatibilità:** `lingue` al posto di `lingue_possibili` e
  `ENG` al posto di `EN`. Se però inviate sia l'alias sia il nome canonico con
  valori diversi, la risposta viene rifiutata.
- **Gli attributi che non conosciamo non fanno fallire la risposta**, ma non
  vengono nemmeno usati in silenzio: compaiono come dimensioni non configurate
  finché un amministratore GEMODO non dichiara come trattarle.

L'endpoint viene letto **dal vivo** a ogni operazione: non ne importiamo una copia.
Deve essere raggiungibile e la sua origine va autorizzata lato GEMODO.

## 2. Autenticazione

Tutte le rotte richiedono un token Bearer emesso da Keycloak.

```http
Authorization: Bearer <access_token>
```

I ruoli necessari sono indicati per ogni rotta qui sotto. `DOCUMENTI_GENERATORE`
serve per validare e generare, `DOCUMENTI_VIEWER` per consultare.

## 3. Trovare il modello da usare

```http
GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&profilo=COLLABORATORE_TECNICO_ER&livello_professionale=V
```

Ruolo: `DOCUMENTI_VIEWER`. Contratto: **`/docs/geban-catalog`**

```json
{
  "tipo_documento": "BANDO_CONCORSO",
  "profilo": "COLLABORATORE_TECNICO_ER",
  "fallback_applicato": true,
  "livello_richiesto": "V",
  "livello_risolto": null,
  "modelli": [
    {
      "modello_id": 101,
      "modello_versione_id": 201,
      "lingua": "IT",
      "livello_professionale": null,
      "stato": "PUBBLICATO",
      "edizioni_derivate": [
        { "modello_id": 102, "modello_versione_id": 202, "lingua": "EN", "edizioni_derivate": [] }
      ]
    }
  ]
}
```

Tre cose da sapere, perché cambiano il vostro codice:

- **`modello_versione_id` è l'identificativo che userete dopo.** Non `modello_id`.
- **Le edizioni in altra lingua sono annidate**, non righe separate. Filtrando per
  `lingua=EN` ottenete invece l'edizione inglese al primo livello, senza il padre.
- **Il fallback vale solo per il livello.** Se chiedete il livello V e non esiste un
  modello dedicato, ricevete quello generico e la risposta ve lo dichiara con
  `fallback_applicato: true`. **Sulla lingua non c'è fallback**: se chiedete EN e
  l'edizione inglese non esiste, non vi diamo l'italiano, vi diamo un risultato
  vuoto. Consegnare un documento nella lingua sbagliata è peggio che non consegnarlo.

## 4. Sapere quali dati servono

```http
GET /api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti
```

Ruolo: `DOCUMENTI_VIEWER`. Restituisce l'elenco dei campi con codice, etichetta,
tipo, lingua, obbligatorietà e ordine, più uno `schema` JSON già pronto per
validare i vostri dati prima di inviarli.

Risponde `409` se la versione non è pubblicata: si genera solo da versioni
pubblicate.

## 5. Validare e generare

Lo stesso corpo vale per entrambe le chiamate.

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "GEBAN-2026-000123",
  "modello_versione_id": 201,
  "data_riferimento": "2026-09-21",
  "dati": {
    "codice_bando": "BANDO-TI-CTER-2026-001",
    "numero_posti": 2
  }
}
```

Le chiavi di `dati` sono i `codice` dei campi ottenuti al passo 4.

**`POST /api/v1/documenti/valida`** (ruolo `DOCUMENTI_GENERATORE`) verifica senza
produrre nulla e risponde con `valido` più l'elenco degli errori per campo.

**`POST /api/v1/documenti/genera`** (ruolo `DOCUMENTI_GENERATORE`) produce il
documento. Contratto: **`/docs/generazione-documenti`**.

- Se i dati sono validi ricevete **direttamente il PDF** (`application/pdf`), con
  `Content-Disposition` e l'header `X-Riferimento-Documentale`.
- Se non lo sono ricevete un JSON con gli errori.

**La generazione è idempotente** sulla coppia `sistema_richiedente` +
`external_context_id`:

- stessa coppia e **stessi dati** → vi restituiamo il documento già prodotto, non
  ne creiamo un altro;
- stessa coppia e **dati diversi** → `409`, perché sarebbe un documento diverso
  sotto lo stesso riferimento.

Usate quindi come `external_context_id` un identificativo stabile del vostro
procedimento, non un valore casuale a ogni tentativo.

## 6. Riprendere un documento già generato

```http
GET /api/v1/documenti/{riferimento}
GET /api/v1/documenti/{riferimento}/download
```

Ruolo: `DOCUMENTI_VIEWER`. Contratto: **`/docs/storage-documenti`**.
Il riferimento è quello restituito nell'header `X-Riferimento-Documentale`.
Il download è possibile solo quando la generazione è `COMPLETATO`.

## Errori che incontrerete

| Codice | Quando |
| --- | --- |
| `ACCESSO_NON_AUTENTICATO` | Token assente, scaduto o non valido |
| `MODELLO_VERSIONE_NON_TROVATO` | Versione inesistente, oppure fuori dal vostro contesto |
| `MODELLO_VERSIONE_NON_PUBBLICATO` | La versione esiste ma è ancora bozza |
| `INTEGRAZIONE_NON_CONNESSA` | L'integrazione non ha superato la verifica dell'endpoint |
| `DISCOVERY_NON_DISPONIBILE` | Il vostro endpoint non ha risposto, o ha risposto fuori forma |

Una versione fuori dal vostro contesto e una inesistente danno la stessa
risposta: non riveliamo l'esistenza di risorse che non potete vedere.

## Come provarle

`/docs` elenca tutti i contratti con Swagger UI, ReDoc e il YAML scaricabile.
Swagger UI è configurato con il login Keycloak, quindi potete provare le chiamate
con un token reale senza scrivere codice.
