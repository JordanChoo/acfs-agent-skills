# ntm Pitfalls

Each entry: **symptom → cause → diagnose → fix.** Drawn from CASS sessions of real users and agents stumbling on `ntm`.

---

## P1 — `projects_base` / `/tmp` confusion (the #1 user trap)

**Symptom:** Running `ntm spawn myproject` either:
- Asks "Create directory? (y/N)" — saying No aborts.
- Spawns under `/tmp/myproject` when the user expected `/data/projects/myproject` (or vice versa).
- Agents start but can't find AGENTS.md / source code / git repo.

**Cause:** `ntm spawn <name>` opens the session's working dir at `<projects_base>/<name>`. If `projects_base` (in `~/.config/ntm/config.toml`) is `/tmp`, then `myproject` becomes `/tmp/myproject` — empty unless you put code there. Agent Mail also keys off this path.

**Diagnose:**
```bash
ntm config show | grep '^projects_base'
ls -la "$(ntm config show | awk -F'\"' '/^projects_base/{print $2}')/myproject"
```

**Fix (recommended):**
1. Set `projects_base` to where your actual projects live (e.g. `/data/projects`):
   ```toml
   # ~/.config/ntm/config.toml
   projects_base = "/data/projects"
   ```
2. Pre-create the project dir before spawning:
   ```bash
   mkdir -p "/data/projects/myproject"
   git clone <url> /data/projects/myproject   # if cloning fresh
   ntm spawn myproject --cc=2
   ```

**Why not just say "Yes" to the prompt:** it creates an empty dir at `<projects_base>/<name>`, which is fine for a sandbox but hides the real project. Pre-creating makes it explicit.

(CASS sessions 5, 6, 7 — repeated user questions.)

---

## P2 — Session name is always required

**Symptom:** `ntm send --cod "message"` does nothing useful; user thought attaching to a session would make sends implicit.

**Cause:** `ntm send <session> [prompt] [flags]` — the session is a **positional arg, not implicit from cwd or attach state**.

**Fix:**
```bash
ntm send myproject --cod "message"   # always pass the session name
```

**Convenience:** add a shell alias if you usually work on one session:
```bash
alias send-myproject='ntm send myproject'
```

(CASS session 2 — user explicitly asked twice.)

---

## P3 — `--cass-check` failures break `ntm send`

**Symptom:** `ntm send` fails with `cass execution failed` (exit 2) or `search failed: internal error: table not found: fts_messages`.

**Cause:** `ntm send` consults CASS by default to detect duplicate work in the past 7 days. If cass is unhealthy (rebuilding, FTS issues, version mismatch), the subprocess fails and the send is aborted.

**Diagnose:**
```bash
cass health --json | jq -r '.status, .recommended_action'
```

**Fix:**
- Bypass for the immediate task: `ntm send <session> --no-cass-check "..."`
- Permanently disable in config: set the relevant `[send]` knob in `~/.config/ntm/config.toml` (varies by ntm version — check `ntm config show`).
- Repair cass: see the `cass` skill (`cass doctor --fix`, `cass index --full`).

(CASS sessions 437, 473, 474, 665.)

---

## P4 — Rate-limit cascade from spawning too many agents

**Symptom:** 30–90 minutes after `ntm spawn`, multiple panes die. Last JSONL line is `queue-operation: enqueue` then silence. `Exit code 144` (SIGSTKFLT) on at least one. `ntm activity` shows STALLED or shows nothing because `remain-on-exit` is off and the panes vanished.

**Cause:** thundering herd of agents on the same provider (e.g. 4–6 Claude Opus sessions) saturate the API rate-limit pool; one agent's slowdown cascades into all of them queuing requests forever.

**Diagnose:**
```bash
ntm activity <session> --watch
# Or post-mortem:
ls /home/ubuntu/.claude/projects/-<workspace>/   # JSONL session files
journalctl --user -t ntm | grep -E 'rate|429|timeout'
```

**Prevent:**
- `--stagger-mode=smart` on spawns ≥ 4 agents (adaptive backoff)
- Mix providers: `--cc=2 --cod=2` rather than `--cc=4`
- Use `--auto-restart` so transient deaths self-heal
- Persist tmux remain-on-exit so dead panes are visible:
  ```bash
  echo 'set-option -g remain-on-exit on' >> ~/.tmux.conf
  tmux source ~/.tmux.conf
  ```

