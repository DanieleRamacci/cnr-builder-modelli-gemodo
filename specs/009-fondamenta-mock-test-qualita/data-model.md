# Data Model - Fondamenta Mock Test E Qualita

Questa feature non introduce dominio amministrativo finale; definisce artefatti di
supporto per ambiente, mock, seed, copertura, profili di integrazione, modelli documentali
controllati e decisioni aperte. Le entita' sotto sono persistibili o versionabili come
configurazioni/manifest di qualita'.

## Entities

### AmbienteLocale

Insieme dei servizi minimi necessari per sviluppo e verifica.

Fields:

- `id`: identificativo ambiente, ad esempio `local-dev`.
- `servizi`: elenco di `ServizioLocale`.
- `profilo`: `MINIMO`, `COMPLETO`, `CI`.
- `stato_atteso`: servizi che devono risultare disponibili.
- `documentazione_setup`: riferimento alla guida di avvio.

Validation:

- deve includere almeno backend, frontend, PostgreSQL, Keycloak e documentale mock.
- deve dichiarare prerequisiti e comandi di verifica.
- non deve richiedere accesso a GEBAN reale.

### ServizioLocale

Servizio componente dell'ambiente.

Fields:

- `nome`: backend, frontend, postgres, keycloak, documentale-mock, mock-geban.
- `categoria`: `APP`, `DATABASE`, `IDENTITA`, `STORAGE`, `MOCK`, `DOCS`.
- `healthcheck`: comando o endpoint di verifica.
- `dipendenze`: altri servizi richiesti.
- `obbligatorio`: boolean.

Validation:

- ogni servizio obbligatorio deve avere una verifica di disponibilita'.
- un servizio non disponibile deve produrre errore di prerequisito, non errore applicativo.

### MigrationSet

Gruppo di migrations necessarie per schema iniziale coerente.

Fields:

- `id`
- `versione`
- `entita_coperte`
- `spec_owner`
- `stato`: `PREVISTA`, `APPLICATA`, `FALLITA`.

Validation:

- deve coprire tipi, categorie, modelli, versioni, campi, sezioni, generazioni e audit.
- ogni entita' deve puntare a una spec owner.

### SeedDemo

Dati iniziali ripetibili per mock e test.

Fields:

- `id`
- `nome`
- `tipo`: `CATALOGO`, `MODELLO`, `SEZIONI`, `PAYLOAD`, `UTENTI_RUOLI`, `GENERAZIONE`.
- `marcatura_demo`: valore obbligatorio che indica dato non reale.
- `spec_owner`
- `resettable`: boolean.
- `dati_sensibili`: deve essere `false`.

Validation:

- ogni seed deve essere marcato come demo.
- nessun seed puo' contenere dati reali o sensibili.
- deve esistere almeno un modello pubblicato demo e un caso non valido/non pubblicabile.

### MockGEBAN

Simulatore del sistema chiamante.

Fields:

- `id`
- `contratti_usati`
- `scenari_supportati`
- `payload_demo`
- `modalita_autenticazione`

Validation:

- deve usare contratti pubblici, non API interne o accesso diretto ai dati.
- deve coprire catalogo, campi/schema, validazione, generazione, stato e download.

### ContrattoOpenAPI

Specifica versionata di una API pubblica, di integrazione o interna rilevante.

Fields:

- `id`
- `nome`
- `versione`
- `file_ref`: percorso del file OpenAPI versionato.
- `api_scope`: `GEBAN`, `BUILDER`, `ADMIN`, `INTERNO`.
- `endpoint_coperti`
- `schemi_coperti`
- `autenticazione`: requisiti JWT/OIDC o `N/A`.
- `autorizzazioni`: ruoli, claim o profili GEMODO richiesti.
- `esempi`: elenco di `EsempioAPI`.
- `catalogo_errori_ref`
- `documentazione_interattiva`: Swagger UI, ReDoc o equivalente.
- `spec_owner`

Validation:

- ogni endpoint pubblico o di integrazione deve essere presente in almeno un contratto.
- il contratto deve essere creato prima dell'implementazione runtime dell'endpoint.
- Swagger/ReDoc devono essere generati dalla stessa sorgente OpenAPI versionata.
- stati, campi e codici errore pubblici devono essere coerenti con esempi e catalogo errori.

### EsempioAPI

Payload o risposta dimostrativa pubblicabile.

Fields:

- `id`
- `contratto_openapi`
- `scenario`: successo, errore validazione, non autorizzato, conflitto, fallimento.
- `request_ref`
- `response_ref`
- `dati_demo`: deve essere `true`.
- `contiene_segreti`: deve essere `false`.
- `contiene_dati_reali`: deve essere `false`.

