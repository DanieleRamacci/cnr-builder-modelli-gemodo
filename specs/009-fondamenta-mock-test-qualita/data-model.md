# Data Model - Fondamenta Mock Test E Qualita

Questa feature non introduce dominio amministrativo finale; definisce artefatti di
supporto per ambiente, mock, seed, copertura e decisioni aperte. Le entita' sotto sono
persistibili o versionabili come configurazioni/manifest di qualita'.

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
