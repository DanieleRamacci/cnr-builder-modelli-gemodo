# Collaudo frontend sul server di test

Il checkpoint disponibile copre l'area amministrativa Configurazione:
lista, creazione, configurazione e verifica delle integrazioni. Il flusso
manager di creazione modello non e' ancora disponibile. Il collaudo e la
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

## Prova sulla pagina pubblicata

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
