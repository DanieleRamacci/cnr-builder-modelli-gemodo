# Research: Dimensioni Generiche Del Modello

**Feature**: `011-dimensioni-generiche-modello` | **Data**: 2026-09-23

Questo documento risolve le incognite tecniche del piano. Ogni voce e' una
decisione con la sua motivazione e l'alternativa scartata. Le decisioni nuove
prendono un identificativo `DEC-011-*` nella forma gia' in uso nel progetto.

## Stato del codice verificato (2026-09-23)

Rilettura diretta delle sei superfici che la spec dichiara cablate. Tutte
confermate; nessuna e' cambiata dalla stesura della spec.

| Superficie | Posizione | Forma attuale |
| --- | --- | --- |
| Enforcement | `backend/app/builder/service.py:111` `_verifica_dimensione` + due chiamate in `crea_modello` | due invocazioni letterali, `"lingua"` e `"livello"` |
| Ripiego policy | `backend/app/builder/service.py:108` `POLICY_DI_RIPIEGO` | `{"lingua": False, "livello": True}` |
| Divieto generico | `backend/app/builder/service.py` `DIMENSIONI_SENZA_GENERICO` | `{"lingua"}` |
| Persistenza | `backend/app/catalog/models.py:61-62` | `lingua` String(2) NOT NULL default `IT`, `CheckConstraint IN ('IT','EN')`; `livello_professionale` String(64) nullable |
| Identita' | `backend/app/builder/service.py:52` `_identita_modello` | `scope`/`lingua_slug` con nomi umani scritti a mano (`"Italiano"`, `"Inglese"`, `"Tutti i livelli"`) |
| Unicita' pubblicazione | `backend/app/builder/repository.py:314` `get_versione_pubblicata_corrente` | filtro su cinque colonne, fra cui `lingua` e `livello_professionale` |
| Elenco al builder | `backend/app/builder/service.py:131` `_dimensioni_note` | `return {"lingua", "livello"}` |
| Contratto GEBAN | `backend/app/catalog/schemas.py:42-43` `ModelloCatalogoSchema` | `lingua: LinguaModello` obbligatorio, `livello_professionale: str \| None` |
| Fallback catalogo | `backend/app/catalog/service.py:74-88` | `if livello_professionale is not None and not versions` — il nome della dimensione e' nel codice |

Gia' generico e da non toccare:

- `backend/app/configurazione/service.py:339` `_dimensioni_catalogo` raccoglie
  `lingua`, `livello` e **qualunque chiave extra con lista** dalle foglie, grazie
  a `NodoDiscovery(extra="allow")` (`backend/app/discovery/schemas.py:37`).
- `PolicyDimensione` (`backend/app/catalog/models.py:106`) ha gia' chiave
  `(tipo_documento_id, nome_dimensione)`. **Non cambia forma**, come dice la
  spec: cambia chi la fa rispettare.

## DEC-011-PERSISTENZA-DIMENSIONI (decisa 2026-09-23)

**Decisione**: i valori di dimensione vivono in una colonna `dimensioni JSONB
NOT NULL DEFAULT '{}'` su `modello_documento`, come documento piatto
`{nome_dimensione: valore}`. `lingua` e `livello_professionale` vengono
migrate dentro e le colonne dedicate **eliminate**.

**Motivazione**: FR-004 e' il requisito che decide. L'unicita' della versione
pubblicata deve considerare *tutte* le dimensioni valorizzate, cioe' confrontare
due insiemi di coppie. Con JSONB e' un'uguaglianza — `ModelloDocumento.dimensioni
== :dimensioni` — che PostgreSQL valuta per contenuto, indipendente dall'ordine
di inserimento delle chiavi, e che un indice GIN puo' servire. In piu':

- **FR-006** («nessun valore implicito di ripiego») diventa strutturale:
  l'assenza della chiave *e'* l'assenza della dimensione. Nessun default di
  colonna puo' inventare `IT` per un tipo documento che non ha la lingua.
