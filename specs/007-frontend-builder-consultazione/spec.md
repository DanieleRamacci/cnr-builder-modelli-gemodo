# Feature Specification: Frontend Builder E Consultazione

**Feature Branch**: `007-frontend-builder-consultazione`

**Created**: 2026-06-19

**Status**: In implementazione (2026-09-18) - primo incremento descritto in `plan.md`/
`tasks.md`, scope MVP ADR 0002 (User Story 4/5 sotto), User Story 1/2/3 restano Draft/
scope futuro.

**Input**: Estratta da `PROPOSTA-servizio-gestione-modelli-bando.md` sezioni §11 e §16.6.

Aggiornamento 2026-09-18: incremento Contesti e transizioni di versione
implementato e verificato localmente (T039/T040/T044), senza editor completo.
US1/US2 restano parziali; naming automatico, lingua e livello sono T041-T043.
Il quality gate indipendente non e' superato.

## Clarifications

### Session 2026-09-21 (design handoff `design_handoff_modellario/`)

Riferimento grafico ricevuto per l'incremento futuro (User Story 1/2/3, editor
completo): `design_handoff_modellario/README.md` + `screens.json` + il
prototipo HTML `design/Gestione Modelli.dc.html`. E' un prototipo generico per
PA (contesti di esempio "Appalti e contratti" ecc.), hi-fi su colori/
tipografia/spaziature/stati, **da adattare** ai contesti reali di GEMODO, non
da copiare come codice. Sette schermate: 1a contexts-list, 1b/1c/1d varianti
della lista modelli, 2a categorize-wizard, 2b builder-editor, 3a derive-model.

Decisioni confermate con l'utente su due conflitti reali fra design e
implementazione MVP gia' costruita (T039/T040/T055):

- **1a sostituisce le tab dei contesti**: la pagina dedicata a card
  (ricerca, filtri a chip, metriche) diventa la nuova landing `/contesti` per
  il prossimo incremento, al posto delle tab attuali dentro la stessa pagina.
  Richiede rilavorare uno schermo gia' verificato con Playwright - non e' un
  semplice restyle.
- **2a adotta le tendine a cascata**: il futuro editor completo sostituisce la
  navigazione ad albero cliccabile (usata oggi in `modello-crea.component.ts`
  per l'MVP US5) con 4 select L1-L4 dipendenti, azzeramento a cascata e
  stepper 3 passi, come nel prototipo.
- **1b tabella resta il default, 1c griglia il toggle vista** (`?view=grid`):
  seguito il suggerimento del designer nel README, non ridiscusso. **1d
  master/detail** resta proposta unica non pianificata, valutabile in un
  incremento successivo.
- **3a (`Crea modello derivato`) e' il target futuro** per generare da un
  modello esistente una variante che eredita sezioni, testi, flag di blocco e
  mapping segnaposto del padre, cambiando solo attributi aggiuntivi (lingua in
  primis). **Dipende da 2b** (editor completo con sezioni/segnaposto persistiti
  per versione), che non esiste ancora: finche' 2b non e' costruito, 3a non e'
  implementabile nella sua forma piena. Il meccanismo oggi disponibile e gia'
  funzionante (`T067`, "Crea edizione collegata" in Contesti/lista modelli)
  resta l'unico modo reale di ottenere un modello derivato per lingua fino a
  quel momento: precompila integrazione/tipo/percorso/livello e propone la
  lingua ancora disponibile, ma crea un modello indipendente (nessuna copia di
  contenuto, nessun riferimento al padre) - un sottoinsieme volutamente piu'
  semplice di 3a.

**Non ancora modellato, richiede decisione prima di specificare FR/schema**:
3a nel design propone dimensioni di derivazione generiche oltre la lingua
(esempi nel prototipo: ambito, canale, soglia) con select "eredita" per
ciascuna. Nessuna di queste esiste oggi nel dominio (`001`/`002` modellano solo
`lingua` e `livello_professionale`, migration `0016`). Non vanno inventate qui:
se servono davvero, richiedono un nuovo `DEC-007-*` in
`docs/decision-register.yaml` con owner e impatto su `001`/`002`, non solo una
riga di UI. Restano inoltre esplicitamente aperte le domande gia' segnalate dal
design stesso (`screens.json.screens[].openQuestions` di 3a): derivazione a piu'
livelli e sua rappresentazione in 1b, traduzione automatica dei testi ereditati
al cambio lingua, se rendere modificabili i livelli L1-L4 del derivato.

### Session 2026-09-21 (fallback catalogo, policy dimensione, associazione)

Chiude parte delle domande lasciate aperte dalla sessione precedente
(dimensioni di derivazione generiche oltre la lingua) con tre decisioni
registrate in `docs/decision-register.yaml`:

- **`DEC-007-FALLBACK-LIVELLO-CATALOGO`**: `GET /catalogo/modelli` con un
  `livello_professionale` specifico privo di modello dedicato MUST cercare, in
  un secondo passo esplicito, il modello con `livello_professionale IS NULL`
  (il generico) invece di restituire lista vuota. Supera *parzialmente* la
  regola "nessun fallback automatico" della sessione 2026-09-18 (mai stata una
  voce di questo registro, solo prosa): il fallback vale **solo** per il
  livello. `lingua` e `percorso_categorizzazione` restano a match esatto,
  senza fallback - motivato dal fatto che ogni edizione linguistica ha un
  ciclo di vita di pubblicazione indipendente (FR-034..038), tornare
  un'edizione diversa da quella richiesta sarebbe scorretto, non una
  scorciatoia accettabile.
- **`DEC-002-POLICY-DIMENSIONE-CATEGORIZZAZIONE`**: ogni dimensione della
  categorizzazione (`livello`, `lingua`, e future) ha una policy booleana
  `consente_valore_generico`, registrata per `tipo_documento_id +
  nome_dimensione` (una volta per nome, non per nodo/foglia). Oggi hardcoded
  nel codice; va resa configurazione esplicita e persistita, **separata** da
  `DefinizioneStruttura`/`StrutturaInput` (l'esempio presentazionale di
  contratto per GEBAN, modulo `configurazione`) per non legare un
  comportamento runtime a un documento che resta volutamente non vincolante.
  L'albero reale, per un contesto integrato, arriva sempre live dall'adapter
  discovery, mai da quell'esempio. Owner spec `002`, impatto su `010` (dove va
  costruita la schermata di configurazione, sezione dedicata sotto) e su
  questa spec (il form di creazione modello legge questa policy invece di
  avere lingua/livello hardcoded).