(CASS sessions 163, 164, 189 — full crash forensics.)

---

## P5 — `AGENTS.md` not picked up by spawned agents

**Symptom:** Spawned agents act like a fresh install; ignore project conventions.

**Cause:** the agent's working directory is `<projects_base>/<session_name>`. AGENTS.md must live there. If your actual project root is elsewhere (e.g. you spawned in `/tmp/myproject` but the real project is `/data/projects/foo`), agents never see it.

**Diagnose:**
```bash
projects_base=$(ntm config show | awk -F'"' '/^projects_base/{print $2}')
ls -la "$projects_base/<session>/AGENTS.md"
```

**Fix:** see P1 — fix the `projects_base` mismatch, then ensure `AGENTS.md` is in the project dir.

---

## P6 — Stalled / zombie panes silently consuming quota

**Symptom:** `ntm send` queues prompts; agents never respond. After a while everything else feels slower.

**Cause:** an agent loop hung on a tool call, but the tmux pane stayed alive. NTM's monitor keeps sending prompts to the dead loop. Other agents on the same account share the rate-limit budget with the zombie.

**Diagnose:**
```bash
ntm activity <session> --watch                    # look for STALLED / 0 velocity
ps -ef | grep -E 'claude|codex' | grep -v grep    # how many actually running?
```

**Fix:**
```bash
# Find the bad pane (e.g. pane 5)
tmux list-panes -t <session> -F '#{pane_index} #{pane_pid} #{pane_title}'
tmux kill-pane -t <session>:0.5
ntm add <session> --cc=1                          # spawn a replacement
# Or, going forward:
ntm spawn <session> --auto-restart
```

---

## P7 — Calling interactive TUIs from inside an agent

**Symptom:** Session hangs forever after running `ntm dashboard` or `ntm palette` from a bash tool inside an agent pane.

**Cause:** these are bubble-tea TUIs; non-TTY contexts can't drive them.

**Fix:** use the headless equivalents:
```bash
ntm dashboard <session> --no-tui                   # plain text
ntm dashboard <session> --json | jq                # structured
ntm activity <session> --json | jq                 # state table as JSON
ntm list --json                                    # session list as JSON
```

---

## P8 — Memory-guard surprise kills

**Symptom:** A pane dies unexpectedly with no agent-side error. `journalctl` mentions `tmux-spawn` cgroup OOM kill at 8 GB.

**Cause:** the optional `ntm-memory-guard` daemon applies 8 GB hard / 6 GB soft limits per agent pane. Normal agents peak around 1–2.3 GB; a leaking pane will hit the cap.

**Diagnose:**
```bash
ntm-memory-guard --status         # current limits and usage per pane
systemctl --user status ntm-memory-guard
```

**Tune:** raise via env vars:
```bash
NTM_MEMORY_MAX=12G NTM_MEMORY_HIGH=10G systemctl --user restart ntm-memory-guard
```

---

## P9 — Label / session name collisions

**Symptom:** `ntm spawn myproject --label frontend` succeeds but `ntm attach myproject` doesn't show the new agents.

**Cause:** `--label` creates a new session named `myproject--frontend`, not the bare `myproject` session. They share the project dir but are independent tmux sessions.

**Fix:**
```bash
ntm list --project myproject              # see all labels
ntm attach myproject--frontend            # attach to the labeled session
```

---

## P10 — Spawn races / "session already exists"

**Symptom:** Re-running `ntm spawn myproject --cc=2` after a previous spawn either silently appends, or errors strangely.

**Fix:** use `--safety` to fail-fast on existing sessions; `ntm add` to extend an existing one:
```bash
ntm spawn myproject --cc=2 --safety              # error if myproject already exists
ntm add   myproject --cc=1                       # add one more agent to existing
```

---

## Quick Diagnostic Block

Run this when ntm "isn't working":

```bash
echo "=== ntm quick check ==="
echo "--- version & PATH ---";   which ntm; ntm --help 2>&1 | head -1
echo "--- projects_base ---";    ntm config show | grep '^projects_base'
echo "--- sessions ---";         ntm list 2>/dev/null
echo "--- activity ---";         ntm activity --json 2>/dev/null | jq -c 'length, .[0] // {}' 2>/dev/null
echo "--- cass health ---";      cass health --json 2>/dev/null | jq -c '{status, healthy}'
echo "--- tmux ---";             tmux ls 2>/dev/null | head
```
