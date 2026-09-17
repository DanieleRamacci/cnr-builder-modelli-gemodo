# Discovery HTTP e dismissione legacy - 2026-09-17

Sono implementati DTO ricorsivi, porta canonica e adapter HTTP collegato al
builder. AdapterLocale, ORM/repository del catalogo esterno e API di
classificazione sono eliminati. Firma, runner e onboarding amministrativo
restano task aperti: non si dichiara completata la feature 010.

## Configurazione operativa

Nel processo backend, o nelle variabili Coolify inoltrate dalla compose:

```sh
export GEMODO_DISCOVERY_ENDPOINTS='{"BANDO_CONCORSO":"https://geban-service.test.si.cnr.it/api/v1/gemodo/discovery"}'
```

La mappa tipo -> URL e' un ponte operativo, non l'implementazione dello
stato CONNESSO in T038-T041. Nessun URL hardcoded nel dominio, nessun fallback
locale. Configurazione assente/non valida: 503 `DISCOVERY_NON_CONFIGURATA`.
Sono ammesse solo URL HTTP/HTTPS approvate dall'operatore; nessuna API
pubblica accetta URL arbitrari.

Con token gestore autorizzato sul contesto, in Swagger `/docs/builder-discovery`
(stessa sorgente versionata di `/redoc/builder-discovery`; `/docs` include
anche le transizioni di pubblicazione gia' implementate):

1. `GET /api/v1/builder/tipi-documento/BANDO_CONCORSO/struttura-disponibile`
   restituisce `codice_tipo_documento`, `validita`, `nodi` ricorsivi; non
   restituisce piu' le vecchie liste piatte `tipologie`/`campi`.
2. `POST /api/v1/builder/modelli` accetta, per esempio:

```json
{
  "codice": "BANDO_TD_RICERCATORE",
  "nome": "Bando TD ricercatore",
  "codice_tipo_documento": "BANDO_CONCORSO",
  "percorso_categorizzazione": ["TD", "RICERCATORE"]
}
```

3. Creare la versione con campi della sola foglia selezionata, poi inviare
   in revisione, approvare e pubblicare con le route builder esistenti.

Codici categoria/tipologia scalari accettati solo per una foglia univoca;
in caso di ambiguita' e' necessario il percorso completo. I tag informativi
profilo/tipologia alimentano solo i riferimenti di ricerca compatibili;
parsing e identita' della selezione dipendono dal percorso. Le scritture
leggono discovery aggiornata escludendo la cache.

## Migrazione e ritiro

Prima del deploy/`alembic upgrade head`: backup DB e finestra di manutenzione,
senza vecchi processi in scrittura. Il container esegue l'upgrade all'avvio.
Migration 0009 migra riferimenti in codici/percorso ed elimina
`categoria_documento`, `tipologia_bando_sol`, `tipologia_bando`,
`classificazione_catalogo`, `registro_contratti_dati` e le FK relative.
Downgrade bloccato: rollback richiede backup pre-0009 e applicativo precedente.
Il catalogo completo non e' ricostruibile dai soli riferimenti dei modelli.

Modelli GEMODO, UUID/public_id, versioni, strutture, campi, audit, sezioni e
generazioni sono preservati. Non e' stato aggiornato un DB operativo nella
sessione: migrazione verificata su Postgres temporaneo. Migration storiche e
manifest da esse usato restano per installazioni da zero, non per discovery.

Ritirate (404) le route `/api/v1/catalogo/tipi-documento` e suffissi `profili`,
`categorie`, `classificazione`, anche da OpenAPI/pagina test. `/catalogo/modelli`
resta ricerca dei soli modelli GEMODO pubblicati: nessuna allowlist locale,
codici senza corrispondenze producono lista vuota. `/campi-richiesti` legge
il contratto della versione. `/documenti/genera` resta simulato, senza PDF.

## Prova in sola lettura

Dalla radice del repository:

```sh
uv --directory backend run python -c 'from app.discovery.adapter_http import AdapterHTTP; c=AdapterHTTP("https://geban-service.test.si.cnr.it/api/v1/gemodo/discovery").catalogo_discovery("BANDO_CONCORSO", forza_aggiornamento=True); i=c.indice_percorsi(); print({"tipologie": len(c.nodi), "foglie": sum(n.campi is not None for n in i.values()), "campi_TD_RICERCATORE": len(i[("TD", "RICERCATORE")].campi)})'
```

Il servizio di test deve essere raggiungibile. La prova non crea modelli e non
scrive dati nel DB. Alla verifica del 2026-09-17: 10 tipologie, 65 foglie,
16 campi nel percorso TD/RICERCATORE. I conteggi possono cambiare lato GEBAN.

## Contratto interno

`catalogo_discovery(codice_tipo_documento, forza_aggiornamento=False)` restituisce
il catalogo del tipo richiesto. `indice_percorsi()` costruisce in memoria una
mappa da tuple di codici a nodi; costruirla una volta per ciclo di verifica.
`forza_aggiornamento=True` esclude la cache per una verifica corrente.

TTL cache predefinito 60 secondi, max 32 voci, memoria di processo soltanto.
Ogni adapter crea la propria cache salvo iniezione esplicita. Non condividere
una cache fra integrazioni con credenziali/perimetri diversi senza aggiungere
la loro identita' alla chiave. I riempimenti sono sincronizzati per chiave;
HTTP avviene fuori dal lock comune, senza bloccare tipi documento diversi.

Limiti configurabili: 10 secondi complessivi, 2 MiB decompressi totali,
64 pagine, 64 livelli. Risposte non conformi producono
`DISCOVERY_NON_CONFORME` (502); indisponibilita' e timeout producono
`DISCOVERY_NON_DISPONIBILE` (503). Nessun redirect seguito.
L'URL iniziale e' approvato operativamente; il servizio di registrazione
amministrativa rimane da implementare.

Il formato HAL supportato e' documentato nel contratto OpenAPI. Link di pagina
su un'origine diversa e versioni temporali discordanti fra frammenti sono
rifiutati. `livelloBase` e' normalizzato in `livello_base`, senza inferire
implicitamente vincoli sul campo livello o rinominare i codici inglesi.

## Lavoro residuo

T055-T058: firme e runner; T038-T041: onboarding e guard per stato;
US1/US2: definizione/esportazione tramite API amministrativa. Self-service
richiede una propria sorgente progettata, non il catalogo legacy.
Pubblicazione concorrente e generazione ufficiale restano nei task 002/004.

## Test

```sh
uv --directory backend run pytest -m 'not e2e'
```

I test automatici non chiamano il discovery GEBAN reale. Usano un server HTTP
locale per risposta completa/paginazione e trasporti controllati per gli errori.
Migrazione e builder usano PostgreSQL reale. Run finale non-e2e 2026-09-17:
206 passati, 12 e2e esclusi, nessun test saltato. Checklist requisiti FR-016
presente; reviewer deve includere esplicitamente i contratti YAML nel diff,
perche' il tracking automatico documenti di adev censisce solo markdown
(gap MEDIUM tracciato in T071, non risolto falsificando il ledger).
