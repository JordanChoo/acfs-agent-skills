---
name: directus
description: >-
  Discipline for self-hosted Directus headless CMS projects with row-level
  multitenancy and custom extensions. Use when the repo has docker-compose
  with `directus/directus`, an `extensions/` folder, `@directus/sdk` or
  `@directus/extensions-sdk` in deps, a `snapshot.yaml` / schema migration
  file, or the user mentions Directus, collections, flows, hooks/endpoints/
  operations, filter rules, permissions, policies, or schema snapshots.
  Encodes the row-level tenant pattern, permission filter syntax, SDK
  composables, extension scaffolding, schema-promotion workflow, and the
  recurring traps (cache invalidation, system-collection writes, public role).
---

# directus

Decision logic for self-hosted Directus projects in this environment. Default tenancy model: **row-level (single instance, `tenant_id` FK + filter rules)**. Default deploy: **Docker / docker-compose**. Extensions are first-class.

## Triggers

Load this skill when ANY of:
- Files: `docker-compose*.y*ml` referencing `directus/directus`, `snapshot.yaml`, `extensions/`, `directus.config.{js,ts}`, `package.json` with `@directus/sdk` or `@directus/extensions-sdk`
- User mentions: Directus, collection, item, field, flow, hook, endpoint, operation, policy, role, filter rule, permission, snapshot, M2A/M2M/M2O, `directus_users`, `directus_files`

## Canonical stack signature

```
directus/directus:latest                       # pinned in prod (e.g. :11.x)
postgres:16                                    # mysql/mariadb supported but pg is default
@directus/sdk: ^19.x                           # composable client
@directus/extensions-sdk: ^13.x                # only if writing extensions
Node.js 22, pnpm >=10 <11                      # if building extensions
```

Confirm `DB_CLIENT`, `STORAGE_LOCATIONS`, and `SECRET` in the env before touching anything that talks to Directus. Missing `SECRET` rotates session tokens on every restart.

## Core mental model

Directus **mirrors** your database. It does not own the schema — every Directus "collection" is a Postgres/MySQL table, every "field" is a column. Two parallel concerns:
- **Database schema**: tables, columns, FKs, indexes — managed via Directus admin OR raw SQL/migrations. Both stay in sync because Directus introspects on boot.
- **Directus metadata**: `directus_collections`, `directus_fields`, `directus_relations`, `directus_permissions`, etc. — system tables that describe interfaces, display modes, validation, presets. Only Directus knows about these.

Schema snapshots (`directus schema snapshot` → `directus schema apply`) capture **both**. Raw SQL migrations capture only the first. This is the #1 source of "it works on my laptop" bugs.

### System collections you'll touch
`directus_users`, `directus_roles`, `directus_policies`, `directus_permissions`, `directus_files`, `directus_folders`, `directus_flows`, `directus_operations`, `directus_revisions`, `directus_activity`. All queryable via `/users`, `/files`, etc. — not `/items/directus_users`.

---

## Multitenancy: row-level pattern (default)

Single Directus instance, every tenant-scoped collection has a `tenant_id` M2O to a `tenants` collection. Isolation is enforced by **permission filter rules** that reference `$CURRENT_USER.tenant_id`, not by application code.

### Required schema shape

```sql
-- tenants is the root
tenants(id, name, slug, ...)

-- every tenant-scoped collection
posts(id, tenant_id, title, ...)  -- tenant_id NOT NULL, FK to tenants.id
projects(id, tenant_id, ...)

-- users belong to a tenant via a custom column on directus_users
ALTER TABLE directus_users ADD COLUMN tenant_id uuid REFERENCES tenants(id);
```

In Directus: add a `tenant_id` field to `directus_users` (Settings → Data Model → Directus Users → Create Field → M2O to `tenants`). This makes `$CURRENT_USER.tenant_id` resolvable in filter rules.

### Permission filter (apply to every tenant-scoped collection, every action)

```json
{
  "tenant_id": { "_eq": "$CURRENT_USER.tenant_id" }
}
```

For **create** actions, add a preset (not a filter) that stamps `tenant_id` automatically so users can't forge it:

```json
// Preset on the create permission
{ "tenant_id": "$CURRENT_USER.tenant_id" }
```

