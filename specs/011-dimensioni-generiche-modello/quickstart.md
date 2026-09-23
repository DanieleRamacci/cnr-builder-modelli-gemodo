# Quickstart: Dimensioni Generiche Del Modello

**Feature**: `011-dimensioni-generiche-modello` | **Data**: 2026-09-23

Scenari eseguibili che provano la feature end-to-end. Sono la controparte
operativa degli Independent Test della spec: ciascuno cita la user story che
verifica. Dettagli di schema in [data-model.md](data-model.md), contratti in
[contracts/](contracts/).

## Prerequisiti

- PostgreSQL reale, non SQLite. La feature poggia su uguaglianza e indice GIN
  su JSONB: uno scenario che passa solo su SQLite non prova nulla di
  DEC-011-PERSISTENZA-DIMENSIONI.
- Migration `0020` applicata.
- Un endpoint discovery raggiungibile che dichiari almeno un tipo documento con
  una dimensione diversa da lingua e livello. `mock-geban/` e' il posto giusto
  per aggiungerlo.

## Setup

```bash
# backend + db
docker compose up -d postgres
cd backend && alembic upgrade head

# albero discovery con una dimensione inventata
cd ../mock-geban && <comando di avvio del mock>
```

L'albero servito dal mock deve contenere, su una foglia:

```json
{
  "codice": "FORNITURA",
  "descrizione": "Contratto di fornitura",
  "area_geografica": ["NORD", "CENTRO", "SUD"],
  "campi": [{"codice": "oggetto", "obbligatorio": true}]
}
```

Nota: nessuna chiave `lingue` e nessuna `livelli_possibili`. E' il punto —
`NodoDiscovery` ha `extra="allow"`, quindi `area_geografica` arriva senza che
GEMODO sappia cosa sia.

## Scenario 1 - Registrare il valore di una dimensione qualsiasi (US1)

1. Registra l'integrazione e scopri il tipo documento `CONTRATTI`.
2. Apri la schermata policy dimensioni: `area_geografica` compare fra le
   dimensioni senza policy. Registrala con `consente_valore_generico = false`.
3. Crea due modelli sulla stessa foglia, identici salvo `area_geografica`:
   `NORD` e `SUD`.

**Atteso**: entrambi esistono; hanno `codice` e `nome` **diversi**; rileggendoli
ciascuno riporta il proprio `dimensioni: {"area_geografica": "..."}`.

**Fallisce se**: i due modelli ricevono lo stesso nome (FR-003 non soddisfatto),
o la creazione del secondo viola `uq_modello_documento_tipo_codice`.

## Scenario 2 - La policy vale davvero (US2)

Con `area_geografica` a `consente_valore_generico = false`, crea un modello
**senza** valorizzarla: `dimensioni: {}`.

**Atteso**: HTTP 400, codice `DIMENSIONE_RICHIEDE_VALORE`, messaggio che nomina
`area_geografica`. E' **lo stesso** errore funzionale che oggi si ottiene
omettendo la lingua — non un errore nuovo.

Poi porta la policy a `true` e ripeti: il modello viene creato con
`dimensioni: {}`.

**Fallisce se**: il primo tentativo riesce. E' la falsa impressione di
configurazione che US2 esiste per eliminare.

## Scenario 3 - Pubblicare senza collisioni (US3)

Prendi i due modelli dello Scenario 1, versionali e pubblicali entrambi.

**Atteso**: dopo la seconda pubblicazione, **entrambe** le versioni sono in
stato `PUBBLICATO`. Nessuna e' stata archiviata dall'altra.

**Fallisce se**: la pubblicazione del secondo archivia il primo — significa che
`get_versione_pubblicata_corrente` non sta confrontando `dimensioni`.

Verifica complementare, che l'unicita' non sia stata semplicemente disattivata:
pubblica una **seconda versione dello stesso modello** e controlla che la
precedente venga archiviata, come prima.

## Scenario 4 - Nessun valore implicito (US5, FR-006)

Il tipo documento `CONTRATTI` non dichiara la lingua. Crea un modello.

**Atteso**: `dimensioni` non contiene la chiave `lingua`. Interroga il database:

```sql
SELECT dimensioni FROM modello_documento WHERE codice = '<codice>';
-- {"area_geografica": "NORD"}   <- nessuna lingua
```

**Fallisce se**: compare `"lingua": "IT"`. E' il dato falso che la spec cita
come conseguenza della colonna NOT NULL, e la ragione per cui la colonna
sparisce invece di diventare nullable.

Prova complementare: su questo modello la funzione «crea edizione collegata»
**non deve essere offerta**, perche' `CONTRATTI` non ha dimensioni obbligatorie
multivalore. Non e' un errore da gestire: e' un pulsante che non compare
(DEC-011-DERIVAZIONE-GOVERNATA-DA-POLICY).

**Seconda parte — il catalogo espone il tipo senza lingua**: pubblica il modello
e interroga `GET /api/v1/catalogo/modelli?tipo_documento=CONTRATTI`.

**Atteso**: il modello compare, con `lingua: null` e
`dimensioni: {"area_geografica": "NORD"}`. E' la meta' di US5 che la prima
stesura del piano rinviava a una decisione GEBAN e che
DEC-011-CONTRATTO-GEBAN-ADDITIVO ha sbloccato.

