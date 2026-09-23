---
name: langfuse-evals
description: >-
  How to build, run, and review LLM prompt testing & evals on a self-hosted Langfuse. Use
  whenever the task involves Langfuse, prompt experiments, datasets, LLM-as-a-judge, offline
  regression evals, online/production evals, agent/RAG evaluation, scores, prompt management or
  prompt optimization, `run_experiment`/`dataset.run_experiment`, `create_score`, dataset runs,
  Evaluation Rules, or gating CI on eval regressions — in Python or TypeScript. Encodes the
  agreed approach: Langfuse is the control plane; run the pipeline over the API/SDK (the official
  project MCP is an optional read/write interactive surface); configure
  prompts/datasets/evaluators/experiments IN Langfuse for UI<->code parity; keep it evergreen.
  Reference implementation: github.com/JordanChoo/csv-langfuse (see its AGENTS.md).
---

# langfuse-evals

Operating guide for prompt experimentation, testing, and evals on **self-hosted Langfuse** (v4, OpenTelemetry-based; ClickHouse-owned, MIT-core). Follow these defaults unless the user overrides them.

## Mental model (get this right)

Langfuse is a **database + UI + two server-side workers**. Your code is a **client** that reads inputs from it and writes outputs back over the **API/SDK**. "Runs in your code" and "stored in Langfuse" are both true.

- **Langfuse executes:** managed **LLM-as-a-judge** evaluators + **online eval rules** + dashboards.
- **Your code executes:** the experiment **task** (your prompt/app on each item) + **code-only evaluators** (deterministic, library, agent-structural). Their scores still persist into Langfuse.
- **You (agent) are the author/operator:** write + run that code, read results back, iterate. The **pipeline** (OTel tracing, `run_experiment`, CI) runs on the **API/SDK**. Langfuse **also** ships an official **project MCP** (`<LANGFUSE_HOST>/api/public/mcp`, `streamableHttp`, `Basic base64(pk:sk)`, ~120 **read/write** tools: prompts, traces, datasets, scores, evaluators, rules, metrics, dashboards) — an optional interactive surface; restrict to reads via a client allowlist. It doesn't ingest OTel traces or run experiment loops — keep those on the SDK.

## Locked defaults

1. **Self-hosted Langfuse v4** — treat it as a **remote endpoint** (set `LANGFUSE_HOST`). Hosting is typically a **managed provider (e.g. Elestio)** or K8s/Helm; local Docker-Compose only for a throwaway dev instance. On a managed host there is **no infra to run**.
2. **Both SDKs** — Python primary (`langfuse>=4,<5`), TypeScript secondary (`@langfuse/*` v5). Everything is OpenTelemetry.
3. **Configure prompts, datasets, evaluators, experiments IN Langfuse** so UI and code edit the same objects (parity via the Evaluators / Evaluation Rules API, Prompt CMS, Datasets API).
4. **Managed evaluators = LLM-as-judge only.** Deterministic / library (Ragas, DeepEval) / agent-structural checks run in code and write scores into the **same** runs.
5. **Evergreen:** config-driven thresholds (`eval.config.yaml`), pinned SDK majors, one `lf_client` init module, versioned datasets, CI-gated PRs, and an **export-to-git** of Langfuse config.
6. **Prompt "optimization" is a loop you run, not a Langfuse feature** — propose variant → `run_experiment` → compare scores → promote winner. Great for agents to drive.

## Prerequisites

- Env: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (v4 also `LANGFUSE_BASE_URL` — keep in sync).
- **Self-host must have an LLM Connection** configured in Project Settings (judge/playground model, e.g. `claude-sonnet-5` / `claude-opus-5` / `gpt-4o`) or managed judges, Prompt Experiments, and the Playground won't run.

## The core loop (identical from UI or code)

1. Prompt in the **Prompt CMS** (versions + labels; `production` = deployed). 2. Configure a managed **LLM-judge** evaluator. 3. Curate a **dataset** (versioned). 4. Run a **Prompt Experiment** (prompt × dataset × judge) → a **Dataset Run** with scores (UI **or** `run_experiment`). 5. Compare runs (baseline vs variant). 6. Iterate the prompt (UI edit or agent writes a new version via API), re-run, compare.

