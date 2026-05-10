# cass Recipes

Copy-paste search patterns for the situations that come up most often. Each block is self-contained.

---

## Recall

### Last time I worked on X
```bash
cass search "X" --robot --limit 5 --fields summary --max-content-length 200
```

### Errors / warnings around a topic
```bash
cass search "stripe webhook timeout" --robot --limit 10 --fields summary --max-content-length 300 \
  | jq '.hits[] | {agent, source_path, line_number, snippet}'
```

### The exact line that introduced a fix (then read it)
```bash
hit=$(cass search "fixed retry logic" --robot --limit 1 --fields summary | jq -r '.hits[0]')
path=$(echo "$hit" | jq -r .source_path)
line=$(echo "$hit" | jq -r .line_number)
cass view "$path" -n "$line" -C 15
```

### What did I do yesterday?
```bash
cass timeline --since yesterday --until today --json | jq
# Or scoped to current project:
cass timeline --since yesterday --workspace "$(pwd)" --json
```

---

## Overviews (token-cheap)

### Counts by agent
```bash
cass search "<topic>" --robot --aggregate agent
```

### Counts by project
```bash
cass search "<topic>" --robot --aggregate workspace
```

### Time distribution (last 30 days, by date)
```bash
cass search "<topic>" --robot --aggregate date --days 30
```

### Multi-field agg
```bash
cass search "<topic>" --robot --aggregate agent,workspace,date --week
```

---

## Scoping

### Just this project
```bash
cass search "<q>" --robot --workspace "$(pwd)"
```

### Just one agent
```bash
cass search "<q>" --robot --agent claude_code
cass search "<q>" --robot --agent codex --agent gemini   # OR with multiple --agent flags
```

### Just remote sources (e.g. another machine)
```bash
cass search "<q>" --robot --source remote
cass search "<q>" --robot --source work-laptop   # specific host
```

### Time window
```bash
cass search "<q>" --robot --today
cass search "<q>" --robot --yesterday
cass search "<q>" --robot --week
cass search "<q>" --robot --days 30
cass search "<q>" --robot --since 2026-04-01
cass search "<q>" --robot --since '-7d'      # relative; quote it
cass search "<q>" --robot --since '-24h' --until now
```

---

## Chained / piped

### Intersection (sessions matching A *and* B)
```bash
cass search "playwright" --robot --robot-format sessions \
  | cass search "flaky"   --robot --sessions-from -
```

### From stdin file list
```bash
ls /home/ubuntu/.codex/sessions/2026/04/*.jsonl > /tmp/sources.txt
cass search "deploy" --robot --sessions-from /tmp/sources.txt
```

### Get a per-line list of sessions
```bash
cass search "<q>" --robot --robot-format sessions --limit 50
# Each line is one source_path — feed into other tools
```

---

## Sessions list

### What's the current session in this cwd?
```bash
cass sessions --current --json | jq '.sessions[0]'   # most recent in cwd
```

### 20 most recent sessions in a project
```bash
cass sessions --workspace /data/projects/scry --json --limit 20 | jq '.sessions[]'
```

### 5 sessions across all projects (no filter)
```bash
cass sessions --json --limit 5 | jq '.sessions[]'
```

> JSON shape: `{ "sessions": [ {"path","workspace","agent","title","modified","size_bytes","message_count","human_turns","source_id","origin_host"} ] }`. The session file path is `.sessions[].path`.

---

## Drill-in

### File-line context (Markdown / JSONL line numbers)
```bash
cass view <source_path> -n <line>           # ±5 lines (default)
cass view <source_path> -n <line> -C 20     # ±20 lines
cass view <source_path> -n <line> --json    # for scripting
```

### Message-level context (transcripts)
```bash
cass expand <source_path> --line <line>           # ±3 messages (default)
cass expand <source_path> --line <line> -C 10     # ±10 messages
```

### Full session as Markdown
```bash
cass export <source_path> --format markdown --output /tmp/session.md
```

---

## Diagnostics

### Fast preflight (use before any search loop)
```bash
cass health --json | jq -r '.recommended_action // "ready"'
```

### Full state
```bash
cass status --json
```

### Per-source visibility
```bash
cass diag --json | jq '.connectors'
cass sources agents list --json
```

### Index management
```bash
cass index           # incremental
cass index --full    # rebuild from source files
cass index --watch   # background reindex on file changes (run in tmux)
```

### Repair (safe — only rebuilds derived data)
```bash
cass doctor --fix
```

---

## Pagination

### Cursor-based (recommended for robot output)
```bash
out=$(cass search "<q>" --robot --limit 5 --robot-meta)
next=$(echo "$out" | jq -r '._meta.next_cursor // empty')
[ -n "$next" ] && cass search "<q>" --robot --cursor "$next" --limit 5
```

### Offset-based (simpler)
```bash
cass search "<q>" --robot --limit 10 --offset 0
cass search "<q>" --robot --limit 10 --offset 10
```

---

## Token discipline

When you expect to feed cass output back into the model:
```bash
cass search "<q>" --robot \
  --limit 5 \
  --fields summary \
  --max-content-length 200 \
  --max-tokens 500
```

When you only need the count, *never* page through hits — aggregate:
```bash
cass search "<q>" --robot --aggregate agent | jq '.aggregations'
```
