# Integrare un sistema esterno

Questa pagina descrive, in modo generico, cosa deve fare un sistema esterno per
usare GEMODO: cosa espone, come si autentica, quali rotte chiama e in che
ordine. Vale per qualunque sistema e tipo documento. Il primo caso reale, con
i suoi valori concreti, è [GEBAN](casi/geban.md).

Riferimenti:

- forma dei dati: [Contratto dati](contratto-dati.md);
- elenco completo delle rotte e Swagger per provarle: [Riferimento API](riferimento-api.md);
- architettura e isolamento: [Architettura e modularità](architettura.md).

I contratti OpenAPI sono la fonte autorevole; questa pagina è una guida.

## In breve

```text
 1. Il sistema espone il discovery         GET  <url scelto dal sistema>
 2. L'amministratore GEMODO lo registra    (interfaccia: Impostazioni -> Nuovo contesto)
    e lo verifica
 3. I gestori creano e pubblicano i modelli (interfaccia: builder)
 4. Il sistema cerca il modello            GET  /api/v1/catalogo/modelli
 5. Legge i dati richiesti                 GET  /api/v1/catalogo/modelli/{id}/campi-richiesti
 6. Valida (facoltativo) e genera          POST /api/v1/documenti/valida
                                           POST /api/v1/documenti/genera  -> PDF
```

## 1. Il discovery: cosa espone il sistema

Un solo URL `GET` che risponde con il proprio dominio: tipi documento, albero
di categorizzazione, dimensioni e campi sulle foglie. Forma e regole sono in
[Contratto dati](contratto-dati.md). In sintesi:

- profondità e nomi dei livelli sono liberi; una foglia è un nodo con `campi`;
- più tipi documento possono stare nella stessa risposta;
- le dimensioni sono attributi della foglia con una lista di valori;
- GEMODO legge il discovery dal vivo, non ne importa una copia;
- l'URL deve essere raggiungibile da GEMODO e autorizzato nel suo deploy;
- in questa versione del contratto il discovery non richiede autenticazione.

Contratto OpenAPI: [`/docs/geban-discovery-endpoint`](/docs/geban-discovery-endpoint).
Il nome è storico: il contratto è lo stesso per ogni sistema.

## 2. Registrazione in GEMODO

La fa l'amministratore GEMODO
([guida](utenti/amministrazione.md)):

1. crea un contesto con la sua integrazione. Il **nome del contesto nel token**
   deve essere quello che ACE scrive nei token del sistema e dei suoi utenti;
2. inserisce l'URL del discovery e avvia la **verifica**: solo un'integrazione
   `CONNESSO` è usabile;
3. compila il **profilo di accesso**:
    - quali ruoli del contesto diventano quali permessi GEMODO;
    - quali client tecnici del sistema sono ammessi.

Un tipo documento appartiene a una sola integrazione: due integrazioni non
possono dichiarare lo stesso codice (`TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE`).

## 3. Autenticazione

Ogni chiamata porta un token Bearer emesso da Keycloak CNR (ACE):

```http
Authorization: Bearer <access_token>
```

Il token deve:

- provenire da un client ammesso: il client di login di GEMODO o un client
  dichiarato nel profilo di accesso dell'integrazione;
- portare il contesto dell'integrazione con i ruoli
  (`contexts.<contesto>.roles`), che il profilo di accesso traduce in permessi.

| Permesso | Rotte |
|---|---|
| `DOCUMENTI_VIEWER` | Ricerca nel catalogo e campi richiesti (passi 4 e 5) |
| `DOCUMENTI_GENERATORE` | Valida e genera (passo 6) |

Per l'intero flusso servono **entrambi** nel contesto dell'integrazione: con
l'isolamento per contesto attivo, come nel deploy, il catalogo controlla
`DOCUMENTI_VIEWER` e non accetta `DOCUMENTI_GENERATORE` al suo posto. Il profilo
di accesso deve quindi concederli insieme.

Un permesso vale solo nel contesto che lo concede. Una risorsa di un altro
contesto risponde `404`, come se non esistesse.

## 4. Trovare il modello

```http
GET /api/v1/catalogo/modelli?tipo_documento=<TIPO>&profilo=<CODICE>&dimensione[<nome>]=<valore>
```

| Parametro | Significato |
|---|---|
| `tipo_documento` | Obbligatorio. Codice del tipo documento dichiarato nel discovery. |
| `profilo` | Codice del nodo del percorso con `tipo_livello: "profilo"`; se nessun nodo lo è, il codice della foglia. |
| `codice_tipologia` | Codice del nodo del percorso con `tipo_livello: "tipologia"`, se esiste. |
| `dimensione[<nome>]` | Valore di una dimensione, per esempio `dimensione[area_geografica]=NORD`. |
| `lingua`, `livello_professionale` | Forme brevi per le dimensioni `lingua` e `livello_professionale`. |
| `data_riferimento` | Data alla quale il modello deve essere valido. |

