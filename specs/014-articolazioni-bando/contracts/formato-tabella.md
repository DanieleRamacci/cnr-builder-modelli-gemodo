# Formato documentale: tabella con righe ripetute (014)

Estensione additiva di `GEMODO_DOCUMENT_V1`
(`backend/app/documentale/schemas.py`). Un documento senza `righe` resta
valido e si rende come prima.

## Blocco

```json
{
  "id": "b-posti",
  "tipo": "TABELLA",
  "posizionamento": "BODY",
  "ordine": 7,
  "colonne": ["Codice", "Tematica", "Posti", "Sede"],
  "righe": [
    {
      "ripeti_per": "articolazioni",
      "celle": [
        {"frammenti": [{"testo": "{{articolazioni.campi.codice_bando}}"}]},
        {"frammenti": [{"testo": "{{articolazioni.descrizione}}"}]},
        {"frammenti": [{"testo": "{{articolazioni.campi.numero_posti}}", "grassetto": true}]},
        {"frammenti": [{"testo": "{{articolazioni.campi.sede_lavoro}}"}]}
      ]
    },
    {
      "ripeti_per": null,
      "celle": [
        {"frammenti": [{"testo": "Totale"}]},
        {"frammenti": []},
        {"frammenti": [{"testo": "{{numero_posti}}", "grassetto": true}]},
        {"frammenti": []}
      ]
    }
  ],
  "placeholder_usati": [
    "articolazioni.campi.codice_bando", "articolazioni.descrizione",
    "articolazioni.campi.numero_posti", "articolazioni.campi.sede_lavoro",
    "numero_posti"
  ]
}
```

## Resa con il bando 367.501

| Codice | Tematica | Posti | Sede |
|---|---|---|---|
| 367.501-A | Tematica A - Laboratorio di chimica ambientale | **2** | Istituto sull'Inquinamento Atmosferico |
| 367.501-B | Tematica B - Strumentazione oceanografica | **5** | Istituto di Scienze Marine |
| 367.501-C | Tematica C - Sistemi informatici di calcolo | **3** | Istituto di Informatica e Telematica |
| Totale | | **10** | |

La riga ripetuta diventa tre righe, nell'ordine dei dati. La riga fissa
"Totale" usa un segnaposto del padre ed esce una volta.

## Regole

Vedi [data-model.md](../data-model.md#3-formato-documentale-gemodo_document_v1-esteso-additivo).
