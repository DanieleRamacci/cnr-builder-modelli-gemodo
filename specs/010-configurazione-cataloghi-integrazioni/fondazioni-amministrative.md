# Fondazioni Amministrative - 2026-09-17

Nota storica del primo incremento: il successivo
[incremento US1/US2](./definizione-export.md) implementa definizione,
generazione/export e lettura dashboard. Le indicazioni sotto di API non
implementate descrivono lo stato precedente, non il runtime corrente.

Questo incremento riprende T005-T008 e T014, non implementa l'interfaccia
Angular o gli endpoint amministrativi US1-US4.

La migration 0010, successiva alla dismissione 0009, crea:

- `attributo_profilo`: attributi della definizione/esempio proprietario GEMODO.
- `schema_discovery_generato`: documentazione di esempio versionata per tipo.
- `endpoint_integrazione`: URL, timeout e metadati del futuro test di conformita'.

Nessuna tabella viene popolata dal discovery GEBAN. Nessun catalogo esterno
viene copiato nel DB, e nessun adapter locale viene reintrodotto.
Gli adapter non consultano ancora queste tabelle: l'URL esplicito operativo
rimane `GEMODO_DISCOVERY_ENDPOINTS`, fino al completamento di US3/T041.

`require_configurazione_admin` usa l'autenticazione esistente e richiede
`GEMODO_ADMIN`; il solo `GEMODO_MODELLI_GESTORE` non e' sufficiente.
I test esercitano il guard su una route di prova, non su endpoint runtime
amministrativi, che non sono ancora registrati.

Il contratto amministrativo v0.2 riallinea formato errori e tipi campo al
backend corrente. T002 resta parziale fino al riallineamento completo US1.

## Verifica E Deployment

Test: `uv --directory backend run pytest -m "not e2e"`.
I test di migration usano PostgreSQL reale e verificano anche downgrade a
0009 e nuovo upgrade. Nessuna migrazione e' stata eseguita su DB operativo.
Test mirati amministrativi: 8 passati, nessuno saltato. Suite completa non-e2e:
214 passati, 12 e2e esclusi, nessuno saltato (24.17s). La review indipendente
di questo incremento e' bloccata dalla policy di invio a servizi esterni:
serve autorizzazione esplicita per trasmettere repository/diff a Claude.
Il precedente report PASS non verifica queste nuove fondazioni.

Prima del deployment fare backup: l'avvio backend applica automaticamente
le migration pendenti, inclusa la 0009 distruttiva se ancora non applicata.
La 0010 puo' essere rimossa tornando a 0009, perdendo i nuovi dati
amministrativi; non tentare di oltrepassare la 0009 per ricostruire il catalogo.

## Residui

T019 richiede il design della definizione/esempio proprietario completo;
T002 richiede il conseguente allineamento contrattuale. Seguono servizi,
endpoint e dashboard US1-US4. La verifica hash/runner T055-T058 richiede
conferma delle soglie di classificazione, senza inventare blocchi di generazione.
T071 resta un gap non bloccante del censimento YAML nel tooling adev;
il diff dei contratti deve essere sottoposto esplicitamente alla review.
