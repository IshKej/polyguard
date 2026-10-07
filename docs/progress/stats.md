# Statistics sprint log (branch sprint/stats)

Running log, updated after every step. No live scan has ever run; nothing here is a result.

## Step 0, baseline (2026-10-06)

Read PREREGISTRATION.md, the engine statistics, test_stats_properties.py, mutation_check.py,
docs/research/statistics.md and docs/research/resource_measures.csv. No changes yet.
Baseline suites on b29a719: test_engine 168/168, test_stats_properties 24/24, api/test_api 90/90,
verify_all 223/223 (STATE.md still says 221), consistency pass, rehearsal PASS.
mutation_check not yet run on this checkout.
mutation_check baseline: 13/13 killed.

## Step 1, capability exclusion claim (task 3b), checked exactly

Claim in docs/research/statistics.md: with 6 controls the "confirmed capability limited" flag
essentially never fires. Checked with `engine.wilson_ci_cc` directly (no simulation needed,
the rule is deterministic given the counts):

- Upper ends of the continuity corrected interval at n = 6: 0/6 gives 0.4832, 1/6 gives 0.6352.
- The flag needs that upper end below half of English's observed control rate.
  English 6/6 makes the threshold 0.5, so only a language at 0/6 can be flagged.
  English 5/6 or lower makes the threshold 0.4167 or lower, so **no language can ever be flagged**.
- Probability the flag fires = P(English 6/6) x P(language 0/6) = e^6 (1 - v)^6 for true follow
  rates e (English) and v (the language):

| English true rate e | v = 0.0 | v = 0.1 | v = 0.2 | v = 0.3 | v = 0.4 |
|---|---|---|---|---|---|
| 1.00 | 1.000 | 0.531 | 0.262 | 0.118 | 0.047 |
| 0.95 | 0.735 | 0.391 | 0.193 | 0.086 | 0.034 |
| 0.90 | 0.531 | 0.282 | 0.139 | 0.063 | 0.025 |
| 0.80 | 0.262 | 0.139 | 0.069 | 0.031 | 0.012 |

Verdict: **confirmed for partial limits, too strong for total incapacity.** A language the bot
truly cannot operate in (v = 0) is flagged 74% of the time if English follows 95% of benign
requests, and every time if English is perfect. A language at 30% to 40% of English capability,
clearly under the half threshold the rule names, is flagged only 3% to 12% of the time, and never
when English misses a single control. The rule protects against total collapse only, and only
when English is perfect. Documented in README limits and STATE.

Smallest per language control counts where partial limits become confirmable (same rule):
English perfect needs n = 9 to confirm 1 of n, English one miss needs n = 11 (1 of n) and
n = 8 (0 of n).

## Step 2, power_simulation claim (task 3a), reproduced

Claim in the note: `engine.power_simulation`'s minimum detectable gap (MDE) is 13% to 22% too
small (its numbers: 0.076 vs 0.086 and 0.092 vs 0.112). Note that those ratios are "realistic is
13% to 22% LARGER"; stated as "engine is smaller" they would be 12% to 18%. The note also compared
its own trend world, not the engine function itself.

Reproduced with `power_check.py` (new, standard library, seeds 20261007 onward, 1000 scans per
point, 15 attacks per language, gaps 0.04 to 0.20, MDE by linear interpolation at 80% power), in
the engine's own tier step world, with the engine's own `mann_whitney_u` and rejection rule.
"Realistic" uses the note's assumed logit spreads: language 0.5, shared attack 1.0, translation
noise 0.5. Run before the fix (engine had no spread parameter):

| design | high rate | engine as it was | realistic | realistic larger by | engine smaller by |
|---|---|---|---|---|---|
| catalog now, 38 low / 25 high | 0.15 | 0.0759 | 0.0858 | +13.0% | 11.5% |
| catalog now, 38 low / 25 high | 0.30 | 0.0933 | 0.1094 | +17.3% | 14.7% |
| note's design, 35 low / 28 high | 0.15 | 0.0758 | 0.0846 | +11.7% | 10.5% |
| note's design, 35 low / 28 high | 0.30 | 0.0910 | 0.1069 | +17.5% | 14.9% |

Language spread alone (0.5, no attack or noise spread) gave MDEs of 0.0943 and 0.1197 (catalog
design), 24% and 28% above the engine. A zero spread run of the new simulator matched the engine
(0.0775 vs 0.0759, 0.0939 vs 0.0933), so the comparison is like for like.

Verdict: **confirmed in direction, slightly overstated in size.** The engine was optimistic:
its MDE was 10.5% to 14.9% too small against the note's realistic spread (realistic needs a gap
11.7% to 17.5% larger). The note's upper end of 22% did not reproduce in the step world. All of
this depends on spread sizes that are guesses until a live scan estimates them.

Fix: `power_simulation` and `languages_needed` take `lang_sd` (logit scale spread between
languages of one tier, tier expected rate held exactly at p_low / p_high), default
`engine.LANG_SD = 0.5`. `lang_sd=0` reproduces the old model draw for draw. Language spread is
the part that drives the optimism and that more attacks cannot remove.

## Step 3, exploratory trend test (task 1)

- `docs/research/resource_measures.csv` moved to `data/resource_measures.csv`, content unchanged
  but line endings normalised from CRLF to LF (the repo pins LF, so a CRLF hash would not survive
  a clean checkout),
  SHA-256 `110a0aa0cb9c8406276e1487f8b2e001895edab6c2b9b97b027f837c732dd6f3`
  (pinned as `engine.RESOURCE_SHA256`). All 87 catalog languages present. Crawl id for the
  measure used, `cc_share_percent`: **CC-MAIN-2026-39** (single crawl; the file's prior crawl
  column is CC-MAIN-2025-13 and is not used). Only `code`, `cc_share_percent` and `cc_crawl_id`
  are read. The file's Joshi and tier columns are a snapshot from before the 2026-10-05 Joshi
  correction (Gujarati, Norwegian, Kyrgyz still show class 4 / high there); tiers always come
  from `languages_catalog`. Note the research note averaged six crawls; this file and the code
  use CC-MAIN-2026-39 alone.
