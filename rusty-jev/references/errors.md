# Rusty Jev errors

## Shape

A failed tool call is a normal JSON-RPC result (HTTP 200) with `isError: true` and no
`structuredContent`. Parse the text block:

```json
{"error": {"code": "upstream_rate_limited", "message": "The provider is rate limiting; try again later.", "retry_after_s": 30}}
```

- `message` is fixed per code and never contains provider text or your input.
- `retry_after_s` (whole seconds) appears only on `rate_limited` and `upstream_rate_limited`.
- `field` may appear on `invalid_input`: a path such as `items[3]`, `claims`, `top_k` or
  `caller`. A problem inside `questions` or `categories` is reported as just that name, or with
  no `field` at all (for example an unknown key inside a question's `criteria`).
- Error results carry no `usage`, even when the call was billed. Track billed failures yourself.

## Codes

"Charged" means the provider was paid for the attempt, and its cost counts against the daily cap.

| Code | Message | Charged | What to do |
| --- | --- | --- | --- |
| `invalid_input` | The request did not match the tool's schema. | No | Fix the input. No `field` means: unknown or missing field, wrong JSON type, duplicate key, the 90 KB text total, the 128 KB body, `classify` items × categories over 8,000, or the provider refusing the request as too large |
| `unknown_model` | That model is not available. | No | Use `jev`, `jev-latest` or `jev-1.13` exactly, or leave `model` out |
| `provider_not_configured` | No decision provider is configured. | No | Server configuration. `list_models` shows `provider: "none"`. Report it |
| `rate_limited` | Too many requests; try again later. | No | Wait `retry_after_s` (60). Put more items in each call. 300 calls a minute in all, 60 per `caller` label |
| `daily_cap_reached` | The daily spending cap has been reached. | No | Stop paid calls. It resets at 00:00 UTC. A smaller call may still fit. Tell the operator |
| `service_unavailable` | The decision service is temporarily unavailable; try again later. | No | Rate limiter or spend ledger unreachable, or a bad server setting (price, timeout, cap). Retry once after a pause; if it repeats, it is configuration. Report it. Never paid, though a lost ledger reply can leave a reservation counted against the day's cap |
| `upstream_rate_limited` | The provider is rate limiting; try again later. | No | Wait `retry_after_s` (about a minute if it is absent), then retry once |
| `upstream_rejected` | The provider rejected the request. | No | Do not retry unchanged: a key, billing, or provider-limit problem (for example too many options). Report it |
| `upstream_unavailable` | The provider is unavailable. | Maybe | Covers provider 5xx (not charged) and a dropped connection or redirect (charged in full). You cannot tell which, so retry at most once, later |
| `upstream_timeout` | The provider did not answer in time. | Yes | The default deadline is 10 s. Make the request smaller (fewer items, shorter text) before retrying |
| `invalid_provider_answer` | The provider's answer failed validation. | Yes | The model's answer broke a rule (bad probabilities, missing answer). Retry at most once; if it repeats, report it with the time |

The other seven codes (`invalid_batch`, `batch_over_budget`, `too_many_active_batches`,
`batch_not_found`, `batch_cancelled`, `interrupted`, `not_processed`) belong to the bulk tools,
which are not published yet.

## Protocol-level errors

These come back as a JSON-RPC `error`, not a tool result. Each still uses a slot of the global
rate limit when it is a `tools/call`.

| Code | Message | HTTP | Cause |
| --- | --- | --- | --- |
| `-32602` | Unknown tool | 200 | The tool name is not published (for example a bulk tool, or a name still carrying the portal or client prefix) |
| `-32602` | Invalid params | 200 | No `params`; `name` missing or not a string; `arguments` `null` or not an object (a missing `arguments` is treated as `{}`, so `list_models` succeeds and other tools give `invalid_input`); a duplicated `params` or `arguments` key; `initialize` without `protocolVersion` |
| `-32601` | Method not found | 200 | An unknown JSON-RPC method |
| `-32600` | Unsupported protocol version | 400 | An `MCP-Protocol-Version` header other than `2025-11-25` (a missing header is accepted, and `initialize` is not checked) |
| `-32600` | Invalid Request | 400 | A malformed JSON-RPC envelope or a batch array |
| `-32700` | Parse error | 400 | The body is not valid JSON |

A body over 4 MB never reaches JSON-RPC: it gets HTTP 413 with `{"error":"payload_too_large"}`.
Between 128 KB and 4 MB it is a tool error, `invalid_input` with no `field`.

The Worker answers HTTP 401 `{"error":"unauthorized"}` when the portal's gateway bearer is
missing or wrong: a portal configuration problem, not yours to fix. Access login or service
token failures are answered by the portal itself, before the Worker. Never retry either; report
it or fix your credentials.

## Retry policy in one line

After `rate_limited`, wait the full `retry_after_s` (60), then retry. After
`upstream_rate_limited`, wait `retry_after_s` (about a minute if absent), then retry once. Neither
failed call cost anything. After `service_unavailable`, retry once after a pause. After
`upstream_unavailable`, `upstream_timeout` or `invalid_provider_answer`, retry once in total,
smaller in the timeout case (splitting into two smaller calls counts as that one retry), knowing
the failed attempt may have been billed and the retry will be. Never retry `invalid_input`, `unknown_model`, `upstream_rejected`,
`provider_not_configured` or `daily_cap_reached` without changing something first.
