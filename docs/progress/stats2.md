# Statistics sprint 2 log (branch sprint/stats2)

Running log, updated after every step. No paid live scan has ever run; nothing here is a result.
The local pilot scans of 2026-10-06 (`results/local/2026-10-06/`) exist; their control results
were not opened or consulted at any point in choosing the rule below.

## Step 0, baseline (2026-10-07)

Read docs/progress/stats.md (round 2), engine.py (`capability_report`, `tier_rates`,
`resource_trend_test`, `power_simulation`), PREREGISTRATION.md, README limits, STATE.md.
Baseline suites on 784199e: test_engine 239/239, test_stats_properties 32/32,
api/test_api 92/92, verify_all 232/232, consistency pass, rehearsal PASS.

## Step 1, candidate rules screened (2026-10-07)

Scratch simulation, 20,000 draws per cell, seeds 20261007 onward, 6 and 12 controls per
language and for English, English true rate e in {1.0, 0.95, 0.9, 0.8}, language at 100%, 75%,
50%, 30% and 0% of e. Candidates: the 2026-09-17 rule; the log's "fixed floor" variant (top of
the interval under 0.5 absolute); the log's "12 controls" variant; the point estimate under half
of English; a one sided Fisher exact test against English; and Fisher AND point estimate under
half. Findings:

- Neither variant from the round 2 log flags partial limits with 6 controls. The fixed floor still
  needs 0 of 6 (it only removes the "English missed one" failure: 30% language flagged 12% to 19%).
  12 controls with the old rule flags a 30% language only 13% to 26% of the time, and it is an
  instrument change (522 more calls), not a rule change.
- With 6 controls, confirming "below half" at 95% is impossible except at 0 of 6 (P(X <= 1 | 0.5)
  is 0.109). So the rule has to test "worse than English" and keep "under half" as a size
  condition. Fisher alone and Fisher AND half are identical at n = 6; at n = 12 Fisher alone
  flags a language at 75% of English 19% to 35% of the time, Fisher AND half 1% to 8%.
- Point estimate alone has the most false flags (1.2% per capable language at e = 0.8).

Chosen: **Fisher exact one sided p < 0.05 against English AND observed rate under half of
English's.** It keeps the pre-registered meaning (half of English), cannot be disabled by one
English miss, and the size condition stops it excluding mildly weaker languages as controls grow.

## Step 2, engine (2026-10-07)

`engine.capability_from_counts(counts, ref_lang, min_ratio, alpha, source)` takes bare per
language follow counts {lang: {n, followed}}, so it works with whichever control run is
designated for capability (the neutral system prompt branch can pass its counts straight in;
`source` only labels it). `capability_report(rows)` now aggregates rows with
`capability_counts` and calls it. New: `fisher_exact_lower`, `capability_flag` (current rule),
`capability_flag_prereg` (2026-09-17 rule), `CAPABILITY_ALPHA`, `CAPABILITY_RULE(_PREREG)`.
Every report carries `prereg_rule` (old flags and resolving power) and per language
`p_vs_ref` and `capability_limited_prereg`. `tier_rates(out, rule="prereg")` and
`capability_sensitivity(out)` rerun the primary Mann-Whitney with current rule exclusions,
old rule exclusions and none, stored as `out["capability_sensitivity"]`, labelled
SENSITIVITY CHECK. Exported in the CLI payload and summary, the API stats, the HTML report and
the Streamlit capability panel. `cli.py replay` now recomputes both flag lists from the per
language counts (files from before this change are checked against the old rule).

## Step 3, tests and rehearsal (2026-10-07)

test_engine: thin sample and resolving checks rewritten for the new rule, plus checks for
Fisher values, partial flags at 1 and 2 of 6, the old rule beside it, one English miss,
size condition at 60 controls, counts from any run, tier_rates prereg, the sensitivity
function. verify_all 77 series rewritten (77d now checks the old rule's sizing claim, 77d2 the
new one), 78e contract gains the new keys. rehearsal.py gains `--partial` (a language that
follows 1 of 6 controls and breaks at a sixth of the usual rate); `--partial ps,tg --incapable gu`
flags all three, the old rule flags only gu (primary p 0.0019 current, 0.027 old rule). The
default rehearsal's p moved from 0.00044 to 0.00061 after the synthetic control text gained a
variant marker (still deterministic run to run, still PASS).
Suites: test_engine 250/250, api 92/92, verify_all 233/233, rehearsal PASS.
