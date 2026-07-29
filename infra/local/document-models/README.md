# Modelli documentali controllati

Il builder visuale GEMODO (spec `007-frontend-builder-consultazione`, in dipendenza da
`003-sezioni-placeholder-versionamento`) **non e' un editor HTML**. L'utente compone il
documento tramite blocchi e posizionamenti ammessi, come in un word processor limitato:
intestazione, logo, titolo, paragrafi, tabelle semplici, colonne controllate, firme
posizionabili, footer e interruzioni di pagina, con stili e placeholder scelti da un
elenco chiuso (spec `009`, FR-036..FR-038; decisione confermata in
`specs/009-fondamenta-mock-test-qualita/spec.md`, sessione 2026-07-07).

Quello che l'utente compone viene salvato come **modello documentale controllato**,
struttura versionata (`ModelloDocumentaleControllato`, `BloccoDocumento`,
`AssetDocumento` in `backend/app/quality/schemas.py`), non come HTML/CSS libero:

- nessun campo del modello puo' contenere HTML libero, CSS libero o script;
- ogni blocco usa solo i tipi ammessi (`INTESTAZIONE`, `LOGO`, `TITOLO`, `PARAGRAFO`,
  `TABELLA`, `COLONNE`, `FIRMA`, `FOOTER`, `INTERRUZIONE_PAGINA`) e un posizionamento
  compatibile con quel tipo;
- ogni asset (logo, immagine) e' referenziato per id, versione e hash, non incollato
  come contenuto libero;
- ogni placeholder usato da un blocco deve essere dichiarato dal modello e coerente con
  il contratto dati del modello/versione (spec `001`/`003`).

Il renderer PDF (spec `004`) legge questa struttura e produce internamente eventuali
formati tecnici intermedi necessari alla generazione, senza mai esporre HTML o CSS
liberi all'utente.

## Validazione

`backend/app/quality/document_model.py` (`validate_document_model`) rifiuta:

- HTML libero, CSS libero o script (`contiene_html_libero`, `contiene_css_libero`,
  `contiene_script`);
- blocchi con tipo/posizionamento non ammessi;
- tabelle senza colonne dichiarate o blocchi colonne con meno di due colonne;
- riferimenti ad asset non presenti tra gli asset del modello;
- placeholder usati da un blocco ma non dichiarati a livello di modello (e, quando
  disponibile il contratto dati, non presenti in esso).

## Seed demo

`bando-concorso-standard-v1.yaml` in questa cartella e' il modello demo pubblicato
usato dal mock GEBAN (`mock-geban/payloads/`) e referenziato come
`demo-bando-concorso-standard-v1` nei profili di integrazione
(`infra/local/integration-profiles.local.yaml`) e nel manifest di readiness qualita'
(`infra/local/quality-readiness.local.yaml`).
