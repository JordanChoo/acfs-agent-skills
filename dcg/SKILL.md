---
name: dcg
description: >-
  What to do when dcg (Destructive Command Guard, the pre-execution hook on this VPS) blocks a
  shell command, and how to write commands it will not block. Use when a Bash call fails with
  "PreToolUse:Bash hook error: BLOCKED by dcg", "Rule: core.filesystem:..." or
  "Rule: heredoc...", when a command needs dcg allow-once, before cleanup (rm -rf, find -delete,
  moving folders out of ~), before discarding git changes (checkout --, restore, reset --hard,
  branch -D, push --force), and before writing files through redirects to variable paths.
  Covers the fix for each rule, how to ask the owner for approval, and the workarounds that are
  forbidden because they defeat the guard.
---

# dcg

dcg reads every Bash command before it runs and denies the ones that could destroy work. A
denial is not an error to route around. It means: this exact command, as written, is not
allowed without the owner. Handled the way below, a block costs one extra turn. In past
sessions (about 550 blocks reviewed), the worst cases took three to five turns of trial and
error, and a few ended in a workaround that defeated the guard.

Evidence for every rule here: [references/rules.md](references/rules.md). Test corpus:
[tests/cases.json](tests/cases.json), checked by `scripts/self-test.sh`.

## When a command is blocked

1. **Read the `Rule:` line.** It names the exact problem. Do not retry the same command, and do
   not retry a near copy.
2. **Look the rule up in the table below** and apply its fix. Almost every block has a fix that
   is better than the blocked command, not just allowed.
3. **Not sure the fix passes?** Test it before running it. Write the command to a file, then:

   ```bash
   dcg test --robot --dialect posix --stdin < /path/to/cmd.txt   # exit 0 allow, 1 deny
   dcg explain "git status"                                        # trace for a harmless command
   ```

   `--dialect posix` is what the Bash hook uses; the default dialect can disagree. Feeding the
   command on stdin keeps its text out of your own Bash call, which dcg would also inspect.
4. **The fix still needs the destructive step** (you really must delete, discard or overwrite
   something)? Stop and ask the owner. See "Asking for approval".
5. **Two blocks on the same goal means stop.** Ask, or choose a different approach. Do not try
   a third variant.

### Never do these (they defeat the guard)

Each of these was seen in past sessions. They count as destructive actions taken without
permission, even when the command succeeds.

- Doing the blocked overwrite or delete in another language or tool: a `python3 -` script,
  `node -e`, `cp` over the file, `install`, `tee`, `npm config set`, `os.remove`,
  `shutil.rmtree`, an Edit that reverts a file to make the same effect.
- Rebuilding a recursive delete by hand: `find -delete`, `find ... | xargs rm`, loops of `rm`.
- Relocate then delete in one call: `mv X /tmp/d && rm -rf /tmp/d`. dcg allows that exact
  form, but it exists for moving disposable build output, not for deleting something dcg just
  refused to delete.
- Reaching around a tool that dcg blocked, for example scraping a token from a config file to
  call an API directly.
- Writing a workaround into a memory note as advice. Write the correct fix instead.

Writing a script with the Write tool and running it is fine for long or awkward commands. It is
not fine as a way to run a command dcg denied.

## Fix by rule

| Rule (from the `Rule:` line) | What it means | Do this |
| --- | --- | --- |
| `redirect-truncate-dynamic-path` | `>` into a path dcg cannot resolve: an unset variable, `$(...)`, `$HOME`, a variable built from another, a loop variable inside the path, or several redirects on one variable | Spell the target path out. Or skip the file: pipe (`\| tail`, `\| jq`) or capture in a variable. Or `>>` into a fresh file. To create a file, use the Write tool, or `dcg create-new <literal path>`, which refuses to overwrite |
| `redirect-truncate-root-home` | `>` onto a file in your home directory | Write a new file name, or use `>>` for a log. If it is config or credentials, ask the owner |
| `credential-file-write` | Writing to a credentials or config path. Also fires on `cp $f $DIR/$f` loops, because the destination is unknown | Loops: name the files and a literal destination (`cp a b /literal/dir/`). Real credential files (`~/.npmrc`, `~/.aws`, `*.env`): show the owner the change and ask. Never put a secret in a command |
| `show-redirect-overwrite-source` | `git show ref:path > path` overwrites the working file | Write beside it: `git show HEAD:path > path.from-head`. Or make a clean worktree |
| `checkout-discard`, `checkout-ref-discard`, `restore-worktree` | Throws away uncommitted changes | `git stash push -m "why" -- <paths>` keeps them recoverable. Or `git worktree add <dir> HEAD` for a clean copy. Or `git restore --staged` to unstage only |
| `reset-hard` | Discards work and moves HEAD | `git stash push -m "why"`, then `git switch --detach <ref>` or a new branch. On a shared tree, ask first |
| `push-force-long` | Overwrites the remote branch | `git push --force-with-lease`. Never force-push a shared branch without the owner |
| `branch-force-delete`, `branch-delete` | Deletes a branch | `git worktree remove <path>` without `--force`, and leave the branch. Give the owner the branch list and the exact delete command |
| `rm-rf-general`, `rm-recursive-general`, `rm-r-f-separate`, `rm-rf-root-home` | Recursive delete. Only literal `/tmp/<dir>` paths are allowed; `/data/tmp` and the session scratchpad are not temp to dcg | Do not clean up: use a new directory name (`staging-2`) or `mktemp -d /tmp/name.XXXXXX`. Literal `/tmp/<dir>` deletes are fine. Single files: `rm -f a b`. Empty dirs: `rmdir`. Anything else: ask |
| `find-delete-general` | `find ... -delete` | Same as `rm -rf`. Never rebuild it with `xargs` |
| `mv-sensitive-source-root-home` | `mv` with a home or system path on either side, out of its subtree | Within home: rename inside one subtree (`mv ~/src/a ~/src/a.old`). Across trees: `cp -a src dst && diff -r src dst`, then deal with the source. Soft-delete: see "Removing things" |
| `mv-dynamic-path` | `mv` with variable paths | Literal paths |
| `heredoc.*:launcher-unverified`, `inline-launcher-unverified`, `substitution-unverified` | A script or command assembled at run time: `"$(cat f)"` as an argument, an interpreter path built from `$(...)`, template literals or `${...}` inside inline code | Write the script with the Write tool and run it by path. Pass long text with a file flag (`--description-file`, `git commit -F`). Call interpreters by literal path |
| `heredoc.posix:pipeline-consumer`, `process-substitution`, `eval-dynamic` | `xargs sh -c`, `< <(...)`, `eval` | Use direct flags (`grep -c`, `find -printf`), a file, or literal arguments |
| `heredoc.python:*` | `os.remove`, `Path.unlink`, star-args `subprocess` in inline Python | Delete named files in shell with `rm -f`. Pass literal argument lists |
| `general.unverified_decision`, or a timeout | The command was too long to check in time (the budget is about 1 second) | Split it into shorter Bash calls, or Write it as a script. Do not resend it unchanged |

