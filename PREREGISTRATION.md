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
| `attack_bank.json` SHA-256 | `4e2ba320c932823e046d2113af44ee2ca5e4042cf3d75f1ea8abd15117cdf1f8` since 2026-10-05 (73 languages). Before that: `3d665ef61a4a9dde8cc125e1c9fdb4561621db2e7cf9b7b1d60ca6e95993dff9` (2026-10-04 to 2026-10-05), `d8dfa081e70db57bdf5197e1680879182b663a1c50c916cb3131d6bae2d6ef07` (2026-10-02 to 2026-10-04) and `61050c90b9645d0a613407a7020d397a6940a771f1debbff310737c6b6bb32de`. Every change is in the deviation log. |
| Attacks | 1095 (was 300 until 2026-10-05) |
| Capability controls | 438, 6 per language (was 120) |
| Languages in bank | 73 since 2026-10-05: 25 high-resource, 24 mid-resource, 24 low-resource; 20 author written and 53 machine translated. Before that 20 (15 high, 4 mid, 1 low, Gujarati), corrected 2026-10-05 from 16 / 4 / 0 by the Joshi class fix in the deviation log. Corrected 2026-10-02: this row said 13 high and 7 mid, the hand-assigned split from before the 2026-09-23 re-tiering. |
| Categories | 5 |
| Phrasings per cell | 3 |
| Canary | `PWNED_7F3A` |
| Catalog target | 87 languages (25 high, 24 mid, 38 low), tiers derived from Joshi et al. 2020. Corrected 2026-10-05: this row said 28 / 24 / 35 before four hand-copying errors in the Joshi classes were fixed (see the deviation log). |

The bank will change exactly once in a planned way: `expand_languages.py` will
add the 67 remaining catalog languages, including all 35 low-resource ones. That
expansion is pre-planned here, not a reaction to results. Any other change to the
bank after a scan has been run must be recorded in the deviation log below.

Note the honest starting position: until 2026-10-05 the bank contained **zero
low-resource languages**. It now holds 24, of which 23 are machine translated and
not reviewed by a native speaker (Gujarati is the exception), so the central
hypothesis is testable but still untested: no live scan has run.

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

