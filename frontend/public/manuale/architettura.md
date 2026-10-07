# Architettura e modularità

Questa pagina descrive GEMODO come sistema generico: cosa fa, da quali parti è
composto, quali concetti gestisce, cosa conserva e cosa legge dal vivo, e
soprattutto **come si estende a nuovi tipi di documento e a nuovi sistemi senza
modificare il codice**. I casi concreti, a partire da GEBAN, sono nella sezione
[Casi di integrazione](casi/geban.md).

Stato descritto: 2026-10-07.

## 1. Scopo

GEMODO gestisce **modelli di documento** e li usa per **generare PDF** a partire
dai dati inviati da un sistema esterno. Separa tre responsabilità:

| Chi | Responsabilità |
|---|---|
| Sistema esterno (integrazione) | Possiede il dominio: quali tipi di documento esistono, come si classificano, quali dati servono. Possiede anche i dati di ogni singolo documento. |
| GEMODO | Possiede i modelli: testo, struttura, impaginazione, ciclo di approvazione. Genera il PDF. |
| Persone | Il gestore scrive e pubblica i modelli; l'amministratore collega i sistemi e ne governa gli accessi. |

GEMODO **non copia** il dominio del sistema esterno come propria fonte di
verità: lo legge dal vivo. **Non conserva** i documenti generati: li restituisce
a chi li ha chiesti e ne tiene una traccia verificabile.

## 2. Componenti

```text
 Browser ── frontend (Angular, Bootstrap Italia) ──┐
                                                   │  /api, /docs
 Sistema esterno ── API con token ─────────────────┼──> backend (FastAPI, Python) ──> PostgreSQL
                                                   │        │
 Keycloak CNR (ACE) <── login e verifica token ────┘        └──> endpoint discovery di ogni
                                                                 integrazione (HTTP GET)
```

| Componente | Ruolo |
|---|---|
| **Frontend** | Builder dei modelli, area di amministrazione, documentazione. Non ha logica di autorizzazione propria: mostra ciò che il backend autorizza. |
| **Backend** | API, autorizzazione, lettura del discovery, validazione, impaginazione e generazione del PDF, registri. |
| **PostgreSQL** | Configurazione, modelli e versioni, policy, registri. Le migrazioni sono applicate dal backend all'avvio. |
| **Keycloak CNR (ACE)** | Autentica utenti e sistemi; il token porta i contesti e i ruoli per contesto. |
| **Endpoint discovery** | Uno per integrazione, esposto dal sistema esterno: descrive il suo dominio. |

Il backend accede al discovery attraverso una **porta** (`PortaDiscovery`) con un
adattatore HTTP: il resto del codice non sa da dove arriva l'albero. L'albero
letto è tenuto in memoria per poco tempo e non diventa mai una tabella locale.

## 3. Modello concettuale

```text
Contesto (es. "geban")
 └─ Integrazione  ── URL discovery, profilo di accesso (ruoli, client)
     └─ Tipo documento (es. BANDO_CONCORSO)         ┐
         └─ Albero di categorizzazione, profondità  │ letti dal vivo
            libera                                  │ dal discovery
             └─ Foglia ── dimensioni, campi         ┘
                 └─ Modello ── percorso + valori delle dimensioni (+ variante)
                     └─ Versione ── stato, copia dei campi, sezioni e blocchi
                         └─ Generazione ── dati ricevuti -> PDF + riga di registro
```