## Habits that avoid blocks

- **Literal paths** in every `>`, `rm`, `mv` and `cp`. dcg follows a simple `S=/path; cmd > $S/x`,
  but not much more, and the cases it misses are hard to predict.
- **Files go through the Write tool**, not `cat > file <<EOF`. Scripts too: Write them, then run
  `python3 /path/script.py`.
- **One destructive step per Bash call.** If one segment of a chain is denied, nothing in the
  chain runs, including the build and tests before it.
- **No cleanup steps in chains.** Leave scratch directories behind or use a new name; the
  session scratchpad is isolated anyway.
- **Do not mention dangerous commands in quoted text** when a plain description works ("refused
  to force-delete the branch" rather than the command). dcg 0.16.0 handles most quoted text, but
  older versions did not, and rewording costs nothing.

## Removing things

Ask before deleting anything you did not create in this task. When the owner says to remove
something:

1. Check it holds nothing unique (`git status`, `diff -r` against the copy you keep).
2. Prefer a recoverable soft-delete. The Trash folder may not exist, and `mv X
   ~/.local/share/Trash/` then **renames X to Trash** instead of moving it in. Always:

   ```bash
   mkdir -p ~/.local/share/Trash/files
   mv ~/src/old-copy ~/.local/share/Trash/files/
   ```

   An absolute source under `/data/tmp` is denied; `cd` to its parent and use a relative name.
3. Give the owner the exact permanent-delete command (for example
   `! rm -rf ~/.local/share/Trash/files/old-copy`) instead of running it. A hard recursive
   delete needs the owner's exact command and explicit acknowledgement on this VPS.
4. Report what moved where, with the time.

## Asking for approval

In the past sessions reviewed, owners approved by running the command themselves with `!`; no
one used an allow-once code. Make that easy:

1. State what the command does and what it affects (paths, branches, sizes), and why the safe
   alternatives do not work.
2. Give one copy-ready line: `! <exact command>`. Mention the `dcg allow-once <code>` from the
   denial as the other option.
3. Stop and wait. Do not retry, do not try a variant while waiting.

## Known quirks (dcg 0.16.0)

- `dcg test` with the default dialect can deny what the hook allows; always pass
  `--dialect posix`. `dcg hook --batch` replays exact hook payloads (JSONL), which is what this
  skill's self-test uses.
- dcg's own trash advice (`mv <path> ~/.local/share/Trash/`) breaks when that folder does not
  exist. Use `Trash/files/` after `mkdir -p`, as above.
- The session scratchpad (`/data/tmp/claude-1000/...`) is not treated as temp: recursive deletes
  there are always denied, and absolute moves out of it to home are denied.
- Several false positives seen in older sessions are allowed now: a heredoc to `$F`, a heredoc
  inside `$(...)`, `"$(cat file)"` as an argument, and dangerous commands named in quoted text.
  The self-test tracks them; if dcg changes, it fails and this list needs updating.
- In Claude Code transcripts every tool call appears twice (with and without a `cd` prefix).
  When reviewing history, that is not a retry.

## Self-test

```bash
bash scripts/self-test.sh
```

It replays every case in `tests/cases.json` (recorded failures, which must be denied, and the
fixes above, which must be allowed) through `dcg hook --batch`, and checks the skill's
structure. Add a case whenever you meet a new block.
