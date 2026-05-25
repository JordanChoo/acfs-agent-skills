# Self-Test: directus skill

Each test maps to a failure pattern observed in Directus sessions from the CASS corpus.

Run via:
```bash
bash "$(dirname "$(realpath "$0" 2>/dev/null || echo .)")/scripts/self-test.sh"
# Or just:
bash ~/.codex/skills/directus/scripts/self-test.sh
```

---

## Trigger Phrases (must activate the skill)

| Phrase | Expected |
|---|---|
| "Directus-backed Astro build keeps failing" | Activates |
| "Directus admin shows Axios Network Error" | Activates |
| "schema apply didn't show the new fields" | Activates |
| "how should I set PUBLIC_URL and CORS_ORIGIN" | Activates |
| "add a Directus healthcheck" | Activates |
| "Directus is down during build, what now?" | Activates |

---

## Structure

```bash
SKILL_DIR=~/.codex/skills/directus
test -f "$SKILL_DIR/SKILL.md"
test -f "$SKILL_DIR/SELF-TEST.md"
test -x "$SKILL_DIR/scripts/self-test.sh"
```

---

## Behavioural Checks

### B1 — Agent classifies the project shape first

The skill should push the agent to decide between:

- frontend consuming Directus
- self-hosted Directus stack
- Directus internals (permissions/extensions/schema)

Jumping straight to app code or env edits is the antipattern.

### B2 — Frontend work chooses a build mode explicitly

The agent should identify one of:

- live CMS mode
- offline cached mode
- offline seeded mode

Running an empty-cache build with Directus down and treating it as authoritative is the failure case.

### B3 — Env separation is explicit

The skill should keep `DIRECTUS_URL` server-side and reserve `PUBLIC_*` for browser-visible vars.

### B4 — Domain triage starts with `PUBLIC_URL` vs request host

For admin/network errors, the skill should compare the browser hostname to the failing request URL before chasing other causes.

### B5 — Schema promotion includes cache invalidation

`schema apply` must be followed by restart or `/utils/cache/clear`.

### B6 — Tests isolate mutable Directus cache

When a codebase has Directus build tests and fallback tests, the skill should call for per-process `CACHE_DIR` isolation.

---

## Failure-Case Tests

### F1 — Offline build guidance exists
The skill must explicitly mention:

- `Directus` down / unavailable
- cache fallback
- migration-seeded or seeded offline data
- forbidden empty-cache review/signoff

### F2 — Cache-race guidance exists
The skill must mention:

- `CACHE_DIR`
- per-process or temp cache dir
- build/test cache sharing as a risk

### F3 — `PUBLIC_URL` / `CORS_ORIGIN` guidance exists
The skill must mention:

- `PUBLIC_URL`
- `CORS_ORIGIN`
- request host or browser address bar comparison
- removing `PUBLIC_URL` as a rollback option

### F4 — Health-check guidance exists
The skill must mention:

- `/server/health`
- `/server/info`
- representative `/items/...` read

### F5 — Schema-apply cache invalidation guidance exists
The skill must mention:

- `schema apply`
- `docker compose restart directus` or `/utils/cache/clear`

### F6 — Multitenancy/extension root-bypass guardrail exists
The skill must mention:

- `accountability: null`
- `tenant_id`
- Public role or `admin_access`

---

## Cleanup

The self-test is read-only and does not require cleanup.

