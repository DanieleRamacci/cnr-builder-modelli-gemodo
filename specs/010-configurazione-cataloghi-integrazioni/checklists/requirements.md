# Checklist qualita' requisiti - dismissione FR-016

Creato: 2026-09-17. Destinatario: autore/reviewer Spec Kit.
Perimetro: T061-T070; non certifica requisiti pronti per US1-US4 o firme/runner.

- [x] CHK001 La distinzione tra catalogo esterno e modelli/contratti proprietari e' esplicita? [Chiarezza, FR-016]
- [x] CHK002 Il ritiro di tabelle/FK/API legacy e la preservazione degli identificativi sono dichiarati? [Completezza, FR-016, plan Phase 0]
- [x] CHK003 Il percorso e' definito senza assumere nomi o profondita' dei livelli? [Generalita', data-model PortaDiscovery]
- [x] CHK004 Sono distinti endpoint assente, indisponibilita' e forma non conforme, senza fallback locale? [Copertura eccezioni, incremento-discovery]
- [x] CHK005 Il cambio di semantica del filtro tipologia e' esplicito nel contratto v0.4 e nelle spec condivise? [Coerenza, 001 FR-020, T067]
- [x] CHK006 Self-service e onboarding sono esplicitamente rinviati anziche' implicati dall'assenza di URL? [Ambito, FR-010, US3 scenario 4, SC-003]
- [x] CHK007 La migrazione definisce backup, manutenzione e rollback, senza promettere ricostruzione del catalogo? [Recupero, incremento-discovery]
- [x] CHK008 API builder e codici errore hanno riferimenti versionati ed esempi success/error? [Contratti, contracts/builder-discovery-api.openapi.yaml]
- [x] CHK009 Soglie di verifica/versioning non decise restano fuori dal lavoro autorizzato? [Ambiguita' tracciata, T055-T058 sospesi]
- [x] CHK010 Autorizzazione sul contesto e' distinta dalla futura amministrazione integrazioni? [Sicurezza, plan Constitution Check, T014]
