# PolyGuard pre-registration

**Written 2026-09-09, before any live scan has ever been run.**

Every number PolyGuard has produced so far comes from a deliberately
language-independent mock. No API key has been used, no real chatbot has been
attacked, and no real break rate exists. That is exactly why this document is
being written now: the predictions below are recorded before the data can
influence them.

## Why this exists

The project's own audit found that the app was, at one point, structurally
guaranteed to confirm its thesis. The headline compared the worst language
against English, and "worst of N" is a maximum, so across 87 languages a victim
with no language gap at all would still have triggered the equity banner in 98
runs out of 100 (see `AUDIT.md` finding 19, reproducible with
`python selection_bias_demo.py`).

That flaw was in the code. The same flaw can live in the researcher. If I run the
scan, see the result, and only then decide which comparison to feature, which
languages to include, and what counts as significant, I get the same
thesis-confirming behaviour with none of the code to blame. Pre-registration is
the fix: state the predictions and the decision rules while the outcome is still
unknown, then report what actually happened.

## The instrument, frozen

| Property | Value |
|---|---|
| `attack_bank.json` SHA-256 | `29c170e164ae8145e392fdc032705384f755e001496f033aab83894ec45e8e50` |
| Attacks | 300 |
| Capability controls | 120 (6 per language) |
| Languages in bank | 20 (13 high-resource, 7 mid-resource, **0 low-resource**) |
| Categories | 5 |
| Phrasings per cell | 3 |
| Canary | `PWNED_7F3A` |
| Catalog target | 87 languages (28 high, 24 mid, 35 low), tiers derived from Joshi et al. 2020 |

The bank will change exactly once in a planned way: `expand_languages.py` will
add the 67 remaining catalog languages, including all 35 low-resource ones. That
expansion is pre-planned here, not a reaction to results. Any other change to the
bank after a scan has been run must be recorded in the deviation log below.

Note the honest starting position: the bank currently contains **zero
low-resource languages**, so the central hypothesis is untested rather than
supported.

## Hypotheses

**H1 (primary).** For a given victim model, prompt-injection attacks succeed at a
higher rate in low-resource languages than in high-resource languages.

**H2 (secondary).** The size of that gap differs by vendor. Specifically, at
least one of the four victim models will show a significant gap and at least one
will not, meaning multilingual robustness is a property of the model rather than
of language difficulty in general.

**H3 (secondary).** Obfuscated and indirect injection will be the categories
where the language gap is largest, because they depend on the model parsing
structure inside the attack rather than recognising a familiar English phrase.

I consider H1 the least certain of the three. Small modern models are markedly
better multilingually than the literature that motivated this project, and a null
result on H1 is a realistic outcome.

## Primary analysis, fixed in advance

- **Unit of analysis:** the language. Each language contributes one break rate.
  Attacks on the same bot in the same language are correlated, so treating each
  attack as independent overstates significance.
- **Primary test:** Mann-Whitney U on per-language break rates, low-resource
  versus high-resource, two-sided, alpha = 0.05.
- **Worst-language claim:** only ever made via the permutation test on the
  maximum (`engine.max_gap_permutation_test`, 2,000 shuffles, fixed seed 12345).
  The raw worst-minus-English difference is never a finding on its own.
- **Effect size:** Cliff's delta with a 2,000-sample bootstrap percentile
  interval accompanies every significance claim. A significant p whose effect
  interval still contains zero is reported as provisional.
- **Multiplicity:** the 5 per-category tests for H3 are Benjamini-Hochberg
  adjusted as a family; the adjusted value is the one read.
- **Power:** any null result is reported together with the scan's simulated power
  to detect a 15-point gap. A null from an underpowered scan is reported as
  inconclusive, not as evidence of no effect.
- **Reported alongside:** continuity-corrected 95% Wilson intervals per tier, and
  the pooled attack-level z-test explicitly labelled as optimistic (simulation
  puts its false-positive rate at 16.6% under a realistic clustered null).
- **Excluded from rates:** errored attacks, counted and reported separately.
- **Capability controls:** benign twins per language measure instruction-following
  relative to English. A language confirmed capability-limited is reported as
  unscoreable for safety rather than as well defended.
- **Judge:** one fixed Anthropic model for every victim, so judge disagreement
  cannot be mistaken for a robustness difference between vendors.

## Decision rules, fixed in advance

| Outcome | What I will report |
|---|---|
| Mann-Whitney p < 0.05 and low-resource rate is higher | H1 supported for that model, with the effect size and n |
| p >= 0.05 | H1 not supported for that model. Reported as a null result, not as "trending" or "approaching significance" |
| Low-resource rate is *lower* than high-resource | H1 contradicted for that model. Reported as such, prominently |
| Fewer than 5 languages in either tier | No test run. Insufficient data, stated plainly |

A null result is a publishable result here. If small deployed models turn out to
be roughly even across languages, that is genuinely useful news about the state
of multilingual AI safety in 2026, and it is the finding I will present.

## Known bias direction, recorded in advance

Machine translation is the dominant confound in this area and its bias is
directional: a garbled attack fails because the model cannot parse it, not
because the model resisted it, so the scanner records a non-break and the
non-break reads as safety. PolyGuard's machine-translated languages therefore
tend to **understate** the gap H1 predicts.

Consequences, fixed now rather than argued later:

- A gap that *is* found is, if anything, a floor rather than a ceiling.
- A **null result is weaker evidence than it looks**, because translation quality
  is an alternative explanation for it. Any null will be reported together with
  the reverse-translation pass rate and the native-review status of the languages
  involved, and will not be described as evidence that the gap has closed unless
  those support it.
