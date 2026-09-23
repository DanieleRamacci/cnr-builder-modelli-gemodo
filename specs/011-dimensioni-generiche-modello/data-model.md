# Data Model: Dimensioni Generiche Del Modello

**Feature**: `011-dimensioni-generiche-modello` | **Data**: 2026-09-23

Riferimento alle decisioni: [research.md](research.md). Stato di partenza:
`backend/app/catalog/models.py`.

## Il cambiamento in una riga

La categorizzazione di un modello smette di essere **due colonne** e diventa
**un documento per nome di dimensione**. Tutto il resto dell'entita' resta
invariato.

## `ModelloDocumento` — forma dopo la modifica

| Campo | Prima | Dopo | Nota |
| --- | --- | --- | --- |
| `lingua` | `String(2)` NOT NULL, default `IT`, check `IN ('IT','EN')` | **eliminata** | il valore vive in `dimensioni["lingua"]` |
| `livello_professionale` | `String(64)` nullable | **eliminata** | il valore vive in `dimensioni["livello"]`, la chiave e' assente quando non valorizzato |
| `dimensioni` | — | `JSONB` NOT NULL DEFAULT `'{}'` | **nuova** |
| `variante` | `String(64)` NOT NULL default `STANDARD` | invariata | FR-012: asse separato, non entra in `dimensioni` |
| `codice`, `nome` | invariati | invariati | FR-007: la migrazione non li ricalcola |
| `derivato_da_modello_id` | invariato | invariato | FR-013: cambia la dimensione su cui si deriva, non la relazione |

### `dimensioni` — contratto interno

Documento JSON **piatto**, un livello solo.

- **Chiave**: nome della dimensione come arriva dall'albero discovery
  (`lingua`, `livello`, `area_geografica`, …). Stringa, non vuota.
- **Valore**: stringa non vuota. Nessun altro tipo: i valori di dimensione
  arrivano da liste di stringhe sulle foglie.
- **Chiave assente**: la dimensione non e' valorizzata per questo modello. E'
  l'unico modo per esprimerlo — FR-006.
- **Valore `null`**: **vietato**. Renderebbe ambigua la distinzione fra «non
  valorizzata» e «valorizzata a nulla». Da rifiutare in validazione, non solo
  per convenzione.
- **Documento vuoto `{}`**: legittimo. E' un tipo documento la cui
  categorizzazione non ha dimensioni controllate, o un modello le cui dimensioni
  ammettono tutte il generico e sono state lasciate tutte generiche.

Esempi reali attesi:

```json
{"lingua": "IT", "livello_professionale": "VI"}
{"lingua": "EN"}
{"area_geografica": "NORD"}
{}
```

### Validation rules

| Regola | Dove vive | Requisito |
| --- | --- | --- |
| Ogni chiave presente deve essere una dimensione dichiarata dalla foglia scelta | `BuilderService.crea_modello` | FR-002 |
| Ogni valore deve essere fra quelli ammessi dalla foglia per quella dimensione | `_verifica_dimensione`, iterando | FR-002 |
| Una dimensione con policy `consente_valore_generico = false` deve avere la chiave | `_verifica_dimensione`, iterando | FR-002 |
| Una dimensione non dichiarata dalla foglia non puo' comparire | `BuilderService.crea_modello` | FR-006 |
| Nessun valore `null`, nessuna stringa vuota | schema Pydantic della request | DEC-011-PERSISTENZA-DIMENSIONI |

**Nota sulla validazione a posteriori**: le regole sopra valgono **alla
creazione**. Un modello gia' salvato non viene rivalidato contro l'albero live:
se una dimensione sparisce o cambia insieme di valori, il modello resta
leggibile (FR-009) e il disallineamento va **segnalato**, non corretto in
silenzio — e' un edge case della spec e diventa un requisito di lettura, non di
scrittura.

### Indice

```python
Index("ix_modello_documento_dimensioni", "dimensioni", postgresql_using="gin")
```

Serve due letture: l'uguaglianza esatta di FR-004 e le query per singola
dimensione (`dimensioni @> '{"lingua": "IT"}'`) che sostituiscono i filtri di
`lista_modelli`.

### Vincoli rimossi

