#!/usr/bin/env bash
# Regenerates public/runtime-config.json from container env vars at container
# startup (not build time) - the browser fetches this once at bootstrap
# (frontend/src/app/runtime-config.ts), before Keycloak is configured. Angular's
# esbuild-based builder does not substitute process.env at build time the way
# Vite's import.meta.env does, so a static-analysis approach does not work here;
# see the commit that added this script for how that was verified.
set -euo pipefail

cd "$(dirname "$0")/.."

KEYCLOAK_ISSUER_URL="${KEYCLOAK_ISSUER_URL:-https://sso.test.si.cnr.it/auth/realms/cnr}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-gemodo-frontend}"
GEMODO_EXTERNAL_DOCS_URL="${GEMODO_EXTERNAL_DOCS_URL:-}"

cat > public/runtime-config.json << EOF
{
  "keycloakIssuerUrl": "${KEYCLOAK_ISSUER_URL}",
  "keycloakClientId": "${KEYCLOAK_CLIENT_ID}",
  "externalDocsUrl": "${GEMODO_EXTERNAL_DOCS_URL}"
}
EOF
