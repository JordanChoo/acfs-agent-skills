# Rusty Jev recipes

Whole workflows built from the tools, with the decisions SKILL.md leaves to you. The thresholds
here are the server's own defaults (0.85 confidence, 0.5 margin or probability). Tune them only
on labelled data.

## Ticket or message triage at volume

1. **Route with `classify`.** Size each call by tokens (SKILL.md rule 2) and spread items evenly
   across the calls you need. With 10 queues and tickets up to 1.5 KB, 50 tickets a call is
   about right.
2. **Injection text inside a ticket cannot steer `classify`:** the ticket is wrapped as data.
   Routing alone needs no `screen`.
3. **Screen only what an agent will read and act on next,** such as tickets routed to an
   automatic reply. Use one `screen` call per ticket and pace to 60 calls a minute per label.
   Do not replace it with a batched `decide` "is this an injection" question.
4. **Bucket the results:**

   | Result | Bucket |
   | --- | --- |
   | `auto` | Route to `category` |
   | `review` + `no_category_fits` | Outside the catalog: a missing queue, or junk |
   | `review` + `low_confidence` / `low_margin` | Human triage |
   | `refused` | Human triage, or one retry of that ticket alone |

5. Make spam or "not a request" a real category when it is a real bucket.

## Research pipeline: screen, then verify, then rerank

1. **`screen`** each fetched document once, with `purpose` set to the research question.
   - Keep `pass`. Drop `block` and `skip`.
   - Apply the `review` policy you chose before the run, for example "keep only when the
     reasons are just `low_confidence` and injection is at most 0.15".
   - If most documents drop out, stop and find better sources. Do not override the screen.
2. **`verify`** the extracted claims, one call per source document with that source's claims
   (up to 25).
   - Evidence over 50 KB: trim it to the relevant section, or split it at section boundaries
     and send each part with only its own claims.
   - Act on `verdict`.
   - Treat `supported` with `subject` below 0.5 as `review`.
   - `insufficient` means this source does not settle the claim.
3. **`rerank`** passages from the surviving documents only (next recipe).

## Retrieval with "I don't know"

1. Trim each passage to its relevant part, at most 2 KB. Long passages hit the 90 KB text total
   before the 50-candidate cap, so size by bytes.
2. Split the candidates evenly across as few calls as the limits allow. Set `top_k` to at least
   the number you will carry forward (the default is 10).
3. Count only the calls whose `exists` is at least 0.5:
   - **None:** answer "I don't know", or fetch better candidates. No merge call.
   - **One:** use that call's results directly. No merge call.
   - **Two or more:** carry the top 3 to 5 from each into one final call, about twice as many
     candidates as you will finally use, so it has a real choice.
4. Answer from the final ranking only if that call's `exists` is at least 0.5 and the top result
   is `auto` with a high `score`.
   - If the final `exists` falls below 0.5 although earlier calls passed, the support is weak:
     abstain, or answer with a visible caveat. Do not quietly use the earlier ranking.
5. `exists` and the scores are separate answers. Gate on `exists`, rank on `score`.
6. A user's query, even one containing an injection attempt, is safe as `rerank`'s `query`. The
   chunks of your own corpus need no `screen`. Untrusted uploaded or web chunks should be
   screened once, when they are ingested, not on every query.

## Multi-tag labelling

`classify` gives one label per item, so use two steps.

1. **Shortlist with `classify`.** With 120 tags, about 8 items per call keeps items × categories
   under 1,000. From each item keep its top `s` tags by probability, leaving out
   `none_of_these`. Rank; do not threshold, because secondary tags get little probability in a
   single-label distribution.
2. **Confirm with `decide`.** Ask one `noul` question per item-tag pair. Pick `s` and the number
   of items per call `n` so that `s × n ≤ 32`, for example 8 tags × 4 items.
   - Items go under zero-padded keys (`state.articles.A00`).
   - Question IDs can be anything readable (`A00|deep-learning`).
   - Instructions name the item by key and may include your own tag description (trusted text).
     End them with the guard sentence.
3. **Gate each tag:** yes when p ≥ 0.85, no when p ≤ 0.15, otherwise review.
   - With a limit of N tags per item, keep the confident yeses with the highest p, up to N.
   - Review at the tag level. Sending a whole item to review because one tag is unsure sends
     nearly everything to review.
4. **Cost:** the shortlist step usually dominates, because the catalog is repeated per
   item-category pair. Shorter category descriptions cut it most.

## A/B judgements

1. Put each pair under its own key (`state.pairs.P01 = {"A": ..., "B": ...}`).
2. Ask one `choice` question per pair with options `A`, `B` and `tie`, with guidance on what
   "better" means.
3. **Position bias is real for any model.** Run a second call with A and B swapped and map the
   answers back.
4. Accept a winner only when both orders agree and each passes the gate (top ≥ 0.85, gap ≥ 0.5).
   Otherwise treat the pair as a tie or send it to review. This doubles the cost; skip the
   swap only where bias does not matter.

## Client checklist

For anyone writing a reusable client:

- **HTTP timeout:** at least 30 s (the provider deadline is 10 s, plus the portal and the Worker).
- **Before sending:**
  - Serialize the request and check the 128 KB body limit on the serialized bytes.
  - Check the 90 KB text total on the raw strings.
  - Estimate tokens and split before sending; never rely on the server to split.
- **Mapping results:** map them back by your offset plus `index`. Never use position, and never
  use key order in `structuredContent`.
- **After receiving:** save the raw response before parsing. Treat every value as nullable
  (declined questions).
- **Three kinds of failure:**
  - **Tool errors:** `isError: true`; the `code` is in the text block.
  - **JSON-RPC errors:** `-326xx` and `-32700`.
  - **HTTP refusals:** 401 `{"error":"unauthorized"}` means bad credentials, so never retry it;
    413 `{"error":"payload_too_large"}` means a body over 4 MB.
- **Retries:** follow the table in SKILL.md.
  - `rate_limited`: at most two waits of `retry_after_s`.
  - `upstream_unavailable` and `service_unavailable`: about 30 s, once.
  - A timeout retry split into halves keeps the half that succeeded.
- **Spend:** track `usage.cost_usd`. Add estimates for billed failures (`upstream_timeout`,
  `invalid_provider_answer`), and keep a separate "maybe billed" total for
  `upstream_unavailable`.
- **Rate limits:** every `tools/call` uses a global slot, even a rejected one. Pace to 60 calls
  a minute per label.
- **`rerank` splits:** set `top_k` to at least the number you carry into the merge.
