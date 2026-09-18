#!/usr/bin/env bash
# Generates TypeScript types from the OpenAPI contracts this MVP consumes
# (specs/007-frontend-builder-consultazione/research.md: types only, no full
# SDK client). Re-run after any change to the source contracts.
#
# Written without associative arrays: macOS ships bash 3.2 by default, which
# does not support them.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(cd .. && pwd)"
OUT_DIR="src/shared/api-types"
mkdir -p "$OUT_DIR"

CONTRACTS="
integrazioni:$REPO_ROOT/specs/010-configurazione-cataloghi-integrazioni/contracts/integrazioni-api.openapi.yaml
configurazione-cataloghi:$REPO_ROOT/specs/010-configurazione-cataloghi-integrazioni/contracts/configurazione-cataloghi-api.openapi.yaml
builder-discovery:$REPO_ROOT/specs/010-configurazione-cataloghi-integrazioni/contracts/builder-discovery-api.openapi.yaml
builder-modelli:$REPO_ROOT/specs/002-builder-modelli/contracts/builder-modelli-api.openapi.yaml
"

for entry in $CONTRACTS; do
  name="${entry%%:*}"
  path="${entry#*:}"
  echo "==> ${name}"
  npx openapi-typescript "$path" --output "${OUT_DIR}/${name}.d.ts"
done
