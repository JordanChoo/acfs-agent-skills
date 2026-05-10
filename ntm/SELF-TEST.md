# Self-Test: ntm skill

Each test maps to a failure pattern observed in CASS or to a flag/command the skill explicitly relies on.

Run via:
```bash
bash ~/.claude/skills/ntm/scripts/self-test.sh   # Claude Code
bash ~/.codex/skills/ntm/scripts/self-test.sh    # Codex
```

The self-test is **read-only** — it doesn't spawn or kill anything. It verifies the binary's command surface still matches what the skill documents.

---

## Trigger Phrases (must activate the skill)

| Phrase | Expected |
|---|---|
| "spawn 4 claude agents on philomena" | Activates |
| "send a prompt to all agents in myproject" | Activates |
| "attach me to the philomena session" | Activates |
| "ntm spawn aborted when I said no to /tmp" | Activates |
| "ntm send isn't working" | Activates |
| "set up a multi-agent project" | Activates |
| "create a tdd workflow with ntm" | Activates |

---

## Behavioural Checks (look at the agent's commands)

### B1 — `ntm send` always includes a session name
The agent should never run `ntm send --cc "..."` without the session name. Pattern to flag: any `ntm send` whose next token starts with `--`.

### B2 — Pre-create the project dir on spawn
Before `ntm spawn myproject ...` the agent should `mkdir -p "$projects_base/myproject"` (or have already verified it exists). Pattern to flag: `ntm spawn` against a session that doesn't yet have a directory under `projects_base`.

### B3 — `--stagger-mode=smart` for ≥4 agents
For spawns of 4+ agents on a single provider, the agent should add `--stagger-mode=smart`. Pattern to flag: `ntm spawn ... --cc=[4-9]` without `--stagger-mode`.

### B4 — No `ntm dashboard` / `ntm palette` from inside an agent
Agents should never call the interactive TUIs from a non-TTY context. Pattern: `ntm dashboard <session>` without `--no-tui` or `--json`. Use `--json` instead.

### B5 — `--no-cass-check` when cass is unhealthy
If `cass health --json` shows `unhealthy` or `rebuilding`, sends should pass `--no-cass-check`.

---

## Failure-Case Tests (against the binary)

### F1 — `ntm spawn` requires a session name
```bash
ntm spawn 2>&1 | head -3
echo "exit=$?  expect: non-zero (usage error)"
```

### F2 — `ntm send` requires a session name
```bash
ntm send --cod "test" 2>&1 | head -3
echo "exit=$?  expect: non-zero"
```

### F3 — Built-in recipes are present
```bash
for r in quick-claude full-stack minimal codex-heavy balanced review-team; do
  ntm recipes list 2>/dev/null | grep -q "$r" && echo "  ✓ $r" || echo "  ✗ $r missing"
done
```

### F4 — Built-in workflow templates present
```bash
for t in red-green review-pipeline specialist-team parallel-explore; do
  ntm workflows list 2>/dev/null | grep -q "$t" && echo "  ✓ $t" || echo "  ✗ $t missing"
done
```

### F5 — `ntm config show` exposes `projects_base`
```bash
ntm config show 2>/dev/null | grep -q '^projects_base' && echo "F5 PASS" || echo "F5 FAIL"
```

### F6 — `ntm send` documents `--cass-check` and `--no-cass-check`
```bash
help=$(ntm send --help 2>&1)
echo "$help" | grep -q -- '--cass-check'    && echo "  ✓ --cass-check"    || echo "  ✗ --cass-check missing"
echo "$help" | grep -q -- '--no-cass-check' && echo "  ✓ --no-cass-check" || echo "  ✗ --no-cass-check missing"
```

### F7 — `ntm spawn` documents `--stagger-mode`
```bash
ntm spawn --help 2>&1 | grep -q -- '--stagger-mode' && echo "F7 PASS" || echo "F7 FAIL"
```

### F8 — `ntm activity` and `ntm dashboard` have `--json` for headless use
```bash
ntm activity  --help 2>&1 | grep -q -- '--json' && echo "  ✓ activity --json"  || echo "  ✗ activity --json missing"
ntm dashboard --help 2>&1 | grep -q -- '--json' && echo "  ✓ dashboard --json" || echo "  ✗ dashboard --json missing"
```

### F9 — `ntm spawn` documents `--worktrees`, `--label`, `--auto-restart`
```bash
help=$(ntm spawn --help 2>&1)
for f in '--worktrees' '--label' '--auto-restart' '--persona' '--no-user' '--safety'; do
  echo "$help" | grep -q -- "$f" && echo "  ✓ $f" || echo "  ✗ $f missing"
done
```

### F10 — Agent-type flags exist on send
```bash
help=$(ntm send --help 2>&1)
for f in '--cc' '--cod' '--gmi' '--all' '--skip-first' '--pane' '--panes' '--tag' '--smart' '--dry-run' '--file' '--context' '--template'; do
  echo "$help" | grep -q -- "$f" && echo "  ✓ $f" || echo "  ✗ $f missing"
done
```

---

## Cleanup

The tests are read-only. No cleanup needed.
