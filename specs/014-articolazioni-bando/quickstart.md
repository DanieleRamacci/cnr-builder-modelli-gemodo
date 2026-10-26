# Quickstart: collaudo del bando multiplo

Scenari che dimostrano la 014 da capo a fondo. Dati finti: bando 367.501,
TD, Collaboratore Tecnico E.R., livello V, tre tematiche.

## Prerequisiti

- Stack locale con database pulito (vedi la procedura e2e del progetto).
- Un discovery che dichiara `articolazioni` sulla foglia
  `TD > COLLABORATORE_TECNICO_ER`: per esempio l'albero GEBAN di test con il
  campo aggiunto, servito dal discovery di collaudo (spec 015) o da un file
  statico nelle destinazioni autorizzate. Esempio di foglia:
  [contracts/discovery-bando-articolato.json](./contracts/discovery-bando-articolato.json).

## 1. Discovery (US1)

1. Registrare e verificare l'integrazione. Atteso: `CONFORME`.
2. Aggiungere a un campo una chiave `foo`. Atteso: `NON_CONFORME`, con la
   chiave e il percorso. Con `_foo`: `CONFORME`.
3. Mettere un sotto-campo di tipo `array`. Atteso: `NON_CONFORME` con percorso.

## 2. Modello singolo e multiplo (US2)

1. Creare un modello su `TD > COLLABORATORE_TECNICO_ER`, IT, V. Atteso: la
   schermata chiede "Bando singolo" o "Bando multiplo".
2. Scegliere "Bando singolo". Atteso: il pannello etichette non mostra i
   sotto-campi.
3. Dal modello singolo, "Crea bando multiplo". Atteso: modello nuovo con lo
   stesso testo, marcato multiplo, con la sezione "Bando multiplo -
   Tematiche del bando".
4. Pubblicare il multiplo senza tabella. Atteso: pubblicazione bloccata con
   il motivo.
5. Inserire una tabella `Codice | Tematica | Posti | Sede`, riga marcata
   "ripeti per Tematiche del bando", e una riga fissa "Totale | | {{numero_posti}} |".
   Atteso: l'anteprima mostra due righe d'esempio e la riga Totale.
6. Aggiungere una seconda riga ripetuta nella stessa tabella. Atteso: blocco.
   Spostarla in un'altra tabella. Atteso: avviso, pubblicazione possibile.
7. Pubblicare entrambi. Atteso: il singolo resta pubblicato.

## 3. Catalogo

1. `GET /api/v1/catalogo/modelli?tipo_documento=BANDO_CONCORSO&codice_tipologia=TD&profilo=COLLABORATORE_TECNICO_ER&livello_professionale=V&lingua=IT`
   Atteso: solo il singolo, `multiplo: false`.
2. Stessa chiamata con `&multiplo=true`. Atteso: solo il multiplo.
3. `campi-richiesti` del multiplo. Atteso: `articolazioni` con `campi`, e
   `schema.properties.articolazioni.items`.

## 4. Validazione e generazione (US3)

Corpo: [contracts/dati-bando-articolato.json](./contracts/dati-bando-articolato.json),
adattato al 367.501 con tre tematiche (2, 5, 3 posti).

1. `genera` sul multiplo. Atteso: un PDF, tabella con tre righe nell'ordine
   dei dati, Totale 10.
2. Togliere `numero_posti` da TEMA_A. Atteso:
   `articolazioni[TEMA_A].campi.numero_posti`, `CAMPO_OBBLIGATORIO`.
3. Due elementi con codice `TEMA_A`. Atteso: `CODICE_ELEMENTO_DUPLICATO`.
4. Togliere `articolazioni`. Atteso: `CAMPO_OBBLIGATORIO` su `articolazioni`.
5. Stesso corpo verso il singolo. Atteso: `CAMPO_NON_AMMESSO` su
   `articolazioni`.
6. Togliere `comune_sede_lavoro` facoltativo da TEMA_C. Atteso: PDF con cella
   vuota.

## 5. Non regressione

- Suite backend e frontend complete; `test_documentazione_allineata.py`;
  `npm run docs:check`.
- Un modello singolo esistente genera lo stesso PDF di prima.