- **`DEC-002-ASSOCIAZIONE-MODELLO-DERIVATO`**: la creazione di un'edizione
  collegata (oggi "Crea edizione collegata"/T067; nome provvisorio in UI
  "Crea versione inglese") MUST registrare un riferimento esplicito al modello
  di origine (associazione dedicata, non un `famiglia_modello_id` sul modello
  - resta valido quanto deciso in `DEC-001-LINGUA-IT-EN`). `GET
  /catalogo/modelli` MUST annidare le edizioni collegate dentro il modello che
  le referenzia, non piu' righe piatte slegate. Il meccanismo, oggi limitato a
  `lingua`, si generalizza a qualunque dimensione con
  `consente_valore_generico=false` una volta introdotta la policy sopra.

**Aggiornamento 2026-09-21 (bis)**: il design handoff e' stato esteso con la
schermata 4a (`configure-dimensions`), che colloca questa configurazione
sotto un'area admin "Impostazioni", quindi in `010`, non in questa spec -
coerente con l'ipotesi gia' scritta qui sopra. Resta pero' **aperto anche nel
design stesso** (`screens.json`, `openQuestions` di 4a: "se questa UI vive in
una sezione Impostazioni a se o dentro il builder") - trattarlo come proposta
forte, non decisione chiusa, finche' non confermato esplicitamente dall'utente.
Vedi `010`'s Clarifications sessione "bis" e la User Story 5 li' aggiunta.

### Session 2026-09-21

- Q: Come interagisce la lingua del modello con i campi discovery? -> A: La
  lingua identifica il modello, mentre la versione conserva tutti i campi della
  foglia; possono esistere due modelli distinti, IT ed EN, con gli stessi campi.
- Q: I livelli professionali della stessa foglia usano contratti campi diversi?
  -> A: No. Tutti i livelli dell'ultima foglia usano gli stessi campi; il livello
  restringe lo scope e puo' distinguere modelli con contenuti diversi.
- Q: Come vengono determinate lingua e livello disponibili? -> A: Sono
  dimensioni controllate della categorizzazione ricevuta dalla discovery sulla
  foglia; GEMODO persiste sul modello la combinazione scelta, senza mantenere
  anagrafiche interne di profili, livelli o lingue.
- Q: La variante richiede una selezione distinta da lingua e livello? -> A: No.
  In questo incremento resta internamente STANDARD e non compare nel form.
- Q: Serve un `famiglia_modello_id` per collegare italiano e inglese? -> A: No.
  Sono modelli separati e il derivato registra soltanto il riferimento diretto al
  modello di origine (`derivato_da_modello_id`). Integrazione, tipo documento,
  percorso di categorizzazione e livello restano invariati; la lingua distingue
  le edizioni. Modelli creati separatamente con gli stessi attributi non vengono
  collegati automaticamente.
- Q: Come richiede GEBAN entrambe le edizioni? -> A: La ricerca catalogo senza
  filtro lingua restituisce tutte le versioni pubblicate corrispondenti. GEBAN
  effettua una chiamata di generazione per ciascuna `modello_versione_id`, con i
  dati previsti dal relativo contratto. `bando_inglese` e' ritirato.

### Pulizia modelli richiesta 2026-09-18

Le installazioni nuove devono terminare senza modelli demo, salvo opt-in
esplicito di test. Non cancellare automaticamente gli ambienti gia' utilizzati.
Contesti permette di eliminare un modello con conferma: eliminazione logica
autorizzata per contesto e auditata, esclusa da catalogo e nuove generazioni.
Versioni e PDF precedenti restano conservati.

### Decisione MVP 2026-09-17 - ADR 0002

Frontend Angular con Design Angular Kit. Admin: tabella integrazioni
inizialmente vuota, creazione manuale, nome/contesto/singolo URL, verifica e
data/esito/errori. Nessun GEBAN preinstallato. Manager: integrazioni connesse
autorizzate, navigazione ricorsiva fino ai campi, creazione modello di test
in BOZZA. Editor visuale e composizione manuale FR-011 sono rinviati oltre
questo MVP: obiettivi successivi, non prerequisiti del PDF semplice.
Vedi [ADR 0002](../../docs/adr/0002-integrazioni-contesti-modelli-test.md).
Questo e' il target confermato. Dal 2026-09-18 la feature attiva in
`.specify/feature.json` e' 007; l'implementazione segue `tasks.md` e non e'
ancora certificata come completa.


### Session 2026-06-22

- Q: Stiamo creando la spec da zero? -> A: No. La spec esiste gia' come draft di copertura; questa sessione la integra con decisioni emerse da builder, sezioni, storage/idempotenza e sicurezza.
- Q: Qual e' il confine con GEBAN? -> A: GEBAN non usa il frontend GEMODO per compilare dati di processo; GEBAN usa le API catalogo/contratto, costruisce la propria maschera e invia richieste di generazione.
- Q: Le autorizzazioni sono applicate dal frontend? -> A: Il frontend abilita, nasconde o disabilita azioni in base a ruolo e contesto, ma il controllo autoritativo resta sempre nel servizio backend secondo la spec sicurezza.
- Q: Il design visuale e lo stack frontend fanno parte di questa spec? -> A: No. Questa spec definisce funzioni, flussi e stati utente; stack e dettagli visuali saranno definiti nel piano tecnico.

### Richiesta successiva al collaudo 2026-09-18 - Contesti e creazione guidata

Da pianificare dopo il minimo US5, non ancora implementata. La gestione generale
dei modelli e' gia' coperta da US1, ma il seguente percorso ne precisa la UX:

- Sostituire l'accesso principale "Crea modello" con "Contesti".
- Mostrare i contesti autorizzati come tab, non come menu a tendina. La presenza
  nel token non concede automaticamente gestione: il backend determina i permessi.
- Selezionando un contesto, mostrare una tabella dei modelli gia' creati, comprese
  le bozze, e il pulsante "Crea modello". Il pulsante richiede il permesso di
  gestione e un'integrazione connessa; un contesto senza modelli resta visibile.
- Riutilizzare il flusso discovery corrente, conservando contesto e integrazione
  nel ritorno alla lista e dopo la creazione. Se piu' integrazioni appartengono
  allo stesso contesto, scegliere esplicitamente la sorgente senza confonderle.
- Codice e nome non sono input liberi: il backend li genera dalla categorizzazione
  validata. Il nome include descrizioni, data di creazione e lingua; il codice
  resta stabile e univoco anche per creazioni simultanee dello stesso percorso.
  Il formato esatto e i limiti di lunghezza devono essere fissati nel contratto.
- La variante non e' testo libero: in questo incremento e' sempre STANDARD,
  assegnata dal backend e non mostrata nel form. Variante, livello e lingua
  restano concetti distinti.
  Non generare varianti dalla data o dal codice univoco per aggirare il vincolo
  di unica versione pubblicata corrente. Variante, versione e lingua sono distinte.
- Prima della conferma, scegliere la lingua da un menu con Italiano/IT e
  Inglese/EN. Disponibilita', campi necessari e persistenza della lingua richiedono
  contratto e validazione backend; non basta filtrare le etichette nel frontend.
La lingua e' una dimensione controllata della categorizzazione esposta dalla
foglia discovery e una proprieta' persistita del modello. Distingue modelli IT
ed EN anche quando condividono percorso e contratto campi. La versione conserva
l'intero insieme dei campi della foglia, senza filtrarli per lingua.

Dalla scheda di un modello il gestore puo' avviare la creazione di un'edizione
collegata in un'altra lingua. Il form riusa integrazione, tipo, percorso e livello,
permette di scegliere soltanto una lingua ancora disponibile e crea un nuovo
modello con identificativi e versioni propri. Il collegamento non richiede una
famiglia: il derivato registra il riferimento diretto al modello origine e copia
in una nuova versione BOZZA struttura e campi della versione piu' recente del
padre. La copia non modifica il modello origine e non pubblica automaticamente
la nuova edizione.

Chiarimento confermato 2026-09-18: "livello" indica il livello professionale,
facoltativo e distinto dalla lingua. Il menu deve offrire "Tutti i livelli"
e i valori ammessi per il profilo scelto, provenienti da discovery/configurazione.
Se selezionato, il livello restringe la categorizzazione del modello e compare
nel nome automatico. Se non selezionato, il percorso resta al profilo scelto
(es. CTER) e il modello copre tutti i livelli di quel profilo, mai altri profili.
Questa copertura deve essere persistita esplicitamente, non dedotta dal nome.
Tutti i livelli dichiarati sull'ultima foglia condividono lo stesso contratto
campi della foglia. Livello generico e livelli specifici possono tuttavia avere
modelli e contenuti differenti; il livello non modifica o filtra i campi.

Il builder ammette modelli solo sull'ultima foglia con campi. La foglia discovery
espone `livelli_possibili` e `lingue_possibili`; GEMODO non mantiene tabelle
anagrafiche interne equivalenti. Il modello persiste percorso, livello scelto
(`null` significa "Tutti i livelli") e lingua scelta. Se la discovery rappresenta
i livelli come rami separati, deve esporre anche una foglia aggregata esplicita
per consentire il modello generico "Tutti i livelli".
Generico e specifico sono modelli distinti, con identificativi e versioni
proprie. Il nome del generico omette la specifica del livello; il nome dello
specifico la include. Il catalogo applica la precedenza esatta e il solo fallback
di livello definito in FR-024. Entrambi possono coesistere;
la pubblicazione e l'archiviazione di uno non devono sostituire l'altro.
Adeguare la chiave del vincolo di pubblicazione includendo lo scope del
livello professionale e la lingua, senza usarne il nome o inventare varianti
univoche. Tipo documento, percorso di categorizzazione, livello e lingua sono
sufficienti a individuare lo scope funzionale del modello.

Acceptance del prossimo incremento: un manager ACE apre Contesti, seleziona
una tab, vede solo i modelli autorizzati di quel contesto, crea una bozza senza
scrivere codice/nome/variante e torna alla tabella con il nuovo record. Contesti
non autorizzati, lingua non disponibile, lista vuota ed errore di lettura sono
stati distinti; nessuna autorizzazione e' demandata alle sole tab frontend.

### Session 2026-09-14 (propagazione da `001`)

- `DEC-001-UFFICIO-PROPRIETARIO` (confermata in `docs/decision-register.yaml`,
  *superseduta 2026-09-15 da `DEC-001-CONTESTO-SOSTITUISCE-UFFICIO`*): oltre
  a GEBAN (un'Applicazione che non usa il frontend, gia' chiarito sopra), il frontend
  GEMODO puo' avere utenti umani il cui token contiene un contesto proprietario (es.
  un futuro contesto "contratti") che accedono via SSO CNR per creare/gestire in
  autonomia modelli dei tipi documento associati a quel contesto (la definizione di
  categorie/tipologie/contratti dati e' invece scope della `010`, non di questo
  frontend). Questo e' distinto dal caso GEBAN gia' descritto ed e' da considerare
  quando questa spec verra' pianificata in dettaglio.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestire modelli da interfaccia builder (Priority: P1)

