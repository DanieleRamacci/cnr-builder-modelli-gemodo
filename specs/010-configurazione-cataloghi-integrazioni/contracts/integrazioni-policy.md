# Policy Del Contratto Integrazioni - T078

Stato: design, non runtime. Contratto: [OpenAPI](integrazioni-api.openapi.yaml).

## Identita' E Accesso

Codice software univoco e contesto esatto, immutabili nel primo incremento:
una modifica di proprieta' richiede procedura esplicita fuori dal CRUD iniziale.
Due integrazioni possono appartenere allo stesso contesto; le loro identita'
esterne restano distinte. I manager leggono solo CONNESSE autorizzate nel
contesto tramite mapping 006, senza unione dei permessi multicontesto.
Il ruolo diretto non scavalca lo scope; valgono 001 FR-034..FR-038 e 006
FR-014..FR-017. Nessuna assegnazione di ruoli dall'admin integrazioni.

## Destinazioni HTTP

La registrazione in UI non approva una destinazione. La policy egress del
deployment contiene allowlist esplicita di origin HTTPS e percorsi consentiti;
default vuota, nessuna chiamata finche' una destinazione non e' approvata.
URL senza userinfo, fragment, credenziali o query con segreti. Nessun redirect.
Link HAL devono restare nell'origin e nei percorsi approvati; rifiutare cicli.

Controllare tutti gli IP risolti prima di ogni richiesta e vincolare la
connessione alla risoluzione verificata, mantenendo TLS hostname validation:
il solo controllo DNS seguito da nuova risoluzione non protegge dal rebinding.
Negare loopback, link-local, multicast, indirizzi non specificati e metadata
cloud. Destinazioni private richiedono eccezione di deployment esplicita e
egress firewall/proxy; nessuna eccezione implicita per un host chiamato geban.
HTTP e server locali ammessi solo in fixture di test isolate, non in produzione.

Primo incremento: sorgenti senza autenticazione applicativa aggiuntiva,
TLS sempre verificato; non inoltrare JWT ACE, cookie o header del chiamante.
Sorgenti che richiedono credenziali sono non supportate finche' non esiste un
contratto per secret reference gestita dal deployment; mai token inseriti nell'URL.

Budget complessivo massimo 10 secondi; timeout configurato 1..10 secondi
include tutte le pagine e lettura body. Limiti cumulativi iniziali riusano
il contratto discovery comune: 2 MiB JSON decompresso complessivi, 64 pagine,
64 livelli; streaming, limiti anche dopo decompressione,
nessun caricamento illimitato prima del controllo dimensioni.

## Verifica E Concorrenza

Verifica sincrona, senza cache, su tutta la mappa non vuota e tutti i rami.
Non confronto con codici, profondita' o valori degli esempi US1/US2.
L'esito contiene versione forma comune, revisione e data, non catalogo/body.
Errore strutturale o di trasporto -> ERRORE corrente; successo -> CONNESSO.
Rifiuto input/URL prima di HTTP non e' un test riuscito.

Una verifica attiva per integrazione: seconda richiesta concorrente -> 409.
Prenotazione atomica con scadenza e identificativo tentativo; nessuna transazione
DB aperta per tutta la chiamata HTTP. Risultato applicabile solo se tentativo e
revisione sono ancora correnti, altrimenti 409 senza cambiare stato. Registrare
il tentativo superato solo nell'audit; crash non lascia un lock permanente.
Cambio URL/timeout rimuove l'esito corrente, passa a DEFINITO e invalida cache;
lo storico resta nell'audit. Cambio nome conserva l'esito precedente, ma rende
superato un test ancora in corso. Esempi modificati non disconnettono.

## Letture Live E Compatibilita'

Prima di HTTP verificare scope e stato; RAM/cache per integrazione e revisione,
mai catalogo DB. Radici e struttura provengono dallo stesso adapter comune.
Le nuove route mappano errori di trasporto/conformita' su 502 e budget scaduto
su 504, non array vuoto; il precedente adapter usa 503 per indisponibilita'.
T080 deve mappare esplicitamente i suoi errori senza cambiare silenziosamente
la semantica delle route precedenti. Un errore di lettura live
non aggiorna automaticamente lo stato dell'ultimo test amministrativo.
La cache non attesta allineamento dei modelli: hash/runner restano rinviati.

Nuove route sono additive e pianificate; API tipi/esempi rimangono opzionali.
Durante T079-T082 rimuovere registrazione/verifica endpoint per tipo e resolver
env; non mantenere due sorgenti operative. Associazione legacy manuale prima
della nuova verifica, preservando ID e storico. Le route builder precedenti
devono risolvere una sorgente registrata non ambigua o rifiutare, senza fallback.
Per route legacy con solo codice tipo: selezione solo fra sorgenti CONNESSE
autorizzate al chiamante; zero corrispondenze -> 404 sanificato, piu' di una
-> 409 SORGENTE_AMBIGUA senza dettagli di sorgenti non autorizzate.
Le route nuove usano integrazioneId e codice espliciti. UUID/public_id dei
modelli rimangono invariati; API consumatore basate su ID ricavano proprieta'
dal modello. API admin esempi identificate dal solo codice richiedono
adeguamento del contratto precedente prima di consentire codici duplicati.
Nessuna deprecazione pubblica o migrazione DB viene eseguita da questo documento.

## Prove Richieste

T084 copre lista vuota, due radici, radice/ramo invalido, assenza di esempi,
concorrenza e scadenza tentativi, modifiche nome/URL durante HTTP, disconnessione,
token multicontesto, URL privati/metadata/redirect/rebinding, limiti compressi,
HAL ciclico e isolamento dei metadati admin. Nessun test verso GEBAN reale.
Le prove consumatore su modello ID, validazione e generazione restano owner
001/006 e sono bloccanti prima dell'uso operativo delle relative API.
