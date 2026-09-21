# Handoff: Modellario — generatore di modelli documentali

## Overview
Interfaccia web per un software che genera **modelli di documento** per la PA.
Flusso amministrativo: **creazione del contesto/integrazione** → **verifica dell'endpoint e scansioni periodiche** → **configurazione delle policy dimensione**.
Flusso redazionale: **contesti applicativi** → **elenco modelli del contesto** → **categorizzazione** (tendine a cascata dal servizio di categorizzazione) → **builder** del modello (editor tipo docx con segnaposto). Dal builder si può inoltre **derivare** un nuovo modello da uno esistente, ereditandone struttura e testi e cambiando solo gli attributi aggiuntivi (es. la lingua).

## About the Design Files
I file in `design/` sono **riferimenti di design realizzati in HTML**: prototipi che mostrano aspetto e comportamento attesi, **non codice di produzione da copiare**.
Il compito è **ricreare queste schermate nell'ambiente del codebase di destinazione** (Angular + design-angular-kit, React, Vue…) usando i suoi pattern e le sue librerie. Se non esiste ancora un ambiente, scegliere il framework più adatto — per questo progetto la scelta naturale è **Angular con `@italia/design-angular-kit`**, perché il prototipo è già costruito sul CSS di Bootstrap Italia.

`design/Gestione Modelli.dc.html` è un singolo documento "canvas" che contiene **tutte e undici le viste** affiancate. Ogni schermata è un `<div class="dv-opt" id="<id>" data-screen-label="<nome>">`: si apre nel browser e si raggiunge via anchor (es. `…#2b`). `support.js` è il runtime del prototipo e **non va portato** nel progetto.

## Fidelity
**High-fidelity.** Colori, tipografia, spaziature, stati e copy sono definitivi e derivati da Bootstrap Italia. Ricreare l'UI fedelmente usando i componenti equivalenti del design system, non riscrivendo il CSS a mano.

Le schermate **1b / 1c / 1d sono tre varianti della stessa pagina** (elenco modelli): scegliere una direzione. Suggerimento: 1b come vista di default, 1c come toggle "griglia". 1a, 2a, 2b, 3a, 4a, 5a, 5b sono proposte uniche; 4b non è una schermata ma la raccolta degli stati di 4a.

## Screens / Views

Mappa file ↔ schermata in `screens.json` (leggibile da un agente). Sintesi:

| id | label | schermata | rotta suggerita |
|----|-------|-----------|-----------------|
| 1a | contexts-list | Elenco contesti / applicazioni | `/contesti` |
| 1b | templates-table | Elenco modelli — tabella | `/contesti/:ctxId/modelli` |
| 1c | templates-grid | Elenco modelli — griglia con anteprima | `/contesti/:ctxId/modelli?view=grid` |
| 1d | templates-split | Elenco modelli — master/detail | `/contesti/:ctxId/modelli/:modelId` |
| 2a | categorize-wizard | Categorizzazione del modello | `/contesti/:ctxId/modelli/nuovo` |
| 2b | builder-editor | Builder del modello | `/modelli/:modelId/builder` |
| 3a | derive-model | Crea modello derivato (dialogo sopra il builder) | `/modelli/:modelId/deriva` |
| 4a | configure-dimensions | Configura dimensioni e policy di derivazione | `/configurazione/tipi-documento/:codice/dimensioni` |
| 4b | configure-dimensions-states | Stati di 4a: caricamento ed errore di sorgente | — (stessa rotta) |
| 5a | new-context | Nuovo contesto / integrazione + struttura di esempio | `/configurazione/contesti/nuovo` |
| 5b | integration-health | Contesto: verifica endpoint e storico scansioni | `/configurazione/contesti/:ctxId/integrazione` |

---

### 1a — contexts-list · Elenco contesti / applicazioni
**Purpose.** Punto di ingresso: l'utente sceglie il contesto (area organizzativa) di cui gestire i modelli.

**Layout** (canvas 1180px).
1. Header applicativo: altezza 60px, `background #0066cc`, testo bianco, padding orizzontale 28px. A sinistra logo (quadrato 26px, bordo 2px `rgba(255,255,255,.7)`, radius 4px) + nome prodotto 16px/700. Nav orizzontale gap 22px, 14px; voce attiva `border-bottom: 3px solid #fff` + 600, le altre `rgba(255,255,255,.82)`. A destra email 13.5px + avatar 32px tondo `rgba(255,255,255,.18)`.
2. Breadcrumb: padding `22px 28px 0`, 13px, `#5a6772`; separatore `/` con opacity .5; ultima voce `#1c2024` 600.
3. Page header: titolo `h1` 34px/700 `#17324d`, letter-spacing -.3px; sottotitolo 15px/1.5 `#5a6772`, max-width 620px. A destra CTA primaria "Nuovo contesto" (`.btn.btn-primary`, icona + 17px, gap 8px). Bordo inferiore `1px solid #e3e7eb`.
4. Toolbar filtri: `background #f7f9fb`, padding `16px 28px`, bordo inferiore `#e3e7eb`. Search 340px max, altezza 38px, bordo `1px solid #c5cdd4`, radius 4px, icona lente 17px a 11px da sinistra. Chip: radius 16px, padding `6px 13px`, 13px; attivo `#0066cc`/bianco 600, inattivi bianchi con bordo `#c5cdd4`, testo `#33485c`. A destra "Ordina per: **ultima modifica**".
5. Griglia card: `grid-template-columns: repeat(3,1fr)`, gap 20px, padding `24px 28px 30px`, fondo bianco.

**Card contesto.** Bordo `1px solid #e3e7eb` + `border-top: 4px solid #0066cc`, radius 4px, padding `18px 18px 14px`. Sigla: 40×40, radius 4px, `background #e6f0fa`, testo `#0066cc` 14px/700. Titolo 17.5px/700 `#17324d`; codice `Roboto Mono` 11.5px/500 `#5a6772`. Descrizione 14px/1.45 `#5a6772`, `min-height: 60px` (allinea i footer). Footer metriche: `border-top 1px solid #eef1f4`, 13px; numero 15px/700 `#17324d`. Link "Apri contesto" 14.5px/600 `#0066cc` con chevron 15px. Ultima cella: placeholder `2px dashed #c5cdd4`, min-height 210px, testo `#0066cc`.

**Contenuto.** 5 contesti reali nel prototipo: Appalti e contratti (AC, CTX-APP, 14), Edilizia privata (EP, CTX-EDI, 22), Tributi (TR, CTX-TRI, 9), Servizi demografici (SD, CTX-DEM, 31), Personale e concorsi (PC, CTX-PER, 17).

---

### 1b — templates-table · Elenco modelli (variante A, consigliata)
**Purpose.** La pagina centrale del prodotto: vedere i modelli già creati nel contesto, filtrarli, aprirne uno in modifica, crearne uno nuovo.

**Layout** (1180px). Header identico a 1a con "Modelli" attivo. Breadcrumb `Contesti / Appalti e contratti`. Page header: `h1` 32px/700 `#17324d` + badge codice contesto (padding `3px 9px`, radius 3px, `#e6f0fa`, testo `#0066cc`, `Roboto Mono` 11px/600); sottotitolo 15px `#5a6772`. Azioni: "Importa .docx" (`.btn-outline-primary`, h 40px) + "Nuovo modello" (primaria, h 40px) → naviga a **2a**.