Validation:

- ogni esempio deve usare solo dati demo.
- nessun esempio puo' contenere token, secret, password, dati personali reali o URL
  ambientali sensibili.
- ogni flusso rilevante deve avere almeno un esempio di successo e un errore funzionale.

### CatalogoErroriFunzionali

Elenco stabile degli errori pubblici esposti da API e scenari.

Fields:

- `id`
- `api_scope`
- `codice`
- `http_status`
- `messaggio_pubblico`
- `condizione`
- `azione_suggerita`
- `audit_richiesto`: boolean.

Validation:

- ogni errore pubblico deve avere codice stabile e messaggio sanificato.
- errori legati a sicurezza, audit, idempotenza e storage devono essere tracciabili alla
  spec owner.
- i messaggi pubblici non devono esporre stack trace, segreti o dettagli tecnici interni.

### PortaleDocumentazione

Documentazione navigabile generata dal repository.

Fields:

- `id`
- `generator_ref`: script o comando di generazione.
- `pagine`: home, roadmap, feature attiva, API readiness, decisioni/vincoli, riuso PA.
- `fonti`: README, Spec Kit, costituzione, project map, contratti, quickstart.
- `verifica_build`: comando di build o validazione.

Validation:

- deve essere raggiungibile dal README.
- deve permettere di trovare proposta, costituzione, feature attiva, stato spec, blocchi,
  decisioni, vincoli, contratti API e quickstart.
- le pagine generate devono essere rigenerabili senza modifiche manuali.

### ReadinessOpenSourcePA

Checklist e metadati necessari a pubblicazione e riuso.

Fields:

- `id`
- `licenza`: `DA_CONFERMARE` finche' non decisa.
- `readme_ref`
- `setup_ref`
- `sviluppo_ref`
- `produzione_ref`
- `architettura_ref`
- `sicurezza_ref`
- `contributing_ref`
- `security_policy_ref`
- `changelog_ref`
- `rilasci_ref`

Validation:

- prima della pubblicazione pubblica la licenza deve essere confermata.
- i documenti devono essere in formato testuale versionabile.
- la checklist deve verificare assenza di segreti, credenziali, dati reali e riferimenti
  ambientali sensibili.

### SistemaRichiedente

Applicazione esterna o modulo autorizzato a consumare contratti e generazione documenti
GEMODO, ad esempio GEBAN, GRADUATORIE o CHECKIN.

Fields:

- `codice`: identificativo funzionale stabile, ad esempio `GEBAN`.
- `nome`: descrizione leggibile del sistema.
- `stato`: `ATTIVO`, `SOSPESO`, `ARCHIVIATO`.
- `client_applicativi`: elenco di `ClientApplicativo` associati.
- `profili_integrazione`: elenco di `ProfiloDiIntegrazione` disponibili.
- `spec_owner`: spec responsabile del contratto applicativo.

Validation:

- ogni sistema richiedente deve avere almeno un client applicativo o una decisione aperta
  che ne blocca la configurazione.
- un sistema sospeso o archiviato non puo' usare scenari operativi di generazione.
- il codice del sistema richiedente usato nei payload deve corrispondere a un profilo
  applicativo GEMODO attivo o esplicitamente mockato in locale/test.

### ClientApplicativo

Identita' tecnica riconosciuta da Keycloak e associata in GEMODO a uno o piu' sistemi
richiedenti.

Fields:

- `client_id`: identificativo del client tecnico o applicativo, ad esempio `geban-backend`.
- `audience_attesa`: audience prevista per chiamare GEMODO.
- `ruoli_claim_richiesti`: ruoli o claim generali richiesti dal token.
- `sistemi_abilitati`: sistemi richiedenti associati.
- `stato`: `ATTIVO`, `SOSPESO`, `DA_CONFERMARE`.
- `gestisce_credenziali`: deve essere `false` in GEMODO.

Validation:

- GEMODO non conserva password, segreti o credenziali del client.
- un token valido in Keycloak non basta per usare un modello se il client non e' associato
  a un profilo di integrazione GEMODO coerente.
- i client reali restano configurabili finche' la spec sicurezza non chiude client,
  audience e ruoli definitivi.

### ProfiloDiIntegrazione

Configurazione applicativa versionata, non credenziale, che collega sistema richiedente,
client, stato, tipi documento, categorie, tipologie, modelli/versioni, contratti dati e
permessi operativi.

Fields:

