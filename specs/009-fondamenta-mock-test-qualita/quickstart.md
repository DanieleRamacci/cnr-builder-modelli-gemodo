# Quickstart - Fondamenta Mock Test E Qualita

Questa guida descrive come validare la feature `009` dopo l'implementazione dei task.
Non sostituisce i test automatici e non richiede accesso a GEBAN reale.

## Prerequisiti

- ambiente locale documentato;
- backend, frontend, PostgreSQL, Keycloak, documentale mock e mock GEBAN disponibili;
- migrations applicate;
- seed demo caricati e marcati come `DEMO`;
- contratti pubblici disponibili per catalogo, campi/schema, validazione, generazione,
  stato e download;
- registro decisioni aperte aggiornato.

## Scenario 1 - Verifica ambiente locale

1. Avviare l'ambiente locale seguendo la documentazione di setup.
2. Eseguire la verifica ambiente.
3. Controllare che tutti i servizi obbligatori risultino disponibili.

Expected:

- backend, frontend, PostgreSQL, Keycloak, documentale mock e mock GEBAN sono raggiungibili;
- eventuali servizi mancanti sono segnalati come prerequisiti non soddisfatti;
- nessun test richiede accesso al DB GEBAN.

## Scenario 2 - Migrations e seed demo

1. Applicare le migrations su database locale pulito.
2. Caricare i seed demo.
3. Verificare presenza di tipo documento, categoria, modello pubblicato demo, payload
   valido e payload non valido.

Expected:

- le entita' principali richieste dalle spec sono create;
- tutti i seed sono marcati come demo;
- nessun seed contiene dati reali o sensibili;
- esiste almeno un modello pubblicato utilizzabile dal mock GEBAN.

## Scenario 3 - Mock GEBAN flusso valido

1. Usare il mock GEBAN per consultare catalogo e modello pubblicato demo.
2. Richiedere campi/schema del modello.
3. Inviare payload demo valido.
4. Richiedere generazione e consultare stato.

Expected:

- il mock usa solo contratti pubblici;
- il payload viene validato;
- la generazione viene tracciata;
- lo stato contiene informazioni coerenti con versione modello, tipo output e riferimento
  quando disponibile.

## Scenario 4 - Errori funzionali e idempotenza

1. Inviare payload demo non valido.
2. Ripetere una generazione valida con stessa chiave e stessi dati.
3. Ripetere una generazione con stessa chiave e dati divergenti.

Expected:

- il payload non valido produce errore funzionale;
- retry identico restituisce generazione esistente;
- retry divergente produce conflitto;
- conflitto e fallimenti rilevanti sono auditabili.

## Scenario 5 - Accesso non autorizzato

1. Usare un ruolo o contesto non autorizzato per consultare stato o download.
2. Verificare risposta e audit.

Expected:

- stato/download non espongono file, payload o dettagli non consentiti;
- l'accesso viene rifiutato;
- l'evento autorizzativo e' previsto dalla matrice di audit.

## Scenario 6 - Matrice copertura e decisioni aperte

1. Aprire il manifest di qualita' conforme a
   [contracts/quality-readiness-contract.yaml](./contracts/quality-readiness-contract.yaml).
2. Verificare che ogni scenario minimo sia collegato a spec owner, requisito e contratto.
3. Verificare che ogni decisione critica abbia stato, owner, assunzione provvisoria e fase
   bloccante.

Expected:

- nessuna decisione critica entra nei task come assunzione silenziosa;
- gli scenari minimi coprono valido, payload non valido, retry idempotente, conflitto,
  fallimento e accesso non autorizzato;
- le parti bloccate da decisioni aperte sono esplicite.