**Barra metriche** (opzionale, prop `showMetrics`): 4 celle `repeat(4,1fr)`, gap 1px su fondo `#e3e7eb` (crea i divisori), celle `#f7f9fb` padding `14px 18px`; etichetta 12.5px/600 uppercase letter-spacing .6px `#5a6772`; valore 26px/700 `#17324d`. Valori: 11 attivi / 2 in revisione / 1 bozza / 438 documenti generati (30 gg).

**Toolbar**: search 300px + 2 select 150px (h 38px) + conteggio risultati a destra.

**Tabella** (`.table.table-hover`, 14.5px). Colonne: Modello · Tipo · Ver. · Stato · Ultima modifica · Utilizzi (destra) · Azioni (destra). Header: 12.5px/600 uppercase, letter-spacing .6px, `#5a6772`, `border-bottom: 2px solid #17324d`. Righe: padding `14px 16px` (28px sui bordi esterni), `border-bottom: 1px solid #eef1f4`, vertical-align middle. Cella Modello: chip formato 30×36 (bordo `#c5cdd4`, radius 3px, fondo `#fbfcfd`, `Roboto Mono` 9px/600 `#5a6772`, testo DOCX/PDF) + nome 700 `#17324d` (link a **2b**) + codice `Roboto Mono` 11.5px `#5a6772`. Cella Ultima modifica: data + autore 12.5px `#5a6772`. Azioni: link "Modifica" 14px/600 + bottone kebab 30×30 bordo `#c5cdd4` radius 4px.

**Badge di stato** (pill: radius 12px, padding `3px 10px`, 12.5px/600, pallino 7px dello stesso ink):
- Pubblicato — bg `#e0f2e4`, ink `#1b7a34`
- In revisione — bg `#fdf1d8`, ink `#8a5a00`
- Bozza — bg `#eceff2`, ink `#5a6772`

**Paginazione**: "Righe 1–7 di 14" 13.5px `#5a6772`; pagine 34×34 radius 4px, attiva `#0066cc`/bianco 700.

**Dati di esempio (7 righe).** MOD-APP-001 Determina a contrarre · Atto amministrativo · 3.2 · Pubblicato · 12/09/2026 M. Rossi · 184 — MOD-APP-004 Contratto di appalto servizi · Contratto · 2.0 · Pubblicato · 09/09/2026 G. Bianchi · 96 — MOD-APP-007 Verbale di gara · Verbale · 1.4 · In revisione · 04/09/2026 L. Ferrari · 72 — MOD-APP-009 Lettera di invito – procedura negoziata · Comunicazione · 1.1 · Pubblicato · 28/08/2026 M. Rossi · 41 — MOD-APP-011 Richiesta di offerta (RDO) · Modulo · 2.3 · Pubblicato · 21/08/2026 S. Conti · 63 — MOD-APP-013 Certificato di regolare esecuzione · Attestazione · 0.9 · Bozza · 14/08/2026 L. Ferrari · 8 — MOD-APP-014 Comunicazione di aggiudicazione · Comunicazione · 1.0 · In revisione · 02/08/2026 G. Bianchi · 35.

---

### 1c — templates-grid · Elenco modelli, griglia con anteprima (variante B)
Stessa rotta di 1b con toggle vista. Header di pagina semplificato (no barra blu nel mock): breadcrumb + `h1` 30px/700, a destra toggle Tabella|Griglia (bordo `#c5cdd4`, radius 4px, segmento attivo `#0066cc`/bianco 600) + CTA primaria.

Griglia `repeat(4,1fr)` gap 20px su fondo `#f7f9fb`, padding `24px 28px 30px`. Card: bianca, bordo `#e3e7eb`, radius 4px. Thumbnail h 150px con fondo `repeating-linear-gradient(135deg,#f2f5f8 0 6px,#e8edf2 6px 12px)`, foglio interno bianco bordo `#dbe2e8` padding `10px 11px` con barre: titolo 7px `#17324d` opacity .8, sottotitolo 4px `#c5cdd4`, righe 3px `#e3e7eb`, **righe segnaposto 3px `#0066cc` opacity .35**. Badge stato in alto a destra (radius 12px, 11.5px/700). Corpo: titolo 16px/700, codice+versione `Roboto Mono` 11.5px, tag (radius 11px, bordo `#dbe2e8`, 11.5px, fondo `#fbfcfd`). Footer: data 12.5px + link "Modifica" 13.5px/700.

---

### 1d — templates-split · Elenco modelli master/detail (variante C)
Layout `grid-template-columns: 440px 1fr`, min-height 560px.

**Lista** (sinistra, fondo `#fbfcfd`, `border-right #e3e7eb`): campo "Filtra modelli" h 38px; righe padding `13px 20px`, `border-bottom #eef1f4`, chip formato 28×34, nome 14.5px/700, meta `codice · vX · data` 12.5px `#5a6772`, badge stato a destra. **Riga selezionata**: `background #eaf3fc` + `border-left: 3px solid #0066cc` (le altre `border-left: 3px solid transparent` per non spostare il testo).

**Dettaglio** (destra, padding `22px 26px 26px`): titolo 23px/700 + meta `Roboto Mono` 12px; azioni Duplica / Genera documento (outline) + **Modifica modello** (primaria → 2b). Sotto `grid-template-columns: 1fr 320px` gap 22px: anteprima documento (stesso pattern tratteggiato di 1c, foglio min-height 360px) e colonna con due box (bordo `#e3e7eb` radius 4px padding `14px 16px`): *Segnaposto usati* (chip `Roboto Mono` 11.5px, bordo `#cfe0f2`, fondo `#f2f7fc`, testo `#0059b3`) e *Storico versioni* (numero versione `Roboto Mono` 12px/600 `#0066cc`, descrizione 13.5px `#17324d`, data+autore 12px `#5a6772`).

---

### 2a — categorize-wizard · Categorizzazione del modello
**Purpose.** Fase intermedia fra "Nuovo modello" e il builder: l'utente classifica il modello scegliendo da tendine servite dal **servizio di categorizzazione**; la categoria determina la struttura di sezioni e i segnaposto del modello generato.

**Layout** (1180px). Header + breadcrumb `Contesti / Appalti e contratti / Nuovo modello`.
**Stepper** (padding `18px 28px 0`): 3 passi — 1 Categorizzazione (attivo: pallino 28px `#0066cc` bianco 700, label 14.5px/700 `#17324d`), 2 Generazione struttura, 3 Editor documento (inattivi: pallino bordo `2px solid #c5cdd4`, blocco a `opacity .55`); connettori `height:2px; background:#e3e7eb; max-width:120px; margin:0 14px`.
Corpo `grid-template-columns: 1fr 380px` gap 26px, padding `20px 28px 28px`.

**Colonna sinistra.** `h1` 30px/700; paragrafo 15px/1.5 `#5a6772` max-width 600px. Poi **4 blocchi-livello** in colonna, gap 16px. Ogni blocco: bordo `1px solid` (`#e3e7eb` neutro, `#b8d4ee` quando valorizzato), radius 4px, padding `14px 16px`, fondo `#fff` (`#f5f6f8` se disabilitato). Riga di intestazione: badge `L1…L4` (`Roboto Mono` 11px/600, fondo bianco, bordo `#dbe2e8`, radius 3px), label 14.5px/700 `#17324d`, hint a destra 12.5px `#5a6772`. Select `.form-select` larghezza 100%, h 42px, padding `0 12px`, 15px, bordo `#c5cdd4`, radius 4px (fondo `#f0f2f4` se disabilitata). Nota sotto la select quando il livello è abilitato e non ancora scelto: "N opzioni restituite dal servizio", 13px `#5a6772`.

