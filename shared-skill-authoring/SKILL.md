---
name: shared-skill-authoring
description: >-
  Create or update shared skills for both Claude and Codex from the canonical
  repo at `~/src/acfs-agent-skills`. Use when adding a new skill, editing an
  existing skill, fixing skill drift, or installing skills across both
  harnesses without editing `~/.claude/skills` or `~/.codex/skills` directly.
---

# shared-skill-authoring

Use this skill when working on the cross-harness skill library in `~/src/acfs-agent-skills`.

## Contract

- `~/src/acfs-agent-skills` is the only source of truth.
- `~/.claude/skills/*` and `~/.codex/skills/*` should be symlinks into that repo.
- Never create or edit skills directly inside the harness-specific directories.
- Exception: skills listed in `scripts/tool-managed.txt` (currently `rch`, `pfr`, `pi-agent-rust`) are owned by their tool's installer and live in the harness dirs as real directories. Never symlink or edit them there; refresh the repo's reference snapshot from the harness copy instead (`cp -R ~/.codex/skills/rch/. rch/`).

## Workflow

1. Audit current state before editing:

```bash
cd ~/src/acfs-agent-skills
bash scripts/audit-drift.sh
```

2. Edit only in the canonical repo:

- New skill: create `<skill-name>/SKILL.md`
- Optional: add `references/`, `scripts/`, and `scripts/self-test.sh`
- Update [SKILLS-CATALOG.md](/home/ubuntu/src/acfs-agent-skills/SKILLS-CATALOG.md) when adding a new skill

3. Validate the specific skill:

```bash
bash scripts/test-all.sh --skill <skill-name>
```

4. Install through the shared installer, not by copying files manually:

```bash
bash scripts/install.sh
```

5. Re-audit after install:

```bash
bash scripts/audit-drift.sh
```

## If install fails

- A real directory under `~/.claude/skills` or `~/.codex/skills` means drift.
- If the real directory matches the canonical repo, back it up, replace it with the canonical symlink, then rerun `scripts/install.sh`.
- If it differs, inspect and preserve the local-only content before normalizing.
- If the real directory belongs to a tool that reinstalls its own skill (the ACFS nightly log shows `Installing <tool> skill`, or the files carry a fresh ~04:1x mtime), do NOT `--force` it — the next run would clobber the symlink. Add the name to `scripts/tool-managed.txt`, refresh the canonical snapshot from the harness copy, and rerun `scripts/install.sh`. One blocked skill no longer aborts the whole install.

## Anti-patterns

- Editing one harness only
- Creating skills directly under `~/.claude/skills` or `~/.codex/skills`
- Skipping `scripts/audit-drift.sh`
- Adding a skill without updating the shared catalog
