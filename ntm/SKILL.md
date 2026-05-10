---
name: ntm
description: >-
  Spawn, attach, and broadcast to multi-agent tmux sessions via the `ntm` CLI
  (Named Tmux Manager). Use when the user asks to "spawn agents", "send to all
  agents", "attach to a session", "set up a multi-agent project", or runs into
  the common `ntm` papercuts (projects_base / `/tmp` confusion, session-name
  required, CASS duplicate-check failures, rate-limit crashes from too many
  concurrent agents).
---

<!-- TOC: TL;DR | Mental model | Decision tree | Real command surface | Recipes | Anti-patterns | Pitfalls | Provenance -->

# ntm — Named Tmux Manager

> **What it is:** `ntm` creates a tmux session under a project directory and spawns one Claude/Codex/Gemini agent per pane, with a default user pane. It supports broadcasting prompts (`ntm send`), targeted prompts (by type, by tag, by pane), recipes/workflows, worktrees, and resource governance. The CLI is the contract; everything has a `--help` and many things have `--json`.

---

## TL;DR — happy path

```bash
# 1. Pre-create the project directory under projects_base (skip the prompt below)
mkdir -p "$(ntm config show | awk -F'\"' '/^projects_base/{print $2}')/myproject"

# 2. Spawn 2 Claude + 2 Codex agents (and a user pane) for that project
ntm spawn myproject --cc=2 --cod=2

# 3. Attach
ntm attach myproject

# 4. Broadcast a prompt to every agent (must always pass the session name)
ntm send myproject --all "Read AGENTS.md and start on the top bead"

# 5. See who's working
ntm activity myproject
ntm dashboard myproject     # interactive (run from a real terminal, not from inside an agent)
```

If you only do those five, you'll be right 90% of the time.

---

## Mental Model

```
projects_base   (config: ~/.config/ntm/config.toml; here = /data/projects)
└── myproject/                 ← session_name MUST match a real dir under projects_base
    ├── AGENTS.md             (each agent reads this on startup)
    ├── .ntm/                 (per-project state, logs, summaries)
    ├── <your code>
    └── tmux session "myproject":
         pane 0: user shell    (--no-user to skip)
         pane 1: cc_1          (Claude, alias "cc")
         pane 2: cc_2
         pane 3: cod_1         (Codex, alias "cod")
         …                     (gmi = Gemini, etc.)
```

**The session name is the project directory name** — `ntm spawn philomena` opens its working dir at `<projects_base>/philomena`. The session name is also the **Agent Mail project key** for cross-agent messaging.

---

## Decision Tree

```
What does the user want?
│
├─ "Spawn N agents on project X"
│   → Recipe #1 (Spawn). Pre-create the dir; pick the right --cc/--cod/--gmi mix.
│
├─ "Send a prompt to all agents / specific agents"
│   → Recipe #2 (Send). Target with --all / --cc / --cod / --tag / --pane.
│
├─ "Attach me to that session"
│   → ntm attach <session>   (always needs the session name)
│
├─ "Status / activity / dashboard"
│   → ntm activity <session> [--watch]      (table)
│   → ntm dashboard <session>                (TUI — DO NOT call from inside an agent)
│
├─ "Set up a TDD / review / specialist team"
│   → Recipe #3 (Recipes & Workflows): -r <recipe> or -t <template>
│
├─ "Multiple parallel goals on one project"
│   → Recipe #4 (Labels): --label frontend / --label backend
│
├─ "Avoid file conflicts between agents"
│   → Recipe #5 (Worktrees): --worktrees
│
└─ "Spawn aborted / asked to create /tmp directory / agents can't find AGENTS.md"
    → §Pitfalls — almost always the projects_base mismatch (P1)
```

---

## Real Command Surface (verified against `ntm --help`)

The full CLI is large (~40 subcommands). These are the ones you'll need 90% of the time.

