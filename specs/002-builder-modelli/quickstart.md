# Quickstart - Builder Modelli Documentali

Gli scenari minimi per validare la feature 002 a mano, sull'ambiente di test o
in locale. Non sostituisce i test automatici: ogni scenario indica quello che
lo verifica a ogni esecuzione della suite.

Aggiornato il 2026-10-01 (T036) al comportamento effettivo: varianti con nota
(FR-019), dimensioni generiche (011), corpo a frammenti e anteprima (012),
profilo calcolato dal backend (007 FR-034).

## Prerequisiti

- backend avviato con database PostgreSQL migrato (`alembic upgrade head`);
- un'integrazione **CONNESSA** per il contesto, che dichiari `BANDO_CONCORSO`
  nella sua discovery: i modelli si creano sui rami dell'albero dal vivo, non
  su un catalogo locale;
- token Keycloak di un utente con `ROLE_MANAGER#<contesto>` (permesso
  `GEMODO_MODELLI_GESTORE` nel contesto); per gli scenari di generazione,
  `DOCUMENTI_GENERATORE`.

Per sapere cosa concede il proprio token: `GET /api/v1/builder/profilo`, o la
pagina **Profilo** dell'interfaccia.

## Scenario 1 - Il primo modello di una categorizzazione

1. Creare un modello (`POST /api/v1/builder/modelli`, o "Nuovo modello"
   dall'interfaccia) scegliendo tipologia, profilo e dimensioni.
2. Creare la prima versione.

Atteso: il modello ha variante `STANDARD`, codice e nome generati dal backend;
la versione parte in `BOZZA`; l'audit registra soggetto, client e ruoli.
Test: `test_varianti_modello.py::test_il_primo_modello_della_categorizzazione_e_standard`.

## Scenario 2 - Un secondo modello sulla stessa categorizzazione

1. Creare un secondo modello con le stesse scelte, **senza** nota di variante.
2. Ripetere indicando una nota ("Firma del Presidente").

Atteso: il primo tentativo è rifiutato e dice quale modello occupa già la
categorizzazione; il secondo crea `VARIANTE_1`, con la nota nel nome. Una nota
uguale a una già usata è rifiutata. Due varianti si pubblicano insieme e il
catalogo le distingue.
Test: `test_un_secondo_modello_senza_nota_e_rifiutato_dicendo_quale_esiste`,
`test_due_varianti_coesistono_pubblicate_con_nomi_distinti`,
`test_la_stessa_descrizione_di_variante_e_rifiutata`.

## Scenario 3 - Comporre il corpo e vederlo prima di pubblicare

1. Aprire la versione in `BOZZA` nell'editor: scrivere un visto con una parola
   in grassetto, un titolo d'articolo dal menu Stile, un elenco numerato con
   una voce a lettere (Tab), un segnaposto scrivendo `/`.
2. Cliccare "Anteprima".

Atteso: il PDF della bozza mostra enfasi, titolo centrato, `1.` e `a)`, e
«etichetta» al posto del segnaposto, con la marcatura di anteprima; nessun
documento viene registrato. Sul foglio dell'editor, salvato il testo, compare
"N pagine nel PDF" e, dove una pagina comincia, una fascia "Pagina N".
Test: `frontend/e2e/builder-lifecycle.spec.ts`, `test_anteprima_api.py`.

## Scenario 4 - Il corpo pubblicato non cambia

1. Portare la versione a `IN_REVISIONE`, `APPROVATO`, `PUBBLICATO`.
2. Provare a riscrivere le sezioni (`PUT .../sezioni`).
3. Creare una versione nuova del modello.

Atteso: la scrittura risponde 409; l'editor mostra la versione in sola
lettura; la versione nuova parte in `BOZZA` con una **copia** delle sezioni
della precedente, modificabile senza toccare l'originale.
Test: `test_sezioni_api.py`,
`test_sezioni_persistenza.py::test_una_versione_nuova_eredita_le_sezioni_senza_condividerle`.

## Scenario 5 - Una nuova versione sostituisce la precedente

1. Pubblicare la versione nuova dello scenario 4.

Atteso: la versione precedente della stessa variante passa a `ARCHIVIATO`; il
catalogo (001) vede una sola versione pubblicata corrente per variante e
dimensioni. Una versione pubblicata si può anche sospendere o archiviare
esplicitamente.
Test: `test_una_versione_pubblicata_si_archivia_e_si_sospende_da_endpoint`.

## Scenario 6 - Autorizzazione per contesto

1. Chiamare una rotta builder senza token.
2. Chiamarla con un token gestore di **un altro** contesto.
3. Chiamarla con un token che sa solo generare (`DOCUMENTI_GENERATORE`).

Atteso: `ACCESSO_NON_AUTENTICATO` (401); per un altro contesto la versione
risulta inesistente (404) dove non va rivelata (anteprima) o non autorizzata
(403) altrove; chi sa solo generare riceve 403. L'interfaccia mostra le
funzioni del builder solo a chi il profilo dichiara gestore.
Test: `test_gestore_di_un_contesto_non_puo_scrivere_su_un_tipo_documento_di_un_altro_contesto`,
`test_anteprima_api.py::test_t038_*`, `test_profilo_api.py`.