Combine with `fields` whitelist that **excludes** `tenant_id` from updatable fields — otherwise an authenticated user can move records between tenants by PATCH.

### Tenant-admin role

A "tenant admin" role gets full CRUD scoped by the same filter — **never** `admin_access: true`, which bypasses all permissions. Reserve `admin_access` for platform operators.

### Red flags for row-level tenancy
- A collection without `tenant_id` that holds tenant data → cross-tenant leak waiting to happen
- A permission without the tenant filter → same
- Filter rule using `$CURRENT_USER` (the id) instead of `$CURRENT_USER.tenant_id` (the FK) → only scopes by user, not tenant
- A flow operation that writes items with `accountability: null` → bypasses permissions; must set tenant_id explicitly
- Custom endpoints using `ItemsService` with `{ schema, accountability: null }` → same; pass real accountability or stamp tenant_id by hand

---

## Permissions, roles, policies

Directus 11+ separates the three:
- **Role** — a label assigned to users (e.g., "Editor"). Roles can be nested.
- **Policy** — a bag of permissions. Attached to a role OR directly to a user.
- **Permission** — one row per `(policy, collection, action)` with `permissions` filter, `fields` whitelist, `validation`, `presets`.

Actions: `create`, `read`, `update`, `delete`, `share`. The "comment" action is on a per-collection basis as of v11.

### Filter rule syntax (used in permissions, flows, SDK queries)

```json
{
  "_and": [
    { "status": { "_eq": "published" } },
    { "tenant_id": { "_eq": "$CURRENT_USER.tenant_id" } },
    { "_or": [
      { "author": { "_eq": "$CURRENT_USER" } },
      { "visibility": { "_in": ["public", "team"] } }
    ]}
  ]
}
```

Operators: `_eq _neq _lt _lte _gt _gte _in _nin _null _nnull _contains _ncontains _starts_with _ends_with _between _nbetween _empty _nempty _intersects _ncontains _regex`.

Dynamic variables: `$CURRENT_USER` (id, or `.field` to dereference), `$CURRENT_ROLE`, `$CURRENT_ROLES` (array, includes nested), `$CURRENT_POLICIES` (array), `$NOW`, `$NOW(-7 days)` / `$NOW(+1 hour)`.

The **Public** role/policy is the unauthenticated default. Review it on every project — accidentally granting `read` to a collection here exposes data to the open internet.

---

## SDK usage (`@directus/sdk`)

Composable client — start empty, add the features you need:

```ts
import { createDirectus, rest, authentication, staticToken, readItems, createItem } from '@directus/sdk';

// Frontend / user session
const client = createDirectus<Schema>(import.meta.env.DIRECTUS_URL)
  .with(authentication('cookie', { credentials: 'include' }))
  .with(rest());

// Server-to-server with a static token (machine user)
const server = createDirectus<Schema>(process.env.DIRECTUS_URL!)
  .with(staticToken(process.env.DIRECTUS_TOKEN!))
  .with(rest());

const posts = await client.request(readItems('posts', {
  filter: { status: { _eq: 'published' } },
  fields: ['id', 'title', 'slug', { author: ['first_name', 'avatar'] }],
  sort: ['-published_at'],
  limit: 10,
}));
```

### Type-safety
Define `Schema` as `{ posts: Post[]; tenants: Tenant[]; ... }`. Generate it with `directus-sdk-typegen` or hand-write it — without it every `readItems` returns `unknown[]`.

### Field selection gotcha
`fields: ['*']` returns scalars only. For relations, use `*.*` (one level) or explicit nested arrays. Don't use `*.*.*` in production — N+1 expansion is unbounded.

### REST equivalents (when SDK isn't an option)
```
GET    /items/{collection}?filter[status][_eq]=published&fields=*,author.name&sort=-published_at&limit=10
POST   /items/{collection}                     # single or array body
PATCH  /items/{collection}/{id}
DELETE /items/{collection}/{id}
GET    /items/{collection}/singleton           # for singleton collections
```

GraphQL is at `POST /graphql` (items) and `POST /graphql/system` (system collections). Same auth header.

---

## Extensions

Three API extension types, four+ app extension types. Scaffold with the SDK CLI:

