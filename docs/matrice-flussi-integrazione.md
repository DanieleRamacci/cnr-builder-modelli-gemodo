# Matrice flussi integrazione, contesti e generazione

Aggiornata il 2026-10-06 dopo verifica del codice e dei test di integrazione.

Questa pagina descrive i casi operativi principali quando GEMODO lavora con
integrazioni, contesti, tipi documento, categorie/tipologie e generazione
GEBAN. La regola guida e': GEMODO non copia il catalogo esterno come sorgente
di verita', ma persiste modelli, versioni, campi, sezioni, policy e registri
che produce.

## Precondizioni

- Un'integrazione ha `codice_contesto`, accessi configurati e, se deve servire
  il builder, un endpoint discovery verificato come `CONNESSO`.
- Il builder usa sempre autorizzazione per contesto (`verify_scrittura_su_contesto`).
- Catalogo, validazione e generazione usano l'isolamento consumer per contesto
  quando `GEMODO_ENFORCE_CONTESTO_CONSUMATORE=true`. In Coolify il default e'
  `true`; nel codice resta `false` per rollout/test locali.
- Il perimetro fine per profilo (tipo/categoria/tipologia/singola versione
  ammessa) resta rinviato: oggi il confine reale e' il `codice_contesto`.

## Matrice casi

| Caso | Comportamento atteso | Esito |
|---|---|---|
| Una integrazione connessa per un contesto autorizzato | Il manager la vede, legge i tipi documento live e crea modelli da una foglia discovery | Regolare |
| Integrazione non connessa | Il manager non puo' usarla per creare modelli | `INTEGRAZIONE_NON_CONNESSA` / 409 |
| Integrazione di altro contesto | Non viene rivelata al manager non autorizzato | 404 sanificato |
| Due integrazioni dello stesso contesto espongono tipi diversi | Ogni tipo puo' essere associato alla propria integrazione quando viene usato | Regolare |
| Due integrazioni dello stesso contesto espongono lo stesso `tipo_documento` | GEMODO rifiuta di associare lo stesso tipo vivo a due integrazioni diverse | `TIPO_DOCUMENTO_ALTRA_INTEGRAZIONE` / 409 |
| Tipo documento locale libero, non ancora associato | Alla prima scrittura tramite integrazione viene associato a quell'integrazione | Regolare |
| Piu' categorie/tipologie nello stesso tipo documento | Il catalogo filtra sui codici salvati nei modelli; nessuna allowlist locale separata | Regolare |
| Categoria/tipologia inesistente o senza modello pubblicato | La ricerca catalogo restituisce elenco vuoto, non errore | 200 con `modelli: []` |
| Percorso non foglia o codici incoerenti col percorso | Il builder rifiuta la creazione | 400/404 |
| Categoria/tipologia ambigua senza percorso completo | Il builder chiede il percorso completo | 400 |
| Modello pubblicato nel proprio contesto | Catalogo, campi richiesti, validazione e generazione funzionano | Regolare |
| Modello di altro contesto richiesto per ID diretto | Non si rivela l'esistenza della versione | 404 `MODELLO_VERSIONE_NON_TROVATO` |
| Ricerca esplicita su tipo documento fuori perimetro | La ricerca e' un filtro esplicito, quindi il rifiuto e' visibile | 403 |
| Token con piu' contesti | I permessi non si sommano fra contesti: ogni risorsa verifica il proprio | Regolare |
| Ruoli diretti senza `contexts.<contesto>.roles` | Con isolamento acceso non autorizzano catalogo/generazione | 404/403 secondo rotta |
| Stessa chiave GEBAN rigenerata con dati diversi | Ogni chiamata produce un PDF nuovo e una riga di registro nuova | Regolare |
| Stessa chiave GEBAN ripetuta con stessi dati | Non c'e' piu' conflitto idempotente; si registra una nuova chiamata | Regolare |
| Registro generazioni non scrivibile | Il PDF non viene consegnato | 503 `REGISTRO_GENERAZIONI_NON_DISPONIBILE` |
| Lettura registro generazioni per riferimento | Solo amministratori GEMODO | 200 admin, 403 non admin |
| Download PDF dopo generazione | Non esiste piu': GEMODO non conserva il file | 404 |

## Note di sicurezza

- Le rotte dirette per versione (`campi-richiesti`, `valida`, `genera`) usano
  404 quando la versione e' fuori contesto, cosi' un chiamante non puo' capire
  se un modello di un altro contesto esiste.
- La ricerca catalogo per `tipo_documento` usa 403 quando il tipo esiste ma
  nessun contesto del token lo autorizza: qui il chiamante ha espresso un filtro
  funzionale, quindi la risposta distingue "non configurato" da "non autorizzato".
- Il registro attivita' e' best-effort; il registro generazioni no. Se la riga
  della generazione non viene scritta, il PDF non esce.

## Verifica eseguita

Comando eseguito il 2026-10-06:

```bash
cd backend && uv run pytest \
  tests/catalog/test_catalog_service_integration.py \
  tests/common/test_autorizzazione_per_contesto.py \
  tests/common/test_contesto_consumatore_profilo.py \
  tests/generazione/test_generazione_e_storage.py \
  tests/attivita/test_registro_attivita.py -q
```

Esito: 31 test passati.

Questi test coprono duplicati/aggregazione del catalogo, categoria o tipologia
senza modello, isolamento fuori contesto, token multi-contesto, ruoli diretti
senza contesto, generazione ripetuta con stessa chiave, registro generazioni e
registro attivita'.

## Fuori scope intenzionale

- Verifica amministrativa PDF/dati: rinviata a una spec futura.
- Monitoraggio continuo delle integrazioni con polling/scheduler ed email se il
  servizio e' giu' o non conforme: rinviato a una spec futura.
- Controlli di drift dati piu' ricchi (versione contratto osservata, dimensioni
  nuove senza policy, modello pubblicato non allineato al discovery corrente):
  da definire nella stessa spec futura di monitoraggio.
- Perimetro fine per profilo su tipo/categoria/tipologia/versione: rinviato e
  da riscrivere sul modello attuale in cui il profilo di accesso vive
  sull'integrazione.
