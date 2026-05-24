# Skills Catalog

Available skills installed at `~/.<harness>/skills/`. Consult this catalog when a task might match a skill — invoke it instead of solving from scratch.

## Infrastructure & Deployment

| Skill | When to use |
|-------|-------------|
| **cf-rust-worker** | Build, configure, deploy Rust-based Cloudflare Workers (wasm32, wrangler, secrets, build failures) |
| **firebase-basics** | Bootstrap + product reference for any Firebase project (CLI login, `firebase use`, MCP wiring, core concepts, IAM, IaC, SDKs) — load first; firebase-stack/emulator-harness build on top |
| **firebase-stack** | Firebase + GCP projects (Firestore, Functions, Hosting, Auth, rules, emulators, secrets) |
| **firebase-emulator-e2e-harness** | Deterministic E2E/integration harnesses around Firebase emulators (seeded Auth, Firestore, Storage) |
| **schema-change-rollout** | Safe schema changes across storage, types, APIs, jobs, UI — migration-window compatibility |
| **rch** | Offload cargo/gcc/bun builds to remote workers (slow compilation, hook routing, remote sync) |

## AI Agent Frameworks

| Skill | When to use |
|-------|-------------|
| **framework-selection** | START of any LangChain/LangGraph/Deep Agents project — determines which framework layer to use |
| **langchain-fundamentals** | Create LangChain agents (create_agent, tools, middleware, error handling) |
| **langchain-dependencies** | Package versions, installation, dependency management for LangChain/LangGraph/LangSmith/Deep Agents |
| **langchain-middleware** | Human-in-the-loop approval, custom middleware hooks, structured output (Pydantic/Zod) |
| **langchain-rag** | RAG systems (document loaders, text splitters, embeddings, vector stores — Chroma, FAISS, Pinecone) |
| **langgraph-fundamentals** | Any LangGraph code (StateGraph, state schemas, nodes, edges, Command, Send, streaming) |
| **langgraph-human-in-the-loop** | LangGraph human-in-the-loop patterns (interrupt, Command resume, approval workflows, error tiers) |
| **langgraph-persistence** | LangGraph state persistence (checkpointers, thread_id, time travel, Store, subgraph scoping) |
| **deep-agents-core** | Any Deep Agents app (create_deep_agent, harness architecture, SKILL.md format, config) |
| **deep-agents-memory** | Deep Agents memory/persistence (StateBackend, StoreBackend, FilesystemMiddleware, CompositeBackend) |
| **deep-agents-orchestration** | Deep Agents subagents, task planning, human approval (SubAgentMiddleware, TodoList, HITL) |

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
| **ntm** | Multi-agent tmux sessions via `ntm` CLI (spawn, attach, broadcast, session management) |
| **cass** | Search past Claude/Codex/Gemini sessions via `cass` CLI (recall prior work, search history) |
| **casr** | Cross Agent Session Resumer (convert/resume sessions across Claude Code, Codex, Gemini) |
| **process-triage** | Triage system processes via `pt` wrapper (runaway processes, scan, deep-scan, plan/apply) |
| **sbh** | Disk-pressure defense for AI coding workloads (disk full, cleanup, ballast, sbh daemon) |
| **dsr** | Doodlestein Self-Releaser (local builds, cross-platform releases when GitHub Actions is throttled) |

## Migrations & Maintenance

| Skill | When to use |
|-------|-------------|
| **bd-to-br-migration** | Migrate docs from bd (beads) to br (beads_rust) — command conversion, AGENTS.md updates |
