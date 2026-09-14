# Quickstart: Verifica Flusso ACE/GEBAN

## Prerequisiti

- Realm Keycloak test: `https://sso.test.si.cnr.it/auth/realms/cnr`.
- Token destinato a GEMODO con `aud` contenente `gemodo-backend`.
- Client ACE ammesso nel profilo integrazione, ad esempio `geri-angular-public`.
- Mapper ACE sul client che emette il token:
  - `Mapper Type`: `ace mapper`
  - `Ace Contexts`: `geban`
  - `Add to access token`: `ON`
  - `Add to ID token`: `OFF`
  - `Add to userinfo`: `OFF`

## Configurazione Attesa

Aggiornare `infra/local/integration-profiles.local.yaml` in modo che il profilo GEBAN
contenga:

- client ACE ammesso;
- audience attesa `gemodo-backend`;
- `token_contexts: [geban]`;
- mapping da `ROLE_GESTORE#geban`, `ROLE_MANAGER#geban`, `ROLE_COORDINATOR#geban`,
  `ROLE_USER#geban` verso `DOCUMENTI_GENERATORE` e `DOCUMENTI_VIEWER`;
- mapping aggiuntivo solo per `ROLE_MANAGER#geban` verso `GEMODO_MODELLI_GESTORE`.

Il backend legge questo file tramite `GEMODO_INTEGRATION_PROFILES_PATH`; se la variabile
non e' impostata usa il manifest locale versionato in `infra/local/integration-profiles.local.yaml`.

## Verifiche Manuali

1. Ottenere un token ACE da GEBAN/ACE.
2. Decodificare il payload JWT senza pubblicare il token completo.
3. Verificare che siano presenti:

```json
{
  "iss": "https://sso.test.si.cnr.it/auth/realms/cnr",
  "aud": ["oauth2-resource", "gemodo-backend", "account"],
  "azp": "geri-angular-public",
  "resource_access": {
    "gemodo-backend": {
      "roles": ["DOCUMENTI_VIEWER", "DOCUMENTI_GENERATORE"]
    }
  },
  "contexts": {
    "geban": {
      "roles": ["ROLE_COORDINATOR#geban"]
    }
  }
}
```

4. Confermare che `gemodo-backend` dentro `aud` venga prodotto stabilmente dal client
   ACE/GEBAN tramite audience mapper o client scope equivalente.
5. Chiamare una API di generazione GEBAN con il token.
6. Attendersi autorizzazione per generazione se il ruolo esterno e' mappato o se sono
   presenti ruoli GEMODO diretti equivalenti.
7. Provare un accesso builder con `ROLE_USER#geban`.
8. Attendersi rifiuto per gestione modelli.
9. Provare un accesso builder con `ROLE_MANAGER#geban`.
10. Attendersi autorizzazione alla gestione modelli nel perimetro GEBAN.

## Comandi Di Test

Da `backend/`:

```bash
uv run pytest tests/common/test_security_jwt.py
uv run pytest tests/integration
```

Per una verifica piu' ampia:

```bash
uv run pytest -m "not e2e"
```

## Esiti Attesi

- Token senza `aud=gemodo-backend`: rifiutato.
- Token con client non censito: rifiutato.
- Token con `contexts.geban.roles` mancante: rifiutato per le azioni GEBAN se non ha ruoli
  GEMODO diretti equivalenti.
- Token con ruolo ACE sconosciuto: rifiutato.
- Token con `ROLE_MANAGER#geban`: abilita generazione e gestione modelli.
- Token con `ROLE_USER#geban`, `ROLE_COORDINATOR#geban` o `ROLE_GESTORE#geban`: abilita
  generazione, non gestione modelli.
