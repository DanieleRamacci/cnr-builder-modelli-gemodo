# Research - Catalogo Modelli E Contratto Dati GEBAN

## Decision: FastAPI backend per la feature 001

**Rationale**: la scelta aggiornata del progetto e' usare Python FastAPI per il backend.
La feature richiede API REST contract-first, validazione di payload dinamici, OpenAPI,
persistenza relazionale e integrazione futura con Keycloak. FastAPI si allinea bene a
Pydantic, type hints, JSON Schema e documentazione OpenAPI.

**Alternatives considered**:

- Backend generico non definito: scartato perche' avrebbe prodotto task poco eseguibili.
- Implementazione frontend-first: scartata perche' GEBAN consuma API backend.

## Decision: PostgreSQL con migrations Alembic

**Rationale**: il dominio ha stati, vincoli univoci, relazioni e storico versioni. Le
migrations rendono esplicite le evoluzioni dello schema.

**Alternatives considered**:

- Storage file/JSON: insufficiente per vincoli e interrogazioni.
- Database GEBAN: vietato dalla costituzione.

## Decision: API REST contract-first con OpenAPI

**Rationale**: GEBAN deve costruire maschere dinamiche e validare payload usando contratti
espliciti. OpenAPI consente versionamento, esempi e test di contratto.

**Alternatives considered**:

- Contratto solo documentato in Markdown: utile ma non abbastanza verificabile.
- GraphQL: non richiesto e meno coerente con proposta REST.

## Decision: validazione payload strict

**Rationale**: i campi extra sono considerati errore. Questo evita che dati non dichiarati
entrino nello snapshot o alterino la generazione.

**Alternatives considered**:

- Ignorare campi extra con warning: rischia divergenza tra GEBAN e servizio modelli.
- Salvare campi extra: viola il principio di contratto dati esplicito.

## Decision: variante modello distinta da versione modello

**Rationale**: modelli simili per stesso tipo, categoria e tipologia possono coesistere
come varianti funzionali, senza abusare del concetto di versione. Le versioni rappresentano
l'evoluzione storica della stessa variante.

**Alternatives considered**:

- Piu' versioni operative sovrapposte della stessa variante: scartato perche' crea
  ambiguita' operativa.
- Un solo modello per contesto: troppo rigido per casi con differenze funzionali.

## Decision: `modello_versione_id` obbligatorio nelle chiamate operative successive

**Rationale**: quando esistono piu' varianti pubblicate nello stesso contesto,
l'identificativo della versione scelta elimina ambiguita'. Il servizio non seleziona
automaticamente "l'ultima" versione. In modalita' operativa esiste una sola versione
pubblicata corrente per variante.

**Alternatives considered**:

- Fallback all'ultima pubblicata: comodo ma ambiguo.
- Selezione per solo codice modello: insufficiente quando piu' varianti sono pubblicate.

## Decision: modalita' catalogo operativa e storica

**Rationale**: GEBAN ha bisogno del catalogo operativo per scegliere versioni utilizzabili,
mentre consultazioni interne possono richiedere storico e filtri di pubblicazione.

**Alternatives considered**:

- Solo catalogo corrente: perde visibilita' storica.
- Solo catalogo completo: troppo rumoroso per il flusso operativo.
