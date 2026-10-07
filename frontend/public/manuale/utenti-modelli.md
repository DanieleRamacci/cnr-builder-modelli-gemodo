# Creare e pubblicare un modello

Questa guida è per chi ha il permesso di **gestore modelli** in un contesto.

## 1. Scegliere il contesto

Da **Contesti** si apre il contesto su cui lavorare (**Apri contesto**). Si vedono
solo i contesti in cui si ha il permesso di gestore.

## 2. L'elenco dei modelli

La pagina **Modelli** elenca i modelli del contesto. Si possono filtrare per
stato, lingua, tipologia, profilo e livello, e azzerare i filtri in un clic.

Da qui si crea un nuovo modello, si apre l'editor di un modello esistente, si
fanno avanzare le versioni (vedi il punto 5) e si elimina un modello. La
colonna **Creato da** dice chi ha creato ciascun modello; gli amministratori
trovano nel menu della riga anche lo **storico** delle azioni. Per creare
nuovi modelli serve almeno un'integrazione **connessa**: altrimenti la pagina lo
segnala.

## 3. Creare il modello: la categorizzazione

**Nuovo modello** apre tre passi: *Categorizzazione*, *Generazione struttura*,
*Editor documento*.

1. **Tipo documento**: l'elenco arriva dal vivo dall'integrazione.
2. **Livelli**: si scende nell'albero un livello alla volta (per esempio
   tipologia, poi profilo) fino a una foglia. Il riquadro *Categorizzazione
   corrente* riassume le scelte fatte.
3. **Attributi del modello**: sono le dimensioni dichiarate dalla foglia, come
   lingua o livello. Per ognuna si sceglie un valore. Dove l'amministratore lo
   consente si può lasciare *Nessun valore specifico*: il modello vale allora per
   tutti i valori.
4. **Campi del contratto**: a destra compaiono i campi della foglia; quelli
   obbligatori sono segnati.
5. **Genera modello** crea il modello in bozza e apre l'editor.

Se per quella categorizzazione esiste già un modello, GEMODO lo dice e mostra
*In cosa differisce*. Si può allora creare una **variante** (**Crea variante**).

## 4. Scrivere il documento: l'editor

L'editor mostra il documento come apparirà nel PDF.

- **Sezioni**: il documento è diviso in sezioni (per esempio "Premesse",
  "Art. 1"). Si aggiungono, si spostano su e giù e si rimuovono dal pannello
  *Sezioni del modello*.
- **Segnaposto**: scrivendo `/` nel testo si apre il menu dei segnaposto. Si
  scorre con le frecce, si inserisce con Invio, si chiude con Esc. Il pannello
  *Segnaposto* elenca tutti i campi disponibili, con la ricerca. Si possono usare
  solo i campi del modello.
- **Stile del blocco**: titolo, paragrafo, elenco, allineamento, grassetto e
  corsivo.
- **Interruzione di pagina**: forza l'inizio di una nuova pagina.
- **Intestazione e piè di pagina**: sono comuni a tutti i modelli dello stesso
  tipo documento e si modificano da *Modifica intestazione e piè di pagina* (vedi
  [Amministrazione](amministrazione.md#intestazione-e-pie-di-pagina)).
- **Salva documento** registra le modifiche.
- **Anteprima** e **Impaginazione** mostrano il PDF come verrà generato.

Il riquadro **Pronto per la pubblicazione** segnala cosa manca prima di poter
pubblicare. Per esempio, un segnaposto che non corrisponde a un campo del
modello.

## 5. Dalla bozza alla pubblicazione

| Stato | Azione per avanzare |
|---|---|
| Bozza | **Invia in revisione** |
| In revisione | **Approva**: la versione resta pronta per la pubblicazione |
| Approvata | **Pubblica** |
| Pubblicata | da qui il sistema esterno può generare documenti |

Pubblicando una nuova versione, quella pubblicata in precedenza per la stessa
categorizzazione viene archiviata: c'è sempre una sola versione in uso.

Una versione pubblicata **non cambia** se poi il sistema esterno modifica i
propri campi: continua a chiedere i dati di quando è stata creata. Per adeguarla
si crea e si pubblica una nuova versione.

## Domande frequenti

**Non vedo il tipo documento o la categoria che mi serve.** L'elenco arriva dal
vivo dal sistema esterno: se non c'è lì, non c'è in GEMODO. Se l'integrazione
non risponde, va avvisato un amministratore.

**Il segnaposto che cerco non c'è.** I segnaposto sono i campi della foglia
scelta. Se il sistema esterno ha aggiunto un campo dopo la creazione della
versione, serve una nuova versione.

**Ho due campi con lo stesso nome.** Vedi la proposta per i casi con più
articolazioni nello stesso bando in [Contratto dati](../contratto-dati.md#campi-ripetibili-080).
Non è ancora disponibile.
