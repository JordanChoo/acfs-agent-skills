---
name: directus
description: >-
  Discipline for self-hosted Directus headless CMS projects with row-level
  multitenancy, custom extensions, and Directus-backed frontend builds. Use
  when the repo has docker-compose with `directus/directus`, an `extensions/`
  folder, `@directus/sdk` or `@directus/extensions-sdk` in deps, a
  `snapshot.yaml` / schema migration file, or the user mentions Directus,
  collections, flows, hooks/endpoints/operations, filter rules, permissions,
  policies, schema snapshots, `PUBLIC_URL`, or `CORS_ORIGIN`. Encodes the
  row-level tenant pattern, frontend offline/cache fallback, self-hosted env
  triage, extension discipline, schema-promotion workflow, and recurring traps
  seen in real sessions.
---

# directus

Directus work in this environment usually falls into one of three buckets:

1. **Frontend consuming Directus at build time**: Astro/Next/static site pulls content from Directus.
2. **Self-hosted Directus instance**: Docker, domains, env vars, storage, backups, health checks.
3. **Directus internals**: permissions, multitenancy, flows, hooks, endpoints, schema snapshots.

Start by classifying which bucket you are in. Do **not** jump straight into app code or env-var edits.

## Triggers

Load this skill when ANY of:

- Files: `docker-compose*.y*ml` referencing `directus/directus`, `snapshot.yaml`, `extensions/`, `directus.config.{js,ts}`, `infra/directus/`, `.env.example` with `DIRECTUS_*` or `PUBLIC_URL`, `package.json` with `@directus/sdk` or `@directus/extensions-sdk`
- User mentions: Directus, collection, item, field, flow, hook, endpoint, operation, policy, role, filter rule, permission, snapshot, `directus_users`, `directus_files`, `PUBLIC_URL`, `CORS_ORIGIN`, `server/health`

## First 5 Minutes

Read these in order before changing anything:

1. Runtime entrypoint: `docker-compose.yml`, k8s manifests, or `infra/directus/`
2. Env contract: `.env.example`, deployment docs, secrets template
3. Schema source of truth: `snapshot.yaml`, `snapshots/`, or migrations
4. Frontend consumer: `src/lib/directus.*`, `src/env.d.ts`, build/tests that call Directus
5. Extensions and ops scripts: `extensions/`, `healthcheck.sh`, backup/restore scripts

Then decide the working mode explicitly:

- **Live CMS mode**: Directus is reachable and you will verify against it.
- **Offline cached mode**: build/test against previously cached Directus responses.
- **Offline seeded mode**: build/test against committed seed fixtures or migration output because Directus is down.

If you do not decide the mode up front, agents repeatedly waste time chasing the wrong failure.

## Core Mental Model

Directus mirrors your database. There are two separate surfaces:

- **Database schema**: tables, columns, FKs, indexes
- **Directus metadata**: `directus_collections`, `directus_fields`, `directus_relations`, `directus_permissions`, interfaces, presets, validations

Raw SQL migrations only cover the first. Schema snapshots cover **both**. This is the root cause of many "works locally, staging is wrong" bugs.

System collections you will touch most often:

- `directus_users`
- `directus_roles`
- `directus_policies`
- `directus_permissions`
- `directus_files`
- `directus_folders`
- `directus_flows`
- `directus_operations`

Query them via system endpoints like `/users` or `/files`, not `/items/directus_users`.

## Happy Path A: Frontend Consuming Directus

This is the most common failure cluster from session history. Treat it as a first-class integration, not "just another fetch."

### 1. Lock the env contract first

For build-time frontends:

- `DIRECTUS_URL` is **server-side only**
- Browser-visible vars use `PUBLIC_*`
- Commit `.env.example`
- Add `src/env.d.ts` so `import.meta.env.DIRECTUS_URL` is typed

Guardrail:

- Do **not** rename `DIRECTUS_URL` to `PUBLIC_DIRECTUS_URL` unless the browser truly needs to hit the CMS directly.
- Do **not** debug browser CORS for an Astro build-time fetch. CORS matters for browser/runtime/admin traffic, not server-side build fetches.

### 2. Use an explicit offline strategy

For Directus-backed static builds, the official fallback order is:

1. Live Directus
2. Cached API payloads
3. Committed migration-seeded fixtures
4. `null` for single-item lookups that genuinely have no fallback

Make this behavior intentional in code:

- List/archive helpers should usually return cached or seeded data instead of throwing.
- Single-item helpers can return `null` when there is no cached/seeded equivalent.
- Log the tier that was used so build/test failures are explainable.