- `codice`: identificativo del profilo, ad esempio `GEBAN_RECLUTAMENTO_V1`.
- `sistema_richiedente`: riferimento a `SistemaRichiedente`.
- `versione`: numero o codice versione del profilo.
- `stato`: `BOZZA`, `ATTIVO`, `SOSPESO`, `ARCHIVIATO`.
- `client_ammessi`: client applicativi autorizzati.
- `tipi_documento_ammessi`
- `categorie_ammessi`
- `tipologie_ammessi`
- `modelli_versioni_ammessi`
- `contratti_dati_ammessi`
- `permessi_operativi`: catalogo, validazione, generazione bozza, generazione ufficiale,
  stato, download.

Validation:

- un profilo attivo deve avere sistema richiedente, client ammessi e almeno un permesso
  operativo esplicito.
- le autorizzazioni fini su modelli, categorie, contratti e operazioni appartengono a
  GEMODO, non a Keycloak.
- un operatore builder puo' vedere o modificare modelli del profilo solo se il token ha
  ruolo/claim generale coerente e GEMODO ha una regola applicativa che lo abilita.
- ogni modifica a un profilo attivo deve essere tracciabile e collegata alle spec owner.

### ModelloDocumentaleControllato

Sorgente strutturata e versionata del layout e del contenuto documentale che il builder
visuale manipolera' senza HTML/CSS libero.

Fields:

- `id`
- `modello_versione_id`
- `formato`: identificativo del formato controllato, ad esempio `GEMODO_DOCUMENT_V1`.
- `pagina`: dimensione, orientamento e margini.
- `regioni`: aree ammesse come intestazione, corpo, footer e area firme.
- `blocchi`: elenco ordinato di `BloccoDocumento`.
- `asset`: elenco di `AssetDocumento` referenziati.
- `stili_ammessi`: stili riusabili controllati.
- `placeholder_usati`
- `spec_owner`

Validation:

- non deve contenere HTML, CSS o script liberi inseriti dall'utente.
- deve usare solo blocchi, regioni, posizionamenti e stili ammessi.
- ogni placeholder usato deve essere presente nel contratto dati o in una regola esplicita
  del modello.
- ogni asset referenziato deve avere identificativo, versione e hash quando disponibile.
- una versione pubblicata deve congelare la struttura per garantire riproducibilita'.

### BloccoDocumento

Elemento visuale ammesso nel modello documentale.

Fields:

- `id`
- `tipo`: `INTESTAZIONE`, `LOGO`, `TITOLO`, `PARAGRAFO`, `TABELLA`, `COLONNE`, `FIRMA`,
  `FOOTER`, `INTERRUZIONE_PAGINA`.
- `contenuto`: testo strutturato o riferimento a dati/asset.
- `posizionamento`: `TOP`, `BODY`, `BOTTOM_LEFT`, `BOTTOM_RIGHT`, `BOTTOM_CENTER`,
  `INLINE`, `COLUMN_LEFT`, `COLUMN_RIGHT`.
- `ordine`
- `stile`
- `placeholder_usati`
- `regole_layout`

Validation:

- il tipo blocco deve essere tra quelli ammessi.
- il posizionamento deve essere compatibile con tipo blocco e regione.
- le tabelle devono dichiarare colonne e fonte dati strutturata.
- le firme devono usare posizioni controllate e non coordinate arbitrarie libere.

### AssetDocumento

Logo, immagine o risorsa grafica referenziata dal modello.

Fields:

- `id`
- `tipo`: `LOGO`, `IMMAGINE`, `TIMBRO`, `ALTRO`.
- `nome`
- `versione`
- `storage_ref`
- `hash_file`
- `dimensioni_consentite`
- `spec_owner`

Validation:

- l'asset deve essere referenziato tramite identificativo, non copiato come contenuto libero.
- l'uso dell'asset deve rispettare dimensioni e posizionamenti consentiti.
- asset usati in modelli pubblicati devono restare recuperabili o storicizzati.

### ScenarioEndToEnd

Flusso verificabile che attraversa piu' feature.

Fields:

- `id`
- `nome`
- `priorita`: `P1`, `P2`, `P3`.
- `tipo`: `VALIDO`, `ERRORE_VALIDAZIONE`, `IDEMPOTENZA`, `CONFLITTO`, `FALLIMENTO`, `AUTORIZZAZIONE`.
- `spec_coinvolte`
- `requisiti_coperti`
- `contratti_coinvolti`
- `expected_outcome`

Validation:

- ogni scenario deve essere collegato ad almeno una user story o requisito.
- gli scenari minimi devono coprire valido, payload non valido, retry idempotente,
  conflitto idempotente, generazione fallita e accesso non autorizzato.

### MatriceCopertura

Collegamento tra requisiti, scenari, contratti e spec owner.

Fields:

