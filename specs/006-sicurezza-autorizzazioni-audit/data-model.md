# Data Model: Sicurezza Autorizzazioni E Audit

## SistemaRichiedente

- `codice`: codice pubblico del sistema sorgente, ad esempio `GEBAN`.
- `nome`: descrizione leggibile.
- `stato`: `ATTIVO` o stato non operativo.
- `client_applicativi`: client Keycloak/ACE ammessi per il sistema.
- `profili_integrazione`: perimetri funzionali configurati.

**Validation rules**: `codice` unico; un sistema non attivo non autorizza chiamate.

## ClientApplicativo

- `client_id`: valore atteso nel claim `azp` o client tecnico equivalente.
- `audience_attesa`: audience obbligatoria, per GEMODO `gemodo-backend`.
- `ruoli_claim_richiesti`: ruoli GEMODO diretti richiesti/compatibili.
- `token_contexts`: contesti ACE letti dal claim `contexts`, ad esempio `geban`.
- `sistemi_abilitati`: sistemi richiedenti per cui il client e' valido.
- `stato`: stato operativo.
- `gestisce_credenziali`: indica se GEMODO deve aspettarsi gestione credenziali tecniche.

**Validation rules**: un client attivo deve avere `client_id`, audience attesa e almeno un
sistema abilitato. I client ACE possono omettere ruoli GEMODO diretti se autorizzati da
mapping di contesto.

## ProfiloDiIntegrazione

- `codice`: identificativo del profilo, ad esempio `GEBAN_RECLUTAMENTO_V1`.
- `sistema_richiedente`: riferimento a `SistemaRichiedente.codice`.
- `versione`: versione del profilo.
- `stato`: `ATTIVO` o non operativo.
- `client_ammessi`: lista di client che possono usare il profilo.
- `tipi_documento_ammessi`, `categorie_ammessi`, `tipologie_ammessi`: perimetro catalogo
  ammesso dal profilo.
- `modelli_versioni_ammessi`, `contratti_dati_ammessi`: versioni/contratti consentiti.
- `permessi_operativi`: operazioni abilitate sul profilo.
- `role_mappings`: trasformazioni da ruoli esterni a permessi GEMODO.

**Validation rules**: tutti i codici catalogo referenziati devono esistere o essere
validabili dal seed/catalogo; un profilo non attivo non produce autorizzazioni.

## ExternalRoleMapping

- `token_context`: chiave dentro `contexts`, ad esempio `geban`.
- `external_role`: ruolo esterno completo, ad esempio `ROLE_MANAGER#geban`.
- `internal_permissions`: permessi GEMODO derivati.
- `scope`: opzionale, limita il mapping a builder, generazione, consultazione o API.
- `tipi_documento`, `categorie`, `tipologie`: opzionali, limitano il mapping a un perimetro
  documentale.

**Validation rules**: nessun mapping implicito per ruoli sconosciuti; `ROLE_MANAGER#geban`
e' l'unico ruolo iniziale che puo' derivare `GEMODO_MODELLI_GESTORE`.

## PrincipalGEMODO

- `subject`: utente o service account dal token.
- `client_id`: claim `azp` o client equivalente.
- `audiences`: claim `aud` normalizzato a lista.
- `direct_roles`: ruoli GEMODO letti da `resource_access.gemodo-backend.roles`.
- `external_context_roles`: ruoli letti da `contexts.<app>.roles`.
- `roles`: permessi GEMODO normalizzati usati dai guard backend.

**Validation rules**: token scaduto, issuer errato, audience mancante, client non ammesso
o assenza di permessi richiesti producono rifiuto autenticativo/autorizzativo.