- **FR-009** (dimensione sparita dall'albero) e' gratis: nessuna chiave
  esterna verso l'albero live, quindi nulla puo' rendere illeggibile un modello.
- Nessuna DDL per ogni dimensione futura: e' il criterio di successo della spec.

**Alternativa scartata — tabella figlia `valore_dimensione_modello`**: e' la
lettura letterale della Key Entity «Valore Dimensione Modello» della spec, e
renderebbe naturali le query per singola dimensione. Scartata perche' FR-004
diventerebbe un confronto fra insiemi di righe (doppia anti-join piu' controllo
di cardinalita'), scritto a mano nel repository e facile da sbagliare in
presenza di concorrenza — esattamente il tipo di logica che questa spec vuole
togliere dal codice. La Key Entity resta valida come **concetto di dominio**: la
coppia `(nome dimensione, valore)` esiste, si materializza come voce del
documento JSONB invece che come riga.

**Costo accettato**: `voci_filtro` e i filtri di `lista_modelli`
(`backend/app/builder/repository.py:30-63,120-135`) passano da `DISTINCT` su
colonna a `jsonb_each_text` con GIN su `dimensioni`. E' lavoro circoscritto a un
solo file e va messo a piano come task proprio.

## DEC-011-CONTRATTO-GEBAN-ADDITIVO (decisa 2026-09-23, rivista lo stesso giorno)

*(Prima stesura: `lingua` restava obbligatoria e l'esposizione dei tipi
documento senza lingua veniva rinviata a una decisione GEBAN. Rivista dopo aver
verificato che `search_modelli` ha `tipo_documento` come parametro obbligatorio:
quel vincolo rende la nullabilita' sicura, e la prudenza della prima stesura
costava US5 senza comprare nulla.)*

**Decisione**: `ModelloCatalogoSchema` **aggiunge** `dimensioni: dict[str, str]`
con l'insieme completo, **conserva** `lingua` e `livello_professionale` come
proiezione di `dimensioni`, e rende `lingua` **nullable** (`str | None`).
Nessun campo rimosso.

**Motivazione**: la modifica e' *schema-breaking ma behavior-safe*, e il motivo
sta in `backend/app/catalog/service.py:33`: `search_modelli` richiede
`tipo_documento` come parametro obbligatorio e fallisce se manca. Ne segue che

1. **GEBAN non riceve mai una risposta mista.** Ogni chiamata nomina un tipo
   documento: una per `BANDO` torna solo modelli BANDO, una per `CONTRATTI`
   solo modelli CONTRATTI.
2. **Tutti i tipi documento che GEBAN consuma oggi dichiarano la lingua**, e la
   policy del bando la rende obbligatoria. Per ogni richiesta che GEBAN fa oggi
   il campo resta presente e popolato: nessun comportamento osservato cambia.
3. Il `null` compare solo per tipi documento che ancora non esistono e che GEBAN
   non ha integrato. Quando li integrera', sapra' gia' che la lingua non ce
   l'hanno — e' il motivo per cui li sta integrando.

L'unico impatto reale e' sul client generato dall'OpenAPI, dove il tipo passa da
obbligatorio a opzionale e puo' servire una ricompilazione. A GEBAN si chiede
quindi una **presa d'atto**, non un'approvazione preventiva: «il campo diventa
opzionale, per il bando resta sempre valorizzato». FR-008 e' soddisfatto —
resta una comunicazione da fare prima del rilascio, non un blocco.

**Conseguenza**: US5 si chiude davvero end-to-end. Un tipo documento con
categorizzazione propria si costruisce, si pubblica **e si espone nel catalogo**
senza attendere nessuno. Nessun blocco del piano dipende da una risposta esterna.

**Alternativa scartata — valore sentinella** (`lingua: "N/A"` per i tipi che non
la dichiarano): conserva l'obbligatorieta' formale del campo al prezzo di un
dato falso nella risposta, cioe' esattamente cio' che FR-006 esiste per
impedire, spostato dal database al contratto.

**Alternativa scartata — esporre nel catalogo solo i tipi documento che hanno la
lingua**: restringe US5 al punto di svuotarla. Un tipo documento che GEBAN non
puo' interrogare non e' integrato.

**Cio' che protegge il contratto non e' lo schema, e' la policy.** Finche'
`BANDO` ha `lingua` con `consente_valore_generico = false`, ogni modello di
bando ha una lingua e il campo non e' mai nullo per GEBAN. Il vincolo vive dove
e' vero — sul tipo documento che lo richiede — invece che in un `NOT NULL` che
per `contratti` sarebbe una bugia. Vedi DEC-011-POLICY-LINGUA-ALL-ADMIN.

## DEC-011-POLICY-LINGUA-ALL-ADMIN (decisa 2026-09-23)

**Decisione**: la protezione che oggi impedisce di dichiarare la lingua generica
— `BuilderService.DIMENSIONI_SENZA_GENERICO = {"lingua"}` nel backend e
`[disabled]="dimensione.nome === 'lingua'"` in
`frontend/src/features/configurazione/dimensioni.component.html:166` — viene
**rimossa**. Il flag passa all'admin, sulla schermata Dimensioni gia' in
esercizio, come per ogni altra dimensione. Al suo posto, prima di salvare una
policy su «consente il generico», la schermata mostra la conseguenza **calcolata
dai dati**.

**Motivazione**: `=== 'lingua'` e' letteralmente un nome di dimensione scritto
nel codice, che il criterio di successo della spec vieta. Ma la protezione che
offre e' reale, quindi non basta toglierla: va sostituita con qualcosa che
protegga senza cablare un nome. Un avviso che dice «N modelli pubblicati
valorizzano questa dimensione; il catalogo la espone a GEBAN; passando al
generico il catalogo potra' restituire un modello che non la valorizza» e'
derivato dai dati, vale per **ogni** dimensione e non conosce la parola
`lingua`.

**Cosa NON cambia**: la policy resta pre-impostata correttamente. La migration
`0018` l'ha scritta per i tipi documento esistenti e `POLICY_DI_RIPIEGO`
(`{"lingua": False, "livello": True}`) la scrive per ogni tipo nuovo alla
creazione, in `_tipo_per_integrazione`. L'admin la rivede, non la inventa. Il
comportamento di oggi non cambia da solo: cambia solo se qualcuno lo cambia
deliberatamente.

**Rischio conservato e dichiarato**: si passa da un vincolo **strutturale** — un
bando senza lingua non e' rappresentabile, nessun bug puo' produrlo — a un
vincolo **configurato**. Se la policy della lingua del bando venisse portata a
`true`, il fallback del catalogo si attiverebbe (DEC-011-FALLBACK-GOVERNATO-DA-POLICY):
GEBAN chiede `lingua=EN`, non trova il modello inglese, riceve il
`modello_versione_id` del modello generico e genera **un documento che non e'
inglese, credendo di aver ottenuto quello che aveva chiesto**. Non un errore: un
documento sbagliato consegnato in silenzio. E' esattamente cio' che
`DEC-001-LINGUA-IT-EN` proteggeva.

Mitigazione, non eliminazione: l'avviso in schermata descrive questo scenario, e
un test verifica che con le policy di default una richiesta `lingua=EN` senza
modello inglese **non** ripieghi sul generico.

**Precisazione utile nei task**: portare la policy della lingua a generico
**non** rende impossibile l'inglese — i modelli con `lingua = EN` restano
creabili. Rende inaffidabile la *distinzione*. L'avviso va scritto di
conseguenza: il pericolo e' la risposta sbagliata, non la funzione mancante.

## DEC-011-DEFAULT-DIMENSIONE (decisa 2026-09-23, assorbe DEC-002-DEFAULT-VALORE-DIMENSIONE)

*(Rivista lo stesso giorno. La prima stesura decideva «nessun default»: sicura
ma costava un clic su ogni dimensione, sempre, per proteggere da un caso raro.
L'utente ha chiesto di conservare la comodita' attuale; la revisione tiene
insieme le due cose.)*

**Decisione**: il valore proposto e' una **proprieta' dichiarata della
dimensione**. `PolicyDimensione` guadagna `valore_default: str | None`, scelto
nella schermata Dimensioni dove l'admin gia' imposta la policy. Il form
preseleziona quel valore se c'e', e non preseleziona niente se e' vuoto. Per una
dimensione che ammette il generico, «nessun valore» e' un default esprimibile.

**Motivazione**: il comportamento odierno — il primo valore dell'elenco — sembra
una regola e non lo e'. `IT` esce perche' GEBAN elenca l'italiano per primo, e
**il contratto discovery non garantisce che quell'ordine resti stabile**: se
GEBAN riordinasse l'elenco, il form inizierebbe a proporre `EN` e nessuno se ne
accorgerebbe finche' non nascesse un bando inglese per sbaglio. FR-011 vieta
l'ordine come regola proprio per questo.

Con il default dichiarato, per il bando si imposta `lingua → IT` e
`livello_professionale → generico`: **l'admin vede esattamente quello che vede
oggi**, ma perche' l'ha deciso, non perche' l'integrazione elenca in
quell'ordine. Per `area_geografica` si lascia vuoto, e il form non propone
nulla — giusto, perche' non esiste un'area «normale».

**Alternativa scartata — nessun default**: soddisfa FR-011 nel modo piu' rigido
ma sposta su ogni creazione un costo che si paga una volta sola in
configurazione. Rigore pagato dall'utente sbagliato.

**Alternativa scartata — primo valore dell'elenco**: e' il comportamento
odierno, ed e' esattamente cio' che FR-011 vieta. Adottarlo richiederebbe di
modificare FR-011, non di interpretarlo.

**Costo**: una colonna su `PolicyDimensione`, un controllo nella schermata gia'
esistente, una migration. Contenuto, e chiude
`DEC-002-DEFAULT-VALORE-DIMENSIONE` invece di aggirarla.

**Verifica di FR-011**: «la preselezione proviene da `valore_default`, mai
dall'ordine dell'albero». Un test deve riordinare i valori nella risposta
discovery e verificare che la preselezione **non cambi**.

## DEC-011-FALLBACK-GOVERNATO-DA-POLICY (decisa 2026-09-23, generalizza DEC-007-FALLBACK-LIVELLO-CATALOGO)

**Decisione**: il fallback di `GET /catalogo/modelli` diventa un ciclo sulle
dimensioni richieste: per ogni dimensione la cui policy ha
`consente_valore_generico = true`, se la ricerca con valore esplicito non
produce versioni, si ritenta con quella dimensione non valorizzata. Dove la
policy richiede un valore esplicito, il fallback non scatta.

**Motivazione**: FR-010 in forma diretta. Il comportamento osservabile per
`livello_professionale` non cambia — `DEC-007-FALLBACK-LIVELLO-CATALOGO` resta
valida nel merito — ma smette di essere un nome nel codice.

**Rischio conservato, come chiede la spec**: la protezione della lingua
(«tornare un'edizione diversa da quella esplicitamente richiesta sarebbe
scorretto, non solo una scorciatoia») oggi e' automatica perche' la lingua ha
`consente_valore_generico = false`. Con la regola generale, se quella policy
cambiasse, il fallback sulla lingua si attiverebbe come effetto collaterale.
Il piano **non** aggiunge una protezione speciale sulla lingua, perche' sarebbe
di nuovo un nome nel codice. Conserva invece la motivazione come commento sulla
policy e come test che verifica il comportamento con la policy di default.

**Ordine del fallback quando piu' dimensioni ammettono il generico**: il piano
adotta il rilassamento **una dimensione alla volta, in ordine alfabetico di
nome**, e si ferma al primo risultato non vuoto. Motivazione: il risultato e'
deterministico e non dipende dall'ordine dell'albero (stesso principio di
FR-011). La risposta deve dichiarare *quali* dimensioni sono state rilassate,
non solo che un fallback c'e' stato — `fallback_applicato: bool` non basta piu'.

## DEC-011-IDENTITA-SENZA-NOMI-CABLATI (decisa 2026-09-23)

**Decisione**: `_identita_modello` compone codice e nome dai valori di
dimensione presenti, in ordine alfabetico di nome dimensione, usando il valore
grezzo. Spariscono `"Italiano"`, `"Inglese"`, `"Tutte le lingue"`, `"Livello X"`,
`"Tutti i livelli"`.

**Motivazione**: FR-003 (due modelli diversi non ricevono mai lo stesso nome) e
il criterio di successo («nessuna dimensione resta scritta a mano»). I nomi
umani per lingua e livello sono, letteralmente, dimensioni cablate nel codice;
per `area_geografica` non esisterebbero comunque.

**Conseguenza accettata e da dichiarare all'utente**: i nomi dei modelli nuovi
diventano meno discorsivi — `... - IT - VI - 2026-09-23` invece di
`... - Livello VI - Italiano - 2026-09-23`. I modelli **esistenti non vengono
rinominati** dalla migrazione (FR-007 protegge l'identita'), quindi per un
periodo convivranno due stili di nome. E' un costo estetico a fronte di un
requisito strutturale; se non fosse accettabile, l'alternativa e' una mappa di
etichette configurata per dimensione, che e' configurazione nuova e andrebbe
decisa a parte.

## DEC-011-MIGRAZIONE-IN-UN-PASSO (decisa 2026-09-23)

**Decisione**: una sola migration Alembic (`0020`) che, nell'ordine:
aggiunge `dimensioni JSONB NOT NULL DEFAULT '{}'`; la popola da `lingua` e
`livello_professionale` riga per riga; crea l'indice GIN; rimuove il
`CheckConstraint ck_modello_documento_lingua`; elimina le due colonne. Downgrade
simmetrico che ricostruisce le colonne dalle chiavi corrispondenti.

**Motivazione**: FR-007 chiede che identita', pubblicazione e collegamento ai
documenti generati siano preservati. Nessuno dei tre passa dalle due colonne:
`codice` e `nome` sono colonne proprie e non vengono ricalcolati; lo stato di
pubblicazione vive su `modello_versione`; il documento generato punta al
modello per id. La migrazione tocca quindi solo la *rappresentazione* della
categorizzazione. Un doppio passo (scrivi su entrambe, poi elimina) servirebbe
per un rilascio senza fermo con due versioni del codice in esercizio: non e' il
caso di questo servizio oggi, e aggiungerebbe una fase di doppia verita'.

**Regola di popolamento**: `lingua` e' NOT NULL, quindi produce sempre
`{"lingua": <valore>}`. `livello_professionale` NULL **non** produce la chiave
`livello` — coerente con FR-006: assenza di chiave significa dimensione non
valorizzata, che e' esattamente il significato odierno di quella colonna NULL
sotto una policy che ammette il generico.

**Verifica obbligatoria**: la migration va provata su PostgreSQL reale con dati,
non solo su SQLite di test — `010/T073` ha gia' aperto questo punto per le
fondazioni amministrative. Va messo a task.

## DEC-011-VARIANTE-RESTA-SEPARATA (conferma, non decisione nuova)

`variante` resta una colonna propria di `modello_documento` e **non** entra in
`dimensioni`. FR-012 lo impone: la variante la decide l'admin, le dimensioni le
dichiara l'integrazione. Entrambe concorrono all'unicita' della pubblicazione,
come due termini distinti della stessa condizione.

## DEC-011-DERIVAZIONE-GOVERNATA-DA-POLICY (decisa 2026-09-23, sostituisce DEC-011-EDIZIONE-DERIVATA-INVARIATA)

*(La prima stesura — `DEC-011-EDIZIONE-DERIVATA-INVARIATA` — teneva la
derivazione legata alla lingua come deroga dichiarata, perche' FR-013 riservava
la generalizzazione a «una decisione nuova». L'utente ha preso quella decisione
lo stesso giorno, e la sua motivazione e' piu' solida della deroga.)*

**Decisione**: la derivazione si definisce sulla **dimensione**, non sulla
lingua. La funzione e' disponibile per una dimensione che, su quel tipo
documento, ha `consente_valore_generico = false` e di cui la foglia dichiara
almeno due valori. Il vincolo passa da `(derivato_da_modello_id, lingua)` a
`(derivato_da_modello_id, nome_dimensione, valore)`. Quando piu' dimensioni o
piu' valori alternativi sono candidati, il sistema **chiede**, non sceglie.

Tradotto in requisiti: FR-013 riscritto, piu' FR-014 nuovo.

**Motivazione, che e' il punto interessante**: la funzione «crea edizione
collegata» ha senso solo se il modello di origine **ha** un valore per quella
dimensione. Se la dimensione ammettesse il generico, esisterebbe un modello che
non la valorizza, e «derivane un'altra versione» non vorrebbe dire niente. La
disponibilita' della funzione coincide quindi **esattamente** con
`consente_valore_generico = false`. Non serve dichiarare che la lingua e'
speciale: la policy che la rende obbligatoria e' gia' la condizione che rende
sensata la derivazione. Il nome esce dal codice senza perdere nulla.

**Comportamento invariato per il bando**: la sola dimensione obbligatoria di
BANDO e' `lingua`, con due valori. Da un modello `IT` l'unica alternativa e'
`EN`: nessuna domanda, stesso comportamento di oggi. La generalita' si paga solo
quando serve.

**Costo reale, misurato**: piu' basso del previsto. `_raggruppa_edizioni`
(`backend/app/catalog/service.py:155`) lavora gia' **solo** su
`derivato_da_modello_id` e non guarda la lingua: non va toccato. Cambiano
`crea_edizione_derivata` e `get_edizione_derivata`
(`backend/app/builder/repository.py:278`), il vincolo unico, e
`EdizioneDerivataCatalogo` nel contratto, che riceve lo stesso trattamento di
`ModelloCatalogo` (`lingua` nullable piu' `dimensioni`).

**Effetto sul criterio di successo**: sparisce l'unica deroga. «Nessuna
dimensione resta scritta a mano nel codice» diventa vero senza eccezioni.

**Effetto sul conflitto con `007`**: si chiude **correggendo `011`, non `007`**.
`007/spec.md:127-128` diceva gia' «il meccanismo, oggi limitato a `lingua`, si
generalizza a qualunque dimensione con `consente_valore_generico=false`»: aveva
ragione, ed era la prima stesura di FR-013 a essere in conflitto con lui.

**Da testare**: su un tipo documento senza dimensioni obbligatorie la funzione
non e' offerta — non e' un errore da gestire, e' un pulsante che non compare.

## Domande senza risposta a fine Phase 0

Nessuna incognita tecnica residua, e **nessun blocco del piano dipende da una
risposta esterna**. La prima stesura ne dichiarava uno — l'esposizione nel
catalogo dei tipi documento senza lingua — poi sciolto da
DEC-011-CONTRATTO-GEBAN-ADDITIVO.

Resta una **comunicazione** da fare, che non blocca l'implementazione ma deve
precedere il rilascio:

- **Presa d'atto di GEBAN su `ModelloCatalogoSchema.lingua` nullable.** Nessun
  lavoro richiesto a GEBAN, nessun cambiamento nelle risposte che riceve oggi;
  eventuale ricompilazione del client generato dall'OpenAPI. Va messa a task
  come consegna, non come attesa.

Fuori piano ma da fare, gia' rilevato nella spec: segnalare a GEBAN il refuso
`descrizione_em` / `medaglione_em` (dovrebbero essere `_en`), sistematico su
tutte e 65 le foglie, **prima** che entri in modelli pubblicati.
