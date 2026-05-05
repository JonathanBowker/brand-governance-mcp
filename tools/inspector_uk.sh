#!/usr/bin/env bash
set -euo pipefail

# Launch MCP Inspector against the live UK Brand Governance MCP endpoint.
# The API key is read from BRAND_GOVERNANCE_API_KEY so it does not need to be
# committed into the repository or passed on the command line history.

if [[ -f ".env" ]]; then
  # Load local repo env vars for convenience without exporting unrelated values.
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

: "${BRAND_GOVERNANCE_API_KEY:?Set BRAND_GOVERNANCE_API_KEY in your environment or .env before launching the inspector.}"

INSPECTOR_BIN="${HOME}/.local/node/node-v22.22.2-darwin-arm64/bin/mcp-inspector"
SERVER_URL="https://advancedanalytica.co.uk/mcp/brand-governance"

if [[ ! -x "${INSPECTOR_BIN}" ]]; then
  echo "mcp-inspector was not found at ${INSPECTOR_BIN}." >&2
  echo "Install it first or update the script to point at the correct binary." >&2
  exit 1
fi

exec "${INSPECTOR_BIN}" \
  --transport http \
  --server-url "${SERVER_URL}" \
  --header "X-Brand-Key: ${BRAND_GOVERNANCE_API_KEY}"
