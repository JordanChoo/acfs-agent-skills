# Skills Catalog

Available skills installed at `~/.<harness>/skills/`. Consult this catalog when a task might match a skill — invoke it instead of solving from scratch.

## Infrastructure & Deployment

| Skill | When to use |
|-------|-------------|
| **gcloud** | Before any `gcloud`/`bq`/`firebase` command, deploying ("push main, prove it's live"), watching Cloud Build, Cloud Run/Functions, logs, Secret Manager, Tasks, Scheduler, BigQuery, emulators on the shared VPS: identity flags on every call (shared global config), reads vs owner-approved writes, `scripts/watch_deploy.py`, PERMISSION_DENIED / reauth / missing-region errors |
| **cloud-build** | Google Cloud Build CI/CD (cloudbuild.yaml, triggers, substitutions, secret manager, multi-stage pipelines wired to AR/Run/GKE/Firebase) |
| **firebase-basics** | Bootstrap + product reference for any Firebase project (CLI login, `firebase use`, MCP wiring, core concepts, IAM, IaC, SDKs) — load first; firebase-stack/emulator-harness build on top |
| **firebase-stack** | Firebase + GCP projects (Firestore, Functions, Hosting, Auth, rules, emulators, secrets) |
| **firebase-emulator-e2e-harness** | Deterministic E2E/integration harnesses around Firebase emulators (seeded Auth, Firestore, Storage) |
| **schema-change-rollout** | Safe schema changes across storage, types, APIs, jobs, UI — migration-window compatibility |
| **rch** | Offload cargo/gcc/bun builds to remote workers (slow compilation, hook routing, remote sync) |

## Networking

| Skill | When to use |
|-------|-------------|
| **tailscale** | Tailscale mesh-VPN / tailnet family — install & configure, exit nodes, subnet routers, ACL policy file, MagicDNS, SSH, **Taildrop** file transfer, Serve/Funnel, Docker/K8s operator, device management (MDM/SCIM/posture), session recording, Aperture (AI/LLM gateway), and `tsnet` Go apps |

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
| **langfuse-evals** | LLM prompt testing & evals on self-hosted Langfuse (datasets, `run_experiment`, LLM-as-judge, online/prod evals, agent/RAG, scores, prompt mgmt/optimization, CI regression gating; Python + TS). Connect via API/SDK, configure in Langfuse. Ref: github.com/JordanChoo/csv-langfuse |

## Decision APIs (MCP)

| Skill | When to use |
|-------|-------------|
| **rusty-jev** | Calling the Rusty Jev MCP (TypeSafe Jev decision model via the `mcp.choostring.ventures` portal): pick between `rusty-jev_classify` / `verify` / `rerank` / `screen` / `decide` / `list_models`, batch and size calls, read `action`/`reasons`/`confidence`, handle errors without double-paying |

## Web & Frontend

| Skill | When to use |
|-------|-------------|
| **astro-site** | Astro v5 static sites (Tailwind v4, MDX, content collections, sitemap, RSS, migrations) |
| **directus** | Self-hosted Directus headless CMS, row-level multitenancy (`tenant_id` + filter rules), permissions/policies, SDK, custom extensions (hooks/endpoints/operations), schema snapshots |
| **modern-web-guidance** | Modern HTML/CSS/client-side JS patterns before writing any web UI code: dialogs/popovers, anchor positioning, container queries, view transitions, scroll-driven animation, forms/autofill/validation, a11y, dark mode, CWV (LCP/INP/CLS), passkeys, sanitization, web components, built-in AI. Runs `npx -y modern-web-guidance@latest search "<query>"` then `retrieve <id>` (offline local search; Node 22+; sends anonymous telemetry unless `DISABLE_TELEMETRY=1`); `guides/` vendored as an offline copy. Not for backend/infra/tooling. Source: github.com/GoogleChrome/modern-web-guidance @ 4dd9683 (v1.0.0, Apache-2.0; guides CC-BY 4.0) |

## Design & UI

Imported third-party design skills. Both target frontend work; pick by job: **impeccable** for any design work on an existing or new UI (24 sub-commands), **hallmark** for building a new page/site from a brief (themes + slop lint).

| Skill | When to use |
|-------|-------------|
| **impeccable** | Design, redesign, shape, critique, audit, polish, harden, animate or otherwise improve a frontend (web or native iOS/Android): `/impeccable <command> <target>` with 24 commands (`init` → PRODUCT.md, `document` → DESIGN.md, `critique`, `audit`, `polish`, `bolder`, `quieter`, `distill`, `typeset`, `layout`, `animate`, `live`, …). Launcher `scripts/impeccable` downloads a checksum-pinned engine binary to `~/.impeccable/bin/` on first run. Source: github.com/pbakaus/impeccable @ d34c87e (v4.8.0, Apache-2.0) |
| **hallmark** | Build a NEW website/page/component that looks designed, not generated: deals 3 of 50 themes, builds from the visitor's job, lints in a browser for AI tells (`scripts/sloplint.mjs --render`), fresh-context review. Also `/hallmark redesign <path>` / `/hallmark audit <path>` (only when named). Never auto-applies to an existing design. Node 18+; render tier needs `puppeteer-core` + Chrome. Source: github.com/Nutlope/hallmark @ 6033bab (v2.0.0, MIT) |

## DevOps & CLI Tools

| Skill | When to use |
|-------|-------------|
| **agent-mail-ops** | Using Agent Mail (session start, one identity per session, reserving files, messaging, contact approval, conflicts, what to do when it is down) and fixing it (`AM is down`, `health_check` red / corrupt SQLite, wedged server, `agent-mail.service`, rogue `am serve-http`, port drift from `127.0.0.1:8765`, failed nightly `am` update, archive rebuild) |
| **br** | Beads issue tracker (`br`, `.beads/`): claim/close/sync without `--force` claims, closing before the work lands, parallel writes, stale-export and UNIQUE errors, `issues.jsonl` merge conflicts (tested br-native recipe), staging the tracker; maps stale AGENTS.md commands (`br prime`, `br import`, `--add-note`) to real ones |
| **dcg** | A Bash command was "BLOCKED by dcg" (Destructive Command Guard), or before cleanup, `rm -rf`, moving folders out of `~`, discarding git changes, force-push/branch delete, or redirects to variable paths: fix by rule, approval protocol, forbidden workarounds, a tested corpus of past blocks |
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