### Session lifecycle
| Command | Use |
|---|---|
| `ntm spawn <name> [flags]` | Create session + agent panes |
| `ntm attach <name>` (alias `a`) | Attach (or switch if already in tmux) |
| `ntm list` | List sessions and pane counts |
| `ntm add <name> [flags]` | Add more agents to an existing session |
| `ntm adopt <tmux-session>` | Wrap an existing tmux session under ntm management |
| `ntm activity [name] [--watch] [--json]` | Real-time agent state table |
| `ntm dashboard [name]` | Interactive TUI dashboard |
| `ntm config show` | Print effective config (incl. `projects_base`) |

### `ntm spawn` — most-used flags
| Flag | Use |
|---|---|
| `--cc N[:model]` / `--cod N[:model]` / `--gmi N[:model]` | Counts per agent type (e.g. `--cc=2:opus`) |
| `--persona <name>[:N]` | Built-in: `architect`, `implementer`, `reviewer`, `tester`, `documenter` |
| `-r, --recipe <name>` | Built-in: `quick-claude`, `full-stack`, `minimal`, `codex-heavy`, `balanced`, `review-team` |
| `-t, --template <name>` | Workflow template: `red-green`, `review-pipeline`, `specialist-team`, `parallel-explore` |
| `--no-user` | Skip the user pane (headless / automation) |
| `--prompt "<text>"` | Initial prompt sent after agents are ready |
| `--init-prompt "<text>"` | Prompt only after `--assign` finishes |
| `-l, --label <name>` | Multi-goal: creates `<name>--<label>` session sharing the project dir |
| `--worktrees` | Each agent gets its own git worktree + branch (parallel-safe) |
| `--auto-restart` | Monitor + restart crashed agents |
| `--stagger-mode smart` | Adaptive delays — recommended when spawning ≥ 4 agents |
| `--cass-context "<query>"` | Inject relevant past-session context |
| `--no-cass-context` | Disable CASS context injection |
| `--safety` | Fail if session already exists (don't accidentally reuse) |

### `ntm send` — most-used flags
| Flag | Use |
|---|---|
| (positional) `<session>` | **Always required**, even when attached to that session |
| `--all` | Every pane including user pane |
| `-s, --skip-first` | Skip the user pane |
| `--cc[=variant]` / `--cod[=variant]` / `--gmi[=variant]` | Filter by agent type / model variant |
| `--tag <name>` | Filter by tag (OR-logic) |
| `-p, --pane N` / `--panes 1,2,3` | Specific pane(s) by index |
| `--smart [--route=affinity\|sticky\|round-robin\|least-loaded\|random]` | Auto-pick best agent |
| `-f, --file <path>` / stdin | Prompt from file or pipe |
| `-c, --context <path[:lines]>` | Inject file contents (repeatable; supports `path:10-50`) |
| `-t, --template <name>` `--var k=v` | Templated prompts |
| `--prefix "..."` / `--suffix "..."` | Wrap file/stdin content |
| `--dry-run` | Preview without sending |
| `--no-cass-check` | Skip CASS duplicate-work check (use if cass is unhealthy or you don't want it) |
| `--cass-check-days N` / `--cass-similarity 0.7` | Tune duplicate detection |
| `--randomize` `--seed N` | Reduce thundering herd when sending individualized prompts |
| `--delay 5s` | Insert delay between prompts |
| `--batch <file>` `--priority-order` `--stop-on-error` | Send a queue of prompts |
| `--json` | Machine-readable output |

### Other useful surfaces
| Command | Use |
|---|---|
| `ntm recipes list` / `ntm workflows list` | See templates |
| `ntm template list` | See prompt templates |
| `ntm agents` | Manage agent profiles |
| `ntm worktrees list` / `merge <agent>` | Manage agent worktrees |
| `ntm bind` | Set up tmux keybinding for the palette |
| `ntm shell <bash\|zsh>` | Eval-able shell integration (tab completion etc.) |

---

## Recipes — paste & adapt

### 1. Spawn (project must exist under projects_base)

```bash
# Discover projects_base (one-time)
projects_base=$(ntm config show | awk -F'"' '/^projects_base/{print $2}')

# Pre-create the project dir so spawn doesn't prompt or abort
mkdir -p "$projects_base/myproject"

# Standard 2+2 (Claude + Codex) with adaptive stagger
ntm spawn myproject --cc=2 --cod=2 --stagger-mode=smart

# Bigger team using a recipe
ntm spawn myproject -r full-stack --auto-restart

# Initial prompt + agents in their own worktrees
ntm spawn myproject --cc=3 --worktrees \
  --prompt "Read AGENTS.md and pick the top bead from \`bv --robot-next\`"
```

### 2. Send (every send needs the session name)

```bash
# Broadcast to all agent panes (skip user pane)
ntm send myproject --skip-first "Run lint and report any errors"

# Target by agent type / model variant
ntm send myproject --cc       "Review the changes"
ntm send myproject --cc=opus  "Deep review on auth flow"
ntm send myproject --cod      "Generate tests for changed files"

# Target by tag (set via personas / profiles)
ntm send myproject --tag=frontend "Update Tailwind classes for the new design"

# Specific pane(s)
ntm send myproject -p 2 "What are you stuck on?"
ntm send myproject --panes 1,3 "Pause and report status"

# Prompt from a file or stdin
ntm send myproject --cc -f prompts/triage.md
git diff | ntm send myproject --all --prefix "Review these changes:"

# Smart routing (pick best agent automatically)
ntm send myproject --smart --route=affinity "Continue work on auth"

# Skip CASS duplicate-check (use when cass is unhealthy)
ntm send myproject --all --no-cass-check "Restart your TUI"

# Preview without sending
ntm send myproject --all --dry-run "test message"
```

### 3. Recipes & Workflows

```bash
# Built-in recipe (predefined agent counts)
ntm spawn myproject -r review-team        # 2 cc + 1 cod (writer + reviewers)
ntm spawn myproject -r codex-heavy        # 4 cod + 1 cc

# Built-in workflow template (coordination pattern)
ntm spawn myproject -t red-green --cc=2   # TDD ping-pong
ntm spawn myproject -t specialist-team    # Architect + impl + QA pipeline
ntm spawn myproject -t parallel-explore --cc=4
```

### 4. Labels (multiple concurrent goals on one project)

```bash
# Two parallel session swarms sharing the project dir
ntm spawn myproject --label frontend --cc=3
ntm spawn myproject --label backend  --cc=2

ntm list --project myproject              # see both
ntm send myproject--frontend --all "..."  # session name is <project>--<label>
```

### 5. Worktrees (parallel-safe edits)

```bash
ntm spawn myproject --cc=3 --worktrees    # each agent gets its own branch + checkout
ntm worktrees list
ntm worktrees merge claude_1              # merge agent_1's work back to main
```

### 6. Activity & dashboard

```bash
ntm activity myproject                    # one-shot table
ntm activity myproject --watch            # auto-refresh every 2s
ntm activity myproject --json | jq '.[] | {pane, type, state, velocity}'

# Interactive dashboard — run from a real terminal, NOT from inside an agent
ntm dashboard myproject
# Headless variants for agents:
ntm dashboard myproject --no-tui
ntm dashboard myproject --json
```

### 7. Stop / clean up

```bash
ntm list                                  # what's running
tmux kill-session -t myproject            # stop the whole session
tmux kill-server                          # nuclear option for everything
```

---

## Anti-Patterns — DO NOT do these

These came from real CASS sessions. The skill exists to keep them from happening again.

### A1. `ntm send` without a session name
**Symptom:** `ntm send --cod "message"` does nothing or errors.
**Cause:** the session name is **always required**, even when you're attached. Sessions are named, not implicit from cwd.
**Correct:** `ntm send myproject --cod "message"`. (CASS session 2:21 — user repeatedly hit this.)

### A2. Spawning without pre-creating the project dir
**Symptom:** "create /tmp directory? (y/n)"; saying No aborts the command.
**Cause:** `ntm spawn <name>` expects `<projects_base>/<name>` to exist (and Agent Mail keys off it). If it doesn't, ntm offers to create it; saying No is the abort path.
**Correct:** pre-create the dir under `projects_base`, *or* set `projects_base` to point at where your real projects live.
```bash
projects_base=$(ntm config show | awk -F'"' '/^projects_base/{print $2}')
mkdir -p "$projects_base/myproject"
```
(CASS sessions 5/6/7 — repeated /tmp confusion.)

### A3. Spawning many agents without `--stagger-mode`
**Symptom:** Agents crash 30–90 minutes in with `agent loop died unexpectedly` or rate-limit errors. JSONL logs show `queue-operation: enqueue` then silence.
**Cause:** thundering herd hits provider API rate limits; multiple agents fail simultaneously.
**Correct:** for ≥ 4 agents, use `--stagger-mode=smart`. For batch sends, use `--randomize --delay 5s` to avoid simultaneous API bursts.
(CASS sessions 163/164 — crash forensics.)

### A4. Sending while CASS is unhealthy
**Symptom:** `ntm send` fails with `cass execution failed` / `search failed: internal error`.
**Cause:** `--cass-check` (the default) consults cass for duplicate-work; if cass is broken, send fails.
**Correct:** `ntm send <session> --no-cass-check "..."`. Then fix cass separately (use the `cass` skill).
(CASS sessions 437/473/474.)

### A5. Calling `ntm dashboard`/`ntm palette` from inside an agent
**Symptom:** session hangs.
**Cause:** these are interactive TUIs; non-TTY agents can't drive them.
**Correct:** `ntm dashboard --no-tui`, `ntm dashboard --json`, or use `ntm activity --json` instead.

### A6. Forgetting AGENTS.md is read from the working dir
**Symptom:** Agents don't follow project conventions; act like a fresh install.
**Cause:** the agent's `cwd` is `<projects_base>/<session_name>`. If `AGENTS.md` lives somewhere else, the agent never sees it.
**Correct:** put `AGENTS.md` under the project dir; verify with `ntm config show` + `ls $projects_base/<session>/AGENTS.md`.
(CASS session 2:11 — explicit user question.)

### A7. Running `ntm send` against a stale or dying session
**Symptom:** Prompts queue but agents never respond. `ntm activity` shows STALLED or zero velocity.
**Cause:** TUI hung, child process stuck, pane survived but agent loop died.
**Correct:** `ntm activity <session> --watch` first; if STALLED, `tmux kill-pane` the dead one and `ntm add` a fresh agent — or use `--auto-restart` on next spawn.

### A8. Running too many concurrent agents from the same provider
**Symptom:** Same as A3 — rate-limit cascade.
**Rule of thumb:** 3–4 Opus or 4–5 Codex on a single provider before you start hitting limits regularly. Mix providers (`--cc=2 --cod=2 --gmi=1`) instead of stacking.

### A9. Inventing flags
**Don't exist:** `ntm send --queue`, `ntm spawn --workdir`, bare `ntm` as a query (it's the help). When in doubt, `ntm <subcommand> --help` is authoritative.

---

## Pitfalls (deeper)

See [PITFALLS.md](references/PITFALLS.md) for symptom → cause → diagnose → fix on each of the above plus a few less common cases (memory limits, label collisions, stale `~/.ntm/pids`, palette-prompt invocation).

---

## Provenance of this skill

Honest about which guidance is grounded where:

- **Grounded in observed user/agent failures (CASS sessions 2/5/6/7/13/163/164/189/223/241/349/437/473/474):** A1 (session-name required), A2 (projects_base / `/tmp` abort), A3 (rate-limit crashes), A4 (`--cass-check` failures), A6 (AGENTS.md confusion), A7 (stalled panes), and the matching pitfalls.
- **Verified against `ntm --help` on the installed binary:** all flags, command names, and recipe/workflow names. The self-test asserts these.
- **Extrapolated:** A5 (TUI-from-agent hangs) and A9 (invented-flag warning) follow the same logic as the cass skill. A8's "rule of thumb" numbers are estimates; the failure pattern is real but specific limits depend on your account.

When you hit a usage failure mode the skill doesn't catch, add it to PITFALLS.md (with a session ID or reproducer) and add a check to `scripts/self-test.sh`.
