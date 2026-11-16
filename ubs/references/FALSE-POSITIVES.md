# UBS triage: examples are not automatic exemptions

A finding is a hypothesis. Read the code, its execution context, and the exact
rule/location. Preserve correct behavior and meaningful tests.

| Pattern from sessions | Verify before dismissing | Appropriate response |
|---|---|---|
| Rust `assert!`, `expect`, direct indexing | Is it inside a test function or an inline `#[cfg(test)]` module? Is the assertion testing the intended invariant? | Keep intentional test failures. Production input/provider-response panics need investigation. Do not rewrite valid assertions merely to reduce counts. |
| Indexing after bounds checks | Does the guard dominate every access, including arithmetic and early-return paths? Can mutation invalidate it? | Document the concrete bound; fix a missing guard, not the scanner's wording. |
| Cloning names inside a loop | Does the map need an owned key? Is the loop bounded? | Retain necessary ownership; optimize only for an actual cost/problem. |
| `lib/`, `dist/`, `build/` warnings | Is this directory actually generated, rather than handwritten Rust/JS library source? Can you map it to checked source? | Narrowly exclude verified generated/vendor output, not every directory named `lib`. |
| `__proto__`, fake keys in tests | Is the value intentionally synthetic, and is no real credential embedded or used against a live service? | Keep attack fixtures that prove defenses. A secret in a test is still a secret. |
| `page.$eval` / `$$eval` | Is it the framework's DOM-evaluation API? What crosses the trust boundary into the browser? | Do not equate its name with global `eval`; still inspect passed code/data. |
| `process.env` in backend code | Does it remain server-only? Is the value logged, returned, serialized, or bundled into a browser asset? | A read alone is not proof of a leak; actual downstream exposure is a bug. |
| JSX props reported as assignments | Is the parser mistaking JSX attribute syntax for an assignment? | Triage that rule/location; do not exclude all `.tsx`. |
| `!= null` | Is a dual null/undefined guard intentional? | Preserve it. Replacing it with `!== null` changes behavior. |
| Promise warnings in browser/load-test scripts | Is the API truly synchronous (e.g. a particular k6 API), and are async failures otherwise handled? | Verify API semantics before dismissal; legitimate unhandled parsing/lifecycle failures still need fixes. |

## Noise-reduction order

1. Save the raw scan. Count by rule and path; prioritize changed production code.
2. Sample each noisy rule/context, then inspect all potentially dangerous cases.
   Counts and samples are navigation aids, not proof that remaining matches are safe.
3. Record why a finding is intentional, unreachable, generated, guarded, or a
   scanner limitation. Include rule and location where practical.
4. A supplemental Rust `--exclude-tests` scan can help locate production findings
   when supported. It cannot replace required coverage of tests or helpers.
5. Use `.ubsignore` only for justified scope boundaries. Keep explanations on their
   own comment lines; do not assume trailing comments or negation/glob syntax work
   like Git's. Test the actual local module's matching behavior.
6. For inline `ubs:ignore`, prove the original diagnostic is suppressed and a nearby
   real finding is still detected. Suppression is analyzer/version-specific. If it
   is ineffective, keep a documented triage instead of widening the exclusion.

An error label does not prove a bug. A test filename, generated-looking path,
zero exit, or unchanged warning count does not prove safety. Complete the normal
compiler, test, security and project-specific gates independently.