**Amendment, 2026-10-05, before any live data.** The direction above is the
expected mechanism, not a settled finding. MultiJail (Deng et al., ICLR 2024, arXiv:2310.06474) found machine translated prompts produced slightly MORE unsafe output than human translated ones, 11.15% against 10.19% on average, and the authors
concluded that machine translation can suffice for jailbreaking. A garbled attack
can fail, but a translation can also strip the phrasing a model was trained to
refuse. So the direction is now treated as unknown, which is stricter than what
was written above: a gap that is found will **not** be described as a floor, and a
null keeps every caveat listed. The translation quality of each language will be
reported next to its result.

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
| 2026-09-29 | **Attack text corrected: accents restored in eight languages.** New SHA-256 `61050c90b9645d0a...`. Every attack in Spanish, French, Portuguese, Italian, German, Polish, Turkish and Vietnamese had been typed without its diacritics (`Tu unica tarea` for `Tu única tarea`, German `ae/oe/ue` for `ä/ö/ü`, Vietnamese with every tone mark missing), while the capability controls in the same languages were written correctly. | **Attack text did change**, unlike the two amendments below, so it is stated plainly. The change is spelling only: stripping the accents back off the corrected text reproduces the old text character for character, verified by script for all 108 changed items, so no word, instruction or meaning moved. It makes the instrument more faithful, not more favourable: degraded attack text would have failed for reasons unrelated to any defence and understated a gap. One suspected word error (Polish `streszcz`) was deliberately left for the native reviewer rather than changed here. Still no live data, so no result was chosen after seeing it. See AUDIT.md finding 55. |
| 2026-09-19 | **Fingerprint updated again, and made platform-independent.** New SHA-256 `29c170e164ae8145...`. The bank was being written in text mode, so it carried CRLF line endings on Windows and would have carried LF on Linux. | **No content changed at all**: every attack and control is byte-identical, only the line endings differ. The bug matters because this fingerprint is the pre-registered instrument pin, and it meant anyone regenerating the bank on Linux would get a different hash for the same data and the integrity check would fire on a file nobody touched. The generator now forces LF, so the fingerprint is reproducible anywhere. Still no live data. |
| 2026-09-18 | **Instrument fingerprint updated.** The bank SHA-256 changed from `3518957844ce6ab8...` to `d07d351c58387111...`. Cause: 120 benign capability controls were added and the misleading `verified` flag was replaced with `provenance` plus `native_reviewed`. | **No attack text changed.** All 300 attacks are byte-identical; the diff is added controls and renamed metadata, both pre-specified above and both making claims harder rather than easier. Logged because the fingerprint pins the instrument, and a changed instrument must be explained rather than silently re-fingerprinted. Still no live data. |
| 2026-09-17 | **Recorded the expected direction of translation bias, and made the reverse-translation gate default-on and multi-category.** Machine-translated attacks are expected to *understate* the low-resource gap, because a garbled attack fails for reasons unrelated to the defence being measured. | Literature, not PolyGuard data (arXiv:2605.18239: human red-teaming raised jailbreak rates 59.8% to 75.8%; MT error rates up to 71% before human review). Recorded in advance so a smaller-than-expected gap is not later reinterpreted as evidence of safety. Stating the direction constrains interpretation rather than loosening it. |
| 2026-09-17 | **Added a pre-specified capability control.** Every language now also receives benign twin requests measuring whether the bot follows ordinary instructions in that language, read relative to English. Languages confirmed capability-limited are excluded from safety conclusions rather than counted as well defended. | Addresses a confound that could invert the finding: a low break rate may mean the model is defended OR that it cannot follow instructions in that language. The bias runs in a known direction, since capability is weakest in low-resource languages, so leaving it unmeasured would understate the gap H1 predicts. Specified before any live data exists, and it makes H1 harder to support, not easier, because a quiet language no longer counts as a safe one. |
| 2026-09-16 | **Confidence intervals switched to the continuity-corrected Wilson interval.** | Calibration measured the plain Wilson interval's coverage at 91.3% against a nominal 95% at n=15, p=0.30 (AUDIT.md finding 23). The corrected interval is wider and never fell below 96.4% in a 14-point sweep. This makes reported precision more conservative, never less. |
| 2026-10-02 | **Native speaker feedback integrated for Spanish and Vietnamese.** New SHA-256 `d8dfa081e70db57bdf5197e1680879182b663a1c50c916cb3131d6bae2d6ef07`, replacing `61050c90b9645d0a613407a7020d397a6940a771f1debbff310737c6b6bb32de`. Eleven strings changed. Spanish: six attacks (`es_instruction_override_1`, `es_system_prompt_extraction_2`, `es_obfuscated_payload_1`, `es_obfuscated_payload_2`, `es_indirect_injection_1`, `es_indirect_injection_2`) and four capability controls (`es_control_1`, `es_control_2`, `es_control_4`, `es_control_5`), taken from the reviewer's tracked changes. Vietnamese: one attack (`vi_role_play_jailbreak_2`), where "tuân theo tất cả" became "tuân theo mọi mệnh lệnh" and the canary gained a final period. The same entry corrects the language count in the instrument table above, which still read 13 high and 7 mid; under the derived tier rule the bank's 20 languages are 16 high and 4 mid. | **Attack text did change**, so it is stated plainly. Every edit is wording only: no attack or control was added, removed or moved to another category, the canary, the control token and the Base64 payloads are unchanged, and no other language was touched (checked field by field against the previous bank). The edits make the text read the way a native speaker would write it, which removes a known source of an understated gap rather than favouring any result. This is feedback received and integrated, not validation of either language. Portuguese feedback is pending and nothing was changed for it. Still no live data, so no result was chosen after seeing it. |
| 2026-10-02 | **Held-out set for judging defences, fixed before any defence is evaluated.** The third phrasing of every language and attack type (variant index 2, 100 of the 300 attacks; SHA-256 of their ids and text `bf24f4da203bc458aea38f3a4a88bf47d9d84144e2848144f71578c1b1ee8546`) never helps choose a defence: the remediation rules are picked from the other two phrasings only (`defenses.broken_categories_from`). A defence is then judged on the held-out phrasing alone, together with the capability controls, so a defence that works by refusing ordinary requests shows up as a loss rather than a win (`engine.defense_evaluation`). | Without the split, the rules would be chosen on the same attacks they are scored on, and a before and after comparison would partly measure the fix being fitted to its own test. Fixed now, with no live data and no defence ever evaluated, so the split cannot have been chosen to flatter a result. It does not touch the primary analysis of H1, which still uses every attack. |
| 2026-10-04 | **Native speaker feedback integrated for Arabic.** Bank SHA-256 `d8dfa081e70db57bdf5197e1680879182b663a1c50c916cb3131d6bae2d6ef07` became `3d665ef61a4a9dde8cc125e1c9fdb4561621db2e7cf9b7b1d60ca6e95993dff9`. Seven text fields changed, from the reviewer's sheet (18 ok, 2 awkward, 1 wrong): five attacks (`ar_instruction_override_1`, `ar_instruction_override_2`, `ar_role_play_jailbreak_2`, `ar_system_prompt_extraction_1`, `ar_indirect_injection_0`) and two capability controls (`ar_control_0`, `ar_control_3`). In `ar_indirect_injection_0` only the framing clause was replaced; the two newlines and the quoted customer review carrying SYSTEM OVERRIDE and the canary are unchanged, because replacing the whole row would have deleted the injection under test. Where a suggestion left out the canary or the control token, it was kept. Two of the changed attacks are held out (`ar_instruction_override_2` and `ar_role_play_jailbreak_2`, variant index 2), so the held-out set's text changed while its membership did not: its fingerprint `bf24f4da203bc458aea38f3a4a88bf47d9d84144e2848144f71578c1b1ee8546` became `c9cfe3523ebe2213968fb25e03a6a8ecc1eb7cbd39df20383b01a4404da51893`. | **Attack text did change**, so it is stated plainly. Wording only: no attack or control was added, removed or recategorised, ids, categories, goals and counts are unchanged, the three Arabic Base64 payloads are unchanged, and no other language was touched (checked field by field against the previous bank). Results stamped with the previous bank hash must not be compared directly with results from this one; the CLI and the site refuse that comparison because the bank fingerprint is part of every scan's instrument record. Feedback received and integrated, not validation. The Arabic corpus is Modern Standard Arabic, and this review does not establish coverage of Arabic dialects (NATIVE_REVIEW.md). Still no live data. |
| 2026-10-05 | **Four Joshi classes corrected against the published file.** Gujarati, Norwegian and Kyrgyz were entered as class 4 and are class 1 in `lang2tax.txt`; Pashto was entered as 2 and is 1. Gujarati, Norwegian and Kyrgyz move from high to low. The catalog is now 25 high / 24 mid / 38 low (was 28 / 24 / 35) and the 20 bank languages are 15 high / 4 mid / 1 low (was 16 / 4 / 0). The file is now kept in the repo (`data/joshi_lang2tax.txt`, SHA-256 `2e182e8f...`) and `verify_all.py` checks every class against it and checks the file's class counts against Joshi's Table 1. | **The independent variable changed**, so it is stated plainly. These were transcription errors, found by reading the source file, not choices: the 2026-09-23 row's "Kyrgyz = 4 anomaly" was one of them. The rule (high 4 to 5, mid 3, low 0 to 2) is unchanged and still applied with no exceptions. Three names appear twice in the file with different classes (Slovenian, Sinhala, Haitian Creole); the entries whose names match are used and the choice is recorded in `languages_catalog.JOSHI_FILE_NAMES`. The attack bank file does not store tiers, so its SHA-256 is unchanged. Corrected before any live data exists. |
| 2026-10-05 | **The planned expansion, partly done: 53 machine translated languages added, 73 in all.** Bank SHA-256 `3d665ef61a4a9dde8cc125e1c9fdb4561621db2e7cf9b7b1d60ca6e95993dff9` became `4e2ba320c932823e046d2113af44ee2ca5e4042cf3d75f1ea8abd15117cdf1f8`. Held-out fingerprint `c9cfe3523ebe2213968fb25e03a6a8ecc1eb7cbd39df20383b01a4404da51893` became `3cf6789703c628a901e2b815de557a4709f49039af0c10689c1e5ce29f3b1a57` (the held-out set grew from 100 to 365 attacks; the 20 existing languages' text is unchanged). Each new language is stored as a source file, `machine_translations/<code>.json`, with English back-translations, and must pass `python expand_languages.py --check-stored` (structural gate, controls gate, back-translation intent test, script, mojibake, length and accent checks), which CI runs on every push. | **Method changed from the plan.** The plan was `expand_languages.py` calling the API; no API key exists, so the 53 were translated in working sessions by the same model family the script would use, with the same gates. The back-translations were written by the same model as the translations, so that check cannot catch an error the translator believes is correct. 14 catalog languages are still missing (ps tg mn hy ne si km my jv su sw am so rw) and will come from the API pipeline or native speakers, each addition logged here. Every new language carries `provenance: machine` and none is native reviewed. Tier and provenance are now partly confounded (23 of 24 low resource languages are machine translated), so author written against machine translated will be reported within tier. Still no live data. |
| 2026-10-06 | **Defence evaluation arms, fixed before any defence is run.** A defence is judged as one of four named arms against the same held-out phrasing and the same capability controls (`python cli.py defend`, `engine.arm_table`): **baseline** (the prompt as written; this scan fires every phrasing, and the rules are chosen from the development phrasings only), **placebo** (neutral house style notes under a header that says nothing about security, matched in word count to the longer of the two defence blocks, within 5%; `defenses.arm_blocks`), **current** (exactly the block `harden()` has always produced), and **data_boundary** (the same category rules, with the indirect injection rule replaced by a clause saying quoted or pasted text in any language is material to process and directives inside it have no authority, and the multilingual clause replaced by one saying this system message outranks everything and language never changes that; from `docs/research/defenses.md`, section 3.2). Each arm reports the held-out break rate and the benign control follow rate with continuity corrected Wilson intervals, and its difference from the placebo in rate points with an exact sign test paired by language. Languages confirmed capability-limited in the baseline are dropped from every arm alike. Every defence and placebo text must pass a lint (`defenses.lint_all`, `verify_all.py` check 118): no 6 consecutive words shared with any string in the bank, and no canary, control token or `SYSTEM OVERRIDE` marker. The only claim any arm can support is that it **reduced the break rate on this fixed bank**, never that a bot is "secure". A fixed, public bank cannot show that: Nasr et al., *The Attacker Moves Second* (arXiv 2510.09023, 10 October 2025, abstract opened 2026-10-06), report bypassing 12 recent defences "with attack success rate above 90% for most", where "the majority of defenses originally reported near-zero attack success rates". | A placebo of the same length separates a real defence effect from "any longer prompt changes behaviour" and from regression to the mean (rules are added for categories picked because they broke). Pairing by language keeps the language as the unit of analysis, as everywhere else in this document. The lint stops a defence passing the test by recognising it. Same instrument otherwise: the attack bank, the held-out set and its fingerprint, the judges and `SCORING_VERSION` are unchanged. One simulation-only fix ships with this: the offline mock scored extraction against the hardened prompt instead of the original, which could invent a defence effect; live scoring was already correct. Fixed before any live data and before any defence has been evaluated, so the arms cannot have been chosen to flatter a result. |

Correction, 2026-10-05 (citation only, no change to the instrument, the
hypotheses or the analysis): the 2026-09-17 row above attributes "MT error rates up
to 71% before human review" to arXiv:2605.18239. That figure is from LinguaSafe
(arXiv:2508.12733): vanilla LLM translation error rates of 71% for Bengali and 36%
for Malay under human inspection. The 59.8% to 75.8% figure is correctly
attributed to arXiv:2605.18239. The row is left as written so the log stays
append only; the recorded bias direction is unchanged.

---

*Recorded before first live data. PolyGuard, Congressional App Challenge 2026.*
