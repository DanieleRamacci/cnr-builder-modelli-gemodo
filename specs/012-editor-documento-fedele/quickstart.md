# Quickstart: verificare l'editor documentale fedele

**Fase 1 di** `specs/012-editor-documento-fedele/plan.md` | **Data**: 2026-09-29

Come si prova che questa feature funziona davvero. Non sono test unitari: sono i
percorsi con cui si dimostra ciascun criterio di successo, sullo stack vero.

## Prerequisiti

Lo stack locale reale, con un database pulito - questa feature include una
migrazione di dati, e provarla su un database gia' sporco di corse precedenti
non dimostra nulla.

```bash
docker compose -f infra/local/compose.yaml up -d      # Postgres + Keycloak
cd backend && uv run alembic upgrade head
cd frontend && npm start                              # ng serve con proxy sul backend
```

Serve inoltre il bando di riferimento (367.501 CTER) sotto mano: e' il metro di
SC-001 e resta agli atti dell'ente, non nel repository.

---

## SC-001 - Il bando reale e' ricomponibile

Il criterio principale, e l'unico che non si automatizza del tutto.

1. Creare un modello e una versione in BOZZA per il tipo documento
   `BANDO_CONCORSO`.
2. Nell'editor a tutto schermo, ricomporre **tre parti** del bando reale,
   scelte perche' coprono tutto cio' che la feature aggiunge:
   - un "visto" con `VISTO` in grassetto e il titolo di legge in corsivo (US1);
   - l'intestazione `Art. 3` centrata, seguita da commi numerati con lettere
     annidate (US2);
   - il blocco firma in chiusura, allineato a destra (US3).
3. Chiedere l'anteprima e confrontarla col bando reale.

**Atteso**: struttura, enfasi, elenchi e numerazione corrispondono. Font,
sillabazione e punti di a-capo no, e non devono: la spec lo dichiara fra le
Assumptions, la fedelta' e' strutturale, non tipografica.

## SC-002 - Nessuna sintassi da scrivere

Comporre l'elenco annidato del punto precedente **senza digitare** `1.`, `a)`,
`*`, `**` o qualunque altro simbolo di marcatura: solo selezione del testo e
pulsanti.

**Atteso**: i marcatori compaiono nel PDF. Inserendo poi un comma in mezzo, la
numerazione si aggiorna da sola in tutto l'articolo (US2 scenario 1).

## SC-003 - Anteprima e PDF finale coincidono

```bash
# 1. anteprima della bozza
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$API/builder/modelli/$MODELLO/versioni/$VERSIONE/anteprima" \
  -o /tmp/anteprima.pdf

# 2. pubblicare la versione, poi generare con dati veri
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "$API/builder/modelli/$MODELLO/versioni/$VERSIONE/pubblica"
curl -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "$PAYLOAD" "$API/documenti/genera" -o /tmp/finale.pdf

# 3. confrontare la struttura, non i byte
python - <<'PY'
from pypdf import PdfReader
a = "\n".join(p.extract_text() for p in PdfReader('/tmp/anteprima.pdf').pages)
b = "\n".join(p.extract_text() for p in PdfReader('/tmp/finale.pdf').pages)
print('stesso numero di righe:', len(a.splitlines()) == len(b.splitlines()))
PY
```

**Atteso**: ordine dei blocchi, enfasi e numerazione identici; differiscono solo
i valori al posto dei segnaposto.

## SC-004 - I modelli gia' pubblicati non cambiano

La prova della migrazione, e l'unica che va fatta **prima** di eseguirla.

1. Su un database allo stato precedente, generare il PDF di ogni versione
   pubblicata e conservarne il testo estratto.
2. `uv run alembic upgrade head` (la migrazione a frammenti).
3. Rigenerare gli stessi documenti con gli stessi dati.
4. Confrontare il testo estratto, coppia per coppia.

**Atteso**: nessuna differenza. Una differenza qualunque ferma la migrazione:
non si corregge il confronto, si corregge la migrazione.

Non si confrontano i byte dei file: un PDF contiene data di produzione e
identificatori interni che cambiano a ogni generazione.

## SC-005 - Nessun markup entra

```bash
curl -X PUT -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  "$API/builder/modelli/$MODELLO/versioni/$VERSIONE/sezioni" \
  -d '{"sezioni":[{"codice":"s1","ordine":0,"contenuto":[
        {"id":"b1","tipo":"PARAGRAFO","posizionamento":"BODY",
         "frammenti":[{"testo":"<b>VISTO</b> la legge"}]}]}]}'
```

**Atteso**: `422 MODELLO_DOCUMENTALE_NON_VALIDO`. Non un 200 con il testo
ripulito: FR-002 vuole un rifiuto, non una bonifica silenziosa.

Provare anche `{"testo":"clicca","collegamento":"javascript:alert(1)"}`: stesso
esito.

## SC-006 - I caratteri tipografici italiani sopravvivono

Comporre un paragrafo che contenga virgolette curve, apostrofo tipografico,
trattino lungo e lettere accentate, poi generare ed estrarre il testo.

**Atteso**: i caratteri arrivano invariati. Oggi questa prova **fallisce prima
della feature**, e non con un carattere sbagliato ma con un documento in stato
`FALLITO`: il renderer usa un font di base che non li conosce
(`research.md` R1).

---

## Cosa questo quickstart non prova

- **La resa visiva.** Il confronto e' sul testo estratto e sulla struttura. Che
  il grassetto sia il grassetto giusto lo dice l'occhio di chi guarda il PDF
  accanto al bando reale, ed e' parte di SC-001.
- **L'incolla da Word**, finche' R8 resta aperta.