- `id`
- `spec_owner`
- `requirement_id`
- `scenario_id`
- `contract_ref`
- `stato`: `DA_COPRIRE`, `COPERTO`, `BLOCCATO`.
- `note`

Validation:

- ogni scenario minimo deve comparire nella matrice.
- ogni blocco deve puntare a una decisione aperta o prerequisito esplicito.

### DecisioneAperta

Scelta progettuale da confermare.

Fields:

- `id`
- `titolo`
- `owner_spec`
- `spec_interessate`
- `stato`: `APERTA`, `ASSUNTA_PROVVISORIA`, `CONFERMATA`, `SOSPESA`.
- `assunzione_provvisoria`
- `impatto`
- `fase_bloccante`: `SPEC`, `PLAN`, `TASKS`, `IMPLEMENTAZIONE`, `NESSUNA`.
- `data_ultima_revisione`

Validation:

- ogni decisione di §17 deve avere owner e assunzione provvisoria o stato confermato.
- una decisione critica non confermata non puo' entrare in task implementativi come
  assunzione silenziosa.

### VerificaAmbiente

Risultato del controllo ambiente.

Fields:

- `id`
- `ambiente_id`
- `timestamp`
- `servizi_verificati`
- `esito`: `PASS`, `FAIL`, `PARTIAL`.
- `problemi`

Validation:

- deve distinguere prerequisiti mancanti da errori applicativi.
- deve indicare il servizio responsabile del fallimento quando noto.

## Relationships

```text
AmbienteLocale 1--N ServizioLocale
AmbienteLocale 1--N VerificaAmbiente
MigrationSet 1--N MatriceCopertura
SeedDemo N--N ScenarioEndToEnd
MockGEBAN 1--N ScenarioEndToEnd
ContrattoOpenAPI 1--N EsempioAPI
ContrattoOpenAPI 1--N CatalogoErroriFunzionali
ContrattoOpenAPI N--N ScenarioEndToEnd
PortaleDocumentazione N--N ContrattoOpenAPI
ReadinessOpenSourcePA 1--N PortaleDocumentazione
SistemaRichiedente 1--N ProfiloDiIntegrazione
SistemaRichiedente 1--N ClientApplicativo
ClientApplicativo N--N ProfiloDiIntegrazione
ProfiloDiIntegrazione N--N ScenarioEndToEnd
ProfiloDiIntegrazione N--N MatriceCopertura
ModelloDocumentaleControllato 1--N BloccoDocumento
ModelloDocumentaleControllato N--N AssetDocumento
ModelloDocumentaleControllato N--N MatriceCopertura
ScenarioEndToEnd 1--N MatriceCopertura
DecisioneAperta N--N MatriceCopertura
DecisioneAperta N--N Spec
```

## State Transitions

### DecisioneAperta

```text
APERTA -> ASSUNTA_PROVVISORIA
APERTA -> CONFERMATA
ASSUNTA_PROVVISORIA -> CONFERMATA
ASSUNTA_PROVVISORIA -> SOSPESA
SOSPESA -> ASSUNTA_PROVVISORIA
SOSPESA -> CONFERMATA
```

Rules:

- `ASSUNTA_PROVVISORIA` consente planning solo se l'impatto e' esplicito.
- `SOSPESA` deve indicare quali task o parti restano bloccati.
- `CONFERMATA` richiede aggiornamento delle spec interessate.

### VerificaAmbiente

```text
PARTIAL -> PASS
PARTIAL -> FAIL
FAIL -> PASS
```

Rules:

- `PASS` richiede tutti i servizi obbligatori disponibili.
- `PARTIAL` non abilita scenari end-to-end completi.
- `FAIL` deve indicare prerequisiti mancanti o servizi non raggiungibili.

### SistemaRichiedente e ProfiloDiIntegrazione

```text
SistemaRichiedente: ATTIVO -> SOSPESO
SistemaRichiedente: SOSPESO -> ATTIVO
SistemaRichiedente: ATTIVO -> ARCHIVIATO

ProfiloDiIntegrazione: BOZZA -> ATTIVO
ProfiloDiIntegrazione: ATTIVO -> SOSPESO
ProfiloDiIntegrazione: SOSPESO -> ATTIVO
ProfiloDiIntegrazione: ATTIVO -> ARCHIVIATO
```

Rules:

- `ATTIVO` richiede client, ruoli/claim generali attesi, permessi operativi e contratto
  applicativo documentati.
- `SOSPESO` impedisce nuove generazioni operative ma mantiene consultazione/audit secondo
  autorizzazione.
- `ARCHIVIATO` non e' utilizzabile per nuovi scenari operativi.
