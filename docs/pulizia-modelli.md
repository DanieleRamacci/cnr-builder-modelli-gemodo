# Demo ed eliminazione modelli

Le nuove installazioni aggiornate fino alla migrazione 0015 terminano senza
modelli demo. Le migrazioni storiche restano inalterate: 0015 rimuove i modelli
con UUID deterministici del manifest solo se non esistono integrazioni,
documenti generati o modelli diversi dai demo. Non rimuove definizioni
amministrative, tipi documento o funzionalita previste dalla spec 010.

Gli ambienti gia utilizzati non vengono bonificati automaticamente. Per i
test che richiedono il catalogo storico impostare GEMODO_KEEP_DEMO_MODELS=1
prima dell'upgrade iniziale. Cambiare il flag dopo 0015 non reinserisce demo.
Non impostarlo nei deployment operativi.

In Contesti, il pulsante cestino apre una conferma con nome e codice modello.
Annulla ed Escape non inviano scritture. Elimina chiama
DELETE /api/v1/builder/modelli/{modelloId}, autorizzato per contesto.
Il modello assume stato ELIMINATO, le versioni pubblicate sono archiviate
e viene registrato MODELLO_ELIMINATO. Non e piu elencato nel builder/catalogo
e non permette nuove versioni, transizioni o generazioni.
Versioni, campi, audit e PDF gia generati restano conservati; il download dei
documenti esistenti resta disponibile alle identita autorizzate.
Gli identificativi non vengono riutilizzati dall'eliminazione logica.

Per vedere il pulsante su Coolify aggiornare backend e frontend insieme;
l'avvio backend applica la nuova migrazione. Nessuna operazione sul DB remoto
e stata eseguita durante lo sviluppo.
