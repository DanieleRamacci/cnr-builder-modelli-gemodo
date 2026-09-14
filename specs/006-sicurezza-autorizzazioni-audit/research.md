# Research: Sicurezza Autorizzazioni E Audit

## Decision: Centralizzare mapping ruoli nel profilo integrazione

La mappatura tra ruoli ACE/GEBAN e permessi GEMODO sara' configurata in
`infra/local/integration-profiles.local.yaml`, nello stesso profilo che gia' definisce
sistema richiedente, client applicativi, audience, tipi/categorie/tipologie/modeli ammessi
e permessi operativi.

**Rationale**: il file rappresenta gia' il confine autorizzativo tra applicazioni. Tenere
qui anche `contexts.<app>.roles -> permessi GEMODO` permette di aggiungere applicativi,
ruoli o perimetri senza cambiare endpoint e senza mescolare autorizzazione nel catalogo
puro.

**Alternatives considered**:

- Inserire mapping in `seed-demo-catalog.yaml`: scartato perche' il catalogo descrive
  entita' di dominio riusabili da piu' applicativi, non autorizzazioni specifiche GEBAN.
- Creare un file separato solo per ruoli: scartato per ora perche' duplicherebbe chiavi
  di sistema richiedente/client/contesto gia' presenti nel profilo di integrazione.
- Affidare tutto a Keycloak con ruoli GEMODO diretti: supportato come compatibilita', ma
  non sufficiente per il flusso ACE proposto, dove i ruoli istituzionali arrivano in
  `contexts.geban.roles`.

## Decision: Normalizzare sempre verso permessi interni GEMODO

Le API non controlleranno direttamente `ROLE_MANAGER#geban` o altri ruoli esterni. Il
backend costruira' un principal con permessi interni (`DOCUMENTI_GENERATORE`,
`DOCUMENTI_VIEWER`, `GEMODO_MODELLI_GESTORE`, ecc.) derivati sia da
`resource_access.gemodo-backend.roles` sia dal mapping dei claim `contexts.<app>.roles`.

**Rationale**: gli endpoint restano stabili anche se cambiano nomi o semantica dei ruoli
ACE. Il rischio di dare accesso al builder a ruoli GEBAN troppo larghi viene contenuto
dalla mappa.

**Alternatives considered**:

- Leggere ruoli ACE direttamente nei decorator/guard endpoint: scartato perche' porterebbe
  varianti sparse nel codice.
- Accettare qualunque ruolo nel contesto `geban`: scartato perche' un nuovo ruolo ACE non
  deve diventare automaticamente autorizzante.

## Decision: Audience GEMODO obbligatoria anche con context roles

Ogni token accettato deve contenere `aud` con `gemodo-backend`. Il claim
`contexts.geban.roles` qualifica contesto e ruolo, ma non prova che il token sia destinato
alle API GEMODO.

**Rationale**: evita token emessi per altre applicazioni riusati contro GEMODO solo
perche' includono ruoli GEBAN.

**Alternatives considered**:

- Accettare token con solo `contexts.geban.roles`: scartato perche' indebolisce la
  separazione tra resource server.

## Decision: Supportare sia client tecnico di test sia client ACE reale

`geban-backend` resta ammesso per test/CI con ruoli GEMODO diretti. I client ACE reali
vengono ammessi via configurazione, inizialmente `geri-angular-public` o equivalente
comunicato dal team GEBAN.

**Rationale**: preserva i test esistenti e abilita il flusso reale senza forzare GEBAN a
creare un client tecnico dedicato.

**Alternatives considered**:

- Rimuovere `geban-backend`: scartato perche' utile come doppio controllato in locale/CI.
- Accettare qualunque `azp`: scartato perche' il contesto ACE deve arrivare da client
  censiti.
