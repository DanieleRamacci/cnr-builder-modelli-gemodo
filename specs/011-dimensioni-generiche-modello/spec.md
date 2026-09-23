# Feature Specification: Dimensioni Generiche Del Modello

**Feature Branch**: `011-dimensioni-generiche-modello`

**Created**: 2026-09-23

**Status**: Draft

**Input**: Nata dal collaudo dell'interfaccia del 2026-09-23. Domanda dell'utente:
«se domani arriva un tipo documento diverso, sempre nel contesto geban, che si
chiama `contratti`, che non ha la lingua ma ha l'`area_geografica`, e voglio che
quella scelta distingua un documento con id diverso, non posso farlo se non
inserendolo nel contratto dati in fase di sviluppo?». La risposta misurata e'
si': oggi serve sviluppo. Questa spec esiste per renderla no.

Non e' scope nuovo inventato qui: e' il seguito esplicitamente rinviato da tre
punti gia' scritti, che finora non avevano una spec proprietaria.

- `002/tasks.md`: «Generalizzarlo a dimensioni che non siano colonne dedicate
  richiede il refactor dei valori di dimensione, **non previsto qui**».
- `002/tasks.md`: sulla lingua, «Renderla davvero generica richiede una modifica
  di schema e contratto in `001`: **decisione non presa**, non e' un residuo di
  questo task».
- `010/spec.md` FR-019 (User Story 5): la policy per dimensione nasce per non
  avere «bisogno di nuovo codice per ogni dimensione futura».

## Stato di partenza misurato (2026-09-23)

Il meccanismo e' **generico a meta'**, e la meta' mancante e' quella che serve.
Verificato end-to-end servendo un albero discovery con una dimensione inventata
(`canale: ["PEC", "Portale"]`).

**Gia' generico, senza codice nuovo:**

- `IntegrazioniService._dimensioni_catalogo` riconosce `lingue_possibili`,
  `livelli_possibili` e **qualunque altra chiave con una lista** sulla foglia,
  perche' `NodoDiscovery` dichiara `extra="allow"`.
- Una dimensione mai vista viene segnalata come priva di policy e l'admin puo'
  registrarla dall'interfaccia: `PolicyDimensione` ha chiave
  `(tipo_documento_id, nome_dimensione)`, non una colonna per dimensione.
  La parte dichiarativa e' quindi gia' fatta e gia' in esercizio.

**Cablato su `lingua` e `livello`:**

- **Enforcement**: `BuilderService.crea_modello` chiama `_verifica_dimensione`
  esattamente due volte. Una policy su una dimensione diversa viene salvata e
  poi ignorata: non obbliga e non vieta nulla.
- **Persistenza**: `modello_documento` ha due colonne dedicate, `lingua`
  (NOT NULL) e `livello_professionale` (nullable). Non esiste dove registrare
  «questo modello vale per `area_geografica = NORD`».
- **Identita'**: `_identita_modello` compone codice e nome da tipologia,
  profilo, livello e lingua. Due modelli che differissero solo per una
  dimensione nuova avrebbero lo stesso nome.
- **Unicita' della pubblicazione**: `get_versione_pubblicata_corrente` filtra su
  `(tipo, percorso, variante, lingua, livello)`. Una dimensione nuova non
  separa gli slot, quindi due modelli distinti si archivierebbero a vicenda.
- **Elenco al builder**: `_dimensioni_note` restituisce `{"lingua", "livello"}`
  scritto a mano.

**Conseguenza sul caso `contratti`**: `modello_documento.lingua` e' NOT NULL,
quindi un tipo documento che non ha la lingua fra le sue dimensioni ne
riceverebbe comunque una, per default `IT`. Un dato falso.

## User Scenarios & Testing

### User Story 1 - Registrare il valore di una dimensione qualsiasi (Priority: P1)

Come gestore modelli, voglio che il modello ricordi quale valore ho scelto per
ogni dimensione dichiarata dall'integrazione, non solo per lingua e livello,
cosi' che due modelli che differiscono per una dimensione nuova siano davvero
due modelli diversi.

**Why this priority**: senza un posto dove scrivere il valore, nessuna delle
altre storie e' realizzabile.

**Independent Test**: un albero live dichiara una dimensione mai vista; si
creano due modelli identici salvo quel valore; entrambi esistono, hanno codici
e nomi distinti e sono leggibili con il proprio valore.

### User Story 2 - Far rispettare la policy di ogni dimensione (Priority: P1)

Come admin, voglio che la policy che registro valga davvero, qualunque sia la
dimensione, cosi' che dichiararla non sia un gesto senza effetto.

**Why this priority**: oggi salvare una policy su una dimensione nuova da'
all'admin la falsa impressione di aver configurato qualcosa.

**Independent Test**: registrata una policy che richiede un valore esplicito su
una dimensione nuova, la creazione di un modello che la omette viene rifiutata
con lo stesso errore funzionale usato oggi per lingua e livello.

### User Story 3 - Distinguere e pubblicare senza collisioni (Priority: P1)

Come gestore, voglio che due modelli che differiscono per una dimensione nuova
restino entrambi pubblicati, cosi' da non vedermi archiviare un modello valido
dalla pubblicazione di un altro.