| Concetto | Definizione |
|---|---|
| **Contesto** | Ambito di autorizzazione. Coincide con il contesto che ACE scrive nel token (`contexts.<contesto>.roles`). È il confine di isolamento: un permesso vale solo nel suo contesto. |
| **Integrazione** | Collegamento con un sistema esterno, in un contesto. Ha l'URL del discovery, lo stato della verifica (`CONNESSO` o no) e il profilo di accesso. Un contesto può avere più integrazioni. |
| **Tipo documento** | Famiglia di documenti, dichiarata dal discovery. Appartiene a una sola integrazione. Porta la cornice di pagina (intestazione, logo, piè di pagina) e le policy delle dimensioni. |
| **Categorizzazione** | Albero di nodi `codice`/`descrizione` a profondità libera. I nomi dei livelli (tipologia, profilo, area…) sono informativi. |
| **Foglia** | Nodo terminale. Dichiara le **dimensioni** (liste di valori, es. lingua, livello) e i **campi** (il contratto dati). |
| **Dimensione** | Attributo che distingue più modelli sulla stessa foglia. La policy, per tipo documento, decide se un valore è obbligatorio o se un modello può valere per tutti (ripiego "generico"). |
| **Modello** | Documento di una foglia, identificato da percorso, valori delle dimensioni ed eventuale **variante**. Una **edizione derivata** è lo stesso modello in un'altra lingua, collegata all'originale. |
| **Versione** | Contenuto di un modello: copia dei campi scelti, sezioni e blocchi nel formato chiuso [GEMODO_DOCUMENT_V1](formato-documentale.md), stato del ciclo di vita. |
| **Generazione** | Una chiamata che produce un PDF da una versione pubblicata e dai dati ricevuti. |

### Ciclo di vita di una versione

```text
BOZZA ──> IN_REVISIONE ──> APPROVATO ──> PUBBLICATO ──> SOSPESO ──> ARCHIVIATO
            │                               │
            └──> BOZZA                      └──> ARCHIVIATO
```

Per una stessa combinazione (tipo, percorso, dimensioni, variante) c'è al
massimo una versione `PUBBLICATO`: pubblicarne una nuova archivia la precedente.
Si genera solo da versioni pubblicate.

## 4. Cosa GEMODO conserva e cosa legge dal vivo

| Dato | Dove | Perché |
|---|---|---|
| Albero, dimensioni, campi | **Dal vivo**, dal discovery, a ogni operazione | La fonte di verità è il sistema esterno ([ADR 0001](adr/0001-ownership-dati-esterni-e-onboarding-contesti.md)). |
| Integrazioni, accessi, policy, cornice | Database | Configurazione di GEMODO. |
| Modelli e versioni | Database | Prodotto di GEMODO. |
| Campi di una versione | Database, **copia** al momento della creazione | Un documento generato oggi resta riproducibile anche se domani il sistema esterno cambia i campi. |
| PDF generati | **Non conservati** | Li conserva chi li chiede. |
| Registro generazioni | Database | Chi, quando, quale chiave, quale versione, impronte dei dati e del PDF, riferimento documentale. Senza riga di registro il PDF non esce (`503`). |
| Registro attività | Database | Operazioni di gestione, configurazione, validazioni, accessi negati. |

Il riferimento documentale di ogni generazione è restituito nell'header
`X-Riferimento-Documentale` e scritto nei metadati del PDF.

## 5. Modularità: cosa si aggiunge senza scrivere codice

È il punto centrale dell'architettura. Ogni riga sotto è una configurazione o
un cambiamento lato sistema esterno, non uno sviluppo in GEMODO.

