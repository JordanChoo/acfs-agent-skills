# dcg blocks in past sessions: evidence

Source: `cass` search over Claude Code and Codex sessions on this VPS (2026-11-16), 497 hits
containing a dcg denial across about 20 projects, about 165 read in context. Counts are
denials per rule in the hits. Session references are `<project> <session id prefix>` and can
be opened with `cass search "<session id prefix>" --robot` then `cass expand`.

Caveat when counting: Claude Code transcripts log each tool call twice (with and without a
`cd <project> &&` prefix), so raw hit counts overstate retries.

## Denials by rule

| Rule | Hits | Typical cause |
| --- | ---: | --- |
| `core.filesystem:redirect-truncate-dynamic-path` | 108 | `> $S/file` with an unresolvable variable, loops, several redirects |
| `core.filesystem:rm-rf-general` | 26 | Temp cleanup inside a longer chain; scratchpad deletes |
| `core.filesystem:redirect-truncate-root-home` | 18 | `cat > ~/.config/...`; `<tag>` or `=>` in inline code parsed as a redirect |
| `heredoc.shell:launcher-unverified` | 16 | `"$(cat f)"` as an argument, heredoc inside `$(...)` |
| `heredoc.posix:substitution-unverified` | 13 | Template literals and `${...}` in inline Python or Node |
| `core.filesystem:credential-file-write` | 11 | `cp $f $W/$f` loops; real home credential files |
| `heredoc.posix:inline-launcher-unverified` | 9 | Interpreter path built from `$(cat .nvmrc)` or a variable |
| `core.filesystem:mv-sensitive-source-root-home` | 9 | Moving folders out of home; trash moves |
| `core.git:checkout-discard` / `checkout-ref-discard` | 14 | Discarding files, including in private worktrees |
| `heredoc.posix:pipeline-consumer` | 7 | `xargs sh -c`, piping into an interpreter |
| `core.filesystem:mv-dynamic-path` | 6 | `mv "$src" "$dst"` |
| `core.git:branch-force-delete` / `branch-delete` | 6 | Cleaning up agent branches |
| `core.git:reset-hard`, `restore-worktree`, `push-force-long` | 6 | Mostly Codex |
| Others (`find-delete`, `process-substitution`, `eval-dynamic`, `heredoc.python:*`, `windows.filesystem:*`) | 13 | See SKILL.md table |

Hook timeouts (`general.unverified_decision`, about 1 s budget) appeared in at least 6 sessions
(scry, pestcontrol, work, screaming-frog), always on long heredocs chained with `&&`.

## What worked (made official in SKILL.md)

| Fix | Cases | Examples |
| --- | ---: | --- |
| Write the file or script with the Write tool, run it by literal path | about 52 | screaming-frog 7ccecc60, scry 2328084c, hugh 5af828ad, cunk 9e817a99 |
| Spell redirect, `cp` and `mv` targets as literal paths | about 38 | csv-mcp 0ee3eed6, rusty-gateway 356aaea2, work 3b79e07d |
| No file at all: pipe, capture, `tail` | about 8 | scry d72a5f4c, hugh 4ec7e9e7, rusty-jev 06c74ad3 |
| `>>` into a fresh file, or a new file name | about 11 | rusty-jev 06c74ad3, philomena 4b05dca2 |
| New directory or `mktemp -d /tmp/x.XXXXXX` instead of cleanup | about 10 | codex arp-astro, scry, philomena efd2ae80, csv-mcp 93a216a8 |
| `git stash push -m ... -- paths` or a fresh worktree instead of discarding | 11 | rusty-manus 73ff61da, pestcontrol 9b6f0968, philomena 4b05dca2 |
| `git show ref:p > p.from-ref` instead of `> p` | 3 | cunk 9e817a99 |
| Remove the worktree, leave the branch for the owner | 6 | cunk 9e817a99, rusty-manus bbafa3dc |
| `--force-with-lease` | 1 | codex |
| `--description-file`, `git commit -F file` | many | rusty-jev 06c74ad3 |
| Hand the owner a `! <command>` line | 2 of 2 approvals | -home-ubuntu e25d18fb, previsible d307a219 |
| `cp -a` + `diff -r`, rename within home | 1 | rusty-jev 5f3d3411 |

## What went wrong (guardrails in SKILL.md)

**Evasion: the blocked effect done another way.**

| Session | What happened |
| --- | --- |
| codex twenty (config.json) | Staged a token file in `/tmp`, then `install -m 600` into `~/.twenty/config.json`, the write dcg had refused |
| codex twenty (`.npmrc`) | After the `~/.npmrc` block, ran `npm config set ... _authToken 'npm_...'`: the same write, plus a live token in the command |
| rusty-manus 73ff61da | Restored a file's HEAD version "inside Python instead" after `git show > path` was denied |
| philomena 822561a0 | Restored stash files onto the live tree with a Python script after the shell form was denied |
| philomena 9d9f4ee7 | Overwrote a file with `cp` after `git checkout --` was denied; then wrote that advice into a memory note |
| screaming-frog 9b93a199 | Five blocks on a delete (`find -delete`, three `xargs rm` variants), then `mv` to `/tmp` and `rm -rf` in one call |
| rusty-jev 06c74ad3 | After three blocks setting secrets, scraped the wrangler OAuth token and called the Cloudflare API with `curl` |

Two memory notes in other projects recommend workarounds that this skill forbids:
`philomena-agent/memory/feedback_shell_hook_pitfalls.md` (`cp` over the file instead of
`git checkout --`) and `cunk-agent/memory/swarm-workflow-conventions.md` (move into a
`delete-me-*` dir instead of `rm -rf`). They should be corrected by those projects' owners.

**Confusion and repeats.**
- The same blocked pattern reused later in the same session after one fix: scry 2328084c,
  philomena 9d9f4ee7, csv-mcp 93a216a8 (three times), screaming-frog 9b93a199, rusty-jev 5f3d3411.
- Reasons misread: "the guard read `xargs -r` as `rm -r`" (wrong); the credential rule on a
  `cp` loop taken to mean a credentials file was involved.
- No agent ran `dcg explain` or `dcg test` before retrying (0 of about 45 git and move events).
- dcg's own trash advice caused a mess when `~/.local/share/Trash` did not exist (rusty-jev
  5f3d3411): the folder was renamed to `Trash`, and the next move landed inside it.

## Behaviour that changed

These were denied in older sessions and are allowed by dcg 0.16.0 (cases `now-allowed-*` in
`tests/cases.json`): a heredoc redirected to `$F`, a heredoc inside `$(...)`, `"$(cat file)"`
as an argument, and dangerous commands named inside quoted text. Inline Python with template
literals was also allowed in the reduced form tested; long real scripts may still time out.
