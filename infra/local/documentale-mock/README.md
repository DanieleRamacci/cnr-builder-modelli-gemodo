# Documentale mock

Servizio `documentale-mock` dell'ambiente locale GEMODO (`infra/local/compose.yaml`).

Simula lo storage documentale (documentale interno o S3-compatibile, vedi vincoli di
dominio della costituzione) dietro un riferimento documentale stabile, cosi' che generazione
e download possano essere validati senza dipendere da uno storage di produzione.

- Espone un health endpoint HTTP (`/health`) sulla porta `9000`, usato dalla verifica
  ambiente per lo stato del servizio `STORAGE`.
- Il riferimento documentale restituito da GEMODO resta indipendente dal backend fisico:
  la decisione sullo storage definitivo per PDF resta owner `005` con supporto `004` (vedi
  `docs/decision-register.yaml`).
- Readiness dettagliata: `infra/local/documentale-mock/readiness.yaml`.
