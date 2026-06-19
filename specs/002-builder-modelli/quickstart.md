# Quickstart - Builder Modelli Documentali

Questa guida descrive gli scenari minimi per validare la feature 002 dopo
l'implementazione. Non sostituisce i test automatici.

## Prerequisiti

- backend avviato con database PostgreSQL migrato;
- utente o client autorizzato alle API interne builder;
- seed minimo con tipo documento `BANDO_CONCORSO` e categoria `CTER`.

## Scenario 1 - Creazione modello con variante default

1. Creare un modello senza indicare `variante`.
2. Verificare che la risposta contenga `variante: "STANDARD"`.
3. Creare una prima versione del modello.

Expected:

- il modello viene creato;
- la variante `STANDARD` e' persistita;
- la versione parte in stato `BOZZA`.

## Scenario 2 - Variante duplicata nello stesso contesto

1. Creare un modello `BANDO_CTER_TI` con tipo `BANDO_CONCORSO`, categoria `CTER`,
   tipologia `TI`, variante `STANDARD`.
2. Provare a creare un secondo modello con la stessa combinazione
   tipo/categoria/tipologia/variante.

Expected:

- la seconda richiesta fallisce con errore di conflitto;
- il sistema evita ambiguita' nel catalogo operativo.

## Scenario 3 - Modifica di versione pubblicata

1. Portare una versione da `BOZZA` a `IN_REVISIONE`, poi `APPROVATO`, poi `PUBBLICATO`.
2. Provare ad aggiornare direttamente il contenuto della versione pubblicata.
3. Creare invece una bozza derivata dalla versione pubblicata.

Expected:

- l'update diretto della versione pubblicata fallisce;
- la bozza derivata viene creata in stato `BOZZA`;
- la versione pubblicata originale resta invariata.

## Scenario 4 - Pubblicazione nuova versione della stessa variante

1. Partire da una versione `PUBBLICATO` della variante `STANDARD`.
2. Creare bozza derivata, approvarla e pubblicarla.
3. Verificare lo stato della versione precedente.

Expected:

- la nuova versione diventa `PUBBLICATO`;
- la precedente versione pubblicata della stessa variante passa automaticamente ad
  `ARCHIVIATO`;
- il catalogo operativo della 001 vede una sola versione pubblicata corrente per variante.

## Scenario 5 - Varianti diverse nello stesso contesto

1. Creare una variante `STANDARD` e una variante `FIRMA_PRESIDENTE` per lo stesso
   tipo/categoria/tipologia.
2. Pubblicare una versione corrente per ciascuna variante.

Expected:

- entrambe le varianti possono essere pubblicate;
- ogni variante ha una sola versione `PUBBLICATO` corrente;
- la scelta operativa resta basata su `modello_versione_id`.
