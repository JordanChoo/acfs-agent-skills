---
name: dcg
description: >-
  Handle Destructive Command Guard (DCG) denials and indeterminate hook checks
  without bypassing them. Use when a shell call is blocked by dcg, before risky
  deletion/discard/overwrite operations, or when diagnosing hook dialect, payload,
  timeout, and allow-once behavior. Separate tool acceptance from owner/project
  authorization; preserve shared work and test proposed commands without executing them.
---

# DCG: diagnose the block, preserve the work

**A guard allow is not permission.** Owner instructions and repository rules can
forbid an operation that DCG allows, including deletion in `/tmp`, deleting a
single file, force-with-lease, moving to Trash, stashing shared work, or removing
worktrees. A denial or timeout is not permission to perform the same effect with
a different tool. Follow the stricter applicable rule.

## Happy path after a block

1. **Stop the blocked operation.** Save its rule/reason, tool name, working directory,
   and whether the result was a known denial or an incomplete evaluation. Do not
   assume earlier segments of a blocked compound call ran. Confirm state read-only.
2. **Check the intended effect and existing authorization.** Read the relevant
   AGENTS.md. Inspect affected paths, diffs, ownership and destinations without
   changing them. A scary rule name is a hypothesis, not proof of a secret or data
   loss; a familiar temp path is not proof of disposability.
3. **Choose a genuinely safer next step:**
   - Unneeded cleanup: leave artifacts; use a new temporary directory.
   - Need an old version: inspect a diff or make a separate, fresh snapshot; keep
     the live file and other agents' changes.
   - Already-authorized read/new-file operation hit a parser limit: simplify its
     representation while preserving its non-destructive effect. See the table.
   - Deletion, discard, overwrite, credential changes, shared-state mutation, or
     effects you cannot establish as authorized: prepare the exact proposal and
     ask the owner. Do useful independent work while approval is pending.
4. **Preflight a justified alternative before executing it.** Put the text or exact
   tool JSON into a new file through the available file-editing tool. Set
   `DCG_SKILL` to the directory containing this skill, then run one of:

```bash
# Evaluates text as a Bash/POSIX hook payload; does NOT run the text.
python3 "$DCG_SKILL/scripts/check.py" --command-file /literal/path/command.txt

# Prefer the actual tool payload when diagnosing the integration.
python3 "$DCG_SKILL/scripts/check.py" --payload /literal/path/tool-payload.json
```

5. Read the structured result. `authorization: not_checked` and
   `will_execute_command: false` are intentional. A result of `guard_allows` means
   only that this evaluation allowed it; verify owner authorization, live hook
   context and exact command again before any real execution. `blocked` or
   `unverified` is not a pass. Keep the artifact path and actual exit code.
6. If a clearly safe clarification is still blocked, stop experimenting. Provide
   the exact rule and scoped proposal to the owner. Do not try a succession of
   path, interpreter, quoting, or wrapper variations until one passes.

The helper only invokes `dcg hook --batch --robot`; recorded commands are data.
It retains local stdout/stderr and returns 0 for guard-allow, 1 for a definite
block, and 2 for incomplete/malformed/unsupported evaluation. It changes no DCG
policy, executes no candidate, and grants no override. DCG itself may maintain
its normal diagnostic/history state. Do not put secrets in command text, payload
files or shared reports; summarize rule/paths with secret values redacted.

## Diagnose by effect, then by rule

| Denial family | Appropriate response |
|---|---|
| Dynamic redirect / truncation (`redirect-truncate-*`) | Prove the intended destination and whether it is new. For a new disposable report use a verified fresh literal path or `dcg create-new` (exclusive creation; check its local help). For display, capture output without writing a file. Preserve the underlying command's exit code. Literal `>`, append `>>`, or `tee` is not safe if it still overwrites/corrupts existing data. |
| Credential/config write (`credential-file-write`) | Inspect source/destination roles without printing secrets. A variable `cp` loop can trigger this despite non-secret inputs; explicit paths are appropriate only after proving a fresh, authorized destination. Real credential/config changes need their own authorization; never scrape a token and call a private API because the normal CLI was blocked. |
| Git overwrite/discard (`show-redirect-overwrite-source`, `checkout-*`, `restore-worktree`, `reset-hard`) | Use read-only diff/show or an isolated fresh snapshot. Do not stash, switch/detach the live tree, copy over files, or edit them back to HEAD without authorization. Shared changes are another agent's work, not cleanup. An archive extraction also needs a fresh destination. |
| Force push / branch or worktree removal | Leave it intact and prepare an owner-reviewed proposal. `--force-with-lease` still rewrites history; `worktree remove` still removes a directory. Neither is an automatic substitute. A normal push is appropriate only for the already-authorized fast-forward operation. |
| Delete (`rm-*`, `find-delete-*`) | Skip optional cleanup and retain artifacts. Permission is required whenever project rules require it, even for literal `/tmp`, named files, empty directories, or files created during this task. Do not assemble deletion with loops or xargs. |
| Move (`mv-sensitive-*`, `mv-dynamic-*`) | Treat the move as a filesystem change that needs scope/ownership checks. Prefer leaving/copying for review when appropriate, without removing the source. Only make the exact move that was authorized; changing an absolute source to a relative one to defeat a denial is evasion. |
| Inline/heredoc/substitution/pipeline uncertainty | First inspect what the code does. For authorized harmless work, use literal interpreter/argument lists and separate file editing from tests. Scripts and `--description-file`/commit-message files improve clarity; they do not authorize a previously blocked effect. Do not use `eval`, dynamic launchers, encodings, or alternate tools to hide it. |
| Timeout / `general.unverified_decision` | The guard did not finish its proof, not “safe” or necessarily “destructive.” Split a long authorized operation into independently reviewable short steps; remove optional cleanup from build/test chains. Do not increase hook budgets, disable scanning, or edit policy just to get past it. A file-based script is acceptable only when its actual effects are independently authorized. |