```bash
npx create-directus-extension@latest
# pick type: hook | endpoint | operation | interface | display | layout | module | panel | theme | bundle
```

### Hooks (lifecycle)
```ts
import { defineHook } from '@directus/extensions-sdk';

export default defineHook(({ filter, action }) => {
  // filter = blocking, can mutate payload; action = fire-and-forget
  filter('items.create', async (payload, { collection, accountability }, { services, database }) => {
    if (collection === 'posts' && accountability?.user) {
      const usersService = new services.UsersService({ schema: await getSchema(), database });
      const user = await usersService.readOne(accountability.user, { fields: ['tenant_id'] });
      payload.tenant_id ??= user.tenant_id;  // server-side tenant stamp, defence-in-depth
    }
    return payload;
  });
});
```

Hook events: `(server|app).start`, `auth.*`, `(items|files|users|roles|...).{create,update,delete}` with `before` (filter) and `after` (action) variants. Use `filter` to mutate/block, `action` for side effects (webhooks, logs).

### Endpoints (custom REST routes)
```ts
import { defineEndpoint } from '@directus/extensions-sdk';

export default defineEndpoint((router, { services, getSchema }) => {
  router.get('/tenant-stats', async (req, res) => {
    if (!req.accountability?.user) return res.status(401).end();
    const schema = await getSchema();
    const itemsService = new services.ItemsService('posts', { schema, accountability: req.accountability });
    const count = await itemsService.readByQuery({ aggregate: { count: ['id'] } });
    res.json(count);
  });
});
```
Mounted at `/<extension-name>/...`. Always pass `req.accountability` to services — `accountability: null` runs as root and skips all permission filters (including tenant isolation).

### Operations (Flow steps)
```ts
import { defineOperationApi } from '@directus/extensions-sdk';

export default defineOperationApi<{ tenant_id: string; subject: string }>({
  id: 'send-tenant-email',
  handler: async ({ tenant_id, subject }, { services, getSchema }) => {
    // ...
    return { sent: true };
  },
});
```
Pair with a `defineOperationApp` in `app.ts` for the visual editor card.

### App extensions
Interfaces (field editors), displays (read-only field renderers), layouts (collection views), modules (sidebar pages), panels (Insights tiles), themes. Vue 3 SFCs. Built with the same SDK CLI; output to `dist/` and loaded from the extensions folder.

### Dev/build/deploy

```bash
pnpm dev      # watches src/, rebuilds dist/, hot-reload (API exts need server restart for hooks/endpoints)
pnpm build    # production bundle to dist/
pnpm validate # schema check + structure
```

Deploy: mount the extension folder at `/directus/extensions/<name>/dist/` OR publish to npm with the `directus-extension` keyword and `pnpm add` inside the container. Set `EXTENSIONS_AUTO_RELOAD=true` only in dev — in prod it tanks startup time.

### Bundles
Group related extensions (e.g., interface + display + hook for the same feature) into a single `bundle` extension. One install, one entry in `directus_extensions`.

---

## Flows

No-code automation: trigger (event hook / webhook / schedule / manual / operation) → operations DAG. Operations include: condition, transform, run-script (JS sandbox), notification, webhook, item-create/read/update/delete, mail, log.

### Tenant-safe flow rules
- Flows run with the **trigger user's accountability** by default. Set `accountability: "all"` only if the flow legitimately needs cross-tenant access (rare).
- `run-script` operations have a 10s timeout and no `require` — for anything bigger, write a custom operation extension.
- Manual triggers attached to a collection respect that user's permissions for which items they can run it on.

### When to use Flows vs hooks vs endpoints
- **Flow** — non-developer editable, visual, schedulable, webhooks. Default for cross-system glue.
- **Hook** — needs to block/mutate item writes, runs in-process, must be fast. Defence-in-depth for tenant stamping.
- **Endpoint** — bespoke REST shape (aggregations, RPC-style), or needs to bypass the Items API.

---

## Schema management & promotion

**Always promote schema with snapshots, not raw SQL**, because snapshots round-trip Directus metadata (interfaces, presets, permissions).

