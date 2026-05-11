# UBS False-Positive Catalog

Detailed list of known false positives observed in real agent sessions, with examples and suppression strategies.

---

## Category 1: Compiled JavaScript Output

**ruleIds:** `js.loose-equality`, `js.eval-call`, various
**Trigger:** UBS scans `functions/lib/`, `dist/`, `build/` -- directories containing TypeScript compiler output.
**Example findings:**
- 12x "Loose equality `==` instead of `===`" in `__createBinding` helper (`mod != null`)
- `eval` in bundled polyfills

**Why false:** These are compiler-generated patterns. The source TypeScript is correct; the emitted JS uses idiomatic patterns the compiler produces.

**Suppression:** Add to `.ubsignore`:
```
functions/lib/
dist/
build/
out/
```

---

## Category 2: Test Fixtures & Intentional Payloads

**ruleIds:** `js.prototype-pollution`, `js.hardcoded-secret`, `js.sensitive-data-logging`
**Trigger:** UBS scans test files containing intentional attack payloads and fake credentials.
**Example findings:**
- 2x "Prototype pollution via `__proto__`" in `attack-helpers.ts`, `piiScrubber.test.ts`
- 78x "Hardcoded credentials" in test files (`test-password-123`, `fake-api-key-xxx`)
- 4x "Sensitive data logging" in scripts logging token counts (not actual secrets)

**Why false:** Test fixtures intentionally contain these patterns to test defenses.

**Suppression:** Add test directories to `.ubsignore` or accept these findings as part of the test suite. Inline `// ubs:ignore test fixture` on specific lines if the test file also has real findings.

---

## Category 3: Playwright `$$eval` / `$eval`

**ruleIds:** `js.eval-call`
**Trigger:** Playwright test code uses `page.$$eval('selector', fn)` and `page.$eval('selector', fn)`.
**Example:** `const texts = await page.$$eval('.item', els => els.map(e => e.textContent))`

**Why false:** Playwright's `$$eval` is a remote DOM query API, not `eval()`. The function runs in the browser context as a controlled query, not arbitrary code execution.

**Suppression:** Add to `.ubsignore`:
```
# Playwright scripts use $$eval (not eval)
apps/web/research_*.mjs
tests/e2e/
playwright.config.ts
```

---

## Category 4: TSX JSX Attribute Parsing

**ruleIds:** Various assignment-related rules
**Trigger:** UBS JS module mis-parses JSX/TSX prop syntax as global variable assignments.
**Example:** `<Component value={someVar} />` flagged as assignment to `value`.

**Why false:** JSX attributes are not global assignments. This is a parser limitation in UBS's JS module.

**Suppression:** Add `*.tsx` to `.ubsignore` until the upstream parser is fixed:
```
*.tsx
```

---

## Category 5: Server-Only `process.env`

**ruleIds:** `security.env-in-client`
**Trigger:** UBS flags `process.env.VARIABLE` reads as "environment variable exposed to client."
**Example findings:**
- 59x `process.env.API_KEY` in Firebase Functions source (`functions/src/`)
- `process.env.NODE_ENV` in backend middleware

**Why false:** Node.js Firebase Functions run server-side only. Vite/webpack never bundles them to the client. UBS has no awareness of bundler configuration.

**Suppression:** Inline suppression with consistent comment:
```typescript
const apiKey = process.env.API_KEY  // ubs:ignore server-only env access
```

Or exclude entire backend directories:
```
functions/src/          # if you don't need UBS on backend at all
```

The inline approach is preferred because it preserves scanning for other rules (eval, prototype pollution, etc.) in backend code.

---

## Category 6: Loose Equality in Shell/Markdown

**ruleIds:** `js.loose-equality` (misfire)
**Trigger:** Shell scripts or markdown docs containing `== "string"` comparisons get scanned by the JS module.
**Example:** `if [ "$status" == "failed" ]` in a runbook `.md` file.

**Why false:** Not JavaScript at all.

**Suppression:** Add non-code file types to `.ubsignore`:
```
*.md
*.sh
docs/
```

---

## Triage Decision Matrix

```
Is the file in lib/, dist/, build/, node_modules/?
  YES -> False positive (compiled/vendored). Skip.

Is the file a test file (*.test.*, *.spec.*, test-helpers.*)?
  YES -> Check if the finding is about test payloads (fake creds, attack strings).
    Payloads -> False positive. Skip.
    Actual test logic bug -> Real finding. Fix.

Is the ruleId "security.env-in-client" in backend code?
  YES -> False positive (server-only). Suppress inline.

Is the ruleId "js.eval-call" in Playwright code?
  YES -> False positive ($$eval API). Skip.

Is the file *.tsx and the finding is about prop assignments?
  YES -> False positive (parser limitation). Skip.

None of the above?
  -> Read the code. It's probably a real finding.
```