Livelli e hint: **L1 Dominio documentale** — `servizio: /categorize/domain`; **L2 Famiglia di atto** — "suggerito dal dominio"; **L3 Tipologia** — "suggerito dalla famiglia"; **L4 Variante procedurale** — "opzionale".

Footer azioni: **Genera modello** (primaria h 44px, icona freccia) — **disabilitata finché non sono scelti almeno 3 livelli** — + "Annulla" (outline) + contatore "N di 4 livelli selezionati" 13px.

**Colonna destra** (aside, bordo `#e3e7eb`, radius 4px, fondo `#f7f9fb`, padding `18px 18px 20px`, `align-self: start`), tre blocchi separati da `border-top 1px solid #e3e7eb`:
- *Categorizzazione corrente*: per ogni livello scelto `L#` (`Roboto Mono` 11px/600 `#0066cc`) + valore 14.5px/600 + nome livello 12px. Stato vuoto: "Nessuna scelta effettuata. Inizia dal livello L1."
- *Codice assegnato*: `Roboto Mono` 14px. Nel mock è derivato dalle scelte (`MOD-ATT-DET-A-NEW`), altrimenti "assegnato alla generazione". **In produzione il codice lo assegna il backend** — mostrarlo come anteprima non vincolante.
- *Struttura proposta*: elenco sezioni con pallino 6px `#0066cc`, 13.5px `#33485c`, + nota "Sezioni e segnaposto derivano dalla categoria scelta e restano modificabili nell'editor."

**Albero di categorizzazione del prototipo** (da sostituire con la risposta reale del servizio):
- Atti amministrativi → Determine → {A contrarre, Di liquidazione, Di aggiudicazione}; Delibere → {Di giunta, Di consiglio}
- Contratti → Servizi → {Appalto di servizi, Concessione}; Forniture → {Acquisto beni}
- Comunicazioni → Verso operatori economici → {Lettera di invito, Comunicazione esito}; Verso cittadini → {Preavviso di diniego, Richiesta integrazioni}

Ogni tipologia ha 1–3 varianti (es. A contrarre → Affidamento diretto / Procedura negoziata / Adesione a convenzione).

**Struttura sezioni per famiglia** (mappa `CAT.sections` nel prototipo): Determine → Intestazione dell'ente, Premesse normative, Visti e pareri, Motivazione, Dispositivo, Copertura finanziaria, Sottoscrizione. Delibere → Intestazione, Premesse, Pareri obbligatori, Dispositivo, Sottoscrizione. Servizi → Parti contraenti, Oggetto e durata, Corrispettivo, Obblighi dell'appaltatore, Penali e recesso, Firme. Forniture → Parti contraenti, Oggetto della fornitura, Consegna e collaudo, Corrispettivo, Firme. Verso operatori economici → Intestazione, Oggetto della comunicazione, Termini e modalità, Riferimenti del procedimento, Sottoscrizione. Verso cittadini → Intestazione, Fatti e istruttoria, Motivi ostativi, Termine a difesa, Sottoscrizione. Fallback → Intestazione, Corpo del documento, Sottoscrizione.

---

### 2b — builder-editor · Builder del modello
**Purpose.** Creare/modificare il modello: sezioni di testo editabili come in un docx e segnaposto inseribili dalla libreria a destra.

**Layout** (1320px). `grid-template-columns: 232px 1fr 320px`, min-height 720px, sopra due barre a piena larghezza.

**Topbar**: `background #17324d`, testo bianco, padding `12px 24px`, gap 18px. Link "← Modelli"; divisore verticale 1×26 `rgba(255,255,255,.22)`; titolo 15.5px/700 + meta `MOD-APP-001 · v3.3 bozza · salvato alle 11:24` (`Roboto Mono` 11.5px, `rgba(255,255,255,.7)`, `white-space: nowrap`). A destra: Anteprima, Esporta .docx (bordo `rgba(255,255,255,.5)`, h 36px) e **Pubblica** (fondo bianco, testo `#17324d`, 700).

**Toolbar formattazione**: `background #f7f9fb`, padding `8px 24px`, bordo inferiore `#e3e7eb`. Pulsanti min 32–34px h 32px radius 4px: **B** / *I* / U̲ | H1 H2 | 1. • Tab. A destra hint 12.5px `#5a6772`: "Trascina un segnaposto nel testo, oppure clicca per inserirlo nel punto del cursore".

**Colonna 1 — Outline sezioni** (fondo `#fbfcfd`, `border-right #e3e7eb`, padding `16px 0`). Etichetta di sezione 12.5px/700 uppercase. Righe: padding `10px 16px`, icona handle 13px `#9aa5af`, titolo 13.5px/600 `#17324d`, meta 11.5px `#5a6772` ("bloccata · 2 segnaposto" / "modificabile · N segnaposto"), lucchetto 13px `#8a5a00` sulle bloccate. Selezionata: `background #eaf3fc` + `border-left: 3px solid #0066cc`. In fondo "Aggiungi sezione" (outline, full width, h 36px).

**Colonna 2 — Foglio** (fondo `#e8edf2`, padding `26px 0 34px`). Pagina: width 620px, centrata, bianca, `box-shadow: 0 2px 10px rgba(23,50,77,.14)`, padding `52px 58px 60px`, min-height 640px.
- *Intestazione*: stemma placeholder 38×44 bordo `#c5cdd4`; "Comune di {{ente.denominazione}}" 12.5px/700 `#17324d` + "Area appalti e contratti" `#5a6772`; a destra "Det. n. {{determina.numero}} / del {{determina.data}}" `Roboto Mono` 11.5px. Separatore `border-bottom: 1.5px solid #17324d`.
- *Blocchi sezione*: `position: relative`, margin-top 24px, padding `10px 12px`, radius 3px, bordo `1px solid` (`#0066cc` se attiva, altrimenti transparent), fondo `#fff` (`#fbfaf6` se bloccata). Etichetta flottante a `top:-10px; left:10px`, radius 10px, padding `1px 8px`, 10.5px/600 — modificabile: fondo `#e6f0fa` ink `#0059b3`; bloccata: fondo `#fdf1d8` ink `#8a5a00`. Titolo `h3` 14.5px/700 uppercase letter-spacing .4px `#17324d`. Corpo: 13.5px/1.75 `#1c2024`, `text-align: justify`, `contenteditable` solo se non bloccata, `outline: none`.
- *Firma*: allineata a destra, "Il Responsabile del procedimento" 12.5px/700 + segnaposto `{{rup.nome}}`.
- *Drop zone finale*: `2px dashed #c5cdd4`, padding 14px, testo `#0066cc` 13.5px/600 "Inserisci una nuova sezione di testo".

**Stile segnaposto** (regola `em.ph` — usarla anche per i nodi inseriti a runtime): `font-style: normal; font-family: "Roboto Mono"; font-size: 11.5px; color: #0059b3; background: #e9f2fb; border-bottom: 1.5px dashed #0066cc; padding: 0 2px; white-space: nowrap`.

**Colonna 3 — Pannello** (fondo `#fbfcfd`, `border-left #e3e7eb`, flex column). Tre tab a larghezza uguale (padding `12px 4px`, 13.5px; attiva 700 `#0059b3` + `border-bottom: 3px solid #0066cc`):
1. **Segnaposto** — search h 36px; hint "Trascina nel documento o clicca per inserire. I segnaposto fissi non possono essere rinominati."; gruppi con intestazione (nome 12px/700 uppercase + fonte dati 11.5px). Item: riga bianca bordo `#d9e4ef` radius 4px padding `8px 10px`, `cursor: grab`, handle a 6 punti, token `Roboto Mono` 11.5px `#0059b3`, descrizione 12px `#5a6772`, tipo a destra 11px.
2. **Blocchi** — testi predefiniti della categoria, card cliccabile: titolo 13.5px/700 + preview 12.5px `#5a6772`. Il click inserisce una nuova sezione.
3. **Proprietà** — della sezione selezionata: Titolo sezione (input), Obbligatorietà (select: Obbligatoria / Opzionale / Condizionata), Ripetibile (testo), nota sulle sezioni bloccate.
Footer del pannello: `margin-top: auto`, fondo `#f2f5f8`, bordo superiore, 12.5px: "Categoria: **Atti amministrativi › Determine › A contrarre**".