**Independent Test**: due modelli pubblicati che differiscono solo per il valore
di una dimensione nuova coesistono; il catalogo verso GEBAN li restituisce
entrambi, distinguibili.

### User Story 4 - La lingua smette di essere privilegiata (Priority: P2)

Come progetto, vogliamo che `lingua` sia una dimensione come le altre, cosi' che
la sua regola sia una scelta configurata e non una costante del codice.

**Why this priority**: dipende da US1-US3 e riapre un contratto esterno, quindi
non puo' precederle.

**Independent Test**: la policy della lingua e' modificabile come le altre; un
tipo documento che non dichiara la lingua produce modelli senza lingua, non
modelli con `IT` implicito.

### User Story 5 - Un tipo documento con dimensioni proprie (Priority: P2)

Come admin, voglio integrare un tipo documento la cui categorizzazione non
assomiglia a quella del bando - per esempio `contratti` con `area_geografica` e
senza lingua - senza che serva una modifica di codice.

**Independent Test**: il caso portante di questa spec, verificato end-to-end
contro un endpoint discovery che dichiara quel tipo.

### Edge Cases

- Una dimensione sparisce dall'albero live mentre esistono modelli che la
  valorizzano: i modelli non devono diventare illeggibili ne' sparire.
- Una dimensione cambia insieme di valori ammessi: un modello con un valore non
  piu' ammesso va segnalato, non corretto in silenzio.
- Migrazione dei modelli esistenti: lingua e livello devono diventare valori di
  dimensione senza perdere identita', pubblicazioni e documenti generati.
- Due creazioni simultanee sulla stessa combinazione di dimensioni.

## Requirements

### Functional Requirements

- **FR-001**: Il sistema MUST registrare, per ogni modello, il valore scelto di
  ciascuna dimensione dichiarata, in una struttura per nome di dimensione e non
  in colonne dedicate.
- **FR-002**: L'enforcement MUST iterare sulle policy registrate per il tipo
  documento, invece di verificare un insieme di dimensioni scritto nel codice.
- **FR-003**: L'identita' del modello - codice e nome generati - MUST includere
  i valori delle dimensioni che lo distinguono, cosi' che due modelli diversi
  non ricevano mai lo stesso nome.
- **FR-004**: L'unicita' della versione pubblicata corrente MUST considerare
  tutte le dimensioni valorizzate, non solo lingua e livello, cosi' che la
  pubblicazione non archivi un modello che differisce per una dimensione nuova.
- **FR-005**: Le dimensioni note al builder MUST derivare dalle policy e
  dall'albero live, mai da un elenco scritto nel codice.
- **FR-006**: Un tipo documento che non dichiara una dimensione MUST produrre
  modelli che non la valorizzano: nessun valore implicito di ripiego.
- **FR-007**: La migrazione dei modelli esistenti MUST preservare identita',
  stato di pubblicazione e collegamento ai documenti generati. `lingua` e
  `livello_professionale` diventano valori di dimensione senza che un bando
  gia' generato perda il riferimento al modello da cui e' nato.
- **FR-008**: Il contratto verso GEBAN MUST continuare a esporre le dimensioni
  di un modello pubblicato in forma leggibile da un consumatore esterno. Ogni
  modifica a `ModelloCatalogoSchema` MUST essere concordata: GEBAN oggi riceve
  `lingua` come campo obbligatorio e ci fa affidamento.
- **FR-009**: Una dimensione scomparsa dall'albero live MUST NOT rendere
  illeggibili i modelli che la valorizzano.

### Key Entities

- **Valore Dimensione Modello** *(nuova)*: associa a un modello il nome di una
  dimensione e il valore scelto. Sostituisce le colonne `lingua` e
  `livello_professionale` come sorgente di verita' della categorizzazione.
- **Policy Dimensione** *(esistente, `002`)*: dichiara se una dimensione ammette
  un valore generico. Gia' per nome di dimensione: non cambia forma, cambia
  chi la fa rispettare.
- **Attributo Profilo** *(esistente, `010`)*: attributo dichiarato su un profilo
  dell'albero, gia' descritto come «generalizza il caso livello». E' la
  controparte dichiarativa del valore registrato sul modello.

## Success Criteria

- Un tipo documento con una categorizzazione diversa da quella del bando si
  integra senza modifiche di codice: e' il criterio che chiude la domanda da cui
  questa spec nasce.
- Nessun modello gia' pubblicato perde identita', pubblicazione o documenti
  collegati attraverso la migrazione.
- Nessuna dimensione resta scritta a mano nel codice: la ricerca di `"lingua"`
  e `"livello"` come costanti in `backend/app/builder/` non trova piu'
  occorrenze che governino comportamento.

## Assumptions

- GEBAN resta il consumatore del catalogo e va coinvolto su FR-008: questa spec
  non puo' chiudersi senza una decisione condivisa sul contratto.
- La forma della risposta discovery non cambia: le dimensioni continuano ad
  arrivare come chiavi con liste di valori sulle foglie.
- `DEC-001-LINGUA-IT-EN` va riaperta da US4, non aggirata.
