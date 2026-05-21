---
name: cf-rust-worker
description: >-
  Build, configure, and deploy Rust-based Cloudflare Workers compiled to
  WebAssembly. Covers wrangler.toml setup, worker crate versions, build
  toolchain (rustup + worker-build + wasm32-unknown-unknown), local dev with
  wrangler dev, secrets management, and Cloudflare dashboard deployment. Use
  when creating a new Rust Worker, debugging build failures, or deploying via
  CLI or the CF dashboard UI.
---

# cf-rust-worker — Rust Cloudflare Workers Deployment

Build and deploy Rust Cloudflare Workers that compile to WebAssembly and run on Cloudflare's edge network.

---

## When to use this skill

- Creating a new Rust-based Cloudflare Worker from scratch
- Debugging build failures (cargo not found, wasm target missing, worker crate version mismatch)
- Setting up local development with `wrangler dev`
- Deploying via CLI (`wrangler deploy`) or the Cloudflare dashboard UI
- Configuring secrets for Workers

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Rust (stable) | `rustup` with `wasm32-unknown-unknown` target |
| [worker-build](https://crates.io/crates/worker-build) | `cargo install worker-build` |
| Node.js >= 22 | Required by current Wrangler CLI |
| [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/) | `npm install -g wrangler` |

If using NVM and the default Node version is < 22, prefix commands:
```bash
PATH="$HOME/.nvm/versions/node/v25.9.0/bin:$PATH" wrangler dev
```

---

## Project scaffolding

### Cargo.toml

```toml
[package]
name = "my-worker"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
worker = "0.8"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
console_error_panic_hook = "0.1"
```

**Critical:** The `worker` crate must be >= 0.8.3. Older versions (0.4.x, 0.5.x) are rejected by current `worker-build` with a version mismatch error. Always use `worker = "0.8"` or later.

### wrangler.toml

```toml
name = "my-worker"
main = "build/worker/shim.mjs"
compatibility_date = "2026-05-20"

[build]
command = "curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && . \"$HOME/.cargo/env\" && rustup target add wasm32-unknown-unknown && cargo install -q worker-build && worker-build --release"
```

**Why the build command installs Rust:** Cloudflare's build environment does NOT include Rust. If the build command is just `worker-build --release`, CF dashboard deployments fail with `cargo: not found`. The full command installs the Rust toolchain, adds the WASM target, installs worker-build, then builds. This is idempotent (rustup skips if already installed) so it works both locally and in CF's clean build environment.

**`main` must be `build/worker/shim.mjs`**, not a `.rs` or `.wasm` file. `worker-build` generates a JS shim that loads the compiled WASM module.

### Entry point (src/lib.rs)

```rust
use worker::*;

#[event(fetch)]
async fn fetch(req: Request, env: Env, _ctx: Context) -> Result<Response> {
    console_error_panic_hook::set_once();
    // Your handler logic here
    Response::ok("Hello from Rust!")
}
```

### .gitignore (Rust Worker essentials)

```gitignore
# Secrets
.env
.env.*
.dev.vars

# Rust
/target/

# Wrangler / Cloudflare Workers
/worker/
.wrangler/
build/
*.wasm

# Node (wrangler toolchain)
node_modules/
```

---

## Secrets management

### Production secrets (CLI)

```bash
wrangler secret put MY_SECRET
# Prompts for the value interactively
```

Secrets are stored encrypted by Cloudflare and accessed in Rust via:
```rust
let value = env.secret("MY_SECRET")?.to_string();
```

If a required secret is missing, `env.secret()` returns `Err`. Handle this with a clear error response (not a panic).

### Local development secrets

Create `.dev.vars` in the project root (must be gitignored):
```env
MY_SECRET="local-value"
ANOTHER_SECRET="local-value-2"
```

`wrangler dev` reads `.dev.vars` automatically. Do NOT commit this file.

### Per-environment secrets

```bash
wrangler secret put MY_SECRET --env staging
wrangler secret put MY_SECRET --env production
```

---

## Local development

```bash
wrangler dev
```

This compiles the Rust to WASM and starts a local server (default port 8787). Hot-reload is supported; it recompiles on file changes.

Test with:
```bash
curl http://localhost:8787/
```

---

## Deployment

### Option 1: CLI deployment

```bash
wrangler login    # First time only; opens browser for OAuth
wrangler deploy   # Builds and deploys atomically
```

Wrangler prints the live URL on success (e.g., `https://my-worker.your-subdomain.workers.dev`).

Secrets persist across deployments. You only need to set them once (or when rotating).

### Option 2: Cloudflare dashboard deployment (GitHub integration)

1. Log in to the [Cloudflare dashboard](https://dash.cloudflare.com/) > **Workers & Pages**
2. Click **Create** > **Import a repository**
3. Connect GitHub and select the repository
4. Configure build settings:

| Field | Value |
|---|---|
| **Build command** | *(leave empty)* |
| **Deploy command** | `npx wrangler deploy` |
| **Root directory** | *(leave empty)* |

**Gotchas:**

- **Build command must be empty** when `wrangler.toml` has a `[build]` section. The `[build].command` in `wrangler.toml` runs automatically during `wrangler deploy`. If you duplicate it in the dashboard Build command field, it runs twice.
- **Root directory must be empty** (not `/build` or `build/`). The root directory field tells CF where to find the project files, not where build output goes. Setting it to `build/` causes "root directory not found" errors.
- **Deploy command is `npx wrangler deploy`**, not `wrangler deploy`. The dashboard environment may not have wrangler globally installed.

5. After first deploy, go to **Settings > Variables and Secrets** and add all required secrets. Click **Encrypt** for each.

Every push to `main` triggers an automatic rebuild and deploy.

### Triggering a manual redeploy (dashboard)

Go to **Workers & Pages > your-worker > Deployments**, find the most recent deployment, click the three-dot menu, and select **Retry deployment**. Or push an empty commit:
```bash
git commit --allow-empty -m "trigger redeploy" && git push
```

---

## Environment management

Add environment blocks to `wrangler.toml`:

```toml
[env.staging]
name = "my-worker-staging"

[env.production]
name = "my-worker"
```

Deploy per environment:
```bash
wrangler deploy --env staging
wrangler deploy --env production
```

Each environment gets its own URL and its own set of secrets.

---

## Rollback

**CLI:**
```bash
wrangler deployments list
wrangler deployments rollback <version-id>
```

**Dashboard:** Workers & Pages > your-worker > Deployments > select version > **Rollback**.

Rollbacks are instant. Secrets are unaffected (the previous code runs with current secret values).

---

## Monitoring

```bash
wrangler tail              # Stream live logs
wrangler tail --format json  # Structured output for log aggregation
```

---

## Common build failures and fixes

### `cargo: not found` (CF dashboard deployment)

**Cause:** CF's build environment does not include Rust.
**Fix:** The `wrangler.toml` `[build].command` must install Rust. See the wrangler.toml template above.

### `worker` crate version mismatch

**Symptom:** `worker-build` errors about incompatible `worker` crate version.
**Fix:** Update `Cargo.toml` to `worker = "0.8"` or later. Do not use 0.4.x or 0.5.x.

### `wasm32-unknown-unknown` target not installed

**Symptom:** `error[E0463]: can't find crate for std` or similar during WASM compilation.
**Fix:** `rustup target add wasm32-unknown-unknown`. The wrangler.toml build command template above includes this.

### Wrangler requires Node >= 22

**Symptom:** Wrangler fails to start or shows version compatibility errors.
**Fix:** Upgrade Node.js. With NVM: `nvm install 22 && nvm use 22`.

### `Headers::new()` mut warnings

The `worker` crate's `Headers::new()` returns a mutable-by-default struct in older versions. In 0.8+, use `let headers = Headers::new()` (no `mut`). Methods like `headers.set()` take `&self`, not `&mut self`.

### `with_body()` expects `JsValue`

When building `Request` objects for outbound fetch calls, `with_body()` expects `Option<JsValue>`, not `Option<String>`. Convert with `.into()`:
```rust
.with_body(Some(payload.to_string().into()))
```

---

## Outbound HTTP requests

Workers use Cloudflare's built-in `Fetch` API (no `reqwest` needed):

```rust
use worker::Fetch;

let mut req_init = RequestInit::new();
req_init.with_method(Method::Post);

let mut headers = Headers::new();
headers.set("Authorization", &format!("Bearer {}", api_key))?;
headers.set("Content-Type", "application/json")?;
req_init.with_headers(headers);

req_init.with_body(Some(serde_json::to_string(&body)?.into()));

let req = Request::new_with_init(&url, &req_init)?;
let mut resp = Fetch::Request(req).send().await?;
let text = resp.text().await?;
```

This avoids pulling in `reqwest` and keeps the WASM binary small.

---

## Security checklist for public repos

Before committing to a public repository:

- [ ] `.dev.vars` is in `.gitignore`
- [ ] `.env` and `.env.*` are in `.gitignore`
- [ ] No secrets appear in `wrangler.toml` (use `wrangler secret put` instead)
- [ ] No API keys, tokens, or passwords in any `.rs` file
- [ ] Error responses never leak secrets or full internal URLs
- [ ] Logs use hostnames only, never full URLs (which may contain tokens in query params)

---

## Logging best practices

Use `console_log!` from the `worker` crate:

```rust
console_log!("request_received target_host={} format={}", hostname, format);
```

**Never log:** secrets, authorization headers, full URLs (may contain tokens), request/response bodies containing credentials.

**Always log:** target hostname, response status, format requested, timing.

View logs with `wrangler tail`.

---

## Provenance

This skill was derived from building and deploying [rusty-gateway](https://github.com/JordanChoo/rusty-gateway), a Rust Cloudflare Worker using BrightData's Web Unlocker API. Every gotcha documented here was encountered firsthand during that build (May 2026). The CF dashboard deployment section in particular captures errors that are not well-documented elsewhere: the "cargo not found" build failure, the root directory vs build output confusion, and the need for `npx wrangler deploy` as the deploy command.