Come gestore modelli, voglio usare un'interfaccia dedicata per configurare tipi,
categorie, modelli, campi e sezioni, cosi' da lavorare senza interventi tecnici sul codice.

**Why this priority**: il builder e' lo strumento operativo degli utenti interni.

**Independent Test**: un gestore puo' completare la configurazione base di un modello in
bozza dall'interfaccia.

**Acceptance Scenarios**:

1. **Given** un gestore autorizzato, **When** accede al builder, **Then** puo' gestire
   elementi coerenti con i propri ruoli.
2. **Given** un modello in bozza, **When** il gestore modifica campi e sezioni, **Then**
   vede lo stato aggiornato prima della pubblicazione.
3. **Given** una versione pubblicata, **When** il gestore vuole modificarne il contenuto,
   **Then** l'interfaccia indirizza alla creazione o modifica di una bozza derivata e non
   consente modifica diretta della versione pubblicata.
4. **Given** il gestore compone sezioni con placeholder, **When** inserisce contenuti,
   **Then** l'interfaccia propone placeholder disponibili e mostra anomalie funzionali
   senza richiedere digitazione tecnica libera.
5. **Given** un modello esistente con sezioni e segnaposto gia' composti, **When** il
   gestore avvia "Crea modello derivato" (schermata 3a, design handoff), **Then**
   l'interfaccia mostra la categorizzazione ereditata in sola lettura, propone solo gli
   attributi aggiuntivi ancora disponibili (lingua in primis) e crea un nuovo modello
   indipendente che copia sezioni/testi/segnaposto del padre senza modificarlo. Finche'
   l'editor completo (2b) non esiste, questo scenario resta soddisfatto nella sua forma
   ridotta dall'azione "Crea edizione collegata" gia' disponibile (T067), che precompila
   la creazione ma non copia contenuto ne' mantiene un riferimento al padre.

