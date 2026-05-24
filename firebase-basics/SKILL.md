---
name: firebase-basics
description: >-
  Bootstrap and product reference for any Firebase project — CLI login, project
  selection, MCP wiring, and authoritative Firebase product docs (core concepts,
  CLI, client/admin SDKs, IaC, IAM/security). Use at the start of work on a
  Firebase repo, when you need to look up a Firebase product concept, or when
  setting up the Firebase MCP server. For deploy/rules/secrets discipline see
  `firebase-stack`. For emulator-backed testing see `firebase-emulator-e2e-harness`.
---

# firebase-basics

Bootstrap and product-reference layer for Firebase work. This skill is the entry point: it covers logging into the Firebase CLI, picking an active project, wiring the Firebase MCP server, and points to authoritative product docs under `references/`.

This skill is intentionally **generic and non-opinionated**. For environment-specific discipline (deploy gates, rules tests, index hygiene, secret rotation), load `firebase-stack`. For emulator-backed E2E harness work, load `firebase-emulator-e2e-harness`.

## Triggers

Load this skill when:
- Starting work on a repo with `firebase.json` / `.firebaserc` and no Firebase context yet
- User asks a Firebase product question (what is X, how is it priced, what regions, what SDK)
- Setting up or repairing the Firebase MCP server
- A teammate-handoff repo has no `scripts/` wrapper and you need the bare-CLI baseline

If the repo already has project-specific scripts and `firebase-stack` triggers fire, prefer `firebase-stack`.

## Bootstrap

### 1. Verify the CLI is reachable

```bash
npx -y firebase-tools@latest --version
```

Always invoke as `npx -y firebase-tools@latest <cmd>` rather than bare `firebase` — this pins to the latest published CLI and avoids "works on my machine" version drift. (Yes, even in Bun-default repos; `firebase-tools` is npm-distributed.)

### 2. Log in (interactive)

```bash
npx -y firebase-tools@latest login
```

The login flow opens a browser. If you're an agent in a non-interactive shell, **stop and ask the user to run this themselves** — do not attempt to script around the browser flow.

### 3. Pick an active project

```bash
npx -y firebase-tools@latest use
```

- If output is `Active Project: <PROJECT_ID>`, proceed.
- If no active project, ask the user for an existing project ID and run:

  ```bash
  npx -y firebase-tools@latest use --add <PROJECT_ID>
  ```

- If the user has no project yet, create one (only with explicit user approval — project creation is billable scope):

  ```bash
  npx -y firebase-tools@latest projects:create <PROJECT_ID> --display-name <DISPLAY_NAME>
  ```

### 4. Wire the Firebase MCP server (optional)

The Firebase CLI ships a local MCP server. To make it available to this agent, see [references/mcp-usage.md](references/mcp-usage.md). Detect first — many setups already have a `firebase` entry in their MCP config and re-adding it would overwrite siblings.

## Reference docs

Authoritative Firebase product references, mirrored from [google/skills firebase-basics](https://github.com/google/skills/tree/main/skills/cloud/firebase-basics). Read on demand:

- [Firebase core concepts](references/core-concepts.md) — product list, regional availability, Spark vs Blaze
- [Firebase CLI usage](references/cli-usage.md) — `npx firebase-tools` invocation pattern, self-documenting help
- [Firebase client library usage](references/client-library-usage.md) — web/iOS/Android/Flutter SDKs and Admin SDK pointers
- [Firebase CLI and MCP server](references/mcp-usage.md) — MCP config detection and merge protocol
- [Firebase IaC usage](references/iac-usage.md) — Terraform resources for Firebase
- [Firebase security-related features](references/iam-security.md) — IAM roles, Security Rules basics, App Check

## Extension: Google's full skill bundle

google/skills firebase-basics also instructs the agent to install Google's broader Firebase skill set:

```bash
npx -y skills add firebase/agent-skills -y
```

That bundle adds skills for `firebase-firestore`, `firebase-hosting-basics`, `firebase-auth-basics`, `firebase-app-hosting-basics`, `firebase-data-connect-basics`, `firebase-ai-logic-basics`, `firebase-security-rules-auditor`, and Genkit (`developing-genkit-{js,go,dart}`).

**This is opt-in here, not mandatory.** Reasons to skip it: those skills are generic and don't know about this user's environment conventions (emulator-first testing in `firebase-emulator-e2e-harness`, project-script discipline in `firebase-stack`, beads single-writer policy, Bun defaults). Reasons to run it: you're starting a brand-new Firebase project that needs Firestore data-modeling or Genkit guidance and the existing skills don't cover it. Ask the user before installing.

## See also

- [`firebase-stack`](../firebase-stack/SKILL.md) — environment-specific discipline: deploy targets, rules-test gates, index/query consistency, secret rotation, infra provisioning scripts
- [`firebase-emulator-e2e-harness`](../firebase-emulator-e2e-harness/SKILL.md) — deterministic emulator harnesses for Playwright/Vitest E2E

## Attribution

`references/*.md` are mirrored from [google/skills](https://github.com/google/skills) (Apache 2.0 / per repo LICENSE) and may diverge from upstream over time. Re-fetch from `https://raw.githubusercontent.com/google/skills/main/skills/cloud/firebase-basics/references/<file>` to refresh.
