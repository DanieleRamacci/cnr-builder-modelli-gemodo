# Contratto dati: discovery, campi e validazione

Questa pagina è il **riferimento unico** per chi integra un sistema esterno con
GEMODO (GEBAN è il primo) e per gli agenti che leggono questa documentazione.
Descrive la grammatica generica con cui un sistema esterno dichiara come è
organizzato il proprio dominio e quali dati servono, come GEMODO la verifica e
come valida i dati che riceve per generare un documento.

Vale per qualunque tipo documento, non solo per il bando: il bando è il primo
caso concreto.

| Versione del contratto discovery | Stato |
|---|---|
| **0.7.0** | **Attiva.** È quella che GEMODO applica oggi. |
| **0.8.0** | **Proposta, spec `014`.** Aggiunge il campo ripetibile (casi multipli, per esempio le articolazioni di un bando) e rende non conformi le chiavi sconosciute dentro un campo. Non è ancora implementata: le sezioni che la descrivono sono marcate *0.8.0*. |

Fonti autorevoli, in ordine:

1. il contratto OpenAPI dell'endpoint discovery, pubblicato su
   `/docs/geban-discovery-endpoint`
   (sorgente `specs/010-configurazione-cataloghi-integrazioni/contracts/geban-discovery-endpoint.openapi.yaml`);
2. per la 0.8.0, lo schema
   `specs/014-articolazioni-bando/contracts/discovery-0.8.0.schema.json` e gli
   esempi nella stessa cartella;
3. il codice che li applica: `backend/app/discovery/schemas.py` (lettura del
   discovery) e `backend/app/validation/service.py` (validazione dei dati).

Le rotte, l'autenticazione e il flusso di chiamate sono in
[API per un sistema esterno](api-per-geban.md).

## In una frase

L'integratore descrive la **forma** (un albero di categorie che finisce in
foglie con i campi), GEMODO salva una **copia** dei campi in ogni versione di
modello, e poi valida i **valori** che l'integratore invia contro quella copia.

```text
  DISCOVERY (integratore)          MODELLO (GEMODO)               DATI (integratore)
  albero vivo, letto a ogni   ->   la versione salva i campi  ->  /documenti/valida
  operazione: categorie,           scelti dalla foglia: e' una    /documenti/genera
  dimensioni, campi                copia, non un riferimento      { "dati": {...} }
  "che forma hanno i dati"         "cosa chiede questo modello"   "i valori di questo documento"
```

Tre conseguenze:

- l'albero può cambiare quando vuole l'integratore; GEMODO lo rilegge dal vivo;
- un modello già pubblicato non cambia se l'albero cambia: valida sempre con i
  campi di quando è stato creato;
- la validazione dei dati non legge il discovery: legge la copia del modello.

## Struttura generica del discovery

Un solo URL `GET`, che risponde con un oggetto JSON. Ogni chiave è un codice di
tipo documento; ogni valore è un albero di nodi a profondità libera.

