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
| 010 | Registro software, endpoint, verifica, discovery autorizzato | T079/T080 implementati; HTTP/resolver/viste T081-T084 da implementare |
| 002 | Modello da foglia live, contratto e workflow | Requisiti propagati; adeguamento da verificare |
| 001 | API consumatore e validazione valori | Baseline presente; nuovi requisiti da pianificare |
| 003 | Sezioni minime generate/versionate | Baseline presente; automatismo da pianificare |
| 004 | PDF TEST reale | Da pianificare e implementare |
| 005 | Storage, download e idempotenza | Da pianificare e implementare |
| 006 | JWT, client, permessi per contesto e audit | Baseline presente; nuovi casi da verificare |
| 007 | Admin/manager Angular con Design Angular Kit | Da pianificare e implementare |

Queste sono responsabilita', non sette nuove spec da iniziare da zero.
La feature attiva resta 010. Le altre spec sono state aggiornate nei requisiti,
non avviate nell'implementazione. Ogni passaggio successivo richiede verifica
Spec Kit e cambio feature autorizzato; 004/005/007 necessitano plan/tasks.

## Stato Reale E Prossimo Passo

Gate di sicurezza prima dell'uso operativo: 001 FR-034..FR-038 e 006
FR-014..FR-017 richiedono autorizzazione sul contesto della risorsa per
catalogo, contratto, validazione e generazione anche simulata. Il solo permesso
generale non basta. Runtime ancora da adeguare, tracciato nell'handoff T087.

Il backend contiene configurazione/export di esempi, registro software e
endpoint per software nella persistenza; l'adapter valida tutta la mappa
multi-tipo e usa cache RAM scoped. API admin onboarding e letture manager
non sono ancora implementate; il resolver usa ancora URL di ambiente. Non sono
disponibili le schermate admin/manager o il PDF reale qui descritti.

Prossimo task T081: API admin registro/configurazione/verifica, con politica
URL approvati/SSRF, versioni e tentativi concorrenti. T078-T080 completati;
seguono resolver e letture manager/test T082-T084. Il contratto corrente
per tipi/esempi rimane descrizione del runtime esistente, non del nuovo registro.

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
