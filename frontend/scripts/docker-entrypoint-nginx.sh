#!/bin/sh
# Production entrypoint: regenerate runtime-config.json from the container's
# real env vars at startup (into nginx's served directory, not `public/` -
# see genera-runtime-config.sh for why this can't be baked in at build time)
# before starting nginx.
set -eu

KEYCLOAK_ISSUER_URL="${KEYCLOAK_ISSUER_URL:-https://sso.test.si.cnr.it/auth/realms/cnr}"
KEYCLOAK_CLIENT_ID="${KEYCLOAK_CLIENT_ID:-gemodo-frontend}"
GEMODO_EXTERNAL_DOCS_URL="${GEMODO_EXTERNAL_DOCS_URL:-}"

cat > /usr/share/nginx/html/runtime-config.json << EOF
{
  "keycloakIssuerUrl": "${KEYCLOAK_ISSUER_URL}",
  "keycloakClientId": "${KEYCLOAK_CLIENT_ID}",
  "externalDocsUrl": "${GEMODO_EXTERNAL_DOCS_URL}"
}
EOF

exec nginx -g 'daemon off;'
