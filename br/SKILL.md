---
name: br
description: >-
  Use br (beads_rust) safely for ready-work selection, atomic claims, issue text,
  dependency graphs, evidence-bound closure, and SQLite/JSONL sync in shared repos.
  Use before br writes, after pull/rebase, and for busy/stale/import/merge failures,
  blocked claims, unsupported flags, or tracker changes missing from Git. Preserve
  unpublished DB state, peers' claims and exact-ID graph data; never force through
  safety refusals or mistake syntax support for permission.
---

# br: claim useful work, preserve the tracker, land the evidence

Read the repository's AGENTS.md and the bead before acting. **Repository policy
and user authorization win.** `br --help` determines syntax/capability, not whether
an operation is allowed. This skill does not override no-force/no-deletion rules,
closure gates, milestone order, or coordination requirements.

The tracked JSONL is the portable Git record; the live DB can contain **unexported
issues, comments, relations and audit history**. Calling it disposable is not
permission to rebuild or replace it. `br` does not run Git or publish your work.

## Happy path

1. **Confirm routing and supported syntax.** Check `br --version`, `br where
   --json` and, when needed, `br info --json` / command-specific help. Confirm the
   repository, database, JSONL, prefix and worktree arrangement. Inspect whether
   `BEADS_DB`, `BEADS_JSONL`, command `--db`, or local configuration redirects
   operations. Do not copy an unrelated DB/JSONL or initialize another workspace
   because IDs seem missing. Worktrees may have separate DBs; don't assume claims
   are atomic across independent copies.
2. **Reconcile after Git changes.** In a normal clean, coordinated state, run
   `br sync --import-only` after pull/rebase before issue edits, then verify the
   expected records. Before pulling, flush and land local tracker changes under
   the project coordination rule. If already pulled with unexported DB work, or
   markers/semantic conflicts exist, stop routine sync and use the recovery
   checklist below. Do not flush stale DB contents over newly arrived JSONL.
3. **Pick, inspect, claim.** `br ready --json`; optionally `bv --robot-triage`
   (never bare `bv`). Fresh `br show <id> --json` confirms status, assignee,
   dependencies, acceptance criteria and inherited instructions. Then:

```bash
br update <id> --claim --actor <your-session-name>
```

   Check the exit and `br show` result. A stale recommendation, a blocked issue,
   or a peer's claim is not permission to force it. Pick another ready bead or
   coordinate with its holder. An atomic claim protects only the resolved DB;
   coordinate across worktrees/agents too. Reserve affected files through Agent
   Mail before editing shared code; a bead claim is not a file reservation.
4. **Work and record progress.** Keep writes sequential, append evidence/comments,
   and re-read after errors or concurrent changes. Coordinate graph edits and
   tracker exports. Follow the project's quality gates; do useful independent
   work rather than idle-polling a held bead.
5. **Close on evidence, then publish the closure.** Verify the final implementation
   SHA is on the required remote branch after any rebase, required tests actually
   ran and passed, and acceptance checks were satisfied. Only then:

```bash
br close <id> --reason "Completed. commit=<final sha>; tests: <names> passed"
br sync --flush-only
```

   Verify closure and JSONL content; review/stage `.beads/issues.jsonl` explicitly,
   commit and push that tracker change as well. Code landed is not tracker landed.
   Leave incomplete work open/in progress with a concrete blocker. On abandoning
   your own claim, record handoff evidence and release only that claim, rechecking
   ownership first. Do not clear a peer's newer claim.

Use Agent Mail for ownership/export/graph coordination; when unavailable, follow
project fallback rules and record a bead comment if the tracker is healthy.
A coordination outage does not erase a known claim or file conflict.

## Errors: inspect outcome before retrying

