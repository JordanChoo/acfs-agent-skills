---
name: agent-mail-ops
description: >-
  Diagnose and recover Agent Mail when agents report "AM is down", MCP Agent
  Mail is disconnected, or local configs drift away from the managed endpoint.
  Use when checking `agent-mail.service`, `127.0.0.1:8765`, rogue
  `mcp-agent-mail serve` processes, or split-brain caused by manual servers.
---

# agent-mail-ops

Use this skill for Agent Mail incidents in the ACFS environment.

## Contract

- Production Agent Mail is the managed user service `agent-mail.service`.
- The production MCP endpoint is `http://127.0.0.1:8765/mcp/`.
- The production mailbox is the default shared archive under `~/.mcp_agent_mail_git_mailbox_repo`.
- Never "fix" AM by launching `mcp-agent-mail serve` or `am serve-http` manually against the production mailbox.
- Never rewrite live MCP configs to a random localhost port unless the user explicitly wants an isolated sandbox.

## Fast triage

Run these first:

```bash
systemctl --user status agent-mail.service --no-pager
ss -ltnp | rg '127\.0\.0\.1:8765|:8765'
curl -fsS http://127.0.0.1:8765/health
ps -ef | rg 'mcp-agent-mail serve|am serve-http' | rg -v rg
```

Then inspect config drift in live or backup MCP config files:

```bash
rg -n '127\.0\.0\.1:[0-9]+/(mcp|api)/' /data/projects /home/ubuntu \
  -g 'settings.local.json' -g '*.mcp.json' -g '*.bak'
```

If the incident is isolated to one harness, or follows shared skill changes, also audit shared skill drift:

```bash
cd ~/src/acfs-agent-skills
bash scripts/audit-drift.sh
```

## Decision rule

- `/health` fails and a rogue `mcp-agent-mail serve` exists: likely split-brain from a manual server.
- `/health` is healthy but agents still complain: likely client config drift or a stale client session.
- `scripts/audit-drift.sh` fails: Claude/Codex skill installation drift exists and one harness may be operating on stale instructions even if AM itself is healthy.
- `am doctor check` warnings immediately after recovery are secondary evidence; direct `/health`, listener checks, and config inspection are more authoritative.

## Safe remediation order

- Do not kill processes or restart services without user approval.
- Preferred order:
  1. Stop the rogue manual server by notifying the owning pane/session or via explicit operator action.
  2. Restore live MCP configs to `http://127.0.0.1:8765/mcp/`.
  3. Restart `agent-mail.service` only if it remains unhealthy after the rogue owner is gone.
  4. If only one harness still behaves incorrectly, run `bash ~/src/acfs-agent-skills/scripts/audit-drift.sh` and normalize shared skill drift before doing more AM surgery.
  5. Recheck `/health`, then have affected agents restart or reopen their client sessions.

## Local evidence paths

Open these when you need authoritative machine-local evidence:

- `/home/ubuntu/.config/systemd/user/agent-mail.service`
- `/home/ubuntu/AM_NEXT_STEPS.md`
- `/data/projects/<project>/.ntm/logs/am-*.log`

## Anti-patterns

- Starting a second Agent Mail server on a random port.
- Pointing project-local MCP configs at that random port.
- Treating `am doctor check` alone as proof that AM is down.
- Ignoring shared skill drift when only Claude or only Codex is affected.
- Editing the managed Agent Mail codebase from a consumer repo without owner approval.
