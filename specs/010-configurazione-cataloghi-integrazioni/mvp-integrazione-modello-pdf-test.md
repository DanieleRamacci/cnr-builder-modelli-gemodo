# MVP - Integrazione, Modello E PDF Di Test

Decisione confermata il 2026-09-17. Riferimento:
[ADR 0002](../../docs/adr/0002-integrazioni-contesti-modelli-test.md).

## Flusso Concordato

1. Admin apre Integrazioni: lista inizialmente vuota.
2. Crea un software con nome, codice interno e codice_contesto esatto del JWT.
3. Configura un singolo endpoint discovery e avvia Verifica.
4. Backend verifica trasporto e forma comune di tutti i tipi nella risposta;
   mostra stato, data ed errori sanificati. Nessun esempio locale obbligatorio.
5. Manager vede solo integrazioni connesse autorizzate nel proprio contesto;
   naviga tipo documento e nodi fino alla foglia e visualizza i campi.
6. Crea modello di test in BOZZA; struttura minima automatica e versionata.
   Pubblicazione successiva tramite normale workflow, non automatica.
7. Un chiamante autorizzato richiede generazione indicando versione modello e
   valori. Backend verifica stato, permessi, presenza, tipi e vincoli.
8. Produce PDF non ufficiale TEST con titolo, etichette e valori nell'ordine
   configurato; salva file/riferimento, consente download e retry autorizzati.

Il discovery non contiene valori da stampare. Un opzionale usato dal modello
ma omesso dal payload genera errore. Policy sugli opzionali non usati e sui
campi sconosciuti: requisiti 001 FR-032/033; contratto da definire prima del
cambio runtime. Il comportamento corrente rifiuta gli extra.

## Owner E Dipendenze

| Spec | Responsabilita' MVP | Stato del passaggio |
| --- | --- | --- |
| 010 | Registro software, endpoint, verifica, discovery autorizzato | T077-T083 implementati (registro, resolver, letture manager); T084 (prove avversarie) aperto |
| 002 | Modello da foglia live, contratto e workflow | Reale (builder + integrazione connessa, vedi `test_builder_flow_api.py`) |
| 001 | API consumatore e validazione valori | Reale; `POST /documenti/genera` ritirato a favore del contratto `004` |
| 003 | Sezioni minime generate/versionate | Non toccato in questo incremento: il rendering FR-019/020 usa etichetta/valore ordinati direttamente dal contratto dati, non un motore di sezioni |
| 004 | PDF TEST reale | Implementato per lo scope FR-019/020 (`backend/app/generazione/`); FR-001..018 non pianificati |
| 005 | Storage, download e idempotenza | Implementato per lo scope minimo (`backend/app/storage/`): riferimento, stato, download, idempotenza di base su filesystem locale; FR-011 piena/FR-012/013/015 non pianificati |
| 006 | JWT, client, permessi per contesto e audit | Baseline presente; nuovi casi da verificare |
| 007 | Admin/manager Angular con Design Angular Kit | Da pianificare e implementare |

Queste sono responsabilita', non sette nuove spec da iniziare da zero.
La feature attiva resta 010. Le altre spec sono state aggiornate nei requisiti,
non avviate nell'implementazione. Ogni passaggio successivo richiede verifica
Spec Kit e cambio feature autorizzato; 004/005/007 necessitano plan/tasks.

## Stato Reale E Prossimo Passo

Gate di sicurezza prima dell'uso operativo: 001 FR-034..FR-038 e 006
FR-014..FR-017 richiedono autorizzazione sul contesto della risorsa per
catalogo, contratto, validazione e generazione. Il solo permesso generale non
basta. **Non ancora chiuso**: la generazione reale implementata in questo
incremento riusa i ruoli globali esistenti (`DOCUMENTI_GENERATORE`/
`DOCUMENTI_VIEWER`), non l'enforcement per-contesto tracciato in T087 - vale
per uso di sviluppo/test, non ancora per uso operativo.

Aggiornamento 2026-09-17: registro software, resolver builder e letture
manager sono reali (T081-T083). Il flusso end-to-end descritto sopra (punti
1-8) e' dimostrato per davvero in
`backend/tests/builder/test_builder_flow_api.py::test_flusso_completo_creazione_pubblicazione_e_generazione_documento`:
integrazione connessa -> modello creato dalla foglia live -> pubblicato ->
generazione di un PDF di test reale -> stato/download reali (idempotenza
inclusa). Non disponibili: le schermate admin/manager (007), il motore
sezioni/placeholder vivo (003 resta non toccato - il rendering usa
etichetta/valore ordinati direttamente dal contratto dati).

Prossimo task T084: matrice di prova avversaria (SSRF con pinning della
connessione anti DNS-rebinding, redirect, HAL ciclico, concorrenza sui
tentativi di verifica).

Le migrazioni devono preservare modelli, versioni, identificativi pubblici,
campi, sezioni, generazioni e audit. Nessuna conversione automatica di seed,
token o URL di ambiente in una integrazione GEBAN. Associazione del legacy
esplicita e nuova verifica prima della connessione.

## Fuori Da Questo MVP

Editor visuale, multi-endpoint e replica locale del catalogo sono esclusi.
Hash/runner e soglie di classificazione delle modifiche sono rinviati:
verifica strutturale e validazione payload non attestano da sole l'allineamento
del modello a cambiamenti successivi della sorgente.
Review esterna rinviata: nessuna dichiarazione di feature completa o nuovo PASS.
