# Amministrare integrazioni e contesti

Questa guida è per chi ha il permesso di **amministratore** (`GEMODO_ADMIN`).
Tutto si trova sotto **Impostazioni**.

## Creare un contesto con la sua integrazione

**Nuovo contesto** guida in tre passi.

1. **Dati del contesto**:
    - nome del contesto e sigla;
    - **nome del contesto nel token**: deve coincidere con il contesto che il
      sistema di autenticazione CNR mette nel token degli utenti e dei sistemi,
      per esempio `geban`, altrimenti nessuno riceverà permessi qui;
    - referente tecnico e dimensioni previste.
2. **Struttura di esempio**: si descrive la forma attesa (tipologie, profili,
   campi) e GEMODO genera il JSON da consegnare al team che deve costruire
   l'endpoint. La forma è spiegata in [Contratto dati](../contratto-dati.md).
3. **Verifica dell'endpoint**: vedi la sezione seguente.

## Configurare e verificare l'integrazione

Nella pagina dell'integrazione ci sono tre schede: **Integrazione**,
**Struttura API**, **Profilo di accesso**.

Nella scheda **Integrazione**:

- **URL discovery**: l'indirizzo che il sistema esterno espone. Deve essere fra
  le destinazioni autorizzate dall'installazione; se non lo è, va chiesto a chi
  gestisce il deploy.
- **Timeout (ms)**: quanto attendere la risposta.
- **Verifica**: GEMODO chiama l'endpoint e controlla che la risposta rispetti il
  contratto. L'**Esito verifica** riporta:
    - raggiungibilità dell'endpoint;
    - schema JSON del discovery;
    - tipi documento dichiarati;
    - campi obbligatori.

  Se qualcosa non va, l'esito indica **dove** la risposta è difforme.

Solo un'integrazione **connessa**, cioè verificata con esito positivo, può essere
usata per creare modelli. Si può verificare di nuovo in qualsiasi momento.

La scheda **Struttura API** mostra la risposta JSON dal vivo dell'integrazione.

## Profilo di accesso

Decide chi può fare cosa nel contesto dell'integrazione.

- **Ruoli**: ogni ruolo che il sistema di autenticazione assegna nel contesto
  (scritto senza `#contesto`) viene tradotto in uno o più permessi GEMODO:
  consultazione, generazione, gestione modelli.
- **Client ammessi**: i sistemi (client tecnici) autorizzati a chiamare le API
  per questo contesto, oltre al client di accesso di GEMODO.
- **Copia il profilo di**: parte dal profilo di un'altra integrazione, per
  esempio GEBAN.

Le modifiche valgono dalla richiesta successiva: una revoca è immediata.

## Dimensioni e policy

La pagina **Dimensioni e policy di derivazione** legge l'albero dal vivo
(**Ricarica albero**) e permette di navigarlo fino a una foglia. Per ogni
dimensione dichiarata, per esempio lingua o livello, si decide:

- **Sì, ogni valore è un modello a sé**: serve sempre una scelta esplicita e non
  c'è ripiego su un modello generico;
- **No, un modello può coprire tutti i valori**: il catalogo può usare il
  modello generico quando manca quello specifico;
- **Default**: il valore proposto nel builder. È solo una preselezione, non
  rende obbligatorio nulla.

La policy si applica a tutte le foglie del tipo documento. Una dimensione nuova,
comparsa nell'albero, resta *non configurata* finché non la si imposta; nel
frattempo richiede un valore esplicito.

Se l'integrazione non risponde, le policy già salvate restano attive ma non si
possono modificare.

## Intestazione e piè di pagina

Da **Impostazioni modelli**, per ogni tipo documento:

- **Intestazione**: logo (PNG o JPEG, al massimo 1 MB), testo sotto il logo e,
  se serve, prima riga in grassetto;
- **Piè di pagina**: testo e numero di pagina ("Pagina 2 di 5").

La cornice vale subito per **tutti** i modelli di quel tipo documento.

## Registro attività

Elenca le operazioni (chi, quando, su cosa), con filtri. Si possono caricare le
voci più vecchie con **Carica altri**. Le generazioni dei documenti hanno un
registro separato, che gli amministratori consultano tramite API per riferimento
documentale.

## Eliminare un'integrazione

Dalla scheda **Integrazione**, **Elimina integrazione** chiede conferma. È
un'operazione da riservare alle integrazioni di prova o dismesse.