| Symptom | Response |
|---|---|
| Unsupported command/flag from stale docs | Check local help. Map syntax below; keep the original policy and intent. Do not repeat guesses or edit policy to suit the binary. |
| `cannot claim blocked issue` / held bead | Inspect blockers/holder; pick useful other work. No forced claim, reassignment, dependency removal, or reopening a gate to bypass it. An explicitly authorized takeover still needs exact scope and project-compliant evidence. |
| `database is busy` / lock timeout | Serialize writes, including `sync`; coordinate the shared writer. A bounded `--lock-timeout 30000` can wait, not authorize concurrent destructive work. Re-read exact issue/sync state to learn whether the write landed; don't blindly replay creates or comments. No lock-file deletion or SQL repair. |
| Nonzero close/update or unclear output | The operation is unconfirmed. Inspect structured errors, exit and fresh state; distinguish rejected transition, claim/policy conflict and partial/postcommit failure. Don't report success or repeat a possibly landed write without reconciling it. |
| Short text replacement refused | Read current text and the reason. Prefer append/checklist operations. `--force` can bypass destructive-rewrite and blocker guards; it is not the routine solution. Files avoid quoting errors but still replace the whole field. |
| `--if-unchanged` mismatch (current CLI exits 6) | Another writer changed the bead. Re-read, preserve their work, compose the intended update and use the new `updated_at` only after review; no automatic fresh-timestamp retry. |
| Refusing stale/empty export | Preserve DB and JSONL, inspect exact-ID coverage and changed relations; reconcile before exporting. Never `--allow-stale` or forced export to silence the guard. |
| `UNIQUE constraint failed` / import failure | Capture diagnostics and supported read-only doctor/plan output. It does not prove a rebuild is safe. No deleting the DB, SQL edits, or immediate `--rebuild`. |
| Merge markers / semantic conflict | Stop publication. Preserve both sides and the base plus local DB evidence; use the checklist below. No hand-splicing, one-side checkout, force-newest choice, or fixed-ref assumption. |
| Missing br / test skipped / interrupted command | Report not run or unknown. An absent binary, zero exit from a wrapper, or a diagnostic recommendation is not a passed workflow gate. |

An error envelope's `retryable: true` is not permission to change dependencies or
force a claim. Re-evaluate the actual blocker. Transcript entries can duplicate
the same call/commentary; compare outcomes before counting them as retries.

## Text, claims and graph edits

- Use exact IDs from structured output, not substring greps (`.13` matches `.130`).
  Parse the actual JSON shape: `create --json` can return an object whereas
  `show --json` can return a list. A command exiting zero is not proof of the
  requested status, assignee, or relationships.
- Append with `--append-notes`, `--add-acceptance` or `br comments add`. For a
  deliberate replacement, read the whole field and preserve peer edits. When
  supported, bind an update to the `updated_at` from `show` using `--if-unchanged`.
  Long text: `--description-file file.md` or `br comments add <id> -f file.md`.
  Do not interpolate backticks/`$()` into shell text; zsh string variables are
  not argument arrays. File-based input is quoting hygiene, not merge semantics.
- Priorities are `0`-`4` / `P0`-`P4`; use locally supported types. Keep acceptance
  test names and actual command outcomes, never fabricated “Completed” evidence.
- Search before creating; inspect existing scope, dependencies and acceptance
  criteria. Merge duplicate *work descriptions* deliberately; do not delete IDs
  or discard comments/relations to deduplicate. Close a true duplicate with a
  canonical-ID reason only under the project's closure convention.
- Announce structural graph writes first and use one writer when required.
  `br dep add <issue> <depends-on>` means the first is blocked by the second.
  Verify `br dep cycles` is empty. A parent link does not necessarily implement
  the required milestone dependency; check the actual graph. Do not remove a
  blocker merely to claim work.
- `br epic close-eligible` mutates unless `--dry-run` is supplied. Read the plan
  and verify each child's evidence; eligibility is not proof of tests/deployment.
  Accidental closure needs a reviewed reopen and explanation, not silent churn.

## DB/JSONL recovery checklist

Treat this as investigation, **not a universal force-sync recipe**. Preview any
repair and honor project authorization requirements. `doctor` suggestions do not
supply consent, and a dry run returning zero is only a plan.

1. Coordinate a single tracker writer. Keep peer writes paused for the reviewed
   operation; save current Git status/diffs and exact commit identities before
   changing anything. Preserve unpublished DB work as well as JSONL/base/conflict
   artifacts with a supported consistent backup or an approved quiesced snapshot.
   Include DB companions when present; copying a live DB and WAL sequentially is
   not proof of a consistent backup. Do not open live SQLite directly, delete
   files, move database families aside, or run a broad doctor repair.
2. Inspect `br sync --status --json` and read-only diagnostics available in the
   installed CLI. Hash difference, equal row counts and a clean Git tree are
   **not proof of equal records**. Compare exact IDs and relevant field values,
   status, assignee, comments, dependencies, labels and tombstones. Never count
   closed rows as disposable or compare only `br list` defaults (which may hide
   closed items). Capture unknown coverage rather than asserting completeness.