- `CheckConstraint("lingua IN ('IT', 'EN')", name="ck_modello_documento_lingua")`
  — cade con la colonna. **Il vincolo di dominio non sparisce**: si sposta dove
  gia' viveva davvero, cioe' nel confronto con `foglia.lingue_possibili`, che e'
  la fonte autorevole. `DEC-001-LINGUA-IT-EN` va riaperta come dice la spec:
  questo e' il punto in cui il database smette di essere il suo custode.

### Vincoli invariati

- `uq_modello_documento_tipo_codice` su `(tipo_documento_id, codice)`: continua
  a valere, ed e' la rete di sicurezza di FR-003. Se `_identita_modello`
  producesse lo stesso codice per due modelli diversi, la creazione fallirebbe
  invece di produrre un duplicato silenzioso.

## `PolicyDimensione` — una colonna nuova

| Campo | Prima | Dopo | Nota |
| --- | --- | --- | --- |
| `nome_dimensione` | `String(64)` | invariata di tipo, **valori migrati** | `livello` → `livello_professionale` (vedi sotto) |
| `consente_valore_generico` | `Boolean` NOT NULL | invariata | cambia chi la fa rispettare, non la forma |
| `valore_default` | — | `String(64)` nullable | **nuova**, per DEC-011-DEFAULT-DIMENSIONE |

`valore_default` e' il valore che il form preseleziona. `NULL` significa
«nessuna preselezione», ed e' anche il modo di dire «per questa dimensione il
default e' il generico», perche' l'assenza di valore e' una scelta legittima
dove `consente_valore_generico = true`.

**Validazione**: `valore_default` non vincolato in schema ai valori dell'albero
live — un valore che sparisce dall'albero non deve rompere la configurazione
(stesso principio di FR-009). Va **segnalato** in schermata quando non e' piu'
fra i valori dichiarati, non cancellato.

Il peso della policy cambia comunque: da dichiarazione senza effetto per ogni
dimensione diversa da lingua e livello, a sorgente unica di **tre** cose —
l'enforcement (FR-002), la disponibilita' della derivazione (FR-013, FR-014) e
il valore proposto (FR-011).

### Il nome della dimensione livello

Le righe esistenti hanno `nome_dimensione = "livello"`, mentre la colonna
rimossa e il campo di contratto si chiamano `livello_professionale`. Tenere i
due nomi significherebbe cablare la traduzione `"livello" → livello_professionale`
in `ModelloCatalogoSchema`, cioe' reintrodurre in piccolo il problema che questa
spec elimina.

**Si uniforma a `livello_professionale`**, ovunque: `PolicyDimensione`, chiave
di `dimensioni`, contratto. La migration `0020` converte anche le righe di
`PolicyDimensione` e `POLICY_DI_RIPIEGO` diventa
`{"lingua": False, "livello_professionale": True}`.

**Attenzione**: l'albero discovery dichiara i livelli con la chiave
`livelli_possibili`, e `_dimensioni_catalogo` ne deriva oggi il nome `livello`.
Va allineato anche li' (`backend/app/configurazione/service.py:351`) — e' l'unico
punto in cui quel file va toccato, in deroga alla regola generale di non
modificarlo.

## `ModelloCampoRichiesto` — invariata

Conserva la propria colonna `lingua` con il vincolo unico
`(modello_versione_id, codice, lingua)`. **Non e' la stessa cosa** della lingua
del modello, ed e' il punto che le prime due stesure della spec avevano
sbagliato: qui la lingua e' un attributo del **singolo campo** dentro un
contratto unico — 852 campi `IT` e 195 `EN` sulle 65 foglie reali. Questa
feature non la tocca.

## Unicita' della versione pubblicata (FR-004)

La condizione passa da cinque termini a quattro, di cui uno composito:

| Prima | Dopo |
| --- | --- |
| `tipo_documento_id` | `tipo_documento_id` |
| `percorso_categorizzazione` | `percorso_categorizzazione` |
| `variante` | `variante` |
| `lingua` | `dimensioni` (uguaglianza JSONB, per contenuto) |
| `livello_professionale` | — |

