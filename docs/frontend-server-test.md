# Collaudo frontend sul server di test

Il checkpoint disponibile copre l'area amministrativa Configurazione:
lista, creazione, configurazione e verifica delle integrazioni. E' disponibile
anche il primo flusso manager: scelta contesto, integrazione e tipo documento,
navigazione fino ai campi e creazione modello con versione in BOZZA. Il collaudo e la
review indipendente della feature non sono ancora completati.

## Deploy Coolify

Pubblicare le modifiche nel branch configurato su Coolify e ricostruire il
compose `docker-compose.coolify.yml`. Il servizio `frontend` deve usare
`frontend/Dockerfile`, target `production`, porta interna 80.

Configurare `KEYCLOAK_ISSUER_URL` e `KEYCLOAK_FRONTEND_CLIENT_ID` per il
realm di test. Nel client pubblico Keycloak abilitare Authorization Code
con PKCE e registrare il dominio HTTPS del frontend nelle redirect URI e
nelle web origin. L'utente di prova deve ricevere il ruolo client
`gemodo-backend` / `GEMODO_ADMIN` nel token.

Nel backend configurare l'origine esatta del discovery approvato in
`GEMODO_INTEGRAZIONI_ALLOWLIST`; per un servizio su rete privata usare
`GEMODO_INTEGRAZIONI_ALLOWLIST_PRIVATO`. Riavviare il backend dopo la
modifica. Non usare gli URL localhost del collaudo locale sul server.

Se una pagina esterna chiama direttamente le API GEMODO dal browser, configurare
anche `GEMODO_CORS_ALLOWED_ORIGINS` con le origini esatte, separate da virgola
e senza path, per esempio `https://geban.test.si.cnr.it`.

## Prova sulla pagina pubblicata

L'header mostra nome utente e collegamento al profilo in alto a destra;
il profilo consente logout e visualizzazione esplicita del token corrente.
La home mostra solo le aree consentite. Senza permessi operativi mostra
"Non sei autorizzato ad accedere alle funzioni di GEMODO".

1. Aprire il dominio HTTPS del frontend e completare il login.
2. Aprire Configurazione; una lista vuota e' corretta al primo utilizzo.
3. Creare un'integrazione con codice univoco, nome demo e contesto autorizzato.
4. Verificare lo stato Non verificato e salvare l'URL discovery approvato.
5. Premere Verifica: una sorgente conforme deve mostrare Connesso, data
   e versione contratto; una sorgente non conforme mostra Errore e motivi.
6. Ricaricare la pagina e confermare che configurazione e stato persistano.

Una destinazione non approvata deve essere rifiutata. Un utente senza ruolo
admin non deve vedere Configurazione e non deve accedere alla sua route.

Il discovery deve seguire il contratto ad albero completo 0.4.0;
gli esempi PER_NODI sono una proposta distinta e non sono accettati da questo MVP.

## Diagnosi autenticazione

Un 401 subito dopo login non prova che il token sia scaduto. Controllare
la presenza di Authorization nella richiesta senza condividere il token.
Nei log del backend cercare `Authentication rejected`: il messaggio riporta
Bearer assente, audience non corrispondente oppure la classe di errore JWT
(es. InvalidIssuerError, ExpiredSignatureError, ImmatureSignatureError).
La UI forza un nuovo login con prompt login; nessuna scrittura viene
ripetuta automaticamente. La causa server resta da diagnosticare se il
nuovo login produce ancora 401. Il controllo audience resta condizionale:
token ACE senza aud accettato se le altre verifiche e autorizzazioni passano.

## Prova manager

Il ruolo globale da solo non assegna un contesto: il backend verifica i
mapping configurati per il client e `contexts.<contesto>.roles` nel token.
Con un manager autorizzato, aprire Crea modello, scegliere il contesto e
una delle integrazioni connesse visibili, poi tipo documento e percorso
fino alla foglia. Compilare codice, nome e variante e creare la bozza.
L'esito BOZZA viene mostrato solo dopo la creazione della versione nel backend.
# Reset completo del database di test

Il backend include `gemodo-reset-database`, eseguibile da qualunque directory
del terminale del container. Il comando mantiene lo schema alla migration
corrente e svuota tutte le tabelle applicative, compresi audit e dati demo.

1. Impostare in Coolify `GEMODO_ALLOW_DATABASE_RESET=true` per il servizio.
2. Ridistribuire il backend affinche' comando e variabile siano presenti.
3. Aprire il terminale del container `backend` ed eseguire:

```bash
gemodo-reset-database RESET-GEMODO
```

Il comando deve terminare mostrando `0` per integrazioni, tipi documento e
modelli. Riavviare quindi il backend da Coolify. Al termine della prova,
reimpostare `GEMODO_ALLOW_DATABASE_RESET=false` e ridistribuire.