**Libreria segnaposto del prototipo** (3 gruppi per fonte dati):
- *Ente* (anagrafica interna): `{{ente.denominazione}}` testo, `{{ente.codice_fiscale}}` testo, `{{rup.nome}}` testo
- *Procedimento* (registro determine): `{{determina.numero}}` numero, `{{determina.data}}` data, `{{cig}}` testo, `{{capitolo.codice}}` testo
- *Controparte* (anagrafica fornitori): `{{fornitore.ragione_sociale}}` testo, `{{fornitore.piva}}` testo, `{{importo.netto}}` valuta, `{{importo.lordo}}` valuta

**Sezioni del documento nel prototipo**: Premesse normative (bloccata), Motivazione, Dispositivo, Copertura finanziaria (condizionata). Blocchi di testo predefiniti: Visti e pareri, Clausola tracciabilità flussi, Termini di impugnazione, Trattamento dati personali.

---

### 3a — derive-model · Crea modello derivato
**Purpose.** Da un modello esistente creare una **variante** che eredita struttura, testi e segnaposto del padre e si distingue solo per attributi aggiuntivi (caso d'uso principale: la lingua). La categorizzazione L1–L4 del padre **non** è modificabile: il derivato resta nella stessa famiglia di atto.

**Ingresso.** Pulsante "Crea modello derivato" nella topbar di **2b** (outline su fondo scuro, icona "duplica", h 36px), a sinistra di Anteprima / Esporta .docx / Pubblica.

**Layout.** Dialogo modale sopra il builder: scrim `rgba(23,50,77,.35)` su fondo `#eceff2`, padding 34px. Card: max-width 1000px, centrata, bianca, radius 6px, `box-shadow: 0 12px 40px rgba(23,50,77,.3)`.
- *Header* (padding `20px 26px 18px`, bordo inferiore `#e3e7eb`): `h2` 24px/700 `#17324d`; sottotitolo 14.5px/1.5 `#5a6772` max-width 640px; chiusura "×" 34×34 radius 4px `#33485c` in alto a destra.
- *Corpo*: `grid-template-columns: 320px 1fr`.

**Colonna sinistra — ciò che si eredita** (fondo `#f7f9fb`, `border-right #e3e7eb`, padding `20px 22px 24px`), tre blocchi separati da `border-top 1px solid #e3e7eb`, ciascuno con label 12.5px/700 uppercase ls .6px `#5a6772`:
1. *Modello di origine*: chip formato 30×36 (come in 1b) + nome 15.5px/700 `#17324d` + `MOD-APP-001 · v3.2` in `Roboto Mono` 11.5px.
2. *Categorizzazione ereditata*: i 4 livelli in sola lettura — badge `L#` `Roboto Mono` 11px/600 **`#8a93a0`** (grigio, non blu: segnala che non è azionabile), valore 14px/600 `#33485c`, nome livello 11.5px. Sotto, pill ambra (bg `#fdf1d8`, ink `#8a5a00`, radius 11px, padding `2px 9px`, 12px/600) con lucchetto 11px: "non modificabile nel derivato".
3. *Attributi ereditati*: elenco con spunta verde 13px `#1b7a34`, 13.5px `#33485c`, numero in 700 `#17324d` — "4 sezioni di testo, nello stesso ordine", "11 segnaposto già mappati sulle fonti dati", "1 sezione bloccata (Premesse normative)", "2 blocchi predefiniti collegati alla categoria", "1 impaginazione e intestazione dell'ente".

**Colonna destra — attributi di derivazione** (padding `20px 26px 24px`).
- Titolo `h3` 17px/700 + "servizio: /categorize/derive" 12.5px `#5a6772`; nota 13.5px/1.5: "Ogni valore diverso dall'origine genera una variante. Lascia 'eredita' per mantenere il valore del modello padre."
- **Griglia 2×2** (`repeat(2,1fr)`, gap 14px) di blocchi-campo, stessa grammatica dei livelli di 2a ma badge `D1…D4`: bordo `1px solid` (`#e3e7eb` neutro → `#b8d4ee` se modificato), fondo `#fff` → `#f7fbff` se modificato, radius 4px, padding `13px 15px`; label 14px/700; quando il valore diverge compare a destra la pill "modificato" (bg `#e6f0fa`, ink `#0059b3`, radius 10px, 11px/700). Select h 40px, 14.5px, bordo `#c5cdd4`.
  La **prima opzione di ogni select è `eredita — <valore del padre>`** con `value=""`: è il default e rende esplicito cosa si sta ereditando.
- Campi del prototipo (da sostituire con le dimensioni reali del servizio):
  | badge | campo | valore del padre | opzioni |
  |---|---|---|---|
  | D1 | Lingua del documento | Italiano | Inglese, Tedesco, Francese, Sloveno |
  | D2 | Ambito territoriale | Nazionale | Provincia autonoma di Bolzano, Regione Valle d'Aosta, Regione Friuli-Venezia Giulia |
  | D3 | Canale di trasmissione | Protocollo cartaceo | PEC, Portale appalti, Piattaforma certificata ANAC |
  | D4 | Soglia di importo | Sotto soglia | Sopra soglia UE, Affidamento diretto < 140.000 € |
- **Riepilogo "Modello risultante"** (bordo `#e3e7eb`, radius 4px, fondo `#fbfcfd`, padding `14px 16px`): label uppercase + codice a destra in `Roboto Mono` 13px (nel mock `MOD-APP-001-<XX>-D1`, in produzione **lo assegna il backend**); nome composto 14.5px/700 (`"Determina a contrarre — Inglese · PEC"`); una chip per ogni attributo — modificato `bg #e6f0fa / ink #0059b3`, ereditato `bg #eceff2 / ink #5a6772` — così si legge a colpo d'occhio cosa cambia e cosa no. In fondo checkbox 16px, spuntata di default: "Mantieni il collegamento con il modello di origine: le modifiche alle sezioni bloccate del padre si propagano al derivato."
- *Azioni*: **"Crea e apri nel builder"** (primaria h 44px, icona freccia) — **disabilitata finché nessun attributo diverge dal padre** — + "Annulla" (outline, torna a 2b) + hint 13px: "Modifica almeno un attributo per creare una variante" oppure "N attributi modificati".

**Comportamento alla creazione.** Il backend crea un nuovo modello che copia sezioni, testi, flag di blocco e mapping dei segnaposto del padre, applica gli attributi di derivazione alla categorizzazione e apre il builder (**2b**) sul nuovo modello. Se `mantieni collegamento` è attivo, il derivato conserva un riferimento al padre e le sue sezioni bloccate restano in sola lettura, aggiornate dal padre.

**Decisioni ancora aperte (da confermare col cliente).**
- Se un derivato possa a sua volta essere derivato (derivazione a più livelli) e come rappresentare l'albero in **1b**.
- Se al cambio di lingua i testi ereditati vadano tradotti automaticamente o restino in italiano da tradurre a mano.
- Se i livelli L1–L4 debbano diventare modificabili (ora bloccati per garantire la stessa famiglia di atto).

---

### 4a — configure-dimensions · Dimensioni e policy di derivazione
**Rotta.** `/configurazione/tipi-documento/:codice/dimensioni` (nel mock: `BANDO_CONCORSO`).

**Purpose.** Un admin naviga l'albero di categorizzazione **reale e live** dell'integrazione connessa e, per ogni foglia che raggiunge, vede le dimensioni che quella foglia dichiara (`livello`, `lingua`, in futuro altre come `canale`). Per ogni dimensione stabilisce **se il cambio di valore biforca il modello** o se un modello generico copre tutti i valori.

**Il concetto da rendere evidente:** la policy si imposta **una volta per nome dimensione**, valida su tutto il tipo documento — non nodo per nodo. Se `lingua` è già stata configurata su un'altra foglia, qui compare **già impostata e in sola lettura**, con link "Modifica"; non viene richiesta di nuovo. Tre elementi lo comunicano insieme: il badge verde "configurata", la riga "Configurata da <utente> il <data> · si applica a tutte le foglie di questo tipo documento", e la pill blu accanto al pulsante di salvataggio "si applica a tutte le foglie di questo tipo documento".

⚠️ **Non confondere con la definizione struttura.** Questa schermata configura **comportamento a runtime** del catalogo. La *definizione struttura* (`DefinizioneStruttura`/`StrutturaInput`) serve solo a generare la documentazione di contratto per l'integrazione e **non deve influenzare il runtime**: sono due oggetti distinti. Nel prototipo la distinzione è resa da una nota informativa fissa sotto l'header (box `background #f2f7fc`, `border 1px solid #d9e4ef`, `border-left: 4px solid #0066cc`, radius 4px, padding `12px 15px`, testo 13.5px/1.55 `#33485c`, icona info 17px `#0059b3`). **La *definizione struttura* è ora disegnata in **5a** (colonna destra: struttura minima di esempio da consegnare agli sviluppatori): da 4a va linkata lì.**

**Layout** (canvas 1320px).
1. Header applicativo standard (60px, `#0066cc`) con **"Impostazioni"** come voce attiva.
2. Breadcrumb `Impostazioni / Integrazioni / GEBAN / Dimensioni`.
3. Page header: `h1` 30px/700 `#17324d` + badge codice tipo documento (`#e6f0fa`/`#0066cc`, `Roboto Mono` 11px/600); sottotitolo 15px/1.5 `#5a6772` max-width 720px che enuncia la regola ("La policy vale per **nome dimensione** su tutto il tipo documento"). A destra, stato sorgente allineato a destra, 12.5px: pallino 8px `#1b7a34` + "sorgente live connessa" (600, `#1b7a34`), host in `Roboto Mono`, "albero letto il <data> · ricarica".
4. Nota di disambiguazione (sopra).
5. Corpo: `grid-template-columns: 300px 1fr 340px`, min-height 640px, `border-top 1px solid #e3e7eb`.

**Colonna 1 — Albero dell'integrazione** (fondo `#fbfcfd`, `border-right #e3e7eb`, padding `16px 0 20px`).
Navigazione **a drill-down, non a tendine**: breadcrumb dei nodi visitati (12.5px, separatore `›` opacity .45, nodo corrente 700 `#17324d`, gli altri link `#0066cc` cliccabili per risalire) e sotto l'elenco dei figli del nodo corrente. Riga nodo: padding `11px 18px`, `border-left: 3px solid transparent`, label 13.5px/600 `#17324d`, codice `Roboto Mono` 11px/500 `#5a6772`, meta 11.5px `#5a6772` ("5 profili" per i rami, "3 livelli · IT/EN · +1 dimensione" per le foglie), chevron 15px se ha figli, pill grigia "foglia" (`#eceff2`/`#5a6772`, radius 10px, 11px/700) se è una foglia. Quando il nodo corrente è una **foglia**, la colonna mostra i **fratelli** (gli altri profili dello stesso ramo) con la foglia corrente evidenziata — `background #eaf3fc` + `border-left: 3px solid #0066cc`, meta "foglia selezionata" — così l'admin passa da un profilo all'altro senza risalire dal breadcrumb.

**Colonna 2 — Dimensioni della foglia** (padding `18px 24px 26px`).
- Intestazione: `h2` 21px/700 `#17324d` (nome della foglia) + riga `Roboto Mono` 12px ("profilo · COLLABORATORE_TECNICO_ER"); a destra pill di sintesi — ambra "N dimensione da configurare" (`#fdf1d8`/`#8a5a00`), verde "tutte le dimensioni configurate" (`#e0f2e4`/`#1b7a34`), grigia "seleziona una foglia" quando si è su un ramo. Sotto, spiegazione 14px/1.55 `#5a6772`.
- **Banner di conflitto** (quando un'altra sessione ha cambiato la stessa policy): box `#fdf1d8`, `border 1px solid #f0d9a8`, `border-left: 4px solid #8a5a00`, icona triangolo, titolo 13.5px/700 `#5c3d00` con il nome dimensione in mono, testo 13px che dice **chi**, **cosa** e **quando** ("G. Bianchi ha impostato 'un solo modello copre tutti i valori' 2 minuti fa"), e due azioni: "Usa la versione aggiornata" (fondo `#8a5a00`, testo bianco) / "Mantieni la mia scelta" (bordo `#8a5a00`). Nessun salvataggio silenzioso: la scelta è dell'admin.
- **Card dimensione** (una per dimensione dichiarata, gap 16px). Bordo e fondo cambiano con lo stato: non configurata → `border #f0d9a8`, `background #fffdf7`; configurata → `border #e3e7eb`, `background #fff`. Padding `16px 18px 18px`, radius 4px.
  - Riga superiore: nome dimensione come token (`Roboto Mono` 13.5px/500 `#0059b3` su `#e9f2fb`, radius 3px, padding `2px 8px`) + **badge di stato**: ambra "nuova, non ancora configurata" (`#fdf1d8`/`#8a5a00` — stesso stile della pill "In revisione" di 1b) oppure verde "configurata" (`#e0f2e4`/`#1b7a34`). A destra "valori su questa foglia:" 12.5px + chip valore (bordo `#dbe2e8`, radius 11px, `Roboto Mono` 11.5px `#33485c`).
  - **Stato configurato (sola lettura)**: box interno bianco bordo `#e3e7eb`, spunta verde 15px `#1b7a34`, etichetta della policy 14px/700, esempio 13px `#5a6772`, riga di provenienza 12.5px "Configurata da M. Rossi il 18/09/2026 · si applica a tutte le foglie di questo tipo documento", link **Modifica** 13.5px/600 a destra.
  - **Stato da configurare (o in modifica)**: domanda 14.5px/700 `#17324d` — *"Questa dimensione genera un modello distinto quando cambia valore?"* — e **due opzioni esplicite** (non una checkbox, non "sì/no" nudo), righe cliccabili con radio disegnato (cerchio 18px, bordo 2px `#c5cdd4` → `#0066cc`, punto interno 9px), bordo `#dbe2e8` → `#0066cc` e fondo `#fff` → `#f2f7fc` quando selezionata:
    1. **"Sì, ogni valore è un modello a sé"** — esempio: *"cambiare valore crea sempre un nuovo id, mai un fallback"* — nota "come lingua".
    2. **"No, un solo modello copre tutti i valori salvo scelta esplicita"** — esempio: *"se non trovo un modello per il valore richiesto, uso quello generico"* — nota "come livello".
  - Azioni: **Salva policy** (primaria h 38px, disabilitata finché non si sceglie), "Annulla" (solo quando si sta modificando una policy esistente), e la pill blu `#e6f0fa`/`#0059b3` "si applica a tutte le foglie di questo tipo documento" accanto al pulsante — il punto in cui l'admin capisce che **non** sta configurando solo quel nodo.

**Colonna 3 — Policy del tipo documento** (aside, fondo `#fbfcfd`, `border-left #e3e7eb`, padding `18px 20px 22px`). Riepilogo **editabile** di tutte le dimensioni già configurate: label uppercase 12.5px/700 + nota "Valgono per **BANDO_CONCORSO** su tutte le foglie dell'albero". Card per dimensione (bianca, bordo `#e3e7eb`, radius 4px, padding `12px 13px`): nome in mono 12.5px `#0059b3`, pill della policy a destra — "biforca il modello" (`#e6f0fa`/`#0059b3`) o "ammette il generico" (`#e0f2e4`/`#1b7a34`) —, sintesi 13px `#33485c`, autore+data 12px e link "modifica" (apre la card corrispondente in colonna 2 in stato editabile). In fondo, nota separata da `border-top`: "Le dimensioni non ancora configurate compaiono qui appena l'integrazione le dichiara su una foglia: **N** in attesa" (numero in `#8a5a00`).

**Albero del prototipo** (forma `NodoDiscovery`): `BANDO_CONCORSO` › `CP` Concorsi Pubblici (tipologia) › 5 profili — COLLABORATORE_TECNICO_ER (IV/V/VI, base VI, IT/EN, **+ dimensione `canale`: PEC / Portale bandi / Albo pretorio** = il caso "dimensione nuova"), OPERATORE_TECNICO (VI–VIII, IT), RICERCATORE (I–III, IT/EN), TECNOLOGO (I–III, IT/EN), FUNZIONARIO_AMMINISTRAZIONE (IV–V, IT).
Policy preconfigurate nel mock: `lingua` → biforca (distinct), `livello` → ammette il generico. `canale` è nuova e non configurata: è la card ambra.

### 4b — configure-dimensions-states · Stati di 4a
Due stati resi come card separate (larghezza 620px) perché non convivono nella stessa vista:
1. **Albero non ancora caricato** — spinner 15px (bordo `#c5cdd4` con `border-top-color: #0066cc`) + "Interrogazione dell'integrazione in corso…"; tre skeleton riga h 38px e un blocco h 96px (bordo `#eef1f4`, radius 4px, riempimento `linear-gradient(90deg,#f2f5f8,#e8edf2,#f2f5f8)` con la banda chiara a offset diversi); nota: nessuna policy è modificabile finché l'albero non è stato letto, perché le dimensioni arrivano dalla sorgente e non dalla cache.
2. **Sorgente esterna non raggiungibile** — box `#fdeaea`, `border 1px solid #f0c9c9`, `border-left: 4px solid #a3242c`, icona 18px; titolo 14px/700 `#7a1b22` "Albero non disponibile: l'integrazione non risponde"; testo con **orario dell'ultimo tentativo, host e causa** ("timeout dopo 10s") e la garanzia che le policy salvate restano attive; tre azioni: "Riprova" (fondo `#a3242c`, testo bianco), "Vedi solo le policy salvate", "Dettagli tecnici" (bordo `#a3242c`). Regola: **mai una lista vuota silenziosa** — l'assenza di nodi è sempre spiegata, con orario e via d'uscita.

*(Colori dell'errore: sono i soli due valori nuovi rispetto ai token già documentati — `#a3242c` / `#7a1b22` su `#fdeaea` / `#f0c9c9`, l'`error` di Bootstrap Italia. Vedi Design Tokens.)*

---

### 5a — new-context · Nuovo contesto / integrazione
**Rotta.** `/configurazione/contesti/nuovo`.

**Purpose.** Un amministratore registra una nuova integrazione (nel mock: **GEBAN**) e ne ricava la **struttura minima di esempio** da consegnare agli sviluppatori del servizio, perché i dati arrivino nella forma che ci serve.

**Layout** (canvas 1240px). Header applicativo con **"Impostazioni"** attivo; breadcrumb `Impostazioni / Contesti / Nuovo contesto`; stepper a 3 passi — 1 Dati del contesto, 2 Struttura di esempio (entrambi attivi, pallino `#0066cc`), 3 Verifica dell'endpoint (inattivo, `opacity .55`, link a **5b**). Titolo `h1` 30px/700, sottotitolo 15px/1.5 max-width 700px. Corpo: `grid-template-columns: 1fr 1fr`, gap 26px.

**Colonna sinistra — Dati del contesto.** Campi (label 13.5px/600 `#33485c`, input h 40px bordo `#c5cdd4` radius 4px 14.5px):
| campo | valore nel mock | note |
|---|---|---|
| Nome del contesto | GEBAN — Bandi di concorso | testo libero, in griglia `1fr 200px` con la sigla |
| Sigla | `GEBAN` | mono |
| **Nome del contesto nel token** | `geban` | **mono** — è il valore con cui il contesto si presenta nel **token di autenticazione**: deve coincidere esattamente con quello emesso dagli sviluppatori, altrimenti le chiamate non vengono associate a questo contesto |
| Descrizione | testo su 2 righe | `textarea`, resize verticale |
| Referente tecnico | dev-geban@cnr.esempio.it | in griglia con Ambiente |
| Ambiente | Test / Collaudo / Produzione | select |
| Dimensioni previste | chip `livello`, `lingua` + "+ aggiungi" | chip `#e6f0fa`/`#0059b3` radius 13px con "×" di rimozione; il chip "+ aggiungi" è tratteggiato `#c5cdd4` |

⚠️ **Non esiste un campo "codice tipo documento".** Un contesto può esporre **più tipi di documento**: quali siano lo dichiara l'alberatura restituita dal servizio, non questa schermata. Non reintrodurre quel campo in implementazione.
Nota sotto le dimensioni: dichiararle qui le include nella struttura di esempio, ma la **policy runtime** di ciascuna si imposta dopo la prima scansione, in **4a**.

**Colonna destra — Struttura minima di esempio.**
- Nota informativa blu (stesso box di 4a: `#f2f7fc`, `border-left 4px solid #0066cc`): il file è **documentazione di contratto**, descrive la forma minima che il servizio deve esporre e **non** determina il comportamento a runtime (quello è 4a); più la precisazione sui tipi di documento multipli.
- **Blocco file**: cornice `1px solid #dbe2e8` radius 4px. Barra superiore `#f7f9fb`: nome file in mono 12px (`geban-discovery.example.json`), pill grigia "bozza", e a destra tre azioni h 30px — **Carica .json** e **Copia** (bordo `#c5cdd4`) + **Scarica .json** (primaria). Il file si può quindi generare, scaricare, modificare e ricaricare.
- **Anteprima del JSON**: fondo `#17324d`, testo `#dbe6f2`, `Roboto Mono` 11.5px/1.75, `white-space: pre`; il primo elemento di `campi` è evidenziato in `#8fb9e8` come esempio di campo. Contenuto: `codice_tipo_documento`, `validita`, `nodi[]` con una tipologia `CP` e un `PROFILO_ESEMPIO` che dichiara `livelli_possibili`, `livello_base`, `lingue_possibili` e un campo di esempio — la forma `NodoDiscovery`.
- **"Cosa consegnare agli sviluppatori"**: tre righe file (bordo `#e3e7eb`, radius 4px) con nome in mono `#0059b3`, descrizione 12.5px e link "scarica" — esempio JSON, contratto OpenAPI dell'endpoint, regole su campi e dimensioni.
- Azioni finali: **"Crea contesto e passa alla verifica"** (primaria h 44px → **5b**) + "Salva come bozza" (outline).

---

### 5b — integration-health · Verifica dell'endpoint e storico scansioni
**Rotta.** `/configurazione/contesti/:ctxId/integrazione`.

**Purpose.** Nel contesto scelto, l'amministratore inserisce l'endpoint fornito dagli sviluppatori, verifica che risponda e che la risposta sia valida, e consulta lo storico dei controlli periodici.

**Layout** (canvas 1240px). Header con "Impostazioni" attivo; breadcrumb `Impostazioni / Contesti / GEBAN`; page header con `h1` 30px/700 + badge codice in `#e6f0fa` e azioni a destra ("Dimensioni" → 4a, "Modelli del contesto" → 1b). **Tab di contesto** (bordo inferiore `#e3e7eb`, 14px, gap 22px; attiva 700 `#0059b3` + `border-bottom 3px solid #0066cc`): Integrazione · Dimensioni · Struttura di esempio · Permessi. Corpo: `grid-template-columns: 1fr 360px`, gap 24px.

**Colonna principale.**
1. *Endpoint di discovery*: input mono h 42px (flex, min-width 280px) + select metodo di autenticazione 150px (Token statico / OAuth 2.0 / mTLS) + **"Verifica ora"** (primaria h 42px, icona refresh).
2. *Esito in evidenza*: box verde `#e0f2e4`, `border 1px solid #bfe3c8`, `border-left 4px solid #1b7a34`, ink `#12592a`; cerchio 28px `#1b7a34` con spunta bianca; titolo 15px/700 "Endpoint raggiungibile e risposta valida"; riga meta con **orario, elementi letti e confronto con l'albero registrato**; a destra pill bianca mono "200 OK · 412 ms".
3. *Elenco controlli*: righe bianche separate da 1px `#e3e7eb` (tecnica: contenitore con `gap:1px` su fondo `#e3e7eb`), ciascuna con pastiglia 20px (spunta verde `#e0f2e4`/`#1b7a34`, "!" ambra `#fdf1d8`/`#8a5a00`), label 14px/600, dettaglio 13px `#5a6772`, valore a destra in mono 12px. I sette controlli: Raggiungibilità (412 ms) · Certificato TLS (valido, scadenza) · Autenticazione (token accettato) · Schema della risposta (conforme a NodoDiscovery) · Contenuto dell'albero (1 tipologia, 5 profili, 18 campi) · **Attributi non riconosciuti (1: `canale`)** · Campi obbligatori mancanti (0).
4. *Banner ambra* (`#fdf1d8`, `border-left 4px solid #8a5a00`): l'attributo `canale` trovato su 1 foglia non ha policy registrata, **oggi viene ignorato a runtime**, con link "Configura la policy" → **4a**. È l'anello fra scoperta e configurazione.

**Colonna laterale.**
- *Controllo periodico* (box `#fbfcfd`): pill verde "attivo" + "prossima alle 18:00"; select **Frequenza** (ogni 6 ore / una volta al giorno / una volta a settimana); nota: ogni scansione verifica raggiungibilità, schema e differenze rispetto all'albero registrato, e gli esiti negativi notificano il referente tecnico.
- *Storico scansioni* (cornice `#e3e7eb`): intestazione con "30 giorni"; **sparkline** delle ultime 14 scansioni (barre `flex:1`, radius 2px, altezza = durata; verde `#1b7a34` conforme, ambra `#8a5a00` warning, rosso `#a3242c` fallita) con didascalia "più alto = più lento"; poi le righe delle scansioni recenti — pastiglia esito, titolo 13.5px/600, riga "data ora · origine (manuale con utente / automatica) · dettaglio", durata a destra in mono. Nel mock: 2 conformi, 1 attributo non riconosciuto, 1 **timeout dopo 10 s con 3 tentativi**, 1 conforme. In fondo link "Vedi tutte le scansioni".

**Aperto:** se la verifica manuale possa **scrivere** subito l'albero registrato o debba solo proporre un diff da approvare (nel mock riporta "nessuna differenza", non decide).

## Interactions & Behavior
- **1a → 1b/1c/1d**: click su card contesto / "Apri contesto".
- **1b/1c/1d → 2a**: CTA "Nuovo modello".
- **1b/1c/1d → 2b**: click sul nome del modello o su "Modifica".
- **2a — cascata**: la scelta di un livello **azzera tutti i livelli successivi** e ne ricarica le opzioni; un livello è disabilitato finché il precedente è vuoto. Ogni apertura corrisponde a una chiamata al servizio di categorizzazione con il percorso corrente. `Genera modello` abilitato da 3 livelli; al click si crea il modello (struttura + segnaposto dalla categoria) e si naviga al builder.
- **2b — inserimento segnaposto**: (a) click sull'item del pannello → il token viene inserito **nel punto del cursore** nell'ultima sezione editabile che ha avuto il focus (il prototipo memorizza il `Range` ascoltando `selectionchange`); (b) **drag & drop** dell'item nel testo (`dataTransfer` text/plain col token). Il token è inserito come elemento inline dedicato (`<em class="ph">`), non come testo grezzo.
- **2b — selezione sezione**: click su una riga dell'outline o sul blocco nel foglio → evidenzia il blocco (bordo blu) e apre il tab **Proprietà**.
- **2b — aggiunta sezione**: "Aggiungi sezione", drop zone in fondo al foglio, o click su un blocco predefinito.
- **Sezioni bloccate**: non editabili, fondo `#fbfaf6`, etichetta ambra, lucchetto nell'outline.
- **2b → 3a**: pulsante "Crea modello derivato" nella topbar; il dialogo si apre sopra il builder, "Annulla" e "×" tornano indietro.
- **3a — derivazione**: ogni select parte da "eredita"; al cambio di un valore il blocco si evidenzia, compare la pill "modificato" e nome, codice e chip del riepilogo si ricalcolano; la CTA si abilita al primo attributo divergente e porta al builder del nuovo modello.
- **4a — drill-down**: click su una riga nodo scende di livello; il breadcrumb dell'albero risale a qualsiasi antenato. Nessuna tendina: la navigazione è nodo per nodo, perché l'albero è live e può cambiare profondità.
- **4a — configurazione**: una dimensione senza policy mostra le due opzioni; il click su un'opzione la seleziona e abilita "Salva policy"; al salvataggio la card passa in sola lettura e compare nel riepilogo a destra. "Modifica" (nella card o nel riepilogo) la riapre in scrittura con "Annulla". Salvare una policy la rende in sola lettura **su tutte le foglie**, non solo su quella corrente.
- **4a — conflitto**: se la stessa policy è stata cambiata altrove, il banner ambra chiede di scegliere fra versione aggiornata e propria scelta; nessuna scrittura automatica.
- **5a → 5b**: "Crea contesto e passa alla verifica"; lo stepper mostra la verifica come passo 3 dello stesso flusso.
- **5a — struttura di esempio**: si rigenera dai dati del form; può essere copiata, scaricata, oppure **caricata** da file per partire da una struttura già scritta dagli sviluppatori.
- **5b — verifica**: "Verifica ora" esegue una scansione manuale e aggiorna esito, controlli e storico; il controllo periodico fa lo stesso senza intervento, con notifica al referente sugli esiti negativi.
- **5b → 4a**: dal banner ambra sugli attributi non riconosciuti si va direttamente alla configurazione della policy della dimensione scoperta.
- **Stati mancanti da progettare in implementazione**: loading delle tendine (skeleton/spinner sulla select), errore del servizio di categorizzazione, salvataggio in corso/fallito nella topbar, segnaposto non risolvibile (evidenziazione rossa), lista modelli vuota.

## State Management
**2a**: `cat: string[4]` (il percorso scelto) → derivati: opzioni per livello, abilitazioni, conteggio livelli, codice anteprima, sezioni proposte, abilitazione CTA.
**5b**: `scanFreq` (frequenza del controllo periodico); esito dell'ultima scansione, elenco dei controlli e storico arrivano dall'API.
**4a**: `tpath: string[]` (percorso nell'albero), `policies: Record<nomeDimensione, {policy:'distinct'|'generic', who, when}>` — **chiave per nome dimensione + tipo documento, non per nodo**, `editing` (dimensione in scrittura), `draft` (scelta non ancora salvata), `conflict`. Le dimensioni della foglia sono derivate dal nodo (livelli, lingue, attributi extra), non memorizzate.
**3a**: `deriv: Record<string,string>` (solo gli attributi effettivamente cambiati; valore vuoto = ereditato) → derivati: evidenziazione dei campi, nome e codice risultanti, chip di riepilogo, abilitazione CTA, hint del contatore. La categorizzazione ereditata è di sola lettura e arriva dal modello padre.
**2b**: `sections` (numero/elenco di sezioni presenti), `active` (indice sezione selezionata), `tab` (`segnaposto | blocchi | proprietà`), + riferimento al `Range` di inserimento (fuori da React state: non deve causare re-render).
**Dati da API**: elenco contesti; elenco modelli per contesto (incluso il riferimento al modello padre per i derivati) (con stato, versione, utilizzi, autore); albero di categorizzazione (per livello, dato il percorso); dimensioni di derivazione disponibili con il valore corrente del padre; albero live dell'integrazione (drill-down per nodo) e policy dimensione registrate per tipo documento; esito della verifica endpoint (controlli singoli) e storico delle scansioni; schema dei segnaposto disponibili (raggruppati per fonte dati); contenuto del modello (sezioni con testo, flag locked/obbligatorietà/ripetibilità); storico versioni.
**Nota sul re-render**: nel prototipo il contenuto editabile è montato una volta e poi modificato dal DOM. In un'app reale, tenere il testo delle sezioni fuori dal ciclo di re-render (editor dedicato tipo TipTap/ProseMirror/CKEditor) invece di un `contenteditable` controllato, altrimenti il cursore salta a ogni digitazione.

## Design Tokens
**Colori**
| token | hex | uso |
|---|---|---|
| primary | `#0066cc` | header, CTA, link, accenti |
| primary-dark | `#0059b3` | testo su fondo chiaro, tab attiva |
| primary-hover | `#00478f` | hover dei link |
| primary-050 | `#e6f0fa` | fondo badge/sigle |
| primary-025 | `#e9f2fb` / `#f2f7fc` | fondo segnaposto |
| primary-border | `#b8d4ee` / `#cfe0f2` / `#d9e4ef` | bordi accentati |
| row-selected | `#eaf3fc` | riga/blocco selezionato |
| ink-900 | `#17324d` | titoli, topbar builder |
| ink-800 | `#1c2024` | corpo del documento |
| ink-600 | `#33485c` | testo secondario forte |
| ink-500 | `#5a6772` | testo secondario, label |
| border-300 | `#c5cdd4` | bordi campi |
| border-200 | `#e3e7eb` | divisori |
| border-100 | `#eef1f4` | divisori tabella |
| surface-0 | `#fff` | superfici |
| surface-50 | `#fbfcfd` / `#f7f9fb` | toolbar, pannelli |
| surface-100 | `#f2f5f8` | footer pannello |
| canvas | `#e8edf2` | scrivania del foglio |
| locked | `#fbfaf6` | fondo sezione bloccata |
| field-changed | `#f7fbff` | fondo campo di derivazione modificato |
| ink-400 | `#8a93a0` | badge livello in sola lettura |
| success | bg `#e0f2e4` / ink `#1b7a34` | stato Pubblicato |
| warning | bg `#fdf1d8` / ink `#8a5a00` | In revisione, bloccata |
| neutral | bg `#eceff2` / ink `#5a6772` | Bozza, pill "foglia" |
| error | bg `#fdeaea` / border `#f0c9c9` / accent `#a3242c` / ink `#7a1b22` | errore di sorgente (4b), scansione fallita (5b) |
| success-strong | bg `#e0f2e4` / border `#bfe3c8` / accent `#1b7a34` / ink `#12592a` | esito positivo della verifica (5b) |
| code-surface | bg `#17324d` / ink `#dbe6f2` / accent `#8fb9e8` | anteprima del file di esempio (5a) |
| attention-bg | `#fffdf7` | fondo card dimensione non configurata |
| skeleton | `#f2f5f8` → `#e8edf2` | riempimento dei placeholder in caricamento |

**Tipografia.** `Titillium Web` 300/400/600/700 (UI, font di Bootstrap Italia); `Roboto Mono` 400/500 (codici, segnaposto, date tecniche).
Scala: h1 pagina 30–34px/700 (letter-spacing -.3px) · h1 sezione 28px · h2 23px · card title 16–17.5px/700 · sezione documento 14.5px/700 uppercase (ls .4px) · body UI 14–15px · corpo documento 13.5px/1.75 · meta 12.5–13px · label uppercase 12–12.5px/700 (ls .6px) · mono 11.5px. **Mai sotto 11.5px.**

**Spaziature.** Scala 4px: 4 · 6 · 8 · 10 · 12 · 14 · 16 · 18 · 20 · 22 · 24 · 26 · 28. Padding pagina 28px (26px nel builder), gap griglia 20px, gap colonne 22–26px.

**Radius.** 3px (chip/box documento) · 4px (default: card, campi, bottoni) · 11–16px (pill) · 50% (avatar).
**Ombre.** Tre: card del canvas `0 1px 3px rgba(0,0,0,.06)`; foglio del builder `0 2px 10px rgba(23,50,77,.14)`; dialogo modale `0 12px 40px rgba(23,50,77,.3)` su scrim `rgba(23,50,77,.35)`.
**Bordi.** 1px default; `2px solid #17324d` sotto l'header di tabella; `4px` in cima alle card contesto; `3px` a sinistra delle righe selezionate; `1.5px dashed` sotto i segnaposto; `2px dashed` per le drop zone.

## Assets
Nessun asset binario. Tutte le icone sono **SVG inline a stroke** (`stroke-width` 2–2.2, `stroke-linecap: round`, 12–26px, `currentColor`): plus, chevron, freccia, lente, kebab, handle 6-punti, righe di testo, lucchetto, duplica, spunta. In implementazione sostituirle con il set icone di Bootstrap Italia (`it-icon` / `bootstrap-italia` sprite).
Lo stemma dell'ente nel builder è un placeholder 38×44: serve il logo reale dell'ente.
Font da Google Fonts (Titillium Web, Roboto Mono).

## Files
- `design/Gestione Modelli.dc.html` — tutte e undici le viste, identificate da `id` e `data-screen-label`. Aprire nel browser; aggiungere `#2b` all'URL per saltare al builder. Interattivo: tendine a cascata (2a), tab/outline/inserimento segnaposto (2b), attributi di derivazione (3a), drill-down dell'albero e salvataggio delle policy (4a), frequenza del controllo periodico (5b).
- `design/support.js` — runtime del prototipo, **non portare in produzione**.
- `screens.json` — mappa macchina-leggibile id → label → nome → rotta → scopo → elementi chiave. Da dare in pasto all'agente insieme a questo README.
