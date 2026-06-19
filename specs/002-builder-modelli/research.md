# Research - Builder Modelli Documentali

## Decision: FastAPI backend per il builder

**Rationale**: la scelta tecnica aggiornata del progetto e' backend Python FastAPI. La
feature richiede API interne, validazioni, OpenAPI, transazioni su PostgreSQL e regole di
workflow esplicite; FastAPI con Pydantic, SQLAlchemy e Alembic copre questi bisogni con
meno boilerplate rispetto a uno stack Java/Spring per questo progetto.

**Alternatives considered**:

- Spring Boot: scartato per questa fase perche' aumenterebbe struttura e boilerplate
  rispetto al bisogno corrente.
- Flask: scartato come default perche' richiederebbe piu' integrazioni manuali per
  OpenAPI, validazione e schema contract-first.

## Decision: backend builder separato dal frontend builder

**Rationale**: la feature 002 deve stabilizzare il dominio e le API interne del builder.
Il frontend viene progettato nella spec 007, evitando di mescolare UX, schermate e logica
di stato nello stesso blocco di lavoro.

**Alternatives considered**:

- Includere subito il frontend: scartato perche' aumenta troppo il perimetro e duplica
  decisioni che spettano alla spec 007.
- Gestione manuale solo da DB: scartato perche' viola il principio di modelli
  configurabili tramite workflow.

## Decision: variante modello obbligatoria con default `STANDARD`

**Rationale**: ogni modello deve essere distinguibile in modo uniforme anche quando non
esistono varianti funzionali. `STANDARD` copre il caso ordinario; varianti custom coprono
documenti simili ma non equivalenti nello stesso tipo/categoria/tipologia.

**Alternatives considered**:

- Variante opzionale: scartata perche' crea regole diverse tra modelli con e senza
  variante.
- Variante sempre inserita manualmente: scartata perche' aumenta attrito per il caso
  normale.

## Decision: versione pubblicata non modificabile direttamente

**Rationale**: documenti generati e audit devono poter risalire al contenuto esatto usato
al momento della generazione. Una modifica a contenuto gia' pubblicato crea una bozza
derivata e, dopo approvazione, una nuova versione corrente.

**Alternatives considered**:

- Modifica in-place della versione pubblicata: scartata perche' rompe riproducibilita' e
  audit.
- Duplicazione manuale libera: scartata perche' produce storico incoerente senza relazione
  esplicita con la versione precedente.

## Decision: una sola versione `PUBBLICATO` corrente per variante

**Rationale**: il catalogo operativo deve essere leggibile e non ambiguo. Piu' modelli
simili coesistono come varianti diverse; gli aggiornamenti della stessa variante
sostituiscono la versione corrente precedente.

**Alternatives considered**:

- Piu' versioni pubblicate sovrapposte per la stessa variante: scartato perche' confonde
  la scelta operativa.
- Un solo modello pubblicato per tipo/categoria/tipologia: scartato perche' impedisce
  varianti funzionali legittime.

## Decision: pubblicazione transazionale con archiviazione automatica

**Rationale**: quando una nuova versione della stessa variante diventa `PUBBLICATO`, la
versione corrente precedente deve passare ad `ARCHIVIATO` nello stesso confine
transazionale, evitando finestre in cui il catalogo vede due correnti o nessuna corrente.

**Alternatives considered**:

- Archiviazione manuale prima della pubblicazione: scartata per rischio operativo e
  sequenze parziali.
- Pubblicazione con warning ma senza archiviazione automatica: scartata perche' lascia
  ambiguita' nel catalogo operativo.

## Decision: stati workflow separati

**Rationale**: `APPROVATO` e `PUBBLICATO` sono stati diversi. Una versione approvata e'
pronta per la pubblicazione, ma non e' ancora visibile a GEBAN. Il numero di figure
coinvolte nell'approvazione resta demandato alla spec 006.

**Alternatives considered**:

- Accorpare approvazione e pubblicazione: scartato perche' riduce controllo operativo.
- Introdurre subito workflow multi-approvatore: rinviato alla spec sicurezza/autorizzazioni.
