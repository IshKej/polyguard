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

## Step 4, the justifying simulation, committed as `capability_check.py` (2026-10-07)

`python capability_check.py`: engine's own `capability_flag` and `capability_flag_prereg`,
20,000 seeded draws per cell (seed 20261007 plus cell index), English and the language with
the same control count, plus an exact enumeration column for the current rule (largest
simulation minus exact difference 0.0054; the script fails above 0.015). 6 controls:

| English true rate | language / English | current rule | exact | 2026-09-17 rule |
|---|---|---|---|---|
| 1.00 | 100% | 0.0000 | 0.0000 | 0.0000 |
| 1.00 | 50% | 0.3437 | 0.3438 | 0.0144 |
| 1.00 | 30% | 0.7470 | 0.7443 | 0.1181 |
| 1.00 | 0% | 1.0000 | 1.0000 | 1.0000 |
| 0.95 | 100% | 0.0001 | 0.0001 | 0.0000 |
| 0.95 | 75% | 0.0454 | 0.0469 | 0.0003 |
| 0.95 | 50% | 0.3176 | 0.3198 | 0.0150 |
| 0.95 | 30% | 0.6805 | 0.6765 | 0.0972 |
| 0.95 | 0% | 0.9978 | 0.9978 | 0.7355 |
| 0.90 | 100% | 0.0008 | 0.0007 | 0.0000 |
| 0.90 | 50% | 0.2910 | 0.2953 | 0.0159 |
| 0.90 | 30% | 0.6148 | 0.6114 | 0.0814 |
| 0.90 | 0% | 0.9841 | 0.9841 | 0.5331 |
| 0.80 | 100% | 0.0052 | 0.0051 | 0.0000 |
| 0.80 | 75% | 0.0635 | 0.0641 | 0.0014 |
| 0.80 | 50% | 0.2415 | 0.2459 | 0.0112 |
| 0.80 | 30% | 0.4929 | 0.4885 | 0.0512 |
| 0.80 | 0% | 0.9016 | 0.9011 | 0.2603 |

Expected false flags across the 86 non-English catalog languages, all fully capable: 0.000,
0.005, 0.060 and 0.438 for English true rates 1.00, 0.95, 0.90, 0.80. A language at 75% of
English (above the half line, so a wrong flag) is flagged 4% to 6%. At 12 controls the size
condition keeps that at 1% to 8% while a 30% language is caught 82% to 89%.

Honest reading: the rule now catches total collapse almost always and a language at 30% of
English most of the time, but a language right at half of English only a quarter to a third of
the time. With 6 controls nothing can do much better without many more false flags.

## Step 5, property tests and mutants (2026-10-07)

test_stats_properties gains 6 capability properties (size condition, monotone in follows,
Fisher p range, superset of the old rule at equal counts, exact null flag rate at most alpha for
random true rates and n from 2 to 15, English never flagged and order or names change nothing):
38/38. mutation_check: the old capability mutant moved to the old rule's new code site, and
three mutants added (Fisher summing the wrong tail, size condition dropped, wrong alpha):
20/20 killed.

## Step 6, documents (2026-10-09)

- The rule is dated 2026-10-09 everywhere in code and documents: that is the day the deviation
  row was written, so a reader looking for the row finds it under the date the code names.
- PREREGISTRATION.md: one row appended at the end of the deviation table (after the 2026-10-07
  pilot row), nothing above edited. States the new rule, the old rule kept as a sensitivity
  check, counts from whichever control run is designated, the simulation numbers, why the log's
  two variants were not taken, and that the local pilot control results were not consulted.
- `capability_check.py` gained a "fixed floor" column so the variant comparison in the row is
  reproducible (at 6 controls, English 95%: 0%, 30%, 50% languages flagged 100%, 13%, 2.1%).
- README: the "six controls" sentence in How it works and the capability limit rewritten with
  the numbers; files table gains `capability_check.py`.
- STATE.md: date, a 2026-10-09 sprint note, the decision entry, suite counts (250, 233, 38, 20)
  and the new script.

Suites: test_engine 250/250, test_stats_properties 38/38, api/test_api 92/92, verify_all
233/233, consistency pass, rehearsal PASS (default and `--partial ps,tg --incapable gu`).
mutation_check: first rerun crashed with a Windows paging file error (out of memory, not a
test result); rerunning.
