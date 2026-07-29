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
- OpenAPI versionati, esempi JSON pubblicabili, catalogo errori e Swagger/ReDoc locale/test
  disponibili per le API pianificate;
- documentazione navigabile generata da repository e raggiungibile dal README;
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

## Scenario 7 - Profili integrazione e confine Keycloak/GEMODO

1. Aprire il manifest locale dei profili di integrazione.
2. Verificare che `GEBAN` sia registrato come sistema richiedente con client tecnico,
   audience attesa, ruoli/claim generali e profilo applicativo.
3. Verificare che il profilo indichi tipi documento, categorie, modelli/versioni,
   contratti e operazioni abilitate.
4. Simulare un client con token valido ma profilo GEMODO mancante o non coerente.

Expected:

- GEMODO non conserva password, segreti o credenziali dei client;
- Keycloak fornisce identita', client, audience e ruoli/claim generali;
- GEMODO applica autorizzazioni fini su profilo, modello, contratto e operazione;
- un token valido ma non associato a un profilo GEMODO coerente non abilita generazione,
  download o modifica dei modelli.

## Scenario 8 - Modello documentale controllato

1. Aprire il seed demo del modello documentale controllato.
2. Verificare che dichiari pagina, margini, regioni, blocchi ammessi, stili, asset,
   placeholder e posizionamenti controllati.
3. Verificare che siano presenti esempi per intestazione/logo, titolo, paragrafo, tabella o
   colonne e firma posizionata.
4. Verificare che non siano presenti HTML libero, CSS libero o script.

Expected:

- il modello demo usa una struttura controllata e versionata;
- logo e asset sono referenziati tramite identificativo e versione;
- placeholder e campi sono coerenti con il contratto dati;
- il builder futuro potra' manipolare la stessa struttura tramite editor visuale limitato;
- il renderer PDF usa eventuali formati tecnici intermedi senza esporre HTML/CSS libero
  all'utente.

## Scenario 9 - Documentazione API OpenAPI/Swagger/ReDoc

1. Aprire il manifest di readiness API e i contratti OpenAPI versionati.
2. Verificare che ogni API pubblica o di integrazione abbia endpoint, schemi, stati, codici
   errore, autenticazione, autorizzazioni e riferimenti agli esempi.
3. Avviare la documentazione interattiva locale/test.
4. Verificare che Swagger UI e ReDoc, o equivalenti, siano generati dalla stessa sorgente
   OpenAPI.
5. Verificare che gli esempi JSON contengano solo dati demo.

Expected:

- nessun endpoint operativo viene implementato senza OpenAPI versionato;
- esempi di successo ed errore funzionale sono leggibili e coerenti con il contratto;
- Swagger/ReDoc non divergono dal contratto versionato;
- esempi e documentazione non contengono token, secret, password, dati personali reali o URL
  ambientali sensibili.

## Scenario 10 - Documentazione navigabile e riuso PA

1. Aprire il README del repository.
2. Seguire i link verso documentazione MkDocs, project map, costituzione e feature attiva.
3. Verificare che siano leggibili fasi Spec Kit, blocchi, decisioni, vincoli, contratti API
   e quickstart.
4. Aprire la pagina di readiness open source/PA.
5. Verificare lo stato di licenza, setup, sviluppo, produzione, architettura,
   configurazione, sicurezza, contributi, segnalazione vulnerabilita', test e release.

Expected:

- un revisore trova proposta, costituzione, feature attiva, stato spec, blocchi e decisioni
  in massimo tre passaggi;
- la licenza e' tracciata come `DA_CONFERMARE` finche' non viene decisa;
- la documentazione e' in formato testuale versionabile;
- non sono richiesti documenti privati o conoscenza implicita per capire scelte e vincoli.