---

### User Story 2 - Revisionare e pubblicare da interfaccia (Priority: P1)

Come approvatore modelli, voglio revisionare, pubblicare o archiviare versioni modello,
cosi' da controllare il catalogo operativo esposto a GEBAN.

**Why this priority**: la pubblicazione richiede un controllo umano.

**Independent Test**: un approvatore puo' portare una versione pronta a stato pubblicato
o archiviato secondo i permessi.

**Acceptance Scenarios**:

1. **Given** una versione pronta, **When** l'approvatore la pubblica, **Then** diventa
   visibile nel catalogo operativo.
2. **Given** una versione pubblicata, **When** viene archiviata, **Then** non e' piu'
   proposta per nuove generazioni.
3. **Given** una versione con errori di contratto dati o placeholder, **When** l'utente
   tenta la pubblicazione, **Then** l'interfaccia mostra i blocchi restituiti dal servizio
   e non presenta la pubblicazione come riuscita.
4. **Given** un utente senza ruolo approvativo richiesto, **When** accede a una versione
   pubblicabile, **Then** non puo' completare pubblicazione o archiviazione dall'interfaccia.

---

### User Story 3 - Consultare generazioni (Priority: P2)

Come utente autorizzato, voglio consultare le generazioni documento, cosi' da vedere
stato, payload, esito validazione, riferimento file e audit.

**Why this priority**: la consultazione serve al supporto operativo e alla verifica.

