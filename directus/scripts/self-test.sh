#!/usr/bin/env bash
# directus skill self-test. Read-only content checks against the skill itself.
# Maps 1:1 to SELF-TEST.md and the failure cases mined from Directus sessions.

set -uo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_MD="$SKILL_DIR/SKILL.md"

PASS=0
FAIL=0

ok()  { echo "  ✓ $1"; PASS=$((PASS + 1)); }
bad() { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

expect_pattern() {
  local pattern="$1"
  local label="$2"
  if rg -qi --fixed-strings "$pattern" "$SKILL_MD"; then
    ok "$label"
  else
    bad "$label (missing: $pattern)"
  fi
}

echo "=== directus skill self-test ==="
echo

echo "[Structure]"
for f in \
  "$SKILL_DIR/SKILL.md" \
  "$SKILL_DIR/SELF-TEST.md" \
  "$SKILL_DIR/scripts/self-test.sh"; do
  [ -f "$f" ] && ok "exists: $f" || bad "missing: $f"
done
echo

echo "[B1] project-shape classification exists"
expect_pattern "frontend consuming Directus" "frontend shape documented"
expect_pattern "self-hosted Directus instance" "self-hosted shape documented"
expect_pattern "Directus internals" "internals shape documented"
echo

echo "[B2] build mode classification exists"
expect_pattern "Live CMS mode" "live mode documented"
expect_pattern "Offline cached mode" "offline cached mode documented"
expect_pattern "Offline seeded mode" "offline seeded mode documented"
echo

echo "[F1] offline build failure guidance exists"
expect_pattern "cached API payloads" "cache fallback documented"
expect_pattern "migration-seeded fixtures" "seeded fixture path documented"
expect_pattern "empty-cache build" "empty-cache guardrail documented"
expect_pattern "signoff snapshots" "signoff/regression guardrail documented"
echo

echo "[F2] cache race guidance exists"
expect_pattern "CACHE_DIR" "CACHE_DIR documented"
expect_pattern "per-process temp cache dir" "per-process cache isolation documented"
expect_pattern "Tests that exercise Directus fallback must use a per-process temp cache dir" "test isolation rule documented"
echo

echo "[F3] PUBLIC_URL/CORS guidance exists"
expect_pattern "PUBLIC_URL" "PUBLIC_URL documented"
expect_pattern "CORS_ORIGIN" "CORS_ORIGIN documented"
expect_pattern "browser address bar" "request-host triage documented"
expect_pattern 'Remove `PUBLIC_URL` entirely' "rollback path documented"
echo

echo "[F4] health-check guidance exists"
expect_pattern "/server/health" "server health endpoint documented"
expect_pattern "/server/info" "server info endpoint documented"
expect_pattern "/items/<public_collection>?limit=1&fields=id" "representative collection health probe documented"
echo

echo "[F5] schema-apply cache invalidation guidance exists"
expect_pattern "directus schema apply ./snapshot.yaml" "schema apply documented"
expect_pattern "docker compose restart directus" "restart after apply documented"
expect_pattern "/utils/cache/clear" "cache clear documented"
echo

echo "[F6] multitenancy/root-bypass guardrails exist"
expect_pattern "accountability: null" "root-bypass warning documented"
expect_pattern "tenant_id" "tenant guardrail documented"
expect_pattern "admin_access" "admin_access guardrail documented"
expect_pattern "Public role" "public role guardrail documented"
echo

echo "[F7] operational workarounds promoted to official steps"
expect_pattern "gunzip -t" "backup integrity validation documented"
expect_pattern 'FAILURES=$((FAILURES + 1))' "set -e healthcheck increment workaround documented"
echo

echo "=== Summary ==="
echo "PASS: $PASS    FAIL: $FAIL"
[ "$FAIL" -eq 0 ] && echo "PASS: directus skill covers the observed failure cases" && exit 0
echo "FAIL: directus skill is missing one or more observed failure-case guardrails"
exit 2
