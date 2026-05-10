# ntm Recipes

Copy-paste patterns. Each block self-contained.

---

## Spawning

### One-time setup: discover projects_base
```bash
projects_base=$(ntm config show | awk -F'"' '/^projects_base/{print $2}')
echo "$projects_base"   # e.g. /data/projects
```

### Quick session (default agents)
```bash
mkdir -p "$projects_base/myproject"
ntm spawn myproject --cc=2 --cod=2
```

### With recipe
```bash
ntm spawn myproject -r full-stack            # 3 cc + 2 cod + 1 gmi
ntm spawn myproject -r minimal               # 1 cc
ntm spawn myproject -r review-team           # 2 cc + 1 cod
```

### With workflow template
```bash
ntm spawn myproject -t red-green --cc=2      # TDD ping-pong
ntm spawn myproject -t specialist-team       # architect → impl → QA pipeline
ntm spawn myproject -t parallel-explore --cc=4
```

### With personas (built-in)
```bash
ntm spawn myproject --persona=architect --persona=implementer:2
ntm spawn myproject --persona=reviewer --cc=2
# Built-in: architect, implementer, reviewer, tester, documenter
```

### Mixed model variants
```bash
ntm spawn myproject --cc=2:opus --cc=1:sonnet --cod=1:gpt-5.3-codex
```

### Headless / automation
```bash
ntm spawn myproject --cc=3 --no-user --auto-restart --stagger-mode=smart
```

### Worktrees (parallel-safe edits)
```bash
ntm spawn myproject --cc=3 --worktrees
ntm worktrees list
ntm worktrees merge claude_1                 # merge agent_1's branch
```

### Multiple goals / labels
```bash
ntm spawn myproject --label frontend --cc=3
ntm spawn myproject --label backend  --cc=2
ntm list --project myproject                 # see all
ntm attach myproject--frontend
```

### Spawn with initial prompt
```bash
ntm spawn myproject --cc=2 \
  --prompt "Read AGENTS.md, then \`bv --robot-next\` and start on the top bead"
```

### Spawn with auto-assignment from beads
```bash
ntm spawn myproject --cc=4 --assign --strategy=dependency \
  --init-prompt="Read AGENTS.md first"
```

---

## Sending

### Broadcast (every agent pane)
```bash
ntm send myproject --skip-first "Run tests and report"
ntm send myproject --all       "Quick: git status"
```

### By agent type
```bash
ntm send myproject --cc           "Review the changes"
ntm send myproject --cc=opus      "Deep review"
ntm send myproject --cod          "Generate tests"
ntm send myproject --cc --cod     "Pause and report"     # multiple types
```

### By tag
```bash
ntm send myproject --tag=frontend "Update Tailwind classes"
ntm send myproject --tag=backend  "Refactor the auth middleware"
```

### Specific pane(s)
```bash
ntm send myproject -p 2          "What are you stuck on?"
ntm send myproject --panes 1,3,5 "Pause and report"
```

### From file or stdin
```bash
ntm send myproject --cc -f prompts/triage.md
git diff | ntm send myproject --all --prefix "Review these changes:"
cat error.log | ntm send myproject --cc --suffix "Find the root cause."
```

### File context injection
```bash
ntm send myproject -c src/auth.py "Refactor for clarity"
ntm send myproject -c src/api.go:10-50 "Review these lines"
ntm send myproject -c a.go -c b.go "Compare these"
```

### Templates
```bash
ntm template list
ntm send myproject -t code_review --file src/main.go
ntm send myproject -t fix --var issue="null pointer" --file src/app.go
```

### Smart routing
```bash
ntm send myproject --smart                          "fix auth bug"
ntm send myproject --smart --route=affinity         "continue auth work"
ntm send myproject --smart --route=least-loaded     "any task"
# Strategies: least-loaded, round-robin, affinity, sticky, random
```

### Batch sends
```bash
# prompts.txt: one prompt per line, or --- separated
ntm send myproject --cc --batch prompts.txt --priority-order --stop-on-error
```

### Reduce thundering herd
```bash
ntm send myproject --cc --randomize --delay 5s --batch prompts.txt
```

### Skip CASS duplicate-check (use when cass is unhealthy)
```bash
ntm send myproject --all --no-cass-check "Restart and clear queue"
```

### Preview without sending
```bash
ntm send myproject --all --dry-run "test message"
```

---

## Attaching, monitoring, listing

### Attach
```bash
ntm attach myproject
ntm attach myproject--frontend                # for labeled sessions
```

### Activity (real-time table)
```bash
ntm activity                                  # auto-detect from cwd
ntm activity myproject
ntm activity myproject --watch                # auto-refresh every 2s
ntm activity myproject --watch --interval 1000
ntm activity myproject --json | jq '.[] | {pane, type, state, velocity}'
```

### Dashboard (interactive)
```bash
ntm dashboard myproject                       # TUI — from a real terminal only
ntm dashboard myproject --no-tui              # headless plain text
ntm dashboard myproject --json                # for automation
```

### List sessions
```bash
ntm list
ntm list --project myproject                  # all labels for a project
ntm list --json
```

---

## Adding / modifying / stopping

### Add more agents to an existing session
```bash
ntm add myproject --cc=1
ntm add myproject --cod=1 --persona=reviewer
```

### Adopt an existing tmux session
```bash
ntm adopt my-existing-tmux-session
```

### Stop
```bash
tmux kill-session -t myproject
tmux kill-server                              # nuclear: stop everything
```

---

## Diagnostics

### Quick health snapshot
```bash
ntm config show | grep '^projects_base'
ntm list
ntm activity --json 2>/dev/null | jq -c 'length, .[0] // {}'
cass health --json | jq -c '{status, healthy}'    # for --cass-check failures
```

### When a pane is stalled
```bash
ntm activity myproject --watch                # find STALLED / 0 velocity
tmux list-panes -t myproject -F '#{pane_index} #{pane_pid} #{pane_title}'
tmux kill-pane -t myproject:0.<index>         # kill the bad pane
ntm add myproject --cc=1                      # spawn replacement
```

### Persist tmux remain-on-exit (so dead panes are visible)
```bash
echo 'set-option -g remain-on-exit on' >> ~/.tmux.conf
tmux source ~/.tmux.conf
```

---

## Less-common but useful

### Profiles (saved spawn configs)
```bash
ntm profile list
ntm spawn myproject --profile <name>
```

### Profile sets (predefined teams)
```bash
ntm spawn myproject --profile-set=backend-team
```

### Privacy mode (no session-data persistence)
```bash
ntm spawn myproject --cc=2 --privacy
```

### Auto-restart crashed agents
```bash
ntm spawn myproject --cc=3 --auto-restart
```

### Rate-limit avoidance
```bash
ntm spawn myproject --cc=5 --stagger-mode=smart
ntm spawn myproject --cc=5 --stagger-mode=fixed --stagger-delay=20s
```
