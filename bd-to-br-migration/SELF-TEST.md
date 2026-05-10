# Self-Test: bd-to-br-migration

Each test corresponds to a failure pattern observed in CASS sessions. The verifier should now catch what the previous version missed.

---

## Trigger Phrases (must activate the skill)

| Phrase | Expected |
|--------|----------|
| "migrate from bd to br" | Activates |
| "convert bd commands to br" | Activates |
| "update AGENTS.md from beads to beads_rust" | Activates |
| "bd sync to br sync" | Activates |
| "beads migration" | Activates |
| "fix bd references" | Activates |
| "strip phantom br commands" | Activates |

---

## Structure Validation

```bash
SKILL_DIR=~/.claude/skills/bd-to-br-migration   # or ~/.codex/skills/bd-to-br-migration
ls -la "$SKILL_DIR"
test -x "$SKILL_DIR/scripts/verify-migration.sh"
test -x "$SKILL_DIR/scripts/find-bd-refs.sh"
```

---

## Failure-Case Tests (one per CASS finding)

The verifier must FAIL on each of these. If any test exits 0, the skill regression-tested incorrectly.

### F1 — Plain `bd sync` left in (the work-loss precursor)

```bash
cat > /tmp/test-f1.md <<'EOF'
## Beads
Run `bd sync` at session end.
EOF
./scripts/verify-migration.sh /tmp/test-f1.md
[ $? -eq 2 ] && echo "F1 PASS" || echo "F1 FAIL"
```

### F2 — `br sync --flush-only` without `git add .beads/`

```bash
cat > /tmp/test-f2.md <<'EOF'
## Issue Tracking with br (beads_rust)
**Note:** `br` is non-invasive.
\`\`\`bash
br sync --flush-only
git push
\`\`\`
EOF
./scripts/verify-migration.sh /tmp/test-f2.md
[ $? -eq 2 ] && echo "F2 PASS" || echo "F2 FAIL"
```

### F3 — Phantom `br prime`

```bash
cat > /tmp/test-f3.md <<'EOF'
## Beads (br)
**Note:** non-invasive.
Run \`br prime\` for context, then \`bv --robot-triage\`.
br sync --flush-only
git add .beads/
EOF
./scripts/verify-migration.sh /tmp/test-f3.md
[ $? -eq 2 ] && echo "F3 PASS (caught br prime)" || echo "F3 FAIL"
```

### F4 — Phantom `br doctor --fix`

```bash
cat > /tmp/test-f4.md <<'EOF'
## Beads (br)
**Note:** non-invasive.
Run \`br doctor --fix\` to repair.
br sync --flush-only
git add .beads/
EOF
./scripts/verify-migration.sh /tmp/test-f4.md
[ $? -eq 2 ] && echo "F4 PASS (caught br doctor --fix)" || echo "F4 FAIL"
```

### F5 — Phantom `br update --add-note`

```bash
cat > /tmp/test-f5.md <<'EOF'
## Beads (br)
**Note:** non-invasive.
Use \`br update <id> --add-note "Session end"\`.
br sync --flush-only
git add .beads/
EOF
./scripts/verify-migration.sh /tmp/test-f5.md
[ $? -eq 2 ] && echo "F5 PASS (caught --add-note)" || echo "F5 FAIL"
```

### F6 — Phantom `--description-file`

```bash
cat > /tmp/test-f6.md <<'EOF'
## Beads (br)
**Note:** non-invasive.
\`br create --description-file /tmp/desc.md\`
br sync --flush-only
git add .beads/
EOF
./scripts/verify-migration.sh /tmp/test-f6.md
[ $? -eq 2 ] && echo "F6 PASS (caught --description-file)" || echo "F6 FAIL"
```

### F7 — Phantom `br compact`

```bash
cat > /tmp/test-f7.md <<'EOF'
## Beads (br)
**Note:** non-invasive.
\`br compact --analyze\`
br sync --flush-only
git add .beads/
EOF
./scripts/verify-migration.sh /tmp/test-f7.md
[ $? -eq 2 ] && echo "F7 PASS (caught br compact)" || echo "F7 FAIL"
```

### F8 — Bare `br sync` without mode flag

```bash
cat > /tmp/test-f8.md <<'EOF'
## Beads (br)
**Note:** non-invasive.
At session end, run br sync to flush.
git add .beads/
EOF
./scripts/verify-migration.sh /tmp/test-f8.md
[ $? -eq 2 ] && echo "F8 PASS (caught bare br sync)" || echo "F8 FAIL"
```

### F9 — Mixed bd-NNNN / br-NNNN IDs

```bash
cat > /tmp/test-f9.md <<'EOF'
## Beads (br)
**Note:** non-invasive.
See bd-1xkz and br-9abc for context.
br sync --flush-only
git add .beads/
EOF
./scripts/verify-migration.sh /tmp/test-f9.md
[ $? -eq 2 ] && echo "F9 PASS (caught bd-NNNN)" || echo "F9 FAIL"
```

---

## Happy-Path Test

A correctly migrated file MUST exit 0:

```bash
cat > /tmp/test-good.md <<'EOF'
## Issue Tracking with br (beads_rust)

**Note:** `br` is non-invasive — it never executes git commands. After every `br sync --flush-only` (or any mutation, since auto-flush is on by default), you must manually:

\`\`\`bash
git add .beads/
git commit -m "sync beads"
\`\`\`

### Commands

- \`br ready --json\`
- \`br create -t task -p 2 -d "Fix" "Title"\`
- \`br update <id> --status in_progress\`
- \`br close <id> -r "Done"\`

### Session end

\`\`\`bash
br sync --flush-only
git add .beads/
git commit -m "feat: … (br-1234)"
git push
\`\`\`
EOF
./scripts/verify-migration.sh /tmp/test-good.md
[ $? -eq 0 ] && echo "Happy path PASS" || echo "Happy path FAIL"
```

---

## Run All Tests

```bash
cd ~/.claude/skills/bd-to-br-migration   # or ~/.codex/skills/bd-to-br-migration
bash -c '
fail=0
for n in 1 2 3 4 5 6 7 8 9; do
  bash SELF-TEST.md … # see runner script in scripts/
done
'
```

Or manually run each block above.

---

## Cleanup

```bash
rm -f /tmp/test-f{1,2,3,4,5,6,7,8,9}.md /tmp/test-good.md
```