3. **Markers/rebase:** identify the actual Git operation and captured base/ours/
   incoming commits or index stages. During rebase “ours/theirs” labels differ
   from ordinary branch intuition; current `origin/main` may have advanced and
   is not necessarily the incoming side. Export verified stage/ref contents only
   into **fresh** sidecars, never over existing tracker/evidence. Do not stage a
   sidecar, silently choose one side, hand-splice JSONL or continue with markers.
4. Prefer a supported lossless, exact-ID reconciliation **plan** over rebuild.
   The current CLI offers `br sync --reconcile-additive --json` (read-only by
   default). Inspect conflicts, target DB/source identity and planned changes.
   Where authorized and supported, apply only the reviewed plan with `--apply`
   and its exact `--expect-plan-sha256`; a stale token means stop and re-plan.
   Do not add `--resolve-source-id`, choose timestamp-newest, or replace a
   conflicting scalar/relationship without a reviewed semantic decision. If the
   input has markers, do not feed it to import: first establish complete valid
   source/base/local state through the project's supported recovery procedure.
5. A generic `--import-only` or `--merge` is **not an unconditional lossless union**.
   `--rebuild` removes DB-only entries; `doctor --repair` can also rebuild.
   `--force`, `--force-db`, `--force-jsonl`, `--allow-stale`, and skipping invalid
   records can discard data or bypass refusal. Do not turn them into automatic
   fixes, even after importing a sidecar or checking counts. If no safe supported
   reconciliation is available, stop and report the conflict with preserved
   evidence; ask for the exact semantic/repair decision needed.
6. After an authorized operation, verify the preserved IDs **and** their relevant
   values/relations, audit/tombstone coverage and final JSONL. Plain import can
   leave no dirty rows to export: “Nothing to export” does not prove the file
   contains DB-only records. Check exports themselves before staging, inspect
   semantic differences, then recheck cycles and finish Git. After completing
   rebase/pull, import/reconcile as project policy requires before further edits.

## Git handoff and worktrees

Review `git diff -- .beads/issues.jsonl` and staged contents before committing.
An export may include legitimate peer tracker work: coordinate and describe it;
do not stage another agent's code or use `git add -A`. Preserve unrelated staged
paths. Commit only reviewed paths; mixed edits within a path need coordination.
Check `git status --short .beads/` and verify the tracker commit actually reached
the remote. Never commit `beads.db`, WAL/SHM files, scratch sidecars or private data.

Do not force cleanup or autostash to make a shared-tree rebase work. Fetch/inspect,
coordinate or use an appropriate fresh isolated worktree. Confirm its DB routing
before writes and how claims/exports return to the canonical project. An atomic
claim in one independent DB cannot prevent a claim in another.

## Stale syntax reference (verify local help)

| Old form | Current equivalent / constraint |
|---|---|
| `br prime` | `br ready --json`; guide: `br robot-docs guide` |
| `br import -i ...` | `br sync --import-only` only after routing/state checks |
| `update --add-note` | `--append-notes` or `br comments add` |
| `update <a> --blocks <b>` | `br dep add <b> <a>` |
| `list --parent` | `br ready --parent ... --json` for ready children, not all children; otherwise inspect supported show/query APIs |
| `update --status closed` | `br close <id> --reason ...`, with evidence/policy |
| `doctor --fix` | Alias/support varies; preview available read-only diagnosis and specific repair plan, never run as a harmless check |

## Evidence and tests

[references/evidence.md](references/evidence.md) separates confirmed skill-use
markers, broad tool history, direct incident context, CLI observations and test
limits. This is guidance for supported capabilities, not a promise tied only to
one version string.

Run `bash scripts/test-all.sh --skill br` from the canonical skill repo, or
`bash br/scripts/self-test.sh` for detail. Tests run real br against fresh retained
scratch repos only, clear inherited routing overrides and pin fixture DB paths.
No real project tracker is changed, no files are deleted, and missing br fails
rather than counting as a skipped live pass. Legacy force/overwrite scenarios
are hazard demonstrations on fixtures, not recommended recovery steps. Static
prose checks and independent dry runs supplement CLI tests; none proves all future
merges lossless. Live project repair is outside test scope.
