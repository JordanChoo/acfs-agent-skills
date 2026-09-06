# Skills Catalog

Available skills installed at `~/.<harness>/skills/`. Consult this catalog when a task might match a skill — invoke it instead of solving from scratch.

## Infrastructure & Deployment

| Skill | When to use |
|-------|-------------|
| **cloud-build** | Google Cloud Build CI/CD (cloudbuild.yaml, triggers, substitutions, secret manager, multi-stage pipelines wired to AR/Run/GKE/Firebase) |
| **firebase-basics** | Bootstrap + product reference for any Firebase project (CLI login, `firebase use`, MCP wiring, core concepts, IAM, IaC, SDKs) — load first; firebase-stack/emulator-harness build on top |
| **firebase-stack** | Firebase + GCP projects (Firestore, Functions, Hosting, Auth, rules, emulators, secrets) |
| **firebase-emulator-e2e-harness** | Deterministic E2E/integration harnesses around Firebase emulators (seeded Auth, Firestore, Storage) |
| **schema-change-rollout** | Safe schema changes across storage, types, APIs, jobs, UI — migration-window compatibility |
| **rch** | Offload cargo/gcc/bun builds to remote workers (slow compilation, hook routing, remote sync) |

## Cloudflare Platform & Agents

Imported from [cloudflare/skills](https://github.com/cloudflare/skills) (Apache-2.0). Load **cloudflare** first when the product is not yet chosen; it routes to the others.

| Skill | When to use |
|-------|-------------|
| **cloudflare** | Product discovery + architecture for apps, APIs, AI agents, storage, networking, security — even when no Cloudflare product is named; bundles per-product references (D1, R2, KV, Queues, Vectorize, Workers AI, AI Gateway, Workflows, Containers, Browser Rendering, …) |
| **agents-sdk** | Build/debug/review Cloudflare Agents SDK apps (`agents` package: state + scheduling, callable RPC, MCP servers, workflows, durable execution, HITL, streaming chat, email, voice, codemode, observability) |
| **durable-objects** | Durable Objects for persistent state and coordination (RPC, SQLite storage, alarms, WebSockets; chat rooms, games, booking) |
| **workers-best-practices** | Writing, reviewing, or configuring production Workers (runtime patterns, platform APIs, configuration) |
| **wrangler** | Wrangler CLI: local dev, deploy, and managing Workers, KV, R2, D1, Vectorize, Queues, Workflows |
| **cf-rust-worker** | Rust Cloudflare Workers compiled to wasm32 (worker crate, worker-build, wrangler.toml, secrets, CF dashboard build failures) |
| **sandbox-next** | Cloudflare Sandbox apps on `@cloudflare/sandbox@next` (SDK 1.0 preview) — recommended for new projects |
| **sandbox-stable** | Sandbox apps on the stable `@cloudflare/sandbox` package |
| **sandbox-migrate-to-next** | Port a stable Sandbox app to `@cloudflare/sandbox@next` |
| **nextjs-on-cloudflare** | Next.js on Workers with vinext (new project, migrating an existing app, vinext vs OpenNext) |
| **cloudflare-email-service** | Email Sending / Email Routing integrations and delivery configuration |
| **turnstile-spin** | Set up, repair, or migrate Turnstile bot verification incl. server-side Siteverify |
| **web-perf** | Audit/optimize Core Web Vitals (FCP, LCP, TBT, CLS), render-blocking resources, network chains, Lighthouse |
| **cloudflare-one** | Cloudflare One Zero Trust / SASE (Access, Gateway, WARP, Tunnel, Magic WAN, DLP, CASB, posture, identity) |
| **cloudflare-one-migrations** | Migration assessment, policy mapping, parity gaps, rollout from Zscaler / Palo Alto / legacy VPN-SWG-SASE to Cloudflare One |

## Testing & Quality

| Skill | When to use |
|-------|-------------|
| **playwright-testing** | Playwright E2E tests (selectors, fixtures, traces, flaky tests, emulator project IDs) |
| **ubs** | Pre-commit bug/security scanning (UBS CLI, output parsing, false-positive triage, .ubsignore) |
| **async-state-machine-hardening** | Harden async workflows (queues, webhooks, cron, retries, idempotency, race conditions, state machines) |

## Web & Frontend

| Skill | When to use |
|-------|-------------|
| **astro-site** | Astro v5 static sites (Tailwind v4, MDX, content collections, sitemap, RSS, migrations) |
| **directus** | Self-hosted Directus headless CMS, row-level multitenancy (`tenant_id` + filter rules), permissions/policies, SDK, custom extensions (hooks/endpoints/operations), schema snapshots |

## DevOps & CLI Tools

| Skill | When to use |
|-------|-------------|
| **agent-mail-ops** | Agent Mail incidents in ACFS (`AM is down`, disconnected MCP, `health_check` red / corrupt SQLite, `agent-mail.service`, rogue `mcp-agent-mail serve`, endpoint drift away from `127.0.0.1:8765`, failed nightly `am` update, archive rebuild) |
| **shared-skill-authoring** | Create or update shared Claude/Codex skills from `~/src/acfs-agent-skills`, run drift audits, and install via the canonical symlink workflow |
| **ntm** | Multi-agent tmux sessions via `ntm` CLI (spawn, attach, broadcast, session management) |
| **cass** | Search past Claude/Codex/Gemini sessions via `cass` CLI (recall prior work, search history) |
| **casr** | Cross Agent Session Resumer (convert/resume sessions across Claude Code, Codex, Gemini) |
| **process-triage** | Triage system processes via `pt` wrapper (runaway processes, scan, deep-scan, plan/apply) |
| **sbh** | Disk-pressure defense for AI coding workloads (disk full, cleanup, ballast, sbh daemon) |
| **dsr** | Doodlestein Self-Releaser (local builds, cross-platform releases when GitHub Actions is throttled) |

## Skill Development

| Skill | When to use |
|-------|-------------|
| **skill-creator** | Create, evaluate, and iterate on Claude Code / Codex skills (SKILL.md authoring, benchmark evals, grading agents, packaging) |

## Migrations & Maintenance

| Skill | When to use |
|-------|-------------|
| **bd-to-br-migration** | Migrate docs from bd (beads) to br (beads_rust) — command conversion, AGENTS.md updates |