This is not a hack. In repeated sessions, agents only got deterministic builds after promoting seeded offline data to an official path.

### 3. Do not run ambiguous builds

Allowed modes:

```bash
# Live CMS mode
DIRECTUS_URL=https://cms.example.com pnpm build

# Offline cached/seeded mode
DIRECTUS_URL="" pnpm build
```

Forbidden mode:

- Running a build/review with Directus down, an empty cache, and no seeded fixtures, then treating the output as authoritative

Guardrail:

- Never regenerate signoff snapshots or release artifacts from an empty-cache build unless the offline seeded path is intentional and documented.

### 4. Isolate cache in tests

Repeated failure pattern: one test or build job clears `.cache` while another test is reading from it.

Official rule:

- Tests that exercise Directus fallback must use a per-process temp cache dir via `CACHE_DIR`
- Build-verification tests must not share mutable cache state with unit tests

Example pattern:

```ts
vi.stubEnv('CACHE_DIR', join(tmpdir(), `directus-cache-${process.pid}`));
```

If tests and build verification both touch `.cache`, assume you need isolation.

### 5. Prefer typed SDK usage

```ts
import {
  createDirectus,
  rest,
  readItems,
  readItem,
} from '@directus/sdk';

interface Schema {
  blog_articles: BlogArticle[];
  case_studies: CaseStudy[];
}

const directus = createDirectus<Schema>(process.env.DIRECTUS_URL!).with(rest());

const posts = await directus.request(
  readItems('blog_articles', {
    filter: { status: { _eq: 'published' } },
    sort: ['-date_published'],
    fields: ['id', 'title', 'slug'],
  }),
);
```

Guardrails:

- `fields: ['*']` returns scalars only
- For relations, use explicit nested fields or `*.*`
- Avoid `*.*.*` in production
- Wrap Directus fetches with timeout/error handling so "Directus down during build" does not become a cryptic crash

### 6. Make rebuild hooks explicit

For static sites, create a Directus Flow that triggers your deploy hook when content changes:

- Trigger: create/update/delete on relevant collections
- Action: webhook to Pages/Hosting deploy hook

Do not rely on "someone remembers to redeploy after editing content."

## Happy Path B: Self-Hosted Directus

Default stack signature here:

```text
directus/directus:11.x
postgres:16
Node.js 22 if building extensions
pnpm >=10 <11 for extension work
```

Confirm these env vars before touching anything operational:

- `SECRET`
- `KEY`
- `PUBLIC_URL`
- `DB_CLIENT`
- DB connection vars
- `STORAGE_LOCATIONS`

Missing or rotating `SECRET`/`KEY` causes auth instability and session churn.

### Health checks are mandatory

Minimum verification surface:

```bash
curl -fsS "$DIRECTUS_URL/server/health"
curl -fsS "$DIRECTUS_URL/server/info"
curl -fsS "$DIRECTUS_URL/items/<public_collection>?limit=1&fields=id"
```

If you write a shell healthcheck under `set -e`, avoid `((FAILURES++))` in failure paths. Use:

```bash
FAILURES=$((FAILURES + 1))
```

That exact bug caused false script exits in real Directus ops sessions.

### Custom domain and admin triage

When the Directus admin shell loads but hydrates badly, or browser requests fail with `AxiosError: Network Error`, check this first:

1. Compare the browser address bar host to the failing request URL
2. If they differ, suspect `PUBLIC_URL`
3. Inspect `CORS_ORIGIN`

Rules:

- `PUBLIC_URL` must match the hostname users actually visit
- `CORS_ORIGIN` may need a comma-separated allowlist
- Hard-refresh or use a private window after env changes

Typical fix:

```env
PUBLIC_URL=https://cms.example.com
CORS_ENABLED=true
CORS_ORIGIN=https://app.example.com,https://cms.example.com
```

Rollback tactic when env changes broke the admin:

- Remove `PUBLIC_URL` entirely and let Directus derive it from the request host
- Remove or simplify `CORS_ORIGIN`
- Restart and retest

This rollback path repeatedly unblocked broken self-hosted admin sessions and should be considered official, not improvised.

### Storage and backups

- Local `./uploads` is fine for dev, not for multi-instance prod
- Use S3/R2/GCS for anything past a single container
- Back up the database **and** object storage

Guardrail:

- A non-empty `.sql.gz` file is **not** proof of a valid backup
- Validate compressed dumps with `gunzip -t`
- Inspect the header for a Postgres dump signature
- Resolve the target postgres container explicitly; do not rely on loose `name=postgres` substring matches in shared Docker hosts

## Happy Path C: Schema Promotion