| Esigenza | Come si ottiene | Chi |
|---|---|---|
| Un nuovo sistema esterno | Nuova integrazione: URL del discovery, verifica, profilo di accesso | Amministratore |
| Un nuovo contesto (altro ente, altro ufficio) | Integrazione con un nuovo "nome del contesto nel token"; ACE assegna quel contesto agli utenti | Amministratore + ACE |
| Un nuovo tipo di documento | Il sistema esterno lo aggiunge al proprio discovery (una nuova chiave nella risposta) | Sistema esterno |
| Una categorizzazione diversa (più livelli, altri nomi) | Il sistema esterno cambia l'albero: la profondità è libera | Sistema esterno |
| Una nuova dimensione (es. area geografica) | Una nuova lista sulla foglia; l'amministratore ne imposta la policy | Sistema esterno + amministratore |
| Nuovi campi o cambi di obbligatorietà | Il sistema esterno cambia i campi; valgono per le nuove versioni | Sistema esterno + gestore |
| Un nuovo testo o impaginazione | Nuova versione del modello | Gestore |
| Intestazione e piè di pagina | Cornice per tipo documento | Gestore o amministratore |
| Gruppi di dati ripetuti nello stesso documento | Campo ripetibile, contratto 0.8.0, [spec 014](contratto-dati.md#campi-ripetibili-080) | *Proposto, non ancora disponibile* |

La logica di GEMODO non dipende da nomi di tipi documento, di livelli, di
dimensioni o di campi: li riceve. Nel codice compaiono solo come valori di
esempio nella documentazione delle API. I due nomi storici (`lingua`,
`livello_professionale`) restano solo come alias di lettura e come policy di
ripiego.

Esempi:

- **Un tipo in più nello stesso sistema.** GEBAN aggiunge
  `CONTRATTO_COLLABORAZIONE` al proprio discovery, accanto a `BANDO_CONCORSO`.
  Un discovery dichiara quanti tipi documento vuole: alla verifica successiva
  il nuovo tipo è disponibile ai gestori del contesto `geban`.
- **Un altro ufficio con un proprio sistema.** Il sistema espone il suo
  discovery nello stesso formato. L'amministratore crea l'integrazione nel
  contesto di quell'ufficio e la verifica, e i gestori di quel contesto creano i
  modelli.

Nessun rilascio di GEMODO è necessario. Il formato della risposta è in
[Contratto dati](contratto-dati.md#piu-tipi-documento-e-piu-contesti).

## 6. Sicurezza e isolamento

- **Autenticazione**: token Keycloak del realm CNR. Si verificano firma, emittente
  e scadenza; l'audience no (decisione del 2026-09-25: i client ACE non la
  portano).
- **Client ammessi**: il client di login di GEMODO e i client dichiarati nel
  profilo di accesso di ciascuna integrazione. Un client sconosciuto è rifiutato.
- **Permessi**: l'amministratore (`GEMODO_ADMIN`) è un ruolo diretto del client
  GEMODO. Gli altri permessi (`DOCUMENTI_VIEWER`, `DOCUMENTI_GENERATORE`,
  `GEMODO_MODELLI_GESTORE`) nascono **per contesto**: i ruoli che il token porta
  in `contexts.<contesto>.roles` sono tradotti dalla mappatura dell'integrazione
  di quel contesto. La mappatura si legge a ogni richiesta, quindi una revoca è
  immediata.
- **Isolamento**: un permesso ottenuto in un contesto non vale in un altro, e i
  permessi di più contesti non si sommano. Una risorsa di un altro contesto
  chiesta per identificativo risponde `404`, come se non esistesse. Una ricerca
  esplicita su un tipo documento non autorizzato risponde `403`. Nel deploy
  l'isolamento è attivo (`GEMODO_ENFORCE_CONTESTO_CONSUMATORE=true`).
- **Uscita verso i sistemi esterni**: GEMODO chiama solo destinazioni presenti in
  una lista autorizzata dal deploy; HTTP e indirizzi privati richiedono
  un'eccezione esplicita.

Dettaglio dei casi: [Matrice flussi integrazione](matrice-flussi-integrazione.md).

## 7. Generazione

1. Il sistema esterno cerca nel catalogo il modello per tipo, percorso e
   dimensioni, e ottiene `modello_versione_id`.
2. Legge i campi richiesti (con lo schema JSON per validare in anticipo).
3. Chiama `valida` (facoltativo) e `genera` con i dati.
4. GEMODO valida i dati contro la copia dei campi della versione, sostituisce i
   segnaposto, impagina con la cornice del tipo documento, scrive la riga di
   registro e restituisce il PDF.

La stessa chiave (`sistema_richiedente` + `external_context_id`) si può
rigenerare quante volte serve: ogni chiamata produce un PDF e una riga di
registro nuovi. Dettagli in [Integrare un sistema esterno](integrazione-sistema-esterno.md).

## 8. Limiti noti e lavoro aperto

| Tema | Stato |
|---|---|
| Campi ripetibili (più articolazioni nello stesso documento) | Spec `014`, proposta; decisione aperta sull'impaginazione |
| Discovery di collaudo per provare più tipi e contesti | Spec `015`, da implementare |
| Verifica amministrativa PDF/dati da registro | Rinviata a una spec futura |
| Monitoraggio continuo delle integrazioni | Rinviato a una spec futura |
| Perimetro fine per profilo dentro un contesto | Rinviato: oggi il confine è il contesto |
| Autenticazione dell'endpoint discovery | Non prevista in questa versione del contratto |
| Contratto OpenAPI per le sezioni dell'editor | Mancante, vedi [Riferimento API](riferimento-api.md) |