**Controprova obbligatoria, che GEBAN non e' stato toccato**: interroga
`GET /api/v1/catalogo/modelli?tipo_documento=BANDO`. Ogni modello deve avere
`lingua` **presente e valorizzata**, esattamente come prima. Il campo e'
nullable nello schema ma non nullo qui, perche' la policy del bando lo impone —
e' la proprieta' su cui poggia tutta la decisione.

## Scenario 5 - Il fallback segue la policy (FR-010)

Sul tipo documento `BANDO`, con le policy di default (`lingua` false,
`livello` true):

1. `GET /api/v1/catalogo/modelli?livello_professionale=VI` dove esiste solo il
   modello generico → **fallback applicato**,
   `dimensioni_rilassate: ["livello_professionale"]`.
2. `GET /api/v1/catalogo/modelli?lingua=EN` dove esiste solo il modello `IT` →
   **nessun fallback**, risultato vuoto.

Il punto 2 e' la protezione che `DEC-007-FALLBACK-LIVELLO-CATALOGO` motivava
sulla lingua: qui deve reggere **per via della policy**, non perche' il nome
`lingua` compaia nel codice.

Per provare che e' davvero la policy a reggerla, ripeti dopo aver portato la
policy della lingua a `consente_valore_generico = true` e con un modello di
bando privo di lingua pubblicato: il fallback **deve** scattare, e GEBAN
riceverebbe il `modello_versione_id` del modello generico in risposta a una
richiesta `lingua=EN`. E' il rischio dichiarato nelle Clarifications, ed e' il
motivo per cui va reso visibile in un test invece di restare latente: quel
documento non sarebbe inglese, e nulla lo segnalerebbe.

**Il test da scrivere e' il punto 2 con le policy di default**: l'assenza di
fallback sulla lingua e' il comportamento da proteggere da una regressione.

## Scenario 5b - L'avviso prima di cambiare una policy (DEC-011-POLICY-LINGUA-ALL-ADMIN)

Sulla schermata **Impostazioni → Integrazioni → [integrazione] → Dimensioni**,
scegli il tipo documento BANDO e una foglia, e prova a portare `lingua` su
«un modello puo' coprire tutti i valori».

**Atteso**: l'opzione e' **selezionabile** — il `[disabled]="dimensione.nome ===
'lingua'"` non c'e' piu' — ma prima di salvare compare un avviso con numeri
veri: quanti modelli pubblicati valorizzano quella dimensione e che il catalogo
la espone a GEBAN. L'avviso descrive la conseguenza: il catalogo potra'
restituire un modello che non valorizza la dimensione anche a una richiesta che
chiede un valore preciso.

**Verifica che l'avviso non conosca la parola `lingua`**: ripeti su
`area_geografica` per il tipo documento `CONTRATTI`. Deve comparire lo stesso
avviso, con i numeri di quella dimensione.

**Fallisce se**: l'avviso compare solo per la lingua. Sarebbe di nuovo un nome
di dimensione cablato, con un'interfaccia intorno invece di un `if`.

**Nota**: la policy resta **pre-impostata** correttamente e nessuno deve
crearla a mano — migration `0018` per i tipi esistenti, `POLICY_DI_RIPIEGO` in
`_tipo_per_integrazione` per quelli nuovi. Verifica che un tipo documento creato
dopo la migrazione nasca gia' con `lingua = false`.

## Scenario 6 - Migrazione dei modelli esistenti (FR-007)

Su un database con modelli **gia' pubblicati** e documenti gia' generati, prima
di applicare `0020`, annota per qualche modello: `codice`, `nome`, stato delle
versioni, id dei documenti generati collegati.

Applica `alembic upgrade head`.

**Atteso**: `codice` e `nome` **identici** (non ricalcolati); le versioni
pubblicate ancora `PUBBLICATO`; i documenti generati ancora collegati;
`dimensioni` popolato da lingua e livello, **senza** la chiave `livello` dove la
colonna era NULL.

Poi `alembic downgrade -1` e ricontrolla: le colonne tornano popolate. Un
modello che valorizzava dimensioni diverse da lingua e livello perde quei valori
— e' documentato nella migration, va verificato che sia l'unica perdita.

**Fallisce se**: qualche nome cambia. La migrazione non deve toccare l'identita'.

## Scenario 7 - Dimensione sparita dall'albero (FR-009, edge case)

Con modelli che valorizzano `area_geografica`, rimuovi quella chiave
dall'albero servito dal mock.

**Atteso**: i modelli restano leggibili e restituiscono il proprio valore. Il
disallineamento viene **segnalato** in lettura, non corretto in silenzio.

**Fallisce se**: i modelli spariscono dall'elenco o la lettura va in errore.

## Criterio di successo automatizzabile

Il criterio della spec — «nessuna dimensione resta scritta a mano nel codice» —
e' verificabile come controllo, non solo a occhio:

```bash
cd backend && grep -rn '"lingua"\|"livello"' app/builder/
```

**Atteso**: nessuna occorrenza che governi comportamento, **senza deroghe**.
L'unica cosa che resta legittimamente e' `POLICY_DI_RIPIEGO`, che non governa
comportamento ma fornisce il valore iniziale di una configurazione a un tipo
documento che non ne ha ancora. Ogni altra occorrenza e' un residuo da chiudere.