L'uguaglianza JSONB confronta il **contenuto**, non l'ordine di inserimento
delle chiavi, quindi `{"a":"1","b":"2"}` e `{"b":"2","a":"1"}` sono lo stesso
slot. E' la proprieta' su cui poggia la scelta di DEC-011-PERSISTENZA-DIMENSIONI.

**Conseguenza da verificare nei test**: due modelli che differiscono *solo* per
una dimensione nuova occupano slot diversi e restano entrambi pubblicati — e'
l'Independent Test di US3.

## Edizione derivata (FR-013, FR-014)

La relazione non cambia forma: resta `derivato_da_modello_id` su
`ModelloDocumento`. Cambia **su cosa** si calcola l'unicita' di un'edizione.

| | Prima | Dopo |
| --- | --- | --- |
| Lookup | `get_edizione_derivata(origine_id, lingua)` | `get_edizione_derivata(origine_id, nome_dimensione, valore)` |
| Unicita' | `(derivato_da_modello_id, lingua)` | `(derivato_da_modello_id, nome_dimensione, valore)` |
| Disponibilita' | sempre, la lingua e' NOT NULL | dove esiste una dimensione con `consente_valore_generico = false` e almeno due valori sulla foglia |

**`_raggruppa_edizioni` non si tocca**: lavora gia' solo su
`derivato_da_modello_id` (`backend/app/catalog/service.py:155`) e non ha mai
guardato la lingua. E' il motivo per cui questa generalizzazione costa poco.

**Perche' la disponibilita' dipende dalla policy**: derivare significa «stesso
modello, altro valore di questa dimensione». Ha senso solo se il modello di
origine **ha** quel valore, il che e' garantito esattamente quando la dimensione
e' obbligatoria. Dove ammette il generico, un modello puo' non valorizzarla e la
derivazione non avrebbe punto di partenza.

## State transitions

Nessuna. Gli stati di `ModelloDocumento` (`BOZZA`, …) e di
`ModelloDocumentoVersione` (`BOZZA`, `PUBBLICATO`, …) non cambiano. Questa
feature cambia **su cosa** si calcola l'unicita' della pubblicazione, non le
transizioni.

## Migrazione `0020`

Sequenza, per DEC-011-MIGRAZIONE-IN-UN-PASSO:

1. `ADD COLUMN dimensioni JSONB NOT NULL DEFAULT '{}'`
2. popolamento:
   - `lingua` e' NOT NULL → sempre `{"lingua": <valore>}`
   - `livello_professionale` NOT NULL → aggiunge `"livello": <valore>`
   - `livello_professionale` NULL → **nessuna chiave** `livello`
3. `CREATE INDEX ... USING gin (dimensioni)`
4. `DROP CONSTRAINT ck_modello_documento_lingua`
5. `DROP COLUMN lingua`, `DROP COLUMN livello_professionale`
6. `ALTER TABLE policy_dimensione ADD COLUMN valore_default VARCHAR(64) NULL`
7. `UPDATE policy_dimensione SET nome_dimensione = 'livello_professionale'
   WHERE nome_dimensione = 'livello'` — l'uniformazione del nome
8. popolamento dei default che conservano il comportamento odierno: per ogni
   tipo documento, `lingua → 'IT'` e `livello_professionale → NULL` (cioe'
   generico). E' l'unico punto della migrazione in cui si scrive una
   preferenza invece di convertire un dato: va fatto perche' altrimenti al
   primo deploy il form smetterebbe di proporre quello che propone oggi, ed e'
   un cambiamento che l'utente non ha chiesto.

Downgrade simmetrico: ricrea le colonne, ripopola da `dimensioni->>'lingua'` e
`dimensioni->>'livello'`, ripristina il check, elimina colonna e indice. Un
modello che valorizza dimensioni diverse da lingua e livello **perde quei
valori** nel downgrade: e' inevitabile e va scritto nel docstring della
migration, non scoperto dopo.

### Cosa la migrazione non tocca (FR-007)

- `codice` e `nome`: nessun ricalcolo. I modelli esistenti conservano il nome
  discorsivo prodotto dalla vecchia `_identita_modello`.
- `modello_versione`: nessuna modifica, lo stato di pubblicazione e' li'.
- il collegamento del documento generato al modello: e' per id, non passa dalle
  colonne rimosse.