La risposta elenca i modelli pubblicati, ciascuno con `modello_versione_id`
(**è l'identificativo da usare dopo**, non `modello_id`), le dimensioni e le
edizioni in altra lingua annidate in `edizioni_derivate`.

Se per una dimensione la policy ammette un modello generico e quello specifico
manca, il catalogo restituisce il generico e lo dichiara in
`dimensioni_con_fallback`. Una ricerca che non trova modelli, anche perché
indica una dimensione o un codice che non esistono, risponde `200` con
`modelli: []`, non con un errore.

**Come costruire l'albero per una ricerca univoca.** Il catalogo cerca per
`profilo` e `codice_tipologia`, non per percorso completo. Se lo stesso codice
di foglia compare in più rami, si marcano i livelli con `tipo_livello:
"tipologia"` e `"profilo"`, oppure si usano codici di foglia unici nel tipo
documento. Vedi [Contratto dati](contratto-dati.md#regole-del-nodo).

## 5. Sapere quali dati servono

```http
GET /api/v1/catalogo/modelli/{modelloVersioneId}/campi-richiesti
```

Restituisce i campi della versione e uno `schema` JSON pronto per validare i
dati prima di inviarli. Risponde `409` se la versione non è pubblicata.

## 6. Validare e generare

Lo stesso corpo vale per le due chiamate. Le chiavi di `dati` sono i `codice`
dei campi del passo 5.

```json
{
  "sistema_richiedente": "<CODICE_SISTEMA>",
  "external_context_id": "<identificativo stabile della pratica>",
  "modello_versione_id": 201,
  "data_riferimento": "2026-10-07",
  "dati": { "<codice_campo>": "<valore>" }
}
```

- **`POST /api/v1/documenti/valida`** verifica senza produrre nulla: `valido` ed
  elenco degli errori per campo.
- **`POST /api/v1/documenti/genera`** produce il documento:
    - dati validi: **il PDF** (`application/pdf`), con `Content-Disposition` e
      l'header `X-Riferimento-Documentale`; il riferimento è anche nei
      metadati del PDF, non nel testo visibile;
    - dati non validi: un JSON con gli errori, **sempre con HTTP 200**. I due
      casi si distinguono dal `Content-Type`.

Regole di validazione e codici d'errore: [Contratto dati](contratto-dati.md#validazione-dei-dati).

**Rigenerazione.** La stessa chiave (`sistema_richiedente` +
`external_context_id`) si può usare quante volte serve, anche con dati diversi:
ogni chiamata produce un PDF e un riferimento nuovi. Come chiave si usa
l'identificativo stabile della pratica, e si rigenera a ogni correzione.

**Conservazione.** GEMODO non conserva il PDF: conservarlo è compito del
sistema. Di ogni chiamata GEMODO registra chi, quando, quale chiave, quale
versione e le impronte di dati e PDF. Se la registrazione fallisce il PDF non
viene consegnato (`503 REGISTRO_GENERAZIONI_NON_DISPONIBILE`): si ripete la
chiamata.

## Errori ricorrenti

| Codice | Quando |
|---|---|
| `ACCESSO_NON_AUTENTICATO` | Token assente, scaduto o non valido |
| `MODELLO_VERSIONE_NON_TROVATO` | Versione inesistente, oppure di un altro contesto |
| `MODELLO_VERSIONE_NON_PUBBLICATO` | La versione esiste ma non è pubblicata |
| `CONTESTO_NON_VALIDO` | (400) `tipo_documento` non configurato o non attivo |
| `ACCESSO_NON_AUTORIZZATO` | (403) Ricerca su un tipo documento di un contesto in cui non si hanno permessi |
| `RICHIESTA_NON_VALIDA` | (400) Valori in conflitto per la stessa dimensione, per esempio `lingua` e `dimensione[lingua]` diversi |
| `REGISTRO_GENERAZIONI_NON_DISPONIBILE` | La generazione non si è potuta registrare: il PDF non è stato consegnato |
| `INTEGRAZIONE_NON_CONNESSA` | L'integrazione non ha superato la verifica dell'endpoint |
| `DISCOVERY_NON_DISPONIBILE` | Il discovery non ha risposto |
| `DISCOVERY_NON_CONFORME` | Il discovery ha risposto fuori contratto |

Catalogo completo dei codici: [Riferimento API](riferimento-api.md#codici-di-errore).

## Provare le chiamate

Ogni contratto ha una pagina Swagger UI con il login Keycloak: si provano le
chiamate con un token reale senza scrivere codice. L'elenco completo è in
[Riferimento API](riferimento-api.md).