```json
{
  "<CODICE_TIPO_DOCUMENTO>": {
    "validita": "2026-10-07T08:00:00Z",
    "nodi": [
      {
        "codice": "<codice livello 1>",
        "descrizione": "<testo leggibile>",
        "tipo_livello": "<nome libero del livello, solo informativo>",
        "figli": [
          {
            "codice": "<codice livello 2>",
            "descrizione": "...",
            "figli": [
              {
                "codice": "<codice foglia>",
                "descrizione": "...",
                "<dimensione>": ["<valore>", "<valore>"],
                "campi": [
                  {
                    "codice": "<codice campo>",
                    "etichetta": "<testo per il gestore>",
                    "tipo": "string",
                    "obbligatorio": true,
                    "ordine": 1
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

- **Categorizzazione:** quanti livelli e quanti rami decide l'integratore. Un
  tipo documento può avere un livello, due (come il bando: tipologia, poi
  profilo) o più. GEMODO non assume un numero fisso.
- **Foglia:** è il nodo che porta i `campi`. Un modello si crea sempre su una
  foglia, identificata dal percorso completo dei codici dalla radice.
- **Dimensioni:** sono attributi della foglia con una lista di stringhe, per
  esempio `livelli_possibili`, `lingue` o `area_geografica`. Distinguono più
  modelli sulla stessa foglia.
- **Campi:** il contratto dati della foglia, cioè quali valori servono per
  generare un documento.

Più tipi documento possono stare nella stessa risposta, ciascuno con la propria
chiave.

## Regole del nodo

| Regola | Se violata |
|---|---|
| `codice` (non vuoto) e `descrizione` sempre presenti | non conforme |
| `figli` **oppure** `campi`, mai entrambi e mai nessuno dei due | non conforme |
| `codice` unico fra i fratelli (e fra i nodi radice) | non conforme |
| `codice` dei campi unico nella foglia | non conforme |
| `livelli_possibili`, `livello_base`, `lingue_possibili` solo sulle foglie | non conforme |
| Valori duplicati in `livelli_possibili` o `lingue_possibili` | non conforme |
| `livello_base` deve stare fra i `livelli_possibili` | non conforme |
| `validita` è una data ISO 8601 con fuso orario | non conforme |
| `tipo_livello` | facoltativo, solo informativo: GEMODO non lo usa per camminare l'albero |

Alias accettati per compatibilità: `lingue` per `lingue_possibili` (con `ENG`
per `EN`) e `livelloBase` per `livello_base`. Se arrivano sia l'alias sia il
nome canonico con valori diversi, la risposta è non conforme.

**Chiavi sconosciute sul nodo:** non fanno fallire la risposta.

- Se portano una lista non vuota di stringhe diventano **dimensioni**, mostrate
  all'amministratore come "non configurate" finché non ne imposta la policy.
- Altrimenti sono conservate ma non usate.

## Il campo: grammatica chiusa

La forma di un campo è identica a qualunque livello e per qualunque tipo
documento. È l'unica parte del contratto che non varia.

| Chiave | Obbligatoria | Significato |
|---|---|---|
| `codice` | sì | Identificativo tecnico. È la chiave del valore nei `dati` e il nome del segnaposto nel modello. Unico nella foglia. |
| `etichetta` | sì | Testo mostrato al gestore nel builder. |
| `tipo` | sì | `string`, `number`, `date` (data ISO 8601, es. `2026-10-07`), `boolean`, `array`, `object`. Non esiste un tipo `enum`: le opzioni vanno in `validazione`. |
| `obbligatorio` | sì | Se `true`, i dati di generazione devono contenere un valore non nullo. |
| `ordine` | sì | Intero da 1 in su: ordine di presentazione. |
| `descrizione` | no | Spiegazione del campo. |
| `lingua` | no | `IT` o `EN`. Dalla 0.7.0 la lingua sta sulla foglia; sul campo vale solo come restrizione a una lingua sola. |
| `validazione` | no | Vincoli (`minLength`, `minimum`, …) o riferimento a un attributo del profilo (`{"fonte_opzioni": "profilo.livelli_possibili"}`). |
| `campi` | no, *0.8.0* | Solo su `tipo: "array"`: i sotto-campi di ogni elemento. Vedi [Campi ripetibili](#campi-ripetibili-080). |

### Chiavi non previste dentro un campo

| | 0.7.0 (oggi) | 0.8.0 (spec `014`) |
|---|---|---|
| `campi` su un campo `array` | **scartata in silenzio** | letta: sotto-campi del campo ripetibile |
| `campi` su un campo non `array` | scartata in silenzio | **non conforme** |
| Altra chiave sconosciuta | scartata in silenzio | **non conforme**, con nome della chiave e percorso |
| Chiave che inizia con `_` (es. `_comment`) | scartata | ignorata come annotazione |

Il passaggio da "scartata" a "non conforme" serve perché un dato che
l'integratore pensa di inviare non sparisca senza che nessuno se ne accorga.
Il 2026-10-07 l'albero GEBAN di test (65 foglie, 852 campi) usava sui campi
solo `codice`, `etichetta`, `tipo`, `obbligatorio`, `ordine`, `descrizione`
ed è conforme alla 0.8.0 senza modifiche.

## Verifica di conformità del discovery

Quando un amministratore registra l'URL dell'integratore, GEMODO esegue il
**test di connessione**. Il test legge la risposta e controlla le regole sopra.
L'esito è:

- `CONFORME`: l'integrazione diventa `CONNESSA` e si possono creare modelli;
- `NON_CONFORME`: forma non rispettata. L'esito elenca gli errori con il
  **percorso** del punto difforme;
- `NON_RAGGIUNGIBILE`: errore di rete, timeout o risposta HTTP diversa da 200.

Il test controlla la **forma**, non i valori. Una risposta con tipologie,
profili o campi diversi dagli esempi è conforme, se rispetta la grammatica.

Limiti dell'adapter, configurabili: 10 secondi complessivi, 2 MiB di JSON,
64 pagine, 64 livelli. Superarli rende la risposta non conforme. Durante l'uso
gli stessi controlli producono `DISCOVERY_NON_CONFORME` (HTTP 502) o
`DISCOVERY_NON_DISPONIBILE` (HTTP 503); sono esiti di GEMODO, non errori che
l'integratore deve emettere.

## Cosa può cambiare l'integratore senza toccare GEMODO

| Cambiamento nel discovery | Effetto |
|---|---|
| Nuovo ramo o nuova foglia | Visibile subito nel builder: si possono creare modelli sulla nuova foglia. |
| Più livelli in un ramo | Nessuna modifica: la profondità è libera. |
| Nuova dimensione sulla foglia (es. `area_geografica`) | Compare come dimensione non configurata; l'amministratore ne imposta la policy. Finché non lo fa vale la regola prudente: valore esplicito richiesto. |
| Nuovo campo su una foglia | Disponibile per le **nuove** versioni di modello su quella foglia. Le versioni esistenti non lo chiedono. |
| Un campo passa da facoltativo a obbligatorio (o viceversa) | Vale per le nuove versioni. Le versioni pubblicate validano con l'obbligatorietà salvata. |
| Un campo viene rimosso | Le versioni pubblicate continuano a chiederlo. Una nuova versione non può più includerlo. |
| Una foglia viene rimossa | I modelli esistenti restano; non si possono creare nuove versioni su quel ramo. |

Per adeguare un modello pubblicato a un contratto cambiato si crea una nuova
versione e la si pubblica.

## Cosa si imposta dall'interfaccia di amministrazione

| Dove | Cosa | Effetto |
|---|---|---|
| **Policy dati da struttura** (tipo documento) | Tipologie, profili, attributi con valori ammessi e default, combinazioni, lingue, campi con `obbligatorio` | Genera il JSON del discovery atteso, da consegnare all'integratore come contratto. Usa la stessa grammatica di campo del discovery. Oggi genera un albero a due livelli (tipologia, profilo). |
| **Dimensioni e policy** (integrazione) | Per ogni dimensione dell'albero vivo: `consente_valore_generico` e `valore_default` | Decide se un modello può non avere un valore per quella dimensione (fallback nel catalogo) e la preselezione nel builder. Non rende obbligatorio un campo dati. |
| **Builder** (modello) | Quali campi della foglia entrano nella versione | Il modello chiede solo i campi scelti; i segnaposti del documento devono essere fra questi. |

Per un'integrazione dal vivo, l'obbligatorietà di un campo la decide
l'integratore nel discovery. Il test di connessione non confronta l'albero vivo
con la struttura definita da interfaccia: quella serve a produrre il contratto
da consegnare.

## Validazione dei dati

`POST /api/v1/documenti/valida` e `POST /api/v1/documenti/genera` ricevono lo
stesso corpo. Le chiavi di `dati` sono i `codice` dei campi della versione.

```json
{
  "sistema_richiedente": "GEBAN",
  "external_context_id": "GEBAN-2026-000123",
  "modello_versione_id": 201,
  "data_riferimento": "2026-10-07",
  "dati": { "codice_bando": "BANDO-CD-RIC-2026-001", "numero_posti": 1 }
}
```

Regole applicate contro la copia dei campi salvata nella versione:

| Controllo | Codice errore |
|---|---|
| Chiave in `dati` non prevista dalla versione | `CAMPO_NON_AMMESSO` |
| Campo obbligatorio assente o `null` | `CAMPO_OBBLIGATORIO` |
| Valore del tipo sbagliato (`date` deve essere una data ISO 8601, `number` non accetta booleani) | `TIPO_NON_VALIDO` |

Ogni errore indica il `campo` interessato. I vincoli in `validazione` (per
esempio `minLength`) sono pubblicati nello schema JSON di
`GET /api/v1/catalogo/modelli/{id}/campi-richiesti`, utile per validare prima
di inviare. La validazione di GEMODO oggi controlla presenza, tipo e campi non
ammessi.

## Campi ripetibili (0.8.0)

*Proposta della spec `014`, non ancora implementata.*

Serve quando uno stesso documento contiene più gruppi di dati con la stessa
forma. Per esempio un bando con più **articolazioni** (tematiche, sedi, linee),
ognuna con il proprio codice, numero di posti e sede. Senza questo meccanismo
servirebbero nomi artificiali come `codice_bando_01`, `codice_bando_02`, che
non funzionano perché il numero cambia da procedura a procedura.

La regola è una sola: **un campo con `tipo: "array"` può dichiarare `campi`,
l'elenco dei sotto-campi di ogni elemento.**

- I sotto-campi hanno la stessa forma di un campo normale.
- I sotto-campi sono scalari: `string`, `number`, `date`, `boolean`. È ammesso
  un solo livello di annidamento.
- `articolazioni` non è una parola riservata: è il `codice` scelto per i bandi.
  Un altro tipo documento può dichiarare `lotti` o `sedi` con la stessa regola.
- Un campo `array` senza `campi` resta ammesso, come lista di valori senza
  struttura.
- Una foglia può avere più campi ripetibili.

### Nel discovery: si dichiara la forma

```json
{
  "codice": "articolazioni",
  "etichetta": "Articolazioni del bando",
  "tipo": "array",
  "obbligatorio": false,
  "ordine": 7,
  "descrizione": "Parti distinte della procedura, ciascuna con i propri dati",
  "campi": [
    { "codice": "codice_bando", "etichetta": "Codice articolazione", "tipo": "string", "obbligatorio": true, "ordine": 1 },
    { "codice": "numero_posti", "etichetta": "Numero posti", "tipo": "number", "obbligatorio": true, "ordine": 2 },
    { "codice": "sede_lavoro", "etichetta": "Sede lavoro", "tipo": "string", "obbligatorio": true, "ordine": 3 }
  ]
}
```

Il discovery non elenca le articolazioni reali: dice solo com'è fatta
un'articolazione.

### Nei dati: si inviano gli elementi

Ogni elemento ha sempre tre chiavi:

- `codice`: tecnico, unico nella lista;
- `descrizione`: leggibile, identifica l'elemento nel documento e negli errori;
- `campi`: i valori dei sotto-campi.

```json
"dati": {
  "codice_bando": "BANDO-CD-RIC-2026-001",
  "numero_posti": 3,
  "articolazioni": [
    {
      "codice": "TEMA_A",
      "descrizione": "Tematica A - Scienze del clima, Roma",
      "campi": { "codice_bando": "BANDO-CD-RIC-2026-001-A", "numero_posti": 1, "sede_lavoro": "Istituto di Roma" }
    },
    {
      "codice": "TEMA_B",
      "descrizione": "Tematica B - Biologia marina, Napoli",
      "campi": { "codice_bando": "BANDO-CD-RIC-2026-001-B", "numero_posti": 2, "sede_lavoro": "Istituto di Napoli" }
    }
  ]
}
```

I valori stanno dentro `campi`, non accanto a `codice` e `descrizione`, perché
un sotto-campo può chiamarsi come le chiavi dell'elemento. L'albero GEBAN ha per
esempio un campo con codice `descrizione`.

### Validazione degli elementi

| Controllo | Errore e percorso |
|---|---|
| Campo ripetibile obbligatorio assente o lista vuota | `CAMPO_OBBLIGATORIO` su `articolazioni` |
| Elemento senza `codice` | `CAMPO_OBBLIGATORIO` su `articolazioni[1].codice` (indice da 0) |
| Due elementi con lo stesso `codice` | `CODICE_ELEMENTO_DUPLICATO` su `articolazioni` |
| Elemento senza `descrizione` | `CAMPO_OBBLIGATORIO` su `articolazioni[TEMA_A].descrizione` |
| Sotto-campo obbligatorio mancante | `CAMPO_OBBLIGATORIO` su `articolazioni[TEMA_A].campi.numero_posti` |
| Sotto-campo non dichiarato | `CAMPO_NON_AMMESSO` su `articolazioni[TEMA_A].campi.<codice>` |
| Sotto-campo del tipo sbagliato | `TIPO_NON_VALIDO` su `articolazioni[TEMA_A].campi.<codice>` |

Un sotto-campo può avere lo stesso codice di un campo principale (sopra,
`codice_bando` e `numero_posti`): il percorso li distingue. Lo schema JSON di
`campi-richiesti` descrive gli elementi in `items`.

### Nel builder e nel documento

Il builder mostra i campi principali e, separato, un gruppo collassabile per
ogni campo ripetibile, intitolato con la sua `etichetta`. Un solo documento per
richiesta, qualunque sia il numero di elementi.

Come il modello impagina gli elementi è una **decisione aperta** della spec
`014`. La proposta è un blocco ripetuto per ogni elemento, con segnaposti
relativi all'elemento.

## Esempi completi

Verificati contro lo schema 0.8.0; il bando singolo è valido anche con la 0.7.0.

| Caso | Discovery | Dati |
|---|---|---|
| Bando singolo | `specs/014-articolazioni-bando/contracts/discovery-bando-singolo.json` | `specs/014-articolazioni-bando/contracts/dati-bando-singolo.json` |
| Bando con articolazioni | `specs/014-articolazioni-bando/contracts/discovery-bando-articolato.json` | `specs/014-articolazioni-bando/contracts/dati-bando-articolato.json` |

Il bando singolo è il caso di partenza: senza campi ripetibili tutto funziona
come prima, e un modello già pubblicato non cambia.

## Checklist per una nuova integrazione

1. Scegliere il codice del tipo documento e i livelli della categorizzazione;
   dare a ogni nodo `codice` e `descrizione`.
2. Mettere i `campi` solo sulle foglie, con le cinque chiavi obbligatorie.
3. Dichiarare come dimensioni, sulla foglia, le liste di valori che distinguono
   modelli diversi (lingua, livello, area).
4. Per i gruppi ripetuti usare un campo `array` con `campi` (*0.8.0*), non
   codici numerati.
5. Non aggiungere chiavi proprie dentro un campo; per le note usare il prefisso
   `_`.
6. Esporre l'endpoint, farlo registrare all'amministratore GEMODO e superare il
   test di connessione.
7. Per generare: catalogo per ottenere `modello_versione_id`, `campi-richiesti`
   per sapere cosa inviare, poi `valida` e `genera`.

## Regole per agenti e strumenti automatici

- Il discovery descrive la **forma**; i **valori** viaggiano solo in `dati`.
  Non inserire valori nel discovery né forme nei dati.
- Le chiavi strutturali fisse sono `nodi`, `figli`, `campi`, `codice`,
  `descrizione`. I nomi dei livelli, delle dimensioni e dei campi sono liberi.
- Una foglia è un nodo con `campi`; un nodo non ha mai `figli` e `campi`
  insieme.
- La grammatica del campo è chiusa (vedi la tabella). Non inventare chiavi come
  `id`, `label`, `required`, `type`.
- Un modello pubblicato valida con la propria copia dei campi, non con il
  discovery corrente.
- Distinguere sempre 0.7.0 (attiva) da 0.8.0 (proposta): prima di affermare che
  i campi ripetibili funzionano, verificare `VERSIONE_CONTRATTO_DISCOVERY` in
  `backend/app/discovery/schemas.py`.
- La variante a collegamenti successivi (`url_figli`) descritta in
  [Discovery per nodi](discovery-per-nodi-esempio.md) è una proposta non
  implementata. Il formato in uso è l'albero completo.
