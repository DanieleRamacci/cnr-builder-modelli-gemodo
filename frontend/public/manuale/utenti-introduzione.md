# Introduzione a GEMODO

GEMODO è il servizio del CNR che gestisce i **modelli di documento** e li usa
per **generare documenti PDF** a partire dai dati inviati da un altro sistema.
Non è legato a un tipo di documento: bandi, avvisi, contratti o altro, purché un
sistema ne descriva la struttura.

In breve:

1. un sistema esterno (un'**integrazione**) dichiara come è organizzato il suo
   dominio: tipi di documento, categorie e i dati che servono;
2. chi gestisce i modelli scrive il testo del documento e ci inserisce i
   **segnaposto**, cioè i punti in cui andranno i dati;
3. il modello viene revisionato, approvato e pubblicato;
4. il sistema esterno invia i dati e riceve il PDF.

## Accesso

Si entra con le credenziali CNR. Quello che si vede dipende dai permessi
assegnati nel proprio **contesto**: per esempio `geban` per i bandi gestiti con
GEBAN. Un permesso vale solo nel contesto in cui è assegnato.

| Permesso | Cosa consente |
|---|---|
| Amministratore (`GEMODO_ADMIN`) | Configura integrazioni, tipi documento, policy delle dimensioni e cornice di pagina |
| Gestore modelli (`GEMODO_MODELLI_GESTORE`) | Crea e compone i modelli, ne chiede l'anteprima, li porta in revisione e li pubblica |
| Generatore (`DOCUMENTI_GENERATORE`) | Genera documenti dai modelli pubblicati (di solito un sistema, non una persona) |
| Consultazione (`DOCUMENTI_VIEWER`) | Consulta il catalogo dei modelli pubblicati e i dati che ciascuno richiede (di solito un sistema). Non c'è un archivio dei documenti generati: GEMODO non conserva i PDF |

Nella pagina **Profilo** (in alto a destra, sul proprio nome) si vede, contesto
per contesto, cosa si può fare in GEMODO.

## Il menu in alto

| Voce | Chi la vede | A cosa serve |
|---|---|---|
| **Contesti** | gestori e amministratori | Scegliere il contesto su cui lavorare |
| **Modelli** | gestori | Elenco dei modelli, creazione e pubblicazione |
| **Impostazioni** | amministratori | Integrazioni, profili di accesso, dimensioni, verifica degli endpoint |
| **Registro attività** | amministratori | Chi ha fatto cosa e quando |
| **Documentazione** | tutti | Questa guida e la documentazione tecnica |

Le voci che non riguardano il proprio ruolo non compaiono.

## Parole che ricorrono

- **Contesto**: l'ambito applicativo a cui appartengono integrazioni e modelli,
  per esempio `geban`.
- **Integrazione**: il collegamento con un sistema esterno. GEMODO ne legge la
  struttura dal vivo a ogni operazione.
- **Tipo documento**: per esempio `BANDO_CONCORSO`.
- **Categorizzazione**: il percorso nell'albero del sistema esterno fino a una
  **foglia**, per esempio tipologia "Tempo Determinato", poi profilo
  "Ricercatore". La foglia dichiara i campi del documento.
- **Dimensione**: un valore che distingue più modelli sulla stessa foglia, per
  esempio la lingua o il livello.
- **Campo** e **segnaposto**: un dato richiesto dal modello, come
  `codice_bando`. Nel testo si inserisce come segnaposto e alla generazione
  viene sostituito dal valore.
- **Versione**: ogni modello ha versioni che passano da bozza a pubblicata. Si
  generano documenti solo da versioni pubblicate.

## Il primo caso: i bandi di GEBAN

Oggi GEMODO è collegato a **GEBAN** per i **bandi di concorso**: contesto
`geban`, tipo documento `BANDO_CONCORSO`, categorizzazione per tipologia (per
esempio "Tempo Determinato") e profilo (per esempio "Ricercatore"), con lingua e
livello come dimensioni. Gli esempi di questa guida usano spesso questi valori.
Un altro ufficio o sistema si aggiunge allo stesso modo, con il proprio contesto
e i propri tipi di documento. Dettagli: [Caso GEBAN](../casi/geban.md).

## Dove andare adesso

- Chi scrive i modelli: [Creare e pubblicare un modello](modelli.md).
- Chi configura il servizio: [Amministrare integrazioni e contesti](amministrazione.md).
- Chi vuole capire come è fatto il sistema: [Architettura e modularità](../architettura.md).
- Chi integra un sistema esterno: [Integrare un sistema esterno](../integrazione-sistema-esterno.md)
  e, per provare le chiamate, [Riferimento API](../riferimento-api.md).