- `engine.resource_trend_test(rates, share)`: Spearman rho of per-language break rate against
  web share, two sided permutation p, 10,000 shuffles, seed 20261006, add-one. Rows sorted by
  value (share, rate) before the seeded shuffle, so arrival order and language names cannot
  move p. Ties: average ranks doubled and centred are exact integers, so the statistic is an
  exact integer and "at least as extreme" is exact. Descriptive OLS slope per tenfold share.
  Standard library only. Fewer than 5 usable languages returns no test.
- "Capability adjusted" is taken to mean the same per-language rates the primary test uses:
  languages confirmed capability-limited are left out (as in `tier_rates`) and named. The ratio
  adjustment from the note was not used: the note itself measured the per-language ratio as
  biased upward, and adding it would be a new analysis choice.
- `engine.resource_trend(out)` is called in `scan()`, stored as `out["resource_trend_test"]`,
  exported by `cli.py` (payload, summary line, recomputed by `cli.py replay`), by the web API
  (`stats.resource_trend_test`), shown in `report_html.py` and the Streamlit report (live only),
  always labelled EXPLORATORY.
- Tests: 8 new properties in `test_stats_properties.py` (row order, renaming in any order,
  p in [1/(B+1), 1], rank only, strong monotone trend gives rho -1 and the smallest p, flat
  data gives p exactly 1, null rarely significant, exact fraction reference for ties) and unit
  checks in `test_engine.py`. Mutants added to `mutation_check.py`: dropped ties, arrival order,
  no add-one, and power spread ignored. `mutation_check.py` now also copies `data/` into its
  temporary folder, which the statistics read.

## Step 4, proposed capability rule change (NOT made; needs a deviation log row if adopted)

The pre-registered exclusion stays exactly as written. What follows is a proposal for the
student to decide on, before the first live scan, because changing it afterwards would be a
choice made after seeing data.

1. **Keep the per language exclusion, and report its count every time**, expecting zero. Say
   in the report that it only catches total collapse against a perfect English (Step 1 table).
2. **Add a tier level ratio adjusted gap as a labelled sensitivity analysis**, not a new primary:
   (mean low tier break rate / mean low tier control rate) minus the same for the high tier,
   each capped at 1. Pooling controls by tier gives 38 x 6 = 228 low tier controls instead of 6
   per language, so it has real resolving power. The note's own simulation found the tier
   version unbiased when its assumptions hold and the per language version biased upward; it
   under-corrects when attacks are harder to parse than controls, which must be stated beside it.
3. **Optionally compare against a fixed floor instead of half of English's observed rate**, so
   one missed English control cannot disable the rule (today English at 5/6 makes the flag
   impossible). Raising controls to 12 per language would let 0 to 2 of 12 be confirmed against a
   perfect English, at 6 x 87 = 522 more calls per full scan; I would not, given point 2.

Any of these is a change to the analysis plan and needs its own dated deviation row.

## Step 5, documents and suites (task 2 and 4)

- PREREGISTRATION.md: two dated rows appended to the end of the deviation log (2026-10-06),
  table intact, nothing above edited: the exploratory trend analysis (measure, crawl id, file
  SHA-256, primary unchanged, before any live data) and the power model change.
- README limits: capability controls only catch total collapse; web share trend is exploratory.
  Files table gains `power_check.py` and `data/resource_measures.csv`; the stale "29 engine
  functions" became "every public engine function" (there are 40 public ones now).
- verify_all gains 115 (resource table pinned by SHA-256, one crawl, full catalog, hash quoted in
  PREREGISTRATION.md) and 116 (trend labelled exploratory in report, CLI and app).
- Suites after the changes: test_engine 177/177, test_stats_properties 32/32, api/test_api 90/90,
  verify_all 225/225, consistency pass, rehearsal PASS, mutation_check 17/17 killed.
  `cli.py scan --mock` then `cli.py replay` matches on 26 checks including the trend p.
- STATE.md updated (date, sprint note, counts, capability limit, new files).

## Step 6, power check after the fix

`python power_check.py` rerun on the committed script (old engine rows use `lang_sd=0` with the
same seeds as Step 2 and reproduce its numbers exactly). New default (`engine.LANG_SD = 0.5`):

| design | high rate | old engine | realistic | new default | new against realistic |
|---|---|---|---|---|---|
| catalog now, 38 / 25 | 0.15 | 0.0759 | 0.0858 | 0.0937 | +9.3% |
| catalog now, 38 / 25 | 0.30 | 0.0933 | 0.1094 | 0.1190 | +8.7% |
| note's design, 35 / 28 | 0.15 | 0.0758 | 0.0846 | 0.0934 | +10.3% |
| note's design, 35 / 28 | 0.30 | 0.0910 | 0.1069 | 0.1171 | +9.6% |

The new default now errs about 9% to 10% on the cautious side of the note's realistic model
instead of 10% to 15% on the optimistic side. That is the intended direction for a null report;
the value should be re-estimated from the first live scan's between language spread.

## Step 7, final check and commit

Rerun after every document edit: test_engine 177/177, test_stats_properties 32/32,
api/test_api 90/90, verify_all 225/225, consistency pass, rehearsal PASS, mutation_check 17/17.
Committed on sprint/stats, not pushed or merged. `docs/research/` (the source note) was left
untracked, as it arrived.