## Canonical code

**Python (v4):**
```python
from langfuse import get_client, Evaluation, RegressionError
lf = get_client()

def task(*, item, **kwargs):                     # item.input on a Langfuse dataset
    prompt = lf.get_prompt("keyword-classifier", label="production")   # lives in Langfuse
    from langfuse.openai import openai            # drop-in auto-traces; Claude => OTel instrumentor
    r = openai.chat.completions.create(model=(prompt.config or {}).get("model","gpt-4o"),
        messages=[{"role":"system","content":prompt.compile(keyword=item.input)}], langfuse_prompt=prompt)
    return r.choices[0].message.content.strip()

def exact_match(*, output, expected_output, **kwargs):
    return Evaluation(name="exact_match", value=float(str(expected_output).lower()==str(output).lower()))

result = lf.get_dataset("evaluation/keywords").run_experiment(   # writes DatasetRun+traces+scores to Langfuse
    name=f"keywords @ {GIT_SHA}", task=task, evaluators=[exact_match])
print(result.format())
lf.flush()                                       # REQUIRED in short-lived/CI processes
```

**TypeScript (v5):** `LangfuseSpanProcessor` in `instrumentation.ts` (imported first) → `LangfuseClient` → `langfuse.experiment.run({ name, data|dataset, task, evaluators })` / `dataset.runExperiment(...)`; `observeOpenAI(new OpenAI())`; `await otelSdk.shutdown()` to flush.

**Score anything from code:** `lf.create_score(name=..., value=..., trace_id=..., data_type="NUMERIC")`.

## The four eval modes
- **Offline regression** — `run_experiment`/`dataset.run_experiment` + evaluators; compare runs; gate CI.
- **LLM-as-judge** — managed templates (correctness, relevance, hallucination, helpfulness, conciseness, context-relevance) in the UI/Evaluators API, or a custom judge fn in code.
- **Online/production** — an Evaluation Rule with filters + sampling on live traces; user-feedback scores from `@langfuse/browser`; or an external cron pipeline (`api.observations.get_many` → eval → `create_score`).
- **Agent/RAG** — span per tool call + retrieval; Ragas (faithfulness, context precision/recall); tool-call-correctness code checks.

## CI gating
`langfuse/experiment-action` (script exports `experiment(context)`; `should_fail_on_regression: true`) **or** pytest/vitest that raises **`RegressionError`** below threshold. Tag runs with `release=<git-sha>` + dataset/evaluator versions.

## Do / Don't
- **Do:** put prompts/datasets/evaluators/experiments in Langfuse; reach them via API/SDK; keep UI↔code parity; write code-only evaluators that score into the same runs; export config to git; CI-gate PRs.
- **Don't:** route the pipeline (OTel trace ingestion, experiment task loops, CI gates) through MCP — those stay on the SDK; rely on UI-only config with no git export; use v2 SDK APIs (`langfuse_context`, `Langfuse().trace()`); forget `flush()`/`shutdown()`; hardcode keys/host/thresholds; build a parallel eval store.

## Gotchas
- v4 + OTel APIs (`get_client`, `@observe`, `start_as_current_*`); v2 is legacy. Anthropic/Claude = OTel instrumentation (no drop-in). `LANGFUSE_HOST`↔`LANGFUSE_BASE_URL` renamed in v4 (both work). Real-time ingestion needs `x-langfuse-ingestion-version: 4`. Promptfoo only pulls prompts (no score push-back). EE-only: project RBAC, audit logs, SCIM, retention, masking. Official **project MCP** = `<host>/api/public/mcp` (read/write, `Basic base64(pk:sk)`; full tool list at `mcp.reference.langfuse.com`); community `avivsinai/langfuse-mcp` now largely superseded.

## Reference implementation
`github.com/JordanChoo/csv-langfuse` — full scaffold (infra compose, `lf_client` py+ts, evaluators, dataset sync/export, `run_experiment` CI gate, GitHub Action) and its `AGENTS.md`. Mirror that structure for new eval projects.
