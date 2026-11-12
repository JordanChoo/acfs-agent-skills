---
name: process-triage
description: >-
  Triage system processes with the `pt` wrapper and choose safe remediation.
  Use when diagnosing runaway processes, comparing `pt scan` and `pt deep-scan`,
  or using `pt agent` plan/apply workflows.
---

# process-triage

Use `pt` as the user-facing command and `pt help` for wrapper-aware help.

Core workflows (write JSON to a file, then read the file):
- `pt scan --format json > pt-scan.json`
- `pt deep-scan --format json > pt-deep-scan.json`
- `pt agent plan`
- `pt agent explain`
- `pt agent apply`

Output handling:
- Do not truncate `pt` output with `head`, `tail`, or a similar cutoff
  consumer: a partial JSON document is unparseable, and `pt-core` 2.1.0 and
  earlier abort with SIGABRT when stdout closes mid-write.
- Agent harnesses already truncate tool logs, so redirect to a file and
  query it (for example with `jq`) instead of paging the stream.

Safety:
- Never kill automatically without explicit user approval
- Prefer `pt agent` over legacy `pt robot`
- Use structured output for agent automation