**Independent Test**: una generazione esistente puo' essere trovata con filtri funzionali
e consultata nei suoi metadati.

**Acceptance Scenarios**:

1. **Given** esistono generazioni, **When** l'utente filtra per sistema e tipo documento,
   **Then** vede solo risultati coerenti con filtri e autorizzazioni.
2. **Given** una generazione fallita, **When** viene aperta, **Then** sono visibili esito e
   motivazione funzionale.
3. **Given** una generazione completata, **When** l'utente autorizzato la apre, **Then**
   vede stato, versione modello, tipo output, bozza/ufficiale, metadati file e azioni di
   download consentite.
4. **Given** una generazione non recuperabile o non ancora completata, **When** l'utente
   richiede il download, **Then** l'interfaccia mostra uno stato coerente e non suggerisce
   che il file sia disponibile.

---

### User Story 4 - Registrare e verificare un'integrazione (Priority: P1)

*(Aggiunta 2026-09-18 in fase di planning: FR-021 esisteva gia' senza una User Story
che ne organizzasse gli scenari di accettazione - stesso gap gia' visto e corretto per
FR-025..030 della spec 001. Questa e User Story 5 sono l'MVP confermato dall'ADR 0002;
le User Story 1/2/3 sopra restano scope futuro, non prerequisito.)*

Come amministratore GEMODO, voglio registrare un'integrazione con un software esterno,
configurarne l'endpoint discovery e verificarne la conformita', cosi' da attivarla per i
manager del suo contesto senza toccare file di configurazione o fare un deploy.

**Why this priority**: senza questo, nessuna integrazione puo' mai diventare `CONNESSO` se
non tramite intervento diretto sul database - e' il prerequisito di ogni altro uso operativo
del catalogo esterno (010).

**Independent Test**: un admin puo' creare un'integrazione, vederla in stato "Non
verificato", configurarne l'URL e ottenere "Connesso" o "Errore" con motivi sanificati dopo
una verifica reale, senza mai eseguire una chiamata API a mano.

**Acceptance Scenarios**:

1. **Given** nessuna integrazione esiste ancora, **When** l'admin apre la schermata,
   **Then** la tabella e' vuota - nessun software preinstallato (FR-021).
2. **Given** un'integrazione appena creata, **When** l'admin la vede in lista, **Then** e'
   in stato "Non verificato" senza URL.
3. **Given** un'integrazione con URL configurato verso una sorgente conforme, **When**
   l'admin avvia la verifica, **Then** lo stato diventa "Connesso" con data e versione
   contratto visibili.
4. **Given** un'integrazione con URL irraggiungibile o con forma non conforme, **When** la
   verifica fallisce, **Then** lo stato diventa "Errore" con motivi sanificati, mai uno stack
   trace o un dettaglio tecnico grezzo.
5. **Given** una riconfigurazione basata su una revisione non piu' corrente, **When**
   l'admin salva, **Then** l'interfaccia mostra un conflitto e ricarica lo stato corrente,
   senza sovrascrivere silenziosamente.

---

### User Story 5 - Creare un modello di test dalla struttura scoperta (Priority: P1)

*(Aggiunta 2026-09-18, vedi nota su User Story 4. Copre FR-022/FR-023.)*

Come gestore modelli, voglio navigare la struttura di un'integrazione connessa e
autorizzata per il mio contesto e creare un modello di test in bozza, cosi' da provare un
nuovo tipo documento senza aspettare l'editor completo.

**Why this priority**: e' la prova concreta, richiesta esplicitamente per questo
incremento, che un modello puo' nascere dall'interfaccia e arrivare fino alla generazione
di un PDF di test (004/005) senza il builder visuale completo.

**Independent Test**: un gestore autorizzato su un contesto vede solo le integrazioni
connesse di quel contesto, naviga fino a una foglia e crea un modello che risulta in stato
BOZZA, verificabile anche da Swagger.

**Acceptance Scenarios**:

1. **Given** esistono integrazioni connesse in piu' contesti, **When** il gestore apre la
   lista, **Then** vede solo quelle del proprio contesto, anche se il suo token porta ruoli
   in altri contesti (nessuna fuga di permessi fra contesti).
