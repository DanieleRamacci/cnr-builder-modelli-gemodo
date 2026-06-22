# Quickstart - Sezioni Placeholder E Versionamento

Questa guida descrive gli scenari minimi per validare la feature 003 dopo
l'implementazione. Non sostituisce i test automatici.

## Prerequisiti

- backend FastAPI avviato;
- database PostgreSQL migrato;
- esiste una versione modello in stato `BOZZA`;
- la versione modello ha campi/placeholder disponibili, ad esempio `NUM_POSTI`, `PROFILO`
  e `SEDI`.

## Scenario 1 - Sezione propria della versione modello

1. Aggiungere una sezione alla versione modello in bozza.
2. Modificare testo, ordine e obbligatorieta'.
3. Pubblicare o simulare pubblicazione della versione modello.
4. Tentare una modifica diretta della sezione pubblicata.

Expected:

- la sezione viene salvata nella versione modello;
- la bozza e' modificabile;
- la versione pubblicata non consente modifiche dirette alle sezioni.

## Scenario 2 - Copia sezioni su nuova versione modello

1. Partire da una versione modello con sezioni gia' definite.
2. Creare una nuova versione modello derivata.
3. Verificare che le sezioni siano copiate nella nuova versione.
4. Modificare una sezione nella nuova bozza.

Expected:

- la nuova versione contiene una copia delle sezioni precedenti;
- modificare la nuova bozza non altera la versione precedente.

## Scenario 3 - Template sezione copiabile

1. Creare un template sezione attivo.
2. Usarlo per aggiungere una sezione a una versione modello.
3. Modificare successivamente il template.

Expected:

- il contenuto viene copiato nella versione modello;
- l'aggiornamento del template non modifica la sezione gia' copiata.

## Scenario 4 - Validazione placeholder

1. Associare alla versione modello i placeholder `NUM_POSTI` e `PROFILO`.
2. Creare una sezione con `{{NUM_POSTI}}` e `{{PROFILO}}`.
3. Validare sezioni e placeholder.
4. Inserire poi `{{PROFILLO}}` con errore di battitura e validare di nuovo.

Expected:

- la prima validazione passa;
- la seconda validazione fallisce con `PLACEHOLDER_NON_DISPONIBILE`.

## Scenario 5 - Campo complesso con schema esplicito

1. Definire il campo complesso `SEDI`.
2. Associare uno schema con sotto-campi `citta`, `indirizzo` e `posti`.
3. Validare un payload coerente.
4. Validare un payload con sotto-campo non previsto.

Expected:

- il payload coerente passa;
- il sotto-campo non previsto fallisce con errore stabile.

## Scenario 6 - Sezioni condizionali fuori perimetro

1. Provare a definire una sezione visibile solo se un campo del payload assume un valore.

Expected:

- la configurazione condizionale viene rifiutata o non proposta;
- le sezioni inserite sono considerate sempre presenti.
