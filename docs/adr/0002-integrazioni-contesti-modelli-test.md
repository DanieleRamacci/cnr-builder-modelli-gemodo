# ADR 0002 - Integrazioni, Contesti E Modelli Di Test

Data: 2026-09-17. Stato: confermato dall'utente; implementazione da pianificare
nei task della feature attiva 010 e successivamente nelle spec owner.

## Decisione

L'integrazione rappresenta il software sorgente, non un singolo tipo documento.
L'elenco admin parte vuoto: GEBAN e' un esempio, mai una voce preinstallata,
dedotta dal token, dal seed dei modelli o da un URL di ambiente.

L'admin crea una risorsa con identificativo stabile, codice interno univoco,
nome visualizzato, codice_contesto e un URL discovery opzionale fino alla
configurazione completa. Modalita' iniziale: SINGOLO_ENDPOINT. Non si
implementano registri di URL per livello o navigazione PER_NODI in questo MVP.
La paginazione trasparente del singolo discovery rimane un dettaglio di trasporto.

Il codice_contesto corrisponde esattamente alla chiave contexts.<codice_contesto>
del JWT. Non e' derivato dal nome visualizzato, non assegna ruoli o contesti
agli utenti, non sostituisce client/audience e mapping autorizzativi della 006.
Un manager accede solo alle integrazioni connesse nei contesti dove possiede
il permesso necessario. Due contesti con permesso di gestione consentono
accesso a entrambi; un permesso in uno non si propaga all'altro.

## Verifica E Discovery

L'admin avvia Verifica. GEMODO controlla URL approvato, raggiungibilita',
limiti di trasporto e forma comune dell'intera mappa discovery: tipo documento
-> nodi ricorsivi -> figli oppure campi della foglia. Tutti i tipi restituiti
sono verificati, non solo BANDO_CONCORSO. Valori, nomi e profondita' possono
differire dagli esempi; un esempio generato non e' necessario per connettere.
Le definizioni dei campi non contengono i valori da stampare.

Stati: DEFINITO, CONNESSO, ERRORE. Sono visibili data, esito e motivi sanificati.
Un test fallito non conserva un precedente successo come esito corrente.
Cambiare l'URL richiede una nuova verifica; una verifica contro una revisione
di configurazione superata non puo' abilitare la nuova configurazione.
La modifica di un esempio illustrativo non disconnette un'integrazione:
conta la versione della forma comune, non i valori dell'esempio.

Un endpoint puo' restituire piu' tipi documento sotto lo stesso contesto.
L'identita' esterna e' integrazione_id + codice_tipo_documento + percorso_codici.
Lo stesso codice in due integrazioni non implica gli stessi dati o permessi.
Il catalogo esterno resta in memoria; nel DB persistono integrazione, esiti,
modelli GEMODO e solo i riferimenti/contratti necessari alle loro versioni.

## Percorso Manager E PDF Di Test

Il manager sceglie contesto/integrazione, tipo documento e percorso fino alla
foglia, vede proprieta' e campi, quindi crea un modello di test in BOZZA.
Non puo' modificare il catalogo sorgente o configurare URL/contesti dell'admin.
Il primo rendering e' un PDF semplice: titolo, etichette e valori nell'ordine
configurato. La struttura documentale minima e' generata automaticamente e
versionata, non un template vivo o una nuova architettura alternativa.
L'editor visuale e' rinviato. Frontend: Angular con Design Angular Kit.

Il modello di test segue il normale workflow: per le API di generazione deve
essere pubblicato; crearlo non equivale a pubblicarlo. Il PDF e' non ufficiale,
riconoscibile come TEST, e non costituisce un bando impaginato pronto all'uso.
Il chiamante deve possedere i permessi di generazione previsti dalla 006:
un ruolo di gestione non attribuisce implicitamente generazione ufficiale.

I valori arrivano nella richiesta di generazione (o come valori demo nella
prova), mai dal discovery. La validazione usa il contratto immutabile della
versione: campi obbligatori, tipi, vincoli e presenza dei campi selezionati.
Un opzionale usato dal modello ma omesso dalla richiesta genera errore;
obbligatorieta' nel catalogo e presenza richiesta dal modello sono distinte.
La policy sugli opzionali non usati e sui campi sconosciuti va resa esplicita
nel contratto 001 prima del runtime: il contratto corrente rifiuta gli extra.

Storage, riferimento recuperabile, download autorizzato e retry seguono la
005, anche per il PDF di test. Una prova non puo' essere restituita come
documento ufficiale attraverso un retry o una consultazione.

## Owner E Sequenza

- 010: integrazione, endpoint, verifica della forma comune e stato.
- 002: selezione autorizzata, creazione/versione e pubblicazione del modello.
- 001: catalogo GEMODO esposto al consumatore e validazione dei valori.
- 003: struttura minima automatica/versionata e placeholder dei campi scelti.
- 004: PDF di test e generazione reale; nessun bypass del workflow.
- 005: file, riferimento, download e idempotenza.
- 006: client, JWT, ruolo per contesto, permessi e audit sicurezza.
- 007: sezioni admin e manager, navigazione e stati UI.

La feature attiva resta 010. Le modifiche alle spec owner propagano questa
decisione, ma non ne avviano i task o il codice senza cambio feature autorizzato.
Review esterna, hash/runner periodico e relative soglie restano rinviati:
la verifica strutturale e la validazione dei valori non certificano che un
modello sia allineato a successive modifiche del catalogo.