2. **Given** un'integrazione connessa, **When** il gestore naviga l'albero, **Then** vede la
   struttura reale (profondita' variabile) restituita dalla sorgente esterna, non un
   catalogo locale.
3. **Given** una foglia selezionata, **When** il gestore crea un modello, **Then** ottiene un
   modello in stato BOZZA con i dati inseriti, senza che si apra alcun editor di campi o
   sezioni (fuori scope di questo incremento).
4. **Given** un'integrazione non ancora connessa o un errore di trasporto verso la sorgente,
   **When** il gestore prova ad accedere alla struttura, **Then** l'interfaccia mostra lo
   stato reale (non connesso / errore di trasporto), mai una lista vuota che lo mascheri.

### Edge Cases

- Utente senza ruolo adeguato.
- Token scaduto o sessione non piu' autorizzata.
- Utente con ruolo GEBAN di generazione che tenta accesso al builder GEMODO.
- Utente builder che tenta consultazione o download non consentiti.
- Modello con validazioni incomplete.
- Versione modello pubblicata o archiviata mentre un utente sta modificando una bozza collegata.
- Tentativo di pubblicare una versione non approvata quando il workflow richiede approvazione separata.
- Placeholder non disponibili o campi complessi incompleti durante composizione sezioni.
- Generazione senza file disponibile.
- Generazione con riferimento documentale non recuperabile.
- Download richiesto per generazione fallita, annullata o non completata.
- Payload o snapshot dati non visualizzabile per autorizzazione insufficiente.
- Lista vuota.
- Errore di salvataggio durante modifica bozza.
- Errore funzionale restituito dal servizio che non deve esporre token, segreti o dettagli tecnici.

## Requirements *(mandatory)*

### Richiesta di collaudo 2026-09-18

La creazione dell'integrazione e' persistente e distinta dalla configurazione
dell'endpoint. Dopo nuovo login l'admin puo' riprenderla dalla lista anche
senza URL, con stato UI Da completare. Un errore di lettura non deve essere
confuso con registro vuoto. Il refresh fallito blocca le richieste protette;
la UI offre nuovo login mantenendo il percorso del record. Nessun retry
automatico delle scritture dopo un errore di autenticazione.

La shell mostra nome e icona utente in alto a destra. Il profilo permette
di visualizzare esplicitamente il token della propria sessione e fare logout.
La home mostra Integrazione servizi agli admin e Crea modello ai manager;
senza permessi mostra un messaggio di mancata autorizzazione. Il manager
puo' vedere e scegliere i contesti presenti nel proprio token, ma le
integrazioni e le azioni consentite sono sempre determinate dal backend.

### Functional Requirements

Incremento autorizzato 2026-09-18: Contesti e ciclo di vita versioni (US1/US2).
Il manager vede tab dei contesti autorizzati dal backend e una lista paginata
dei modelli, comprese bozze e modelli senza versioni. Ogni modello mostra
nome, codice, categorizzazione, variante, data e le proprie versioni con stato
e public_id utilizzabile nelle API documenti. L'azione Crea modello mantiene
contesto/sorgente; il ritorno alla lista preserva il contesto.
Le versioni offrono solo il prossimo passo valido: Invia in revisione,
Approva, Pubblica, con conferma esplicita. Il gestore ACE del contesto puo'
eseguire tutti e tre i passi secondo SEC-006-002; non si richiedono nuovi
ruoli ACE. Lo stato si aggiorna solo dopo risposta backend; su conflitto
si rilegge la lista. Pubblicazione puo' archiviare la versione corrente della
stessa combinazione secondo 002. I controlli backend verificano contesto e
appartenenza della versione al modello indicato nel percorso URL.
Editor completo, livello/lingua e naming automatico restano T041-T043.

- **FR-001**: L'interfaccia MUST permettere lettura dei tipi documento e categorie
  della sorgente autorizzata, non modifica del catalogo esterno. Configurare
  integrazioni resta riservato all'admin.
- **FR-002**: L'interfaccia MUST permettere gestione di modelli, versioni, campi e sezioni.
- **FR-003**: L'interfaccia MUST distinguere bozza, revisione, pubblicazione e archiviazione.
- **FR-004**: L'interfaccia MUST mostrare errori di validazione del modello prima della pubblicazione.
- **FR-005**: L'interfaccia MUST permettere consultazione di generazioni, stato, payload, validazione e riferimento file.
- **FR-006**: L'interfaccia MUST rispettare le autorizzazioni applicative definite dalla spec sicurezza.
- **FR-007**: GEBAN MUST NOT usare questo frontend per compilare dati di processo.
- **FR-008**: L'interfaccia MUST mostrare o abilitare azioni coerenti con ruolo, stato della risorsa e contesto operativo, fermo restando che l'autorizzazione definitiva e' applicata dal servizio backend.
- **FR-009**: L'interfaccia MUST gestire i workflow di versione modello `BOZZA`, `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`, `ARCHIVIATO` e `SOSPESO` coerentemente con le spec builder e sicurezza.
- **FR-010**: L'interfaccia MUST impedire modifica diretta di contenuti, campi e sezioni di versioni pubblicate e deve rendere chiara la creazione o modifica di bozze derivate. Nell'incremento corrente, "Crea versione inglese" MUST creare un modello indipendente collegato direttamente al padre e una versione BOZZA che copia struttura e campi della versione piu' recente del padre; la lingua e' l'unico attributo modificato. Nell'incremento futuro con editor completo, la stessa operazione MUST copiare anche sezioni, testi e segnaposto disponibili, senza modificare il padre.
- **FR-011**: L'interfaccia MUST supportare la composizione di sezioni con contenuto strutturato controllato e placeholder selezionabili tra quelli disponibili per la versione modello.
- **FR-012**: L'interfaccia MUST mostrare blocchi di pubblicazione relativi a campi richiesti, placeholder, schema dati, sezioni e validazioni di modello.
- **FR-013**: L'interfaccia MUST rendere evidente quando una generazione e' bozza o ufficiale.
- **FR-014**: L'interfaccia MUST consentire ricerca o filtro delle generazioni per criteri funzionali almeno su sistema richiedente, tipo documento/categoria, stato, periodo e autorizzazioni applicabili.
- **FR-015**: L'interfaccia MUST mostrare per una generazione consultabile almeno stato, timestamp, sistema richiedente, versione modello, tipo output, esito validazione, riferimento file quando disponibile e motivazione funzionale in caso di errore.
- **FR-016**: L'interfaccia MUST consentire download solo quando stato e autorizzazione lo permettono e deve mostrare stati distinti per file non disponibile, generazione fallita, riferimento non recuperabile e accesso non autorizzato.
- **FR-017**: L'interfaccia MUST NOT esporre payload completo, snapshot dati, audit dettagliato o metadati sensibili a utenti non autorizzati.
- **FR-018**: L'interfaccia MUST mostrare stati vuoti, caricamento, errore funzionale e salvataggio fallito in modo comprensibile per l'utente, senza presentare come completate operazioni non confermate dal servizio.
- **FR-019**: Le azioni sensibili avviate dall'interfaccia, incluse pubblicazione, archiviazione, consultazione rilevante e download, MUST essere coerenti con gli eventi audit previsti dalla spec sicurezza.
- **FR-020**: L'interfaccia MUST mantenere separati i percorsi operativi del builder GEMODO dalla consultazione/generazione documenti del flusso GEBAN.

- **FR-021**: L'admin MUST poter creare, elencare e configurare integrazioni
  con nome, codice_contesto e singolo endpoint, verificare e vedere stato,
  data e motivi sanificati. Lista vuota MUST NOT essere riempita da seed/token/env.
- **FR-022**: Il manager MUST poter navigare profondita' variabile fino alla
  foglia, vedere campi/proprieta' e creare un modello senza editor. Creazione
  e pubblicazione MUST essere azioni distinte e confermate dal backend.
- **FR-023**: Visibilita' e azioni MUST rispettare i permessi per ciascun
  contesto anche con token multicontesto; URL e funzioni amministrative MUST NOT
  essere esposti al manager privo di autorizzazione amministrativa.
- **FR-024**: `GET /catalogo/modelli` con `livello_professionale` valorizzato
  e privo di modello dedicato MUST tornare il modello con
  `livello_professionale IS NULL` della stessa combinazione tipo/percorso/lingua
  invece di lista vuota (`DEC-007-FALLBACK-LIVELLO-CATALOGO`). Il fallback
  MUST NOT applicarsi a `lingua` ne' a `percorso_categorizzazione`.
- **FR-025**: La risposta di `GET /catalogo/modelli` MUST annidare le edizioni
  collegate (oggi solo per lingua) dentro il modello che le referenzia
  (`DEC-002-ASSOCIAZIONE-MODELLO-DERIVATO`), non restituirle come righe piatte
  indipendenti. La risposta MUST indicare se il risultato deriva dal fallback e
  distinguere il livello richiesto dal livello effettivamente risolto.
- **FR-027**: `POST /builder/modelli/{modelloId}/edizioni-derivate` MUST
  accettare la lingua destinazione, verificare autorizzazione, disponibilita'
  discovery e assenza di un derivato equivalente, creare un modello con
  identificativi propri e `derivato_da_modello_id` valorizzato, quindi clonare
  struttura e campi della versione piu' recente del padre in una nuova versione
  BOZZA. L'operazione MUST essere atomica e auditata e MUST NOT pubblicare il
  derivato ne' modificare il padre.
- **FR-026** (2026-09-21, chiarito su richiesta esplicita dell'utente - prima
  implicito solo nelle Clarifications, non vincolante): quando una schermata
  gia' presente in `design_handoff_modellario/` (screens.json) viene
  pianificata per l'implementazione, indipendentemente dal suo stato attuale
  ("confermato" o "proposta"), l'interfaccia MUST seguirne struttura,
  organizzazione dei contenuti, flusso di interazione e stile visivo (design
  token: colori, tipografia Titillium Web/Roboto Mono, spaziature, raggi -
  vedi README.md "Design Tokens"), adattati solo ai vincoli tecnici del
  framework di destinazione (Angular + design-angular-kit al posto del CSS
  Bootstrap Italia del prototipo). Non e' ammesso un layout alternativo
  inventato quando esiste gia' una schermata disegnata per quel flusso. Questo
  vale per tutte le schermate elencate nella tabella sotto, per le schermate
  10 elencate nel Design Reference di `data-model.md` di quella spec, e per
  qualunque nuova schermata che venga aggiunta in futuro a
  `design_handoff_modellario/`. **Non copre** flussi per cui nessuna
  schermata esiste nel design (es. l'editor struttura tipo documento di `010`
  US1, gia' implementato prima che questa parte del design esistesse) - in
  quel caso restano validi solo i design token generali, non una struttura
  specifica da copiare, finche' non viene disegnata una schermata dedicata.

Correzione 2026-09-18 (T038): la creazione modello MUST conservare l'integrazione
selezionata nella navigazione. Tipo documentale e discovery sono risolti per
integrazione/codice; la creazione di versioni usa l'ownership persistita del modello.
Tipi legacy omonimi senza endpoint non devono interferire con questo flusso.

### Key Entities

Autorizzazione ACE confermata il 2026-09-18: i client interattivi autorizzati
derivano i permessi dai mapping di `contexts.<contesto>.roles`, senza essere
censiti nei client tecnici di ciascun profilo. Non sono richieste assegnazioni
aggiuntive di ruoli GEMODO agli utenti. Sistemi/profili inattivi, ruoli e contesti
non configurati non concedono permessi; ogni risorsa resta isolata per contesto.
Le chiamate tecniche conservano i controlli sul client e sul profilo ammesso.

- **Utente Builder**: operatore interno del servizio modelli.
- **Utente Consultazione**: utente o client autorizzato a visualizzare stato e metadati di generazioni documento.
- **Schermata Modello**: vista di gestione modello/versione.
- **Schermata Campi**: vista di gestione contratto dati.
- **Schermata Sezioni**: vista di gestione contenuti.
- **Schermata Generazioni**: vista di consultazione documenti generati.
- **Azione UI Autorizzata**: comando visibile o eseguibile in base a ruolo, stato risorsa e contesto, con enforcement finale backend.
- **Stato UI Versione Modello**: rappresentazione utente dello stato della versione modello e delle transizioni ammesse.
- **Filtro Consultazione Generazioni**: criterio funzionale usato per trovare generazioni consultabili.
- **Vista Dettaglio Generazione**: pagina o pannello che mostra stato, metadati, validazione, riferimento file e azioni consentite.
- **Errore Funzionale UI**: messaggio comprensibile che traduce un blocco applicativo senza esporre dettagli tecnici o sensibili.
- **Payload Consultabile**: dati ricevuti o snapshot visualizzabili solo quando autorizzazione e finalita' lo consentono.

### Schermate target dell'incremento futuro (design handoff)

Mappa screen id -> rotta -> stato, da `design_handoff_modellario/screens.json`,
confermata 2026-09-21 (vedi Clarifications). Sostituisce la landing e la
categorizzazione descritte nell'MVP attuale (Contesti a tab, albero
cliccabile) quando US1/US2/US3 verranno pianificate in dettaglio.

| id | schermata | rotta | stato |
| --- | --- | --- | --- |
| 1a | contexts-list | `/contesti` | sostituisce le tab attuali (confermato) |
| 1b | templates-table | `/contesti/:ctxId/modelli` | default confermato |
| 1c | templates-grid | `/contesti/:ctxId/modelli?view=grid` | toggle vista, confermato |
| 1d | templates-split | `/contesti/:ctxId/modelli/:modelId` | proposta, non pianificata |
| 2a | categorize-wizard | `/contesti/:ctxId/modelli/nuovo` | sostituisce l'albero cliccabile (confermato) |
| 2b | builder-editor | `/modelli/:modelId/builder` | editor completo, FR-011, non pianificato |
| 3a | derive-model | `/modelli/:modelId/deriva` | target futuro per FR-010; dipende da 2b; oggi solo il sottoinsieme T067 |
| 4a/4b | configure-dimensions | `/configurazione/tipi-documento/:codice/dimensioni` | vive in `010` (US5), non in questa spec - vedi tabella Design Reference li' |
| 5a | new-context | `/configurazione/contesti/nuovo` | vive in `010` (US1+US2) |
| 5b | integration-health | `/configurazione/contesti/:ctxId/integrazione` | vive in `010` (US3); banner collega a 4a |

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un gestore autorizzato puo' creare una bozza modello completa senza modifiche al codice.
- **SC-002**: Un approvatore autorizzato puo' pubblicare o archiviare una versione modello dall'interfaccia.
- **SC-003**: Un utente autorizzato puo' consultare stato e metadati di una generazione esistente.
- **SC-004**: Il 100% delle azioni non consentite dal ruolo o dallo stato della risorsa non viene presentato come completabile dall'interfaccia e resta comunque rifiutabile dal backend.
- **SC-005**: Il 100% dei blocchi di pubblicazione restituiti dal servizio viene mostrato all'utente come errore funzionale comprensibile.
- **SC-006**: Il 100% delle generazioni consultate distingue stato, bozza/ufficiale, disponibilita' file e autorizzazione al download.
- **SC-007**: Il 100% delle schermate principali del builder e della consultazione gestisce lista vuota, errore funzionale e salvataggio o download non riuscito.
- **SC-008**: Nessun flusso utente previsto richiede a GEBAN di compilare dati nel frontend GEMODO.

## Assumptions

- Le API backend necessarie sono definite nelle spec builder, generazione, storage e sicurezza.
- Decisione confermata il 2026-09-17: l'interfaccia sara' sviluppata con Angular e [Design Angular Kit](https://github.com/italia/design-angular-kit), usando i componenti e gli stili del kit. Il piano tecnico dovra' fissare versioni Angular/kit compatibili e gli eventuali componenti specialistici dell'editor.
- Il frontend Angular e' in implementazione secondo `tasks.md`: shell e autenticazione sono verificate, le schermate admin sono in collaudo e il flusso manager resta da implementare. Swagger/ReDoc e la pagina di test non sostituiscono il frontend previsto da questa spec.
- La nomenclatura dei ruoli applicativi segue la spec sicurezza, inclusi i ruoli `GEMODO_*`, `DOCUMENTI_*` e `SYSTEM_GEBAN`.
- Il frontend non e' fonte autoritativa per autorizzazioni, stato di pubblicazione, audit, idempotenza o disponibilita' file.
- La consultazione del payload completo e degli audit dettagliati e' limitata ai casi autorizzati e non sostituisce la fonte dati GEBAN.