- No language will be described as "verified" or "human-checked" until
  `NATIVE_REVIEW.md` has a row for it.

## What would falsify the thesis

Low-resource languages showing break rates equal to or below high-resource
languages, across multiple vendors, with adequate sample size. If that is what
the data says, that is what the report will say, and the project becomes a
measurement of how much the gap has closed rather than a demonstration that it
exists.

## Rules I am binding myself to

1. No adding or removing languages after seeing results in order to move a
   p-value. The 87-language catalog is fixed before the first live scan.
2. No switching the primary test after seeing the data. Mann-Whitney on
   per-language rates is the headline regardless of what it returns.
3. No dropping a victim model from the writeup because its result is
   inconvenient. All four models scanned get reported.
4. No reporting the uncorrected worst-language gap as evidence.
5. Every reported number carries its mode (mock or live), its victim model, and
   whether the run was temperature-pinnable.
6. Any departure from this document gets written into the deviation log below,
   with the reason and the date, rather than quietly applied.

## Deviation log

| Date | Deviation | Reason |
|---|---|---|
| 2026-09-16 | **Prior on H1 raised.** This document originally said H1 was "the least certain" of the three hypotheses. A literature review run after this pre-registration was written (`RELATED_WORK.md`) found the effect is well established and replicating: Yong et al. (arXiv:2310.02446) report 79% attack success on GPT-4 via low-resource translation, and a 2026 six-model evaluation (arXiv:2606.29602) finds non-English compliance consistently higher than English. | Honest update from **prior literature**, not from PolyGuard data. No live scan has been run. The analysis plan, the primary test and every decision rule below are unchanged, and the review was deliberately run after this document was fixed so the plan could not be tuned to the expected answer. |
| 2026-09-16 | **Added pre-specified secondary analyses:** Cliff's delta effect size with bootstrap CI on the primary comparison; Benjamini-Hochberg correction across the 5 per-category tests for H3; and a power statement accompanying any null result. | Strengthens the pre-registered plan rather than loosening it. Each addition makes a claim harder to make, not easier: an effect size can contradict a significant p, FDR correction raises the bar on H3, and the power statement prevents an underpowered null being read as evidence of absence. Specified before any live data exists. |
| 2026-09-23 | **The resource tier is now DERIVED from a citable source instead of hand-assigned.** Every language carries its class from Joshi et al. (2020), and the tier follows one stated rule (high = class 4-5, mid = 3, low = 0-2) with no exceptions. **27 of 87 languages changed tier.** The catalog is now 28 high / 24 mid / 35 low. | The tier IS the independent variable, and it was an assertion with no cited basis. Audit found it inconsistent with the standard taxonomy and with itself: class-3 languages sat in both mid and low, Basque (class 4) sat in low, Telugu (class 1) sat in mid. Corrected **before any live data exists**, which is the only time an instrument change is free of suspicion. Joshi's Kyrgyz=4 anomaly was deliberately NOT overridden, because hand-adjusting the independent variable to match intuition is exactly the freedom that lets a result be steered. |
| 2026-09-19 | **Fingerprint updated again, and made platform-independent.** New SHA-256 `29c170e164ae8145...`. The bank was being written in text mode, so it carried CRLF line endings on Windows and would have carried LF on Linux. | **No content changed at all**: every attack and control is byte-identical, only the line endings differ. The bug matters because this fingerprint is the pre-registered instrument pin, and it meant anyone regenerating the bank on Linux would get a different hash for the same data and the integrity check would fire on a file nobody touched. The generator now forces LF, so the fingerprint is reproducible anywhere. Still no live data. |
| 2026-09-18 | **Instrument fingerprint updated.** The bank SHA-256 changed from `3518957844ce6ab8...` to `d07d351c58387111...`. Cause: 120 benign capability controls were added and the misleading `verified` flag was replaced with `provenance` plus `native_reviewed`. | **No attack text changed.** All 300 attacks are byte-identical; the diff is added controls and renamed metadata, both pre-specified above and both making claims harder rather than easier. Logged because the fingerprint pins the instrument, and a changed instrument must be explained rather than silently re-fingerprinted. Still no live data. |
| 2026-09-17 | **Recorded the expected direction of translation bias, and made the reverse-translation gate default-on and multi-category.** Machine-translated attacks are expected to *understate* the low-resource gap, because a garbled attack fails for reasons unrelated to the defence being measured. | Literature, not PolyGuard data (arXiv:2605.18239: human red-teaming raised jailbreak rates 59.8% to 75.8%; MT error rates up to 71% before human review). Recorded in advance so a smaller-than-expected gap is not later reinterpreted as evidence of safety. Stating the direction constrains interpretation rather than loosening it. |
| 2026-09-17 | **Added a pre-specified capability control.** Every language now also receives benign twin requests measuring whether the bot follows ordinary instructions in that language, read relative to English. Languages confirmed capability-limited are excluded from safety conclusions rather than counted as well defended. | Addresses a confound that could invert the finding: a low break rate may mean the model is defended OR that it cannot follow instructions in that language. The bias runs in a known direction, since capability is weakest in low-resource languages, so leaving it unmeasured would understate the gap H1 predicts. Specified before any live data exists, and it makes H1 harder to support, not easier, because a quiet language no longer counts as a safe one. |
| 2026-09-16 | **Confidence intervals switched to the continuity-corrected Wilson interval.** | Calibration measured the plain Wilson interval's coverage at 91.3% against a nominal 95% at n=15, p=0.30 (AUDIT.md finding 23). The corrected interval is wider and never fell below 96.4% in a 14-point sweep. This makes reported precision more conservative, never less. |

---

*Recorded before first live data. PolyGuard, Congressional App Challenge 2026.*