```bash
# In source env (dev)
docker compose exec directus npx directus schema snapshot ./snapshot.yaml --yes

# Commit snapshot.yaml to git

# In target env (staging/prod)
docker compose exec directus npx directus schema apply ./snapshot.yaml --yes
```

### The cache invalidation trap
`schema apply` does **not** always invalidate the schema cache. After apply, either:
- `docker compose restart directus`, OR
- `POST /utils/cache/clear` with admin token

If the new fields/collections aren't appearing in API responses after apply, this is almost always why.

### Custom SQL migrations
Live in `<extensions>/migrations/<timestamp>-name.{js,ts}` with `up`/`down` exports. Run automatically on `directus bootstrap` and `directus start`. **Never** modify `directus_*` system tables in a migration — schema may not exist yet on first boot. Use a schema snapshot for that.

### Order on a fresh environment
1. `directus bootstrap` (creates system tables, runs system migrations, creates admin)
2. `directus database migrate:latest` (runs your custom SQL migrations)
3. `directus schema apply ./snapshot.yaml` (applies user collections + metadata)
4. Restart container (cache flush)

---

## Self-hosting essentials

### Required env vars
```
KEY=<uuid>                    # used to sign tokens; rotate = log everyone out
SECRET=<32+ char random>      # encrypts refresh tokens, flow secrets
PUBLIC_URL=https://cms.example.com
DB_CLIENT=pg
DB_CONNECTION_STRING=postgres://...   # or DB_HOST/DB_PORT/DB_DATABASE/DB_USER/DB_PASSWORD
ADMIN_EMAIL / ADMIN_PASSWORD          # only used on bootstrap of empty DB
CACHE_ENABLED=true CACHE_STORE=redis CACHE_REDIS=redis://...   # prod
STORAGE_LOCATIONS=s3
STORAGE_S3_DRIVER=s3 STORAGE_S3_KEY=... STORAGE_S3_SECRET=... STORAGE_S3_BUCKET=... STORAGE_S3_REGION=...
CORS_ENABLED=true CORS_ORIGIN=https://app.example.com
EMAIL_TRANSPORT=smtp ...
```

### File storage
Default is local disk (`./uploads`) — fine for dev, **not** for multi-instance or k8s. Switch to S3/R2/GCS via `STORAGE_LOCATIONS` for anything past a single container.

### Health check
`GET /server/health` — use as the Docker `HEALTHCHECK` and k8s liveness probe.

### Backups
The database is the source of truth — schema snapshots are **not** a backup of data. Back up Postgres + the storage bucket. Test restore quarterly.

---

## Red flags — stop and ask

- A new tenant-scoped collection without `tenant_id` field
- A permission row without `tenant_id` filter (or using `$CURRENT_USER` instead of `$CURRENT_USER.tenant_id`)
- Custom endpoint or flow operation using `accountability: null` for user-triggered actions — defeats tenant isolation
- A role with `admin_access: true` assigned to anyone except platform operators
- The Public role/policy granting read on anything tenant-scoped
- Raw SQL migration touching `directus_*` tables — use a schema snapshot instead
- `EXTENSIONS_AUTO_RELOAD=true` in production
- Missing/rotating `SECRET` or `KEY` between deploys (logs everyone out, breaks flow secrets)
- `fields=*.*.*` in API queries — unbounded N+1
- Schema changes that work in dev but not staging — almost always the cache invalidation trap
- Hook/operation extension that reads `directus_users` with `accountability: null` to "check the tenant" — use the request's accountability instead

---

## What to read first in an unfamiliar Directus repo

1. `docker-compose.yml` / k8s manifests — image tag, env vars, mounted volumes (`/directus/extensions`, `/directus/uploads`)
2. `snapshot.yaml` (or `snapshots/`) — current canonical schema; grep for `tenant_id` to confirm tenancy model
3. `extensions/` folder — list each extension's `package.json` to see types (`directus:extension.type`)
4. `migrations/` folder — any SQL migrations applied on top of the snapshot
5. `.env.example` — required env, especially `KEY`, `SECRET`, `STORAGE_*`, `CACHE_*`
6. Frontend SDK usage — `grep -r '@directus/sdk' src/` to find every query; verify they pass auth and respect tenancy
7. `CLAUDE.md` / `AGENTS.md` — project-specific overrides
