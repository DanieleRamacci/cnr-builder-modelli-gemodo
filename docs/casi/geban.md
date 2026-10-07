# Caso di integrazione: GEBAN

GEBAN, il sistema CNR per i bandi di concorso, è la **prima integrazione** di
GEMODO e quella con cui il servizio è stato costruito e collaudato. Questa
pagina raccoglie i valori concreti del caso. Le regole generali valgono come per
qualunque altro sistema e sono in
[Integrare un sistema esterno](../integrazione-sistema-esterno.md) e
[Contratto dati](../contratto-dati.md).

Dati verificati sul discovery di test il 2026-10-07.

## Riepilogo

| Voce | Valore |
|---|---|
| Contesto (nel token) | `geban` |
| Tipo documento | `BANDO_CONCORSO` |
| Discovery (test) | `https://geban-service.test.si.cnr.it/api/v1/gemodo/discovery` |
| Forma del discovery | Albero completo in una risposta, senza paginazione |
| Livelli | 2: tipologia, poi profilo |
| Foglie | 65 (combinazioni tipologia-profilo) |
| Campi per foglia | 13 o 14; 852 in totale |
| Dimensioni | `lingue` (IT, ENG) e `livelli_possibili` su ogni foglia |
| Client ammesso | `geri-angular-public` (client ACE di GEBAN) |
| Contratto discovery applicato | 0.7.0 |

## L'albero

| Tipologia | Codice | Profili |
|---|---|---|
| Comandi e Distacchi | `CD` | 7 |
| Direttori | `DIR` | 2 |
| Concorsi Pubblici | `CP` | 7 |
| Reclutamento Speciale | `RS` | 7 |
| Categorie Protette | `CATP` | 7 |
| Tempo Indeterminato | `TI` | 7 |
| Selezioni per dipendenti CNR/Candidature | `SDIP` | 7 |
| Mobilità | `MOB` | 7 |
| Tempo Determinato | `TD` | 7 |
| Tempo Determinato PNRR | `TDPNRR` | 7 |

I profili sono `RICERCATORE`, `TECNOLOGO`, `FUNZIONARIO_AMMINISTRAZIONE`,
`COLLABORATORE_TECNICO_ER`, `COLLABORATORE_AMMINISTRAZIONE`,
`OPERATORE_TECNICO`, `OPERATORE_AMMINISTRAZIONE`. I livelli ammessi dipendono
dal profilo, per esempio `I`, `II`, `III` per ricercatori e tecnologi e `IV`,
`V`, `VI` per i collaboratori tecnici.

Ogni nodo porta `tipo_livello` (`tipologia` o `profilo`). GEBAN quindi riempie
entrambi i filtri del catalogo, `codice_tipologia` e `profilo`, e una ricerca
individua un ramo preciso.

Estratto di una foglia, come arriva dal discovery:

```json
{
  "codice": "RICERCATORE",
  "descrizione": "Ricercatore",
  "tipo_livello": "profilo",
  "livelli_possibili": ["I", "II", "III"],
  "lingue": ["IT", "ENG"],
  "campi": [
    { "codice": "codice_bando", "etichetta": "Codice bando", "tipo": "string",
      "obbligatorio": true, "ordine": 1, "descrizione": "Identificativo funzionale del bando" },
    { "codice": "numero_posti", "etichetta": "Numero posti", "tipo": "number",
      "obbligatorio": true, "ordine": 8, "descrizione": "Numero dei posti previsti" }
  ]
}
```

I campi di una foglia tipica sono `codice_bando`, `piano_triennale_assunzione`,
`responsabile_procedimento`, `delegato_responsabile_procedimento`, `profilo`,
`livello`, `tipo_selezione`, `numero_posti`, `sede_lavoro`,
`comune_sede_lavoro`, `titolo`, `descrizione`, `medaglione`; le foglie di
`TDPNRR` aggiungono `progetto`. Lo stesso contratto vale per entrambe le lingue
della foglia: l'edizione inglese di un modello chiede gli stessi campi.

Note di compatibilità usate da GEBAN e accettate dal contratto:

- `lingue` al posto di `lingue_possibili`, con `ENG` al posto di `EN`;
- nessuna `lingua` sui singoli campi: dal 2026-09-24 la lingua sta sulla foglia.

## Accessi

Il profilo di accesso dell'integrazione GEBAN, impostato dalla migrazione
`0028` e modificabile da interfaccia:

| Ruolo ACE nel contesto `geban` | Permessi GEMODO |
|---|---|
| `ROLE_MANAGER` | `GEMODO_MODELLI_GESTORE`, `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` |
| `ROLE_GESTORE` | `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` |
| `ROLE_COORDINATOR` | `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` |
| `ROLE_USER` | `DOCUMENTI_GENERATORE`, `DOCUMENTI_VIEWER` |

GEBAN chiama GEMODO con il token ACE dell'utente che sta lavorando (client
`geri-angular-public`), non con un token tecnico.

## Flusso

1. GEBAN espone il discovery; l'amministratore GEMODO lo verifica.
2. I gestori (`ROLE_MANAGER`) creano e pubblicano i modelli per tipologia,
   profilo, livello e lingua.
3. Per generare il bando, GEBAN:
    - cerca il modello con
      `GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&codice_tipologia=TD&profilo=RICERCATORE&livello_professionale=III&lingua=IT`;
    - legge i campi richiesti;
    - chiama `genera` con `sistema_richiedente: "GEBAN"` e come
      `external_context_id` la chiave del bando;
    - rigenera a ogni correzione e conserva il PDF definitivo.

Le edizioni in inglese sono annidate nel risultato del catalogo
(`edizioni_derivate`); filtrando `lingua=EN` si ottengono al primo livello.

## Policy delle dimensioni

| Dimensione | Policy predefinita | Effetto |
|---|---|---|
| `lingua` | Valore esplicito richiesto | Ogni lingua ha il suo modello; nessun ripiego |
| `livello_professionale` | Generico ammesso | Un modello senza livello vale per tutti i livelli del profilo; il catalogo lo usa come ripiego |

Il cambio del nome interno delle dimensioni non ha richiesto modifiche a
GEBAN: [Dimensioni generiche nel catalogo](../presa-atto-geban-dimensioni-catalogo.md).

## Evoluzioni che riguardano GEBAN

| Tema | Stato |
|---|---|
| Bandi con più articolazioni (tematiche, sedi) nello stesso documento | Spec `014`, proposta: [campi ripetibili](../contratto-dati.md#campi-ripetibili-080). L'albero GEBAN attuale è già conforme al contratto 0.8.0. |
| Discovery di collaudo per provare tipi documento e contesti diversi senza toccare GEBAN | Spec `015`, da implementare |
| Autenticazione dell'endpoint discovery | Da concordare con GEBAN |
