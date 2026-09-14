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

## Verifiche Manuali

1. Ottenere un token ACE da GEBAN/ACE.
2. Decodificare il payload JWT senza pubblicare il token completo.
3. Verificare che siano presenti:

```json
{
  "iss": "https://sso.test.si.cnr.it/auth/realms/cnr",
  "aud": ["gemodo-backend"],
  "azp": "geri-angular-public",
  "contexts": {
    "geban": {
      "roles": ["ROLE_COORDINATOR#geban"]
    }
  }
}
```

4. Chiamare una API di generazione GEBAN con il token.
5. Attendersi autorizzazione per generazione se il ruolo esterno e' mappato.
6. Provare un accesso builder con `ROLE_USER#geban`.
7. Attendersi rifiuto per gestione modelli.
8. Provare un accesso builder con `ROLE_MANAGER#geban`.
9. Attendersi autorizzazione alla gestione modelli nel perimetro GEBAN.

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
