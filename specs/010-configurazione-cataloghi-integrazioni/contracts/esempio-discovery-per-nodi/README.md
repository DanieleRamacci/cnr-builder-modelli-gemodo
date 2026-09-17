# Simulazione GEBAN: discovery per nodi

Proposta di contratto per il confronto con GEBAN. Gli endpoint seguenti devono
essere esposti dal software integrato. Non sono endpoint GEMODO gia' funzionanti.
I JSON allegati permettono di simulare le risposte senza implementare il servizio.
Il [contratto OpenAPI](../geban-discovery-per-nodi.openapi.yaml) documenta schemi,
parametri ed errori. La modalita ad albero completo resta un'alternativa distinta.

## Configurazione iniziale

```json
{
  "codice_tipo_documento": "BANDO_CONCORSO",
  "modalita_discovery": "PER_NODI",
  "url_iniziale": "https://geban.example/api/discovery/bando-concorso"
}
```

Questo e' un esempio della configurazione desiderata, non un payload gia'
accettato dall'API amministrativa attuale. Si registra soltanto l'ingresso.
Sostituire `https://geban.example/api` con la base del server del collega.
Gli URL restituiti sono relativi a questa base API: per esempio
`/discovery/...` diventa `https://geban.example/api/discovery/...`.
Il backend deve verificare che la destinazione sia autorizzata.

## Tre endpoint, quattro percorsi completi

| Endpoint GET | Parametri | Risultato |
|---|---|---|
| `/discovery/bando-concorso` | Nessuno | Tipologie TD e CP |
| `/discovery/bando-concorso/profili` | `tipologia`, `versione_catalogo` | Profili della tipologia scelta |
| `/discovery/bando-concorso/campi` | `tipologia`, `profilo`, `versione_catalogo` | Definizione dei campi della foglia |

Non serve un endpoint per ogni singolo profilo: lo stesso endpoint riceve
parametri differenti. I quattro percorsi demo sono TD o CP, ciascuno con
COLLABORATORE_TECNICO_ER o RICERCATORE. Le combinazioni sono illustrative e
devono essere confermate da GEBAN; non sono un elenco operativo completo.

## Prova passo per passo

1. Chiamare `GET /discovery/bando-concorso`.
   Il collega restituisce [01-tipologie.json](01-tipologie.json).
2. Scegliere TD e copiare il suo `url_figli`:
   `GET /discovery/bando-concorso/profili?tipologia=TD&versione_catalogo=demo-2026-09-17.1`.
   Il collega restituisce [02-profili-TD.json](02-profili-TD.json).
3. Scegliere COLLABORATORE_TECNICO_ER e copiare il suo `url_campi`:
   `GET /discovery/bando-concorso/campi?tipologia=TD&profilo=COLLABORATORE_TECNICO_ER&versione_catalogo=demo-2026-09-17.1`.
   Il collega restituisce [03-campi-TD-COLLABORATORE_TECNICO_ER.json](03-campi-TD-COLLABORATORE_TECNICO_ER.json).
4. La navigazione termina: `percorso` identifica il ramo e `campi` contiene
   la definizione da usare per creare il modello. Non contiene i valori
   di un bando concreto ne' un PDF.

Per cambiare ramo ripetere il passo 2 o il passo 3 con il collegamento
presente nel nodo scelto. Le altre risposte complete sono:

- [02-profili-CP.json](02-profili-CP.json)
- [03-campi-TD-RICERCATORE.json](03-campi-TD-RICERCATORE.json)
- [03-campi-CP-COLLABORATORE_TECNICO_ER.json](03-campi-CP-COLLABORATORE_TECNICO_ER.json)
- [03-campi-CP-RICERCATORE.json](03-campi-CP-RICERCATORE.json)

Nel ramo RICERCATORE, le opzioni del campo `livello` sono I, II, III con
default III. Nel ramo COLLABORATORE_TECNICO_ER sono IV, V, VI con default VI.
`profilo` nella risposta finale contiene gli attributi necessari a risolvere
`validazione.fonte_opzioni` e `validazione.default`, come nell'esempio annidato.

## Regole per la simulazione

- Un nodo con `foglia: false` contiene soltanto `url_figli`.
- Un nodo con `foglia: true` contiene soltanto `url_campi`.
- Un eventuale livello aggiuntivo restituisce altri nodi con la stessa forma;
  non occorre dichiarare quanti livelli restano. Il client segue i collegamenti.
- Gli ID sono stabili e univoci nel tipo documento; `codice` puo' ripetersi
  in rami diversi. I collegamenti conservano il contesto dei nodi selezionati.
- Ogni chiamata successiva riporta `versione_catalogo` ricevuta all'ingresso.
  La versione deve riferirsi allo stesso stato dei dati per tutte le risposte.
  `validita` e' la data di riferimento del catalogo, non un conteggio di livelli.
- Nessuna paginazione in questo piccolo esempio. Prima di introdurla nel
  contratto reale occorre definire come il client recupera le pagine successive.
- L'autenticazione esterna va concordata prima dell'uso operativo.

## Prove di errore

| Richiesta/scenario | HTTP | Codice errore |
|---|---|---|
| `/profili` senza `tipologia` | 400 | `PARAMETRO_NON_VALIDO` |
| `/profili?tipologia=INESISTENTE&versione_catalogo=demo-2026-09-17.1` | 404 | `RAMO_NON_TROVATO` |
| `/campi?tipologia=TD&profilo=INESISTENTE&versione_catalogo=demo-2026-09-17.1` | 404 | `RAMO_NON_TROVATO` |
| Versione richiesta non piu' disponibile | 409 | `VERSIONE_CATALOGO_CAMBIATA` |
| Catalogo temporaneamente non disponibile | 503 | `CATALOGO_NON_DISPONIBILE` |

Gli ultimi segmenti `/profili` e `/campi` nella tabella sono relativi a
`/discovery/bando-concorso`. Ogni errore ha la forma seguente:

```json
{
  "codice": "VERSIONE_CATALOGO_CAMBIATA",
  "messaggio": "Il catalogo e' cambiato. Ripetere la navigazione dall'ingresso"
}
```

Una risposta vuota non sostituisce un errore di connessione. Se il catalogo
cambia durante la selezione e la versione precedente non e' disponibile,
GEMODO deve ripartire dall'ingresso evitando di mescolare versioni diverse.
Questo non determina da solo l'invalidita' dei modelli precedenti: il controllo
delle modifiche sui dati effettivamente usati resta una questione distinta.