## Approval is a separate, explicit step

Before asking, make the proposal concrete using authorized read-only checks:
state the exact command, affected paths/branches/resources, unique work at risk,
why a safer alternative is insufficient, and the consequences. Follow any
project-specific exact-command, acknowledgement, and second-confirmation rules.
A broad “continue” or “finish the task” is not a destructive-operation approval.

DCG may supply a pending `allow-once` code. The **owner** can use the documented
single-command approval flow; the agent must not mint/consume its own grant
without authorization. Check `dcg allow-once --help` for the installed version;
current grants are single-use by default. Do not expand them to reusable or
permanent rules, use `--force`, modify blocklists/allowlists, or disable hooks.
A grant does not replace the owner's authorization or apply to altered commands,
wrappers, paths, or a larger sequence. Do not publish approval codes/raw secrets.

The owner can instead run the exact command themselves. Claude Code's `!` UI
shell mode is specific to that interface; do not present `!` as a universal shell
approval mechanism or expect an API user to have it. If authorization is already
explicit and applicable, do not ask again solely because you changed sessions;
verify whether the live guard still requires the owner's one-shot action.

## No effect-preserving bypasses

After a destructive-effect block, do not recreate that effect with Python/Node,
`cp`, `install`, `tee`, an editor, a package-manager config command, shell aliases,
relative paths, moves to temp followed by deletion, or a direct service API.
Do not make the same bypass permanent in a memory note or DCG configuration.
Changing representation is legitimate only for an independently authorized,
understood operation; “the new form passes” is not sufficient evidence.

Trash is not an authorization shortcut. If a specific move to Trash is approved,
verify the destination exists **as a directory**, check for name collisions and
unique/untracked files, and preserve/report the source-to-destination mapping.
If the destination does not exist, `mv source .../Trash` can rename source to
`Trash`. Do not perform this experiment on user data or evade a refused move by
changing the source spelling. Leaving the directory untouched is valid.

## CLI and hook traps

- Check `dcg --version` and local help. The corpus records **0.16.0 observations**,
  not permanent promises about allowed paths, rule IDs, or parser support.
- `dcg test --robot --dialect posix --stdin` is useful for Bash text. Use the
  actual dialect; the default `unknown` fans out and can disagree. Do not switch
  dialect/config/pack selection to get an allow. Full tool payload, heredoc
  handling, workspace/profile and live budget can still matter.
- A **single** `dcg hook` call can return exit 0 while its stdout says deny.
  Robot `dcg test`, batch hook, and single-hook exit conventions differ. Parse
  the selected mode's response; never infer permission from exit status alone.
- A batch `skip`, missing/duplicate response, malformed JSON, or unsupported tool
  name is unverified. On this VPS, `exec_command` is recognized but a namespaced
  `functions.exec_command` payload can be skipped. Preserve the real payload and
  diagnose the adapter; do not relabel an unknown tool to obtain a false approval.
- Preflights only evaluate; they do not execute or prove arbitrary script-file
  contents safe. The real hook must still evaluate the eventual real tool call.
- Do not infer retries solely from adjacent transcript entries. Some Claude logs
  duplicate calls with/without a `cd` prefix; compare message/tool identity and
  actual follow-up behavior before counting repeated attempts.

## Evidence and verification

[references/rules.md](references/rules.md) records this audit's search scope,
primary message coordinates, prior-audit evidence, and manual policy replays.
[tests/cases.json](tests/cases.json) retains the original mechanical classifier
corpus. Legacy `fix-*` IDs there are historical labels, **not recommendations or
authorizations**. `policy: owner_required`/`forbidden` is independent of `expect`.

Run `bash scripts/test-all.sh --skill dcg` in the canonical shared skill repo.
The suite evaluates commands as data, tests malformed/skip/exit-status handling,
and checks real hook behavior. It never runs candidates, deletes test files,
grants permits, or changes hook configuration. Missing DCG is a failed live-test
setup, not a successful skipped gate. Model adherence is not measured by these
CLI and policy-replay tests.
