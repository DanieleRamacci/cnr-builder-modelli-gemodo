# Accesso utenti tramite contesti ACE

Stato: confermato dall'utente il 2026-09-18. Implementazione tracciata in
specs/007-frontend-builder-consultazione/tasks.md, FR-006/FR-023.

Gli utenti accedono a GEMODO con un client interattivo autorizzato e un mapper
ACE che inserisce `contexts.<contesto>.roles` nell'access token. Non devono
ricevere ruoli GEMODO aggiuntivi in Keycloak. `azp` identifica il client di
login, non il contesto su cui la persona puo' lavorare.

GEMODO valida il token e il client chiamante, quindi applica i role_mappings
dei sistemi e profili attivi. Per i client in GEMODO_ALLOWED_INTERACTIVE_CLIENTS
non richiede l'iscrizione in client_applicativi/client_ammessi di ogni
integrazione. Queste liste restano vincolanti per i client esterni/tecnici e
le autorizzazioni operative dei profili di generazione.

Per GEBAN, ROLE_MANAGER#geban concede gestione modelli solo in geban;
ROLE_USER#geban non concede gestione modelli. Nessun permesso viene derivato
automaticamente dal nome di un ruolo non configurato o da un contesto sconosciuto.
Firma, issuer, scadenza e controllo audience dichiarata restano invariati.
GEMODO_ADMIN non viene derivato dai ruoli ACE: amministrazione del registro
integrazioni e gestione modelli sono funzioni distinte.

## Onboarding di altre integrazioni

1. Configurare il mapper ACE sul client di login per i contesti richiesti.
2. Registrare l'integrazione con codice_contesto esattamente uguale alla chiave ACE.
3. Configurare role_mappings espliciti per quel contesto in un sistema/profilo attivo.
4. Verificare l'endpoint discovery fino allo stato CONNESSO.
5. Verificare con token multicontesto che i permessi non passino tra contesti.

Il mapper da solo non abilita contesti nuovi senza mapping backend. Il client
frontend si configura una volta nella allowlist interattiva, non in ogni profilo.
Non inoltrare i token utente agli endpoint discovery esterni.