Promote schema with snapshots, not raw SQL alone:

```bash
# source env
docker compose exec directus npx directus schema snapshot ./snapshot.yaml --yes

# target env
docker compose exec directus npx directus schema apply ./snapshot.yaml --yes
```

After `schema apply`, clear schema cache:

- `docker compose restart directus`, or
- `POST /utils/cache/clear` with an admin token

This cache invalidation step was repeatedly skipped in real sessions. Treat it as mandatory.

Fresh environment order:

1. `directus bootstrap`
2. custom DB migrations
3. `directus schema apply ./snapshot.yaml`
4. restart / clear cache

Never modify `directus_*` system tables from raw SQL migrations.

## Multitenancy: Row-Level Pattern

Default tenancy model in this environment is single-instance row-level tenancy.

Required shape:

```sql
tenants(id, name, slug, ...)
posts(id, tenant_id, ...)
projects(id, tenant_id, ...)
ALTER TABLE directus_users ADD COLUMN tenant_id uuid REFERENCES tenants(id);
```

Permission filter on every tenant-scoped collection:

```json
{
  "tenant_id": { "_eq": "$CURRENT_USER.tenant_id" }
}
```

Create preset:

```json
{ "tenant_id": "$CURRENT_USER.tenant_id" }
```

Guardrails:

- Exclude `tenant_id` from user-updatable fields
- Never give tenant admins `admin_access: true`
- Never leave a tenant-scoped collection without `tenant_id`
- Audit the Public role on every project

Dynamic variables you will actually use:

- `$CURRENT_USER`
- `$CURRENT_USER.tenant_id`
- `$CURRENT_ROLE`
- `$CURRENT_ROLES`
- `$CURRENT_POLICIES`
- `$NOW`

## Extensions, Hooks, Endpoints, Flows

Scaffold extensions with:

```bash
npx create-directus-extension@latest
```

Use the right surface:

- **Flow**: visual automation, cross-system glue, webhooks, schedules
- **Hook**: block or mutate writes in-process
- **Endpoint**: bespoke REST shape or server-side RPC
- **Operation**: reusable Flow step

### The accountability rule

This is the main Directus extension footgun:

- `accountability: null` runs as root
- It bypasses normal permissions and tenant filters

Rules:

- Endpoints should pass `req.accountability`
- User-triggered hooks/operations must preserve real accountability when possible
- If a root-level operation is unavoidable, stamp `tenant_id` explicitly and document why

Example endpoint pattern:

```ts
import { defineEndpoint } from '@directus/extensions-sdk';

export default defineEndpoint((router, { services, getSchema }) => {
  router.get('/tenant-stats', async (req, res) => {
    if (!req.accountability?.user) return res.status(401).end();
    const schema = await getSchema();
    const items = new services.ItemsService('posts', {
      schema,
      accountability: req.accountability,
    });
    const result = await items.readByQuery({ aggregate: { count: ['id'] } });
    res.json(result);
  });
});
```

## Verification Checklist

Before you call the work done, verify the path you actually touched:

- Frontend:
  - build passes in the intended live or offline mode
  - fallback tier is explicit in logs
  - tests do not share mutable Directus cache state
  - no browser-only env vars were used for server-side fetches
- Self-hosted CMS:
  - `/server/health` and `/server/info` pass
  - one representative collection query passes
  - `PUBLIC_URL` and real hostname match
  - hard refresh/private window after env changes
- Schema changes:
  - snapshot committed
  - apply step documented
  - restart or `/utils/cache/clear` performed
- Multitenancy/extensions:
  - no `accountability: null` leaks
  - tenant filter/preset present
  - Public role audited

## Red Flags: Stop And Ask

- Build output or signoff was generated from Directus-down + empty-cache mode
- Tests share one mutable `.cache` between build verification and Directus unit tests
- `PUBLIC_URL` does not match the admin hostname in the browser
- `CORS_ORIGIN` only includes the public app but the admin is cross-origin
- New schema applied without restart/cache clear
- Raw SQL touches `directus_*` tables
- Root-level extension/service call (`accountability: null`) is being used for user-triggered work
- Tenant-scoped collection has no `tenant_id`
- Public role can read tenant or draft data
- Backup scripts only check "file exists" and not dump integrity

## What To Read First In An Unfamiliar Directus Repo

1. `docker-compose.yml` or infra manifests
2. `.env.example`
3. `snapshot.yaml` or migration folder
4. `src/lib/directus.*` or equivalent CMS client
5. `tests/*directus*` and build verification tests
6. `extensions/`
7. `healthcheck.sh`, backup scripts, restore docs

