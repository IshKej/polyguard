# Research: statistics upgrades that make PolyGuard findings stronger and scans cheaper

**Date:** 2026-10-05
**Scope:** read engine.py, PREREGISTRATION.md, test_stats_properties.py, pilot-plan.md and attack_bank.json as of today. Nothing outside this file was edited and nothing was committed.
**Reading guide:** every method starts with two plain sentences, then the formula, then a standard library sketch, then a test plan. Labels used throughout: **[verified]** means I opened the primary source this session and read the passage; **[abstract only]** means I opened the paper's page but not its full text; **[unverified]** means I did not open a primary source and you should not cite it without checking. **Fact** means measured or read from a source; **Opinion** means my judgement.

---

## 1. Summary in five lines

1. **The max-gap permutation test does not test H1.** Its null is "every language has the same rate", so any real language to language variation (translation quality, script, one odd language) makes it reject with no resource effect at all. In my simulation it false alarmed 7% to 19% of the time when languages varied realistically and there was zero tier effect (section 6). Keep it only as an "is any language different from English" check, and word the report that way.
2. **Power (simulated, 28 high / 24 mid / 35 low languages, 15 attacks each):** the pre-registered Mann-Whitney test reaches 80% power at a low-minus-high gap of about 0.08 to 0.11 (8 to 11 points); a rank-trend test on log Common Crawl share needs about 0.06 to 0.09 if the effect really is a smooth trend; the max-gap test needs about 0.15 to 0.22 (and is answering a different question). The engine's own `power_simulation` is optimistic because it gives every language in a tier the same true rate.
3. **Sequential stopping works only at the tier level.** A betting e-process on random order (low, high) language pairs stopped early in 86% of simulated scans at a 15 point gap and cut attacks fired by 36% (versus its own 28 pair design) and 59% (versus the full 87 language scan); its false alarm rate under no effect was at most 1.1% against a 2.5% budget. It essentially never stops for "no gap" (futility fired in 2% to 9% of null scans), and per-language sequential testing with 15 attacks saves nothing.
4. **Shrinkage fixes the winner's curse but not the intervals.** Empirical Bayes shrunk estimates cut the error of the five worst looking languages from +12 to +20 points (raw) to about -1 to -2 points (shrunk), but EB intervals under-covered (87% and 67% instead of 95%) when errors are shared across languages, which they are here because every language gets the same 15 attacks. Keep the continuity corrected Wilson interval as the displayed interval.
5. **The capability controls barely do anything as built.** With 6 controls per language the "confirmed capability limited" flag cannot fire at all unless English follows 6 of 6 controls and the other language follows 0 of 6; on average 0.5 of 35 low-resource languages were excluded even when understanding collapsed. In my toy model the naive gap was erased (+0.002 against a true +0.15) or reversed (-0.078 against a true 0); a tier level ratio adjustment recovered the truth when its assumptions held. Separately, `max_gap_permutation_test` has a one line floating point tie bug (section 2 above; ranked change 1 in section 4).

---

## 2. Facts about the repo that shape every recommendation

- **Fact:** engine.py imports only the standard library plus `providers` and `languages_catalog`. Every sketch below keeps that.
- **Fact:** attack_bank.json today holds 780 attacks, 312 controls and 52 languages: 28 high, 24 mid and **0 low**. H1 still cannot be tested. PREREGISTRATION.md's instrument table still says 300 attacks, 120 controls, 20 languages.
- **Fact:** every language receives the same 15 attacks (5 categories x 3 phrasings), translated. Attack difficulty therefore hits every language together. The current max-gap permutation test shuffles all outcomes in one pool and ignores this pairing.
- **Fact:** a full 87 language scan is 1305 attack calls plus 522 control calls, 1827 victim calls, plus a judge call whenever a reply contains the canary. docs/pilot-plan.md prices 420 calls at a $1.33 worst case, so 1827 calls scale to roughly $5.80 worst case per victim model (my scaling, assumes similar prompt lengths and that heavy scripts cost like the pilot mix). Four victim models would exceed the $10 pilot cap, which is why fewer calls matters.
- **Fact (bug, small):** `max_gap_permutation_test` tests `if g >= observed:` on floats built from fractions with denominator 15. In floating point 9/15 - 3/15 = 0.39999999999999997 while 8/15 - 2/15 = 0.4, so a shuffle that ties the observed gap is sometimes not counted as "at least as extreme". On one simulated scan (seed 5, 8000 shuffles) the engine returned p = 0.0526 and the same code with a 1e-12 tolerance returned 0.059; on another (seed 77, 20000 shuffles) 0.018 against 0.031. Under a global null (4500 scans, seeds 20261100 to 20261114) the float comparison rejected 3.1% of scans and the tolerance version 2.9% (Monte Carlo error about 0.25 points), so the damage is small on average but it always pushes borderline results toward significance. The permutation p-value is also conservative under the global null (size about 3%, not 5%).

---

## 3. The methods

### 3.1 Anytime-valid sequential testing (e-values, e-processes, betting confidence sequences)

**What, in two sentences.** Imagine you start with $1 and, after each new piece of data, bet part of it that the effect is real; if there is no effect you cannot expect to win, so ending with $40 or more is strong evidence, and that statement stays true even if you decided when to stop by peeking at the data. The $ total is an **e-process**; a **confidence sequence** is the matching estimate: a range for the true average that is valid at every moment at once, so you can watch it shrink and stop whenever it is narrow enough.

**Why PolyGuard cares.** Each attack is a paid call. A fixed 87 language scan always spends all 1305 attack calls even when the gap is obvious after 30 languages. Peeking at an ordinary p-value and stopping when it dips under 0.05 inflates false alarms (a standard result, not from a source I opened); an e-process makes peeking safe.

**Formulas.**

- Bet on the mean of a bounded score X_i in [0,1], null H0: E[X_i | past] <= m (here m = 1/2). Capital after t steps:
  `E_t = product over i of (1 + lambda_i * (X_i - m))`, with each bet fraction `lambda_i` chosen using only data before step i and `0 <= lambda_i <= c/m`.
- Under H0, E_t is a nonnegative supermartingale starting at 1, so **Ville's inequality** gives `P(E_t >= 1/alpha for some t) <= alpha`. [verified: in Waudby-Smith and Ramdas the confidence sequence result "relies centrally on Ville's inequality" and a test martingale is "an e-value even at stopping times"; arXiv:2010.09686v7 full text.]
- Predictable plug-in bet (their eq. 26, with truncation as in Theorem 3, eq. 25) [verified]:
  `lambda_t = min( sqrt( 2 log(2/alpha) / (sigma2_{t-1} * t * log(1+t)) ), c/m )`,
  `sigma2_t = (1/4 + sum_{i<=t} (X_i - mu_i)^2) / (t+1)`, `mu_t = (1/2 + sum_{i<=t} X_i) / (t+1)`, `c` = 1/2 or 3/4.
- Confidence sequence for the mean (their Theorem 3, hedged capital) [verified]: `K+_t(m) = prod(1 + lambda+_i(m)(X_i - m))`, `K-_t(m) = prod(1 - lambda-_i(m)(X_i - m))`, `K_t(m) = max(theta K+_t(m), (1-theta) K-_t(m))`, and `{m : K_t(m) < 1/alpha}` is a (1-alpha) confidence sequence, valid at arbitrary stopping times.
- Related theory: time-uniform confidence sequences from the Cramer-Chernoff method (Howard, Ramdas, McAuliffe, Sekhon, Annals of Statistics 2021) [abstract only]; "safe testing" with e-variables, optional continuation and growth-rate optimality (Grunwald, de Heide, Koolen, JRSSB 2024) [abstract only]; the overview of safe anytime-valid inference (Ramdas, Grunwald, Vovk, Shafer 2022) [abstract only]; a without-replacement version for finite populations (Waudby-Smith and Ramdas 2020) [abstract only]. Contingency table e-variables for comparing two data streams under optional stopping (Turner, Ly, Grunwald; J. Stat. Plan. Inference 2024) [abstract only].

**How I applied it to PolyGuard (my design, Opinion, tested in simulation).**

1. Fix a seeded random order of the 28 high and 35 low resource languages. Fire the 15 attacks for the next (low_k, high_k) pair. `D_k = rate(low_k) - rate(high_k)`, so the language stays the unit of analysis.
2. Score `X_k = (1 + clip(D_k / s, -1, 1)) / 2` with scale `s = 0.30` (chosen before data; any fixed value is valid). Under the null that tier labels do not matter, D_k is symmetric around 0 and E[X_k] = 1/2, so the capital process is a valid e-process for "no tier effect". Clipping keeps the bet in range without hurting validity because the null is symmetric (it would break a confidence interval for the mean of D, which is why futility uses the unclipped version below).
3. Reject (efficacy stop) when `E >= 40`, the same strictness as the pre-registered "p < 0.05 and low rate higher" (a one sided 2.5% test).
4. Futility: run a confidence sequence for the mean of the unclipped D and stop if its top end is below 0.10. This is a claim of the form "the gap is under 10 points with 95% confidence", never "there is no gap".
5. The expected number of pairs is roughly `ln(40) / G`, where G is the per-pair growth rate `E[ln(1 + lambda (X - 1/2))]`. This is a Wald style approximation of mine [unverified]; the simulation below is the real evidence.

**Results (simulation, 100 scans per cell, seeds 20261201 to 20261224; realistic = language effect sd 0.5, attack effect sd 1.0, translation noise sd 0.5 on the logit scale).** "Saved vs the 28 pair design" is the saving caused by sequential stopping alone. "Saved vs the full 87 language scan" also includes simply not scanning the mid tier and the 7 extra low languages, which costs you the trend test and per-language results, so do not count it as free. Attacks only; controls add 6 calls per scanned language.

| high tier break rate | true gap | stopped early for efficacy | pairs scanned (of 28) | attacks fired (of 1305) | saved vs 28 pair design | saved vs full 87 scan |
|---|---|---|---|---|---|---|
| 0.15 | 0.00 | 0% | 28.0 | 840 | 0% | 36% |
| 0.15 | 0.05 | 17% | 26.4 | 793 | 6% | 39% |
| 0.15 | 0.10 | 55% | 23.0 | 690 | 18% | 47% |
| 0.15 | 0.15 | 86% | 18.1 | 542 | 36% | 59% |
| 0.15 | 0.20 | 99% | 13.5 | 406 | 52% | 69% |
| 0.15 | 0.30 | 100% | 10.1 | 304 | 64% | 77% |
| 0.30 | 0.00 | 3% | 27.5 | 826 | 2% | 37% |
| 0.30 | 0.05 | 12% | 27.1 | 812 | 3% | 38% |
| 0.30 | 0.10 | 44% | 24.1 | 722 | 14% | 45% |
| 0.30 | 0.15 | 79% | 19.8 | 594 | 29% | 54% |
| 0.30 | 0.20 | 96% | 15.5 | 465 | 45% | 64% |
| 0.30 | 0.30 | 100% | 10.5 | 315 | 63% | 76% |

**False alarm check (the property that matters).** With a true gap of 0, 1000 scans per cell: the e-process crossed 40 in 0.0% to 1.1% of scans across six heterogeneity settings (binomial only, realistic, strong language heterogeneity, each at high-tier rates 0.15 and 0.30), under the 2.5% budget. The 3% in the gap 0.00 row at rate 0.30 of the table is 3 of 100 scans, within Monte Carlo noise of 2.5%; the 1000 scan check is the better number. Futility stops under the null were 1.8% to 8.6%, so a "clearly no gap" verdict is rare: with at most 28 pairs and a 10 point margin, the data usually cannot rule out a 10 point gap.

**Caveats.** (a) The guarantee is exact for sampling languages with replacement from a language population; for the fixed 63 language set it is approximate, and the without-replacement confidence sequences of Waudby-Smith and Ramdas are the exact tool (not implemented). (b) After an early stop, the Mann-Whitney p-value on the scanned subset is **not valid** (optional stopping). The headline after an early stop must be the e-value and the confidence sequence. (c) The order must be fixed by a recorded seed before scanning; a human choosing the next language after seeing results voids the guarantee. (d) The bank has no low resource languages yet, so this cannot run live until `expand_languages.py` adds them.

**Why not per language.** I simulated per language sequential testing against English on the same 15 paired attacks (a sign e-process on discordant pairs, e-BH of Wang and Ramdas [abstract only], versus exact McNemar with Holm and BH). With 15 attacks and 86 comparisons, no language can reach an e-value of 87/(alpha x k) unless almost every attack is discordant the same way; the per language rule never stopped early (calls share 100% in every cell) and e-BH found 0.2 or fewer languages on average up to a 15 point tier gap (numbers in 3.4). **Not worth building.**

**Sequential Monte Carlo (Fischer and Ramdas, JRSSB 2025) [abstract only]** saves *permutation* draws, which are free CPU, not API calls. Do not use it to save money; it would only matter if the shuffle count became a bottleneck.

**Test plan.** See 3.7. Key properties: e-process never negative; null crossing rate at most alpha over all times (checked: 0.6% in 1500 symmetric null streams of 28 steps); confidence sequence covers the true mean at all times (0 misses in 600 streams); data at exactly the null mean leaves the e-process at 1.

---

### 3.2 Partial pooling of per language rates (beta-binomial empirical Bayes)

**What, in two sentences.** With only 15 attacks per language, a language that happened to break 12 times is probably a bit less bad than 12/15 and one that broke 0 times is probably a bit worse than 0/15, so you pull every language part of the way toward the typical rate, harder when the evidence is thin. "Empirical Bayes" means the typical rate and how spread out languages are get estimated from the 87 languages themselves rather than assumed.

**Formulas.** `k_l | pi_l ~ Binomial(n, pi_l)`, `pi_l ~ Beta(mu*phi, (1-mu)*phi)`. Estimate `(mu, phi)` by maximizing the beta-binomial marginal likelihood over languages. Posterior for language l: `Beta(mu*phi + k_l, (1-mu)*phi + n - k_l)`, posterior mean `(phi*mu + k_l)/(phi + n)`: a weighted average of the raw rate k_l/n (weight n/(n+phi)) and the common rate mu. With a covariate (log Common Crawl share z_l): `mu_l = expit(a + b*z_l)`. Efron and Morris show the same idea (James-Stein shrinkage beats individual averages in total squared error, using batting averages) [verified: JASA 1975, full text opened]; the empirical Bayes idea is Robbins 1956 [verified: page opened, title and venue only]. The beta-binomial likelihood and the posterior formulas are textbook algebra, not taken from a source I opened.

**Simulation (120 scans per scenario, seeds 20261300 to 20261302; truth = each language's rate averaged over the attack universe; Wilson = the engine's continuity corrected interval).**

| scenario | RMSE raw | RMSE EB | RMSE EB with covariate | coverage Wilson | coverage EB | coverage EB with covariate | width Wilson / EB | top 5 error raw | top 5 error EB |
|---|---|---|---|---|---|---|---|---|---|
| language effects only (model is right) | 0.115 | 0.098 | 0.095 | 97.8% | 94.8% | 94.5% | 0.45 / 0.37 | +0.124 | -0.006 |
| realistic (language + attack + translation noise) | 0.123 | 0.098 | 0.090 | 97.5% | 86.8% | 75.2% | 0.47 / 0.31 | +0.157 | -0.024 |
| attack effects only (shared across languages) | 0.123 | 0.087 | 0.047 | 97.7% | 66.5% | 26.4% | 0.48 / 0.19 | +0.198 | -0.023 |

**Reading it.**
- **Fact (simulated):** shrunk estimates have 15% to 29% lower error and remove the winner's curse: the five languages that look worst on raw data are overstated by 12 to 20 points; shrunk, by about 0 to 2 points. This is the honest per language number to rank by.
- **Fact (simulated):** EB intervals are right only when the beta-binomial model is right. The 15 attacks are a shared sample of the attack universe, so a lucky or unlucky attack set moves every language together. The model assumes independence, so its intervals are too narrow (66% and 26% coverage in the shared-effect setting). The Wilson interval over-covers (97.5%) in every setting, which is the direction this project has said it accepts.
- **Opinion:** show the Wilson interval, plus the shrunk point estimate as a second number, labelled "estimated rate after pooling across languages". Do not show EB intervals, and never use the covariate version for display or inputs to tests: it bakes the resource trend into each language's estimate, which makes the trend test circular. For the constant-prior version with equal n the shrinkage is a monotone map of k, so ranks, the Mann-Whitney p and Cliff's delta are unchanged; shrinkage is purely descriptive.
- For rigorous EB intervals the relevant literature is Armstrong, Kolesar and Plagborg-Moller (Econometrica 2022), who build intervals with a critical value that accounts for shrinkage and keep coverage when the Gaussian assumption fails [abstract only]. It is for normal means, so it does not drop straight onto binomial counts; I did not adapt it.
- A full hierarchical logistic model (random language effect, MCMC) would need numpy or Stan and gives similar point estimates; skip it for a standard library codebase.

**Implementation sketch:** appendix `shrink.py` (about 90 lines, standard library only: beta CDF by continued fraction, bisection quantile, Nelder-Mead maximum likelihood). It recovered the true prior in a check (true mean 0.30, phi 10; fitted 0.298, 9.85) and `beta_cdf` matched numerical integration to 1e-12.

---

### 3.3 A trend test against a continuous resource measure

**What, in two sentences.** Instead of cutting languages into three buckets and comparing the ends, line up all 87 languages by how much of the web they occupy and ask whether break rates climb steadily as that share falls. The permutation version shuffles the resource numbers among languages and asks how often a shuffled arrangement shows a trend as strong as the real one, so it needs no distribution assumptions and keeps the language as the unit.

**The measure (Fact, computed today).** Common Crawl publishes the share of crawled pages by detected language per crawl; the language is identified by Compact Language Detector 2, which covers 160 languages [verified: https://commoncrawl.github.io/cc-crawl-statistics/plots/languages, plus its languages.csv downloaded today]. I took the mean of `%pages/crawl` over the six most recent crawls (CC-MAIN-2026-17, 21, 25, 30, 34, 39) for all 87 catalog languages (all 87 are present; script in appendix `ccshare.py`) and used `x = log10(share)`.
- Mean log10 share by tier: high -0.08, mid -0.98, low -2.13. Spearman correlation between tier (0/1/2) and x: 0.80. So tier and x agree broadly but not perfectly.
- Disagreements (Fact): Gujarati is a "high" language by Joshi class 4 yet has x = -1.89 and Kyrgyz (the anomaly noted in languages_catalog.py) x = -1.93, both lower than the best-resourced "low" languages (Azerbaijani -1.21, Nepali -1.22, Albanian -1.30). Basque (high) is -1.41, the same as Macedonian (low). The continuous measure does not need the tier cut offs.

**Formula.** `rho = Spearman(break_rate_l, x_l)` over the 87 languages (average ranks for ties). Permutation p: shuffle x across languages B times, `p = (1 + #{|rho*| >= |rho|}) / (B + 1)` (add-one, as Phipson and Smyth show a permutation p-value should never be zero [abstract only]). Effect size: OLS slope of rate on x with a bootstrap over languages: "change in break rate per tenfold increase in web share".

**Power (simulated).** When the true effect is a smooth trend in x, the trend test needs a smaller gap than Mann-Whitney (table in 3.6); when the true effect is a tier step, Mann-Whitney is better. It also uses the 24 mid-tier languages that the primary test ignores.

**Interpretation, and what it cannot say (Opinion).**
- A negative slope says "languages that are scarcer on the web break more", a dose response. It does not say the web share causes it: script, language family and machine translation quality all travel with web share, and the pre-registration already says translation noise biases toward understating the gap.
- Common Crawl page share is not the victim model's training mix (no lab publishes it for the models in play [unverified]), counts pages not tokens, and CLD2 merges or confuses close languages (Serbian and Croatian, Malay and Indonesian, Norwegian variants). Measurement error in x pulls the slope toward zero, which is the conservative direction.
- The permutation treats languages as exchangeable; related languages cluster, so the p-value is somewhat optimistic. Sensitivity check (exploratory only): permute within script or family blocks.
- If Mann-Whitney is null and the trend is significant, report it as exploratory. The pre-registration (rule 2) keeps Mann-Whitney as the headline.

**Implementation:** `trend_permutation_test` and `bootstrap_slope_ci` in appendix `newstats.py`.

---

### 3.4 Multiple comparisons when showing 87 per language results

**What, in two sentences.** If you look at 87 languages and flag the ones that look bad, some will look bad by luck, so each flag needs a stricter bar. The three standard bars protect against different things: Holm keeps the chance of even one false flag at 5%, Benjamini-Hochberg keeps the share of false flags among all flags at 5%, and simultaneous intervals make all 87 intervals correct at once.

**Formulas (checked against the original papers where noted).**
- **Holm** (sequentially rejective Bonferroni): sort p(1) <= ... <= p(m); reject H(i) while `p(i) <= alpha/(m - i + 1)`; controls the chance of any false rejection with no independence assumption [verified: Holm 1979, full text opened]. Adjusted p: `max over j <= i of min(1, (m - j + 1) p(j))`.
- **Benjamini-Hochberg:** largest k with `p(k) <= k q / m`, reject the k smallest; proved there "for independent test statistics" [verified: Benjamini and Hochberg 1995, full text opened]. Already in engine.py as `benjamini_hochberg`. Under arbitrary dependence use Benjamini-Yekutieli, which multiplies by the harmonic number `H_m` (H_87 = 5.05) [unverified: not opened].
- **e-BH** (Wang and Ramdas): with e-values e_1..e_m, reject the k with the largest e where k is the largest value satisfying `e_(k) >= m / (alpha k)`; controls FDR under any dependence "with no correction" [abstract only; the threshold formula is from memory, [unverified]].
- **Westfall-Young maxT** (permutation): the adjusted p for language l is the fraction of shuffles in which the largest statistic anywhere is at least as large as language l's statistic [method description seen in secondary pages only; [unverified] as to Westfall and Young 1993 itself]. The engine's `max_gap_permutation_test` is exactly this single step maxT for the top language.
- **Simultaneous Wilson intervals:** use `z = Phi^-1(1 - alpha/(2m))`. For m = 87, alpha = 0.05 this is z = 3.443 (computed), versus 1.96 for one interval. `newstats.simultaneous_wilson`.
- **Intervals shown only for selected languages:** Benjamini and Yekutieli's false coverage statement rate says a selected interval needs level `1 - R q / m`, where R languages were selected out of m [abstract only, from a search result; the paper itself was not opened, [unverified]].

**What the 15 attack design can and cannot certify (Fact, exact arithmetic).** Holm threshold per language vs English with m = 86: 0.05/86 = 5.8e-4.
- Unpaired exact (Fisher) one sided: if English broke 0 of 15, a language needs **9 of 15** (a 60 point gap); English 1 of 15 needs 11; 2 needs 12; 3 needs 13; 4 needs 14; 5 or more needs 15 of 15.
- Paired (same 15 attacks): the sign test on discordant pairs needs **at least 11 discordant pairs all in one direction** (0.5^11 = 4.9e-4). So no single language can be flagged at 5% familywise unless the gap versus English is about 60 points or more.
- Simulated discoveries (average count over 100 scans, realistic scenario, 35 languages are truly elevated by the stated tier gap): at a 15 point gap (high tier rate 0.30) Holm found 0.2 languages, BH 13, e-BH 0; at 30 points Holm found 4.9 (rate 0.30) and 3.5 (rate 0.15), BH 44.5 and 34.0, e-BH 10.3 and 3.4. Under a zero gap BH still flagged 1.3 languages on average at high-tier rate 0.30, because every comparison shares one noisy 15 attack English reference: if English is lucky-low, many languages look elevated together.

**Opinion on what to do.** Show all 87 languages as a descriptive table (shrunk estimate, Wilson interval), clearly labelled "not corrected for looking at 87 languages". Make language level claims only through Holm or maxT and expect almost none to survive. Keep the family explicit in the report: one primary test, one pre-specified trend test, 5 H3 tests (BH, already done), 86 per language tests (Holm).

---

### 3.5 Capability controls: attack success conditional on understanding

**What, in two sentences.** A bot that does not understand a language cannot be tricked in it, so a low break rate can mean "well defended" or "does not follow instructions here"; the benign controls measure the second. You can handle that by dropping languages where the controls fail, by dividing the break rate by the control rate, or by ignoring it, and each choice answers a slightly different question with a different bias.

**Model used (my toy model, Opinion).** For language l: `break rate b_l = u_l x c_l`, where u_l is the chance the bot understands the attack and c_l the chance it complies if it does. The controls give an estimate of `v_l`, the chance of following a benign request in that language, used as a stand in for `u_l`. The quantity of scientific interest is `c` (compliance given understanding) by tier.

| choice | what it estimates | bias it introduces |
|---|---|---|
| naive: ignore controls | tier gap in `u*c` | understanding falls with resource, so b_low is dragged down; the gap shrinks toward 0 and can reverse sign |
| exclude languages with failed controls (the pre-registered rule: Wilson upper bound of control rate below half of English) | gap among languages the bot understands | selects on a variable the language itself causes (post-treatment selection): "this bias can be in any direction, it can be of any size" [verified: Montgomery, Nyhan and Torres, AJPS 2018, full text opened]; changes the population; with 6 controls it almost never fires |
| ratio adjust: tier break rate / tier control rate, cap at 1 | `c`, if attacks are as easy to parse as controls and a break needs understanding | over-corrects if the controls are noisy and floors bite; **under-corrects if attacks are harder to parse than controls** (long, obfuscated, Base64); breaks if a bot can echo the canary without understanding |
| trimming bounds in the style of Lee (2009) [abstract only] | sharp bounds under monotone selection | needs a binary treatment and monotonicity; language is not binary; not implemented |
| principal strata ("always understood" languages, Frangakis and Rubin 2002) | effect in the stratum that is understood in both groups | the right estimand but not identified from 6 controls [unverified: only a search result abstract seen] |

**Simulation (400 scans per scenario; 87 languages; 6 controls and 15 attacks per language; true conditional gap 0.15 unless stated; seeds 1 to 4). Mean estimated low-minus-high gap (sd across scans in brackets):**

| scenario | naive | pre-registered exclusion | ratio per language | **ratio by tier** | truth |
|---|---|---|---|---|---|
| A: attacks as easy as controls, lowest understanding 0.30 | +0.002 (0.029) | +0.003 | +0.174 (0.053) | **+0.149 (0.052)** | +0.150 |
| B: attacks harder to parse than controls (understanding squared) | -0.061 (0.026) | -0.060 | +0.029 (0.049) | +0.008 (0.041) | +0.150 |
| C: mild capability loss only (floor 0.70) | +0.089 (0.030) | +0.089 | +0.163 (0.041) | +0.151 (0.039) | +0.150 |
| D: no true gap (0) | -0.078 (0.027) | -0.078 | +0.031 (0.052) | +0.002 (0.045) | 0.000 |

Mean low-resource languages excluded by the pre-registered rule: 0.5 (A), 0.6 (B), 0.0 (C), 0.5 (D) out of 35.

**Why the exclusion never fires (Fact, exact):** `wilson_ci_cc(0, 6)` has upper bound 0.483. The flag needs that bound below half of English's control rate. If English follows 6 of 6, the threshold is 0.5 and only 0 of 6 qualifies; if English follows 5 of 6 the threshold is 0.417 and **no language can ever be flagged**, even at 0 of 6. The code's own `resolves` string says "nothing conclusively" in that case, but the report would still present the rule as protection.

**Opinion, in order of preference.** (1) Keep the pre-registered exclusion exactly as written (changing it now is a deviation) and say in the report how many languages it flagged, expecting zero. (2) Add the tier level ratio adjusted gap as a **labelled exploratory sensitivity analysis**, shown next to the naive gap, with the sentence "assumes attacks are no harder to parse than controls; if they are, this under-corrects (simulated: 0.01 against a true 0.15)". Pooling controls by tier (35 languages x 6 = 210 controls for the low tier) beats per language ratios: in the simulation the spread is the same (sd about 0.05) but the per language version is biased upward (+0.024 in scenario A, +0.031 in scenario D) while the tier version is not (-0.001 and +0.002). (3) Do not call the result "bounds"; scenario B shows the truth can lie outside [naive, adjusted]. (4) Doubling controls to 12 per language costs 522 more calls (+29% of a full scan), mostly for per language flags, which section 3.4 says almost never survive anyway; I would not.

**Caveat on all of this:** the understanding gradient, the compliance gap and the attack-versus-control difficulty are my assumptions; there is no live data. The simulation shows the direction and rough size of the biases, not what the actual victim models will do.

**Implementation:** `newstats.ratio_adjusted_gap`.

---

### 3.6 Power: what gap sizes are detectable

**What, in two sentences.** Power is the chance a test says "real" when there is a real gap of a given size; 80% is the usual minimum worth running a study at. The numbers below come from simulating whole scans (87 languages, 15 attacks each) thousands of times and counting how often each test rejects.

**Simulation design (all code in the appendix; numpy used for speed only, the sketches themselves are standard library).**
- Languages and tiers are the real catalog: 28 high, 24 mid, 35 low. Resource measure is the real log10 Common Crawl share.
- Each language gets 15 shared attacks. Break probability on the logit scale: intercept + slope x (-standardized log share) + language effect (sd tau) + attack effect (sd sigma_a, same attack in every language) + attack-by-language translation noise (sd sigma_e). Outcome is one Bernoulli draw per attack and language (a temperature 0 victim).
- **gap** = expected break rate of the low tier minus the high tier, averaged over the real language set (intercept and slope are solved so the high tier mean and the gap hit their targets exactly). "binomial only" has tau = sigma_a = sigma_e = 0 (every language in a tier has the same true rate, which is what `engine.power_simulation` assumes); "realistic" has tau 0.5, sigma_a 1.0, sigma_e 0.5. The sizes of tau, sigma_a, sigma_e are my guesses; the first live scan will estimate them.
- Tests: Mann-Whitney on per language rates (`engine.mann_whitney_u`, two sided 0.05, low must be higher); Spearman trend permutation (one sided 0.025, so it has the same strictness as the two sided Mann-Whitney in the direction that matters); the engine's pooled max-gap permutation (one sided 0.05 by construction); and a max-gap permutation stratified by attack (shuffle each attack's outcomes across languages). 300 scans per cell, 399 shuffles, seeds 20261005 + cell index and 20261600 + cell index. Monte Carlo error on a power value is about 2.5 points.
- Check (numpy rng seed 77, 20000 shuffles each): on five simulated scans the engine with the tie tolerance and my numpy max-gap agree to Monte Carlo error (0.0312 vs 0.0302, 0.0008 vs 0.0010, 0.5346 vs 0.5385, 0.0628 vs 0.0618, 0.0823 vs 0.0799). The engine as written matched on four and gave 0.018 on the first, about 40% too small.

**Table A. Smallest gap with 80% power (linear interpolation on grids of 9 gaps, effect is a smooth trend in log share).**

| scenario | high tier rate | Mann-Whitney (primary) | trend permutation | max-gap, pooled (engine) | max-gap, stratified by attack |
|---|---|---|---|---|---|
| binomial only | 0.15 | 0.076 | 0.057 | 0.203 | 0.206 |
| binomial only | 0.30 | 0.092 | 0.077 | 0.223 | 0.223 |
| realistic | 0.15 | 0.086 | 0.068 | 0.176 * | 0.150 * |
| realistic | 0.30 | 0.112 | 0.089 | 0.194 * | 0.169 * |

\* includes rejections caused by language to language variation with no tier effect (Table B), so this is partly detecting heterogeneity, not a resource gap.

If instead the true effect is a **tier step** (low tier elevated, nothing else), Mann-Whitney is the better test: 80% power at about 0.075 to 0.11; the trend test needs about 0.10 to 0.13; the max-gap test does not reach 80% even at a 30 point gap (47% to 73%). Plain words: the trend test wins when the world is a gradient, Mann-Whitney wins when the world is a cliff, and max-gap is the wrong tool for H1 either way.

**Back of envelope (Opinion, matches the simulation):** minimum detectable gap for the tier test is roughly `2.8 x sqrt((p(1-p)/15 + tau_eff^2) x (1/28 + 1/35))`. With p = 0.25 and a between language sd of 0.10 that is 2.8 x 0.0396 = 0.11. Language to language variation (tau) is the part extra attacks cannot shrink, so it caps what any scan can resolve.

**Power for the pre-registered "15 point gap" statement:** Mann-Whitney power at a 15 point gap is 0.96 to 1.00 in every scenario above (both effect shapes, both baselines). A null from a complete 28 vs 35 language scan is therefore informative about gaps of 15 points or more, and much less informative about gaps near 5 points (power 0.26 to 0.51 at 5 points). The existing pre-registration language about reporting a null together with its power stays right; just use the realistic column, because `engine.power_simulation` is optimistic: its minimum detectable gap is 13% to 22% smaller than the realistic one (0.076 vs 0.086 and 0.092 vs 0.112).

**Table B. False alarm rate when there is NO tier effect (gap = 0, trend world, 300 scans).**

| scenario | Mann-Whitney | trend (0.025) | max-gap pooled (engine) | max-gap stratified |
|---|---|---|---|---|
| binomial only, rate 0.15 / 0.30 | 3% / 2% | 3% / 3% | 4% / 3% | 3% / 3% |
| realistic, rate 0.15 / 0.30 | 3% / 2% | 2% / 3% | 7% / 12% | 12% / 18% |
| language effects only (tau 0.5), rate 0.30 | 2% | 2% | **19%** | **19%** |
| attack effects only (sigma_a 1.0), rate 0.30 | 4% | 3% | 0% | 3% |

Max-gap rejects when languages differ from English, whatever the reason. The stratified version is exact when only attack difficulty varies (3%) and has more power there (27% vs 14% at a 10 point gap; 72% vs 60% at 20 points), but it is more sensitive to real language variation, so it false alarms more often as an H1 test (18%).

**What repeats buy (200 scans per cell, MW power, high tier rate 0.30, seeds 20261401 to 20261424, error about 3.5 points).** Repeats only help when the victim is sampled above temperature 0, so the same attack can come out differently.

| scenario | gap | 15 attacks x1 | 15 x3 repeats | 15 x5 repeats | 30 attacks x1 | 45 x1 | 75 x1 |
|---|---|---|---|---|---|---|---|
| moderate within-attack randomness | 0.05 | 26% | 40% | 37% | 37% | 48% | 47% |
| moderate within-attack randomness | 0.10 | 77% | 91% | 93% | 92% | 94% | 96% |
| near-deterministic attacks | 0.05 | 34% | 42% | 43% | 44% | 51% | 60% |
| near-deterministic attacks | 0.10 | 75% | 91% | 97% | 97% | 99% | 100% |

- **At temperature 0 (the project's setting for models that allow it) a repeat returns the same answer, so repeats buy exactly nothing.** Models flagged `deterministic: false` are the only place repeats could help.
- Where repeats do help, they plateau by about 3 (the remaining error is which attacks you chose and which languages you sampled, which repeats cannot touch), and **new phrasings beat repeats** per call: 30 distinct attacks (2x the calls) match or beat 15 attacks repeated 3 times (3x the calls) in both scenarios. Prefer new phrasings, which also improve how well results generalize beyond the 15 bank attacks.
- The tier gap is mainly limited by the 28 and 35 languages, not the 15 attacks: going from 15 to 75 attacks takes 5-point-gap power only from 26% to 47%.

### 3.7 Property tests for each new method

I wrote and ran these (appendix `test_new_stats_properties.py`, seed 20261005): **25 of 25 pass** in about 22 seconds. They follow the style of the existing `test_stats_properties.py`: rules that must hold for every input, checked on random inputs.

| method | properties checked |
|---|---|
| e-process / confidence sequence | never negative; a score above the null mean never lowers it and below never raises it; data at exactly the null mean leaves it at 1; under a symmetric null it crosses 40 at any time in at most 2.5% of runs (saw 0.6% of 1500); the 95% confidence sequence misses the true mean at some time in at most 5% of runs (saw 0 of 600); sign e-process after 15 favourable pairs within the 1.75^15 cap |
| shrinkage | `beta_ppf` inverts `beta_cdf`; every shrunk rate lies between its raw rate and the prior mean; interval contains its posterior mean; more breaks never lowers the shrunk rate; fit does not depend on language order; identical languages shrink to the common rate |
| trend test | unchanged by any increasing transform of the resource measure; reversing x flips rho and leaves the two sided p alone; p within [1/(B+1), 1] and rho within [-1, 1]; perfect monotone data gives rho = -1 and exactly the smallest p; with no relationship it rejects 4.7% of 300 runs |
| multiplicity | Holm never below raw or above 1; Holm never more conservative than Bonferroni; BH never above Holm; BY never below BH; simultaneous Wilson interval wider than the single interval and contains the estimate |
| capability adjustment | with perfect controls the adjusted gap equals the naive gap; never uses a rate above 1 |
| tie fix | `9/15 - 3/15` counts as tied with `8/15 - 2/15` under the tolerance and not under plain `>=` |

Properties I did **not** write but recommend when each method ships: a differential test comparing the tie safe max-gap p-value to one computed with `fractions.Fraction` (no float error possible); a replay test that an early stopped scan recomputed from its rows gives the same e-value and stopping pair (like `cli.py replay`); a test that the language order for the sequential scan depends only on the recorded seed; and for any stratified permutation, that it is unchanged by the order of attacks and equals the pooled test when only one attack exists. Add each new function to `mutation_check.py` so a planted bug (for example flipping the sign of the clip, or using the current instead of the previous variance in the bet) is caught.

---

## 4. What PolyGuard should do

### Ranked changes

| # | change | where | effort | preregistration impact | risk |
|---|---|---|---|---|---|
| 1 | Make the tie comparison float safe: `if g >= observed - 1e-12:` (engine.py, `max_gap_permutation_test`, the line `if g >= observed:`), plus a differential test against exact fractions | engine.py, test_stats_properties.py | 1 h | Log as an implementation correction in the deviation log (no live data exists, no result changes hands). Previously saved mock bundles replay with a p-value that differs in the third decimal | low |
| 2 | Reword what the max-gap test claims: "is any language different from English beyond chance", not "are low-resource languages worse". Add one sentence to the report and to the docstring; add one sentence to the Worst-language claim bullet of PREREGISTRATION.md | engine.py docstring, report_html.py, PREREGISTRATION.md | 1 to 2 h | Wording only, no analysis change | low |
| 3 | Add the trend permutation test with a frozen resource table (mean Common Crawl page share over CC-MAIN-2026-17 to 2026-39, 87 values, with the SHA-256 of the file stored beside it, like the bank fingerprint) and a bootstrap slope interval. Report next to Mann-Whitney, never instead of it | languages_catalog.py or a new `resource_share.py`; engine.py `trend_permutation_test`; tests | 4 to 6 h | Add as a **pre-specified secondary analysis** in the deviation log before the first live scan; Mann-Whitney remains the headline (rule 2) | low to medium: construct validity of the measure |
| 4 | Show a shrunk per language estimate beside each Wilson interval, labelled descriptive. Never feed shrunk or covariate-shrunk values into any test | new `shrink.py` imported by engine.py summarize; report_html.py | 5 to 6 h | None (descriptive) | low to medium: users may read it as a measurement |
| 5 | Replace the headline per language significance with Holm adjusted flags (and the Fisher thresholds in the report), keep the "not corrected for 87 looks" label on the table | engine.py new `holm_adjust`; report_html.py | 2 h | State the family (1 primary, 1 trend, 5 H3 with BH, 86 per language with Holm) in the deviation log | low |
| 6 | Add the tier level ratio adjusted gap as an exploratory line, and print how many languages the capability flag could ever flag given English's control rate | engine.py `capability_report` / `tier_rates`; report | 3 h | Exploratory only; pre-registered exclusion rule unchanged | low if labelled; the toy model's assumptions must be quoted next to the number |
| 7 | Rebuild `power_simulation` with a between language sd, and recompute the minimum detectable gap from the first live scan's fitted beta-binomial precision before reading any null | engine.py | 3 h | Strengthens the null reporting rule | low |
| 8 | Sequential tier scan mode: `sequential_tier_scan(fire, high, low, seed, alpha=0.025, scale=0.30)`; CLI `--sequential`; put the order seed, alpha, scale and "sequential" into `instrument()` and `COMPARABLE_FIELDS` so an early stopped scan is never compared with a full one; suppress the Mann-Whitney p when stopped early and print the e-value and confidence sequence instead | engine.py, cli.py, api/ (cancellation interacts) | 10 to 14 h | New scan mode: log as a deviation before first live scan. **The pre-registered research scan still runs all 87 languages**; sequential is for user facing scans and for any multi-model run where cost binds | medium: complexity, and it cannot run live until `expand_languages.py` adds the 35 low languages |
| 9 | Optional: report the attack stratified max-gap p next to the pooled one | engine.py | 2 h | Exploratory only | low |
| 10 | Update the PREREGISTRATION.md instrument table (52 languages, 780 attacks, 312 controls, 0 low) | PREREGISTRATION.md | 0.5 h | Housekeeping row in the deviation log | none |

**Cost view (Opinion):** the only item here that saves calls is #8. On the simulated numbers it removes about 18% of attack calls at a 10 point gap, 36% at 15 points and 52% at 20 points compared with its own 28 pair design; the full 87 language research scan is unaffected. Everything else adds rigor or honesty at zero API cost.

### Draft deviation log rows (paste after checking; fill the date when you commit)

- *Implementation correction, tie comparison in `max_gap_permutation_test`.* "Floating point comparison of tied permutation gaps replaced by a 1e-12 tolerance. No live data, no stated result changes; saved mock replays differ in the third decimal of p."
- *Secondary analysis added before any live data: rank trend of per language break rate against log10 Common Crawl page share (87 languages), two sided permutation p at 0.05 with 10,000 shuffles and a fixed seed, bootstrap slope interval. Mann-Whitney remains the primary test and the headline.* "Uses all 87 languages including the mid tier the primary test omits, and avoids the tier cut offs, two of which (Gujarati, Kyrgyz) sit below some low-resource languages on this measure."
- *Optional sequential scan mode added; the research scan is unchanged.* "Efficacy rule: e-process on clipped paired tier differences reaches 40; seeded random language order; early stop disables the Mann-Whitney p-value for that scan."

### What NOT to do

- **Do not switch the primary test.** Mann-Whitney is already the strongest H1 test in the cliff world and within a few points of the best in the gradient world; the trend test is a pre-specified secondary.
- **Do not claim "resource gap found" from the max-gap p-value.** It rejects 7% to 19% of the time with no tier effect once languages vary.
- **Do not run per language sequential testing or e-BH on 15 attacks.** No savings, nearly zero discoveries.
- **Do not use sequential Monte Carlo testing to save API money.** It saves shuffles, which cost nothing.
- **Do not read an early-stop futility result as "no gap".** At 28 pairs it rarely fires and means only "under 10 points".
- **Do not repeat the same attack at temperature 0.** The reply repeats; you pay for nothing.
- **Do not display empirical Bayes intervals, or any covariate-adjusted shrinkage, as measurements.** They under-cover when errors are shared, and the covariate version makes the trend test circular.
- **Do not describe the ratio adjusted gap as bounds**, and do not add new capability exclusions after seeing data.
- **Do not drop the mid tier or the 7 spare low languages from the research scan to save money**; that is the 36% of the saving that costs you the trend test and the per language table.
- **Do not trust the unchecked parts of this document:** items marked [unverified] or [abstract only] need their source opened before they appear in a submission.

---

## 5. Sources

Status key: **full** = full text opened and the cited passage read; **page** = the paper's page with title, authors and abstract opened; **search** = only a search result snippet was seen (do not cite without opening).

1. Waudby-Smith and Ramdas, "Estimating means of bounded random variables by betting", arXiv:2010.09686v7 (published in JRSSB 2024). **full** (pdf downloaded and read for eq. 24 to 26, Theorem 3, Ville's inequality). https://arxiv.org/abs/2010.09686
2. Howard, Ramdas, McAuliffe, Sekhon, "Time-uniform, nonparametric, nonasymptotic confidence sequences", Annals of Statistics 49(2), 2021. **page**. https://arxiv.org/abs/1810.08240
3. Grunwald, de Heide, Koolen, "Safe Testing", JRSSB (discussion paper), arXiv:1906.07801. **page**. https://arxiv.org/abs/1906.07801
4. Ramdas, Grunwald, Vovk, Shafer, "Game-theoretic statistics and safe anytime-valid inference", arXiv:2210.01948. **page**. https://arxiv.org/abs/2210.01948
5. Waudby-Smith and Ramdas, "Confidence sequences for sampling without replacement", arXiv:2006.04347. **page**. https://arxiv.org/abs/2006.04347
6. Turner, Ly, Grunwald, "Generic e-variables for exact sequential k-sample tests that allow for optional stopping", arXiv:2106.02693 (J. Stat. Plan. Inference 230, 2024). **page**. https://arxiv.org/abs/2106.02693
7. Fischer and Ramdas, "Sequential Monte-Carlo testing by betting", arXiv:2401.07365 (JRSSB 2025). **page**. https://arxiv.org/abs/2401.07365
8. Wang and Ramdas, "False discovery rate control with e-values", arXiv:2009.02824. **page**. https://arxiv.org/abs/2009.02824
9. Holm, "A simple sequentially rejective multiple test procedure", Scandinavian Journal of Statistics 6(2), 1979, 65 to 70. **full** (pdf read). https://www.ime.usp.br/~abe/lista/pdf4R8xPVzCnX.pdf
10. Benjamini and Hochberg, "Controlling the false discovery rate", JRSSB 57(1), 1995, 289 to 300. **full** (pdf read). https://www.dcscience.net/Benjamini-Hochberg-1995-FDR.pdf
11. Benjamini and Yekutieli, "False discovery rate-adjusted multiple confidence intervals for selected parameters", JASA 100, 2005, 71 to 81. **search** (abstract text only). Related page opened: Yekutieli, "Adjusted Bayesian inference for selected parameters", arXiv:0801.0499 (**page**). https://arxiv.org/abs/0801.0499
12. Phipson and Smyth, "Permutation p-values should never be zero", Stat. Appl. Genet. Mol. Biol. 9(1), 2010, arXiv:1603.05766. **page**. https://arxiv.org/abs/1603.05766
13. Brown, Cai, DasGupta, "Interval estimation for a binomial proportion", Statistical Science 16(2), 2001, 101 to 133. **page**. https://projecteuclid.org/euclid.ss/1009213286
14. Efron and Morris, "Data analysis using Stein's estimator and its generalizations", JASA 70(350), 1975, 311 to 319. **full** (pdf read). https://doi.org/10.1080/01621459.1975.10479864
15. Robbins, "An empirical Bayes approach to statistics", Proc. Third Berkeley Symposium, vol. 1, 1956, 157 to 163. **page** (title and venue). https://projecteuclid.org/euclid.bsmsp/1200501653
16. Armstrong, Kolesar, Plagborg-Moller, "Robust empirical Bayes confidence intervals", Econometrica 90(6), 2022, arXiv:2004.03448. **page**. https://arxiv.org/abs/2004.03448
17. Montgomery, Nyhan, Torres, "How conditioning on posttreatment variables can ruin your experiment and what to do about it", AJPS 62(3), 2018, 760 to 775. **full** (pdf read; quote on bias direction and size from its introduction). https://profiles.wustl.edu/en/publications/how-conditioning-on-posttreatment-variables-can-ruin-your-experim/
18. Lee, "Training, wages, and sample selection: estimating sharp bounds on treatment effects", Review of Economic Studies 76(3), 2009, 1071 to 1102. **page** (NBER working paper abstract). https://www.nber.org/papers/w11721
19. Frangakis and Rubin, "Principal stratification in causal inference", Biometrics 58(1), 2002, 21 to 29. **search** (abstract text only).
20. Joshi, Santy, Budhiraja, Bali, Choudhury, "The state and fate of linguistic diversity and inclusion in the NLP world", ACL 2020. **page**. https://aclanthology.org/2020.acl-main.560/
21. Common Crawl, per language page share statistics (CLD2 language identification, 160 languages) and languages.csv, downloaded 2026-10-05. **page and data file**. https://commoncrawl.github.io/cc-crawl-statistics/plots/languages
22. Westfall and Young, "Resampling-based multiple testing", 1993. **not opened** [unverified]; only secondary descriptions seen.
23. Benjamini and Yekutieli, "The control of the false discovery rate in multiple testing under dependency", Annals of Statistics 29(4), 2001. **not opened** [unverified]; used only for the harmonic number factor.
24. Repo files read: engine.py, PREREGISTRATION.md, test_stats_properties.py, docs/pilot-plan.md, attack_bank.json, languages_catalog.py, RELATED_WORK.md.

**Simulation seeds (summary):** power and size 20261006 to 20261065 (cell index added to 20261005); minimum detectable gap grid 20261601 to 20261636; sequential 20261201 to 20261224; sequential null check 20261501 to 20261524; shrinkage 20261300 to 20261302; repeats 20261401 to 20261424; tie size check 20261100 to 20261114; capability scenarios seeds 1 to 4; property tests 20261005. numpy 2.5.1, Python 3.14.3.

---

## 6. Appendix: code (everything below was run; results above come from it)

Save `sim_power2.py` as `sim_power.py` (the other scripts import it under that name); `sim_mde.py` imports it as `sim_power2`, so keep both names or edit one import. Download `cc_languages.csv` from https://commoncrawl.github.io/cc-crawl-statistics/plots/languages.csv into the same folder. Copy `engine.py`, `providers.py` and `languages_catalog.py` beside them. Run order: `ccshare.py` is imported by the others; the standard library modules `anytime.py`, `shrink.py`, `newstats.py` are the proposed additions.

#### anytime.py

```python
"""Pure standard library: betting e-process and confidence sequence for the mean of [0,1] data
(Waudby-Smith and Ramdas 2024, predictable plug-in lambda), plus a sequential sign e-process."""
import math

def prpl_lambda(t, sigma2_prev, alpha):
    """lambda_t = sqrt(2 log(2/alpha) / (sigma2_{t-1} * t * log(1+t)))  (their eq. 26, before truncation)"""
    return math.sqrt(2 * math.log(2 / alpha) / (sigma2_prev * t * math.log(1 + t)))

class Betting:
    """Test H0: mean <= m0 (one sided) and track a confidence sequence for the mean, X in [0,1]."""
    def __init__(self, m0=0.5, alpha=0.05, c=0.5, grid=201, theta=0.5):
        self.m0, self.alpha, self.c, self.theta = m0, alpha, c, theta
        self.t, self.sum_x, self.sum_sq = 0, 0.0, 0.0
        self.mu_hat, self.sigma2 = 0.5, 0.25
        self.ms = [(i + 0.5) / grid for i in range(grid)]          # grid of candidate means
        self.kp = [1.0] * grid; self.km = [1.0] * grid              # K+ and K- for every m
        self.e0 = 1.0                                               # K+(m0): the e-process for H0
        self.e0_max = 1.0

    def update(self, x):
        t = self.t + 1
        lam = prpl_lambda(t, self.sigma2, self.alpha)               # predictable: uses data up to t-1
        for j, m in enumerate(self.ms):
            lp = min(lam, self.c / m); lm = min(lam, self.c / (1 - m))
            self.kp[j] *= 1 + lp * (x - m); self.km[j] *= 1 - lm * (x - m)
        self.e0 *= 1 + min(lam, self.c / self.m0) * (x - self.m0)
        self.e0_max = max(self.e0_max, self.e0)
        self.t, self.sum_x = t, self.sum_x + x
        self.mu_hat = (0.5 + self.sum_x) / (t + 1)                  # mu_hat_t uses x_t
        self.sum_sq += (x - self.mu_hat) ** 2
        self.sigma2 = (0.25 + self.sum_sq) / (t + 1)
        return self.e0

    def cs(self):
        """(lo, hi) of {m : hedged capital < 1/alpha}; grid resolution 1/grid."""
        thr = 1 / self.alpha
        keep = [m for m, a, b in zip(self.ms, self.kp, self.km)
                if max(self.theta * a, (1 - self.theta) * b) < thr]
        return (min(keep), max(keep)) if keep else (None, None)

class SignBet:
    """Sequential sign test for paired binary data: only discordant pairs count.
    z=1 if the language broke and English held, z=0 for the reverse.  H0: P(z=1)=1/2."""
    def __init__(self):
        self.e, self.fav, self.n = 1.0, 0, 0
    def update(self, z):
        phat = (1 + self.fav) / (2 + self.n)                        # Laplace smoothed, predictable
        lam = min(0.75, max(0.0, 2 * phat - 1))                     # Kelly fraction for even odds
        self.e *= 1 + lam * (2 * z - 1)
        self.fav += z; self.n += 1
        return self.e
```


#### shrink.py

```python
"""Pure standard library: beta-binomial empirical Bayes with an optional covariate, posterior intervals."""
import math

def _betacf(a, b, x):                       # continued fraction for the incomplete beta (Lentz)
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny); h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c; c = c if abs(c) > tiny else tiny
        delta = d * c; h *= delta
        if abs(delta - 1.0) < 3e-14: break
    return h

def beta_cdf(x, a, b):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1) / (a + b + 2): return math.exp(lbt) * _betacf(a, b, x) / a
    return 1 - math.exp(lbt) * _betacf(b, a, 1 - x) / b

def beta_ppf(q, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if beta_cdf(mid, a, b) < q: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def bb_loglik(ks, n, mus, phi):
    ll = 0.0
    for k, mu in zip(ks, mus):
        a, b = mu * phi, (1 - mu) * phi
        ll += (math.lgamma(k + a) + math.lgamma(n - k + b) - math.lgamma(n + a + b)
               + math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b))   # binomial coefficient is constant
    return ll

def _nelder_mead(f, x0, step=0.5, iters=300):
    n = len(x0); pts = [list(x0)] + [[x0[j] + (step if j == i else 0) for j in range(n)] for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i]); pts = [pts[i] for i in order]; vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < 1e-9: break
        cen = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        tr = lambda t: [cen[j] + t * (pts[-1][j] - cen[j]) for j in range(n)]
        xr = tr(-1.0); fr = f(xr)
        if fr < vals[0]:
            xe = tr(-2.0); fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]: pts[-1], vals[-1] = xr, fr
        else:
            xc = tr(0.5); fc = f(xc)
            if fc < vals[-1]: pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]; vals[i] = f(pts[i])
    i = min(range(n + 1), key=lambda i: vals[i]); return pts[i], vals[i]

def expit(z): return 1 / (1 + math.exp(-z))

def fit_eb(ks, n, xs=None):
    """Return dict(a, b, phi, loglik). mu_l = expit(a + b*x_l) (b=0 when xs is None); phi = prior sample size."""
    xs = xs or [0.0] * len(ks); free_b = any(x != 0.0 for x in xs)
    def nll(p):
        a, lphi = p[0], p[1]; b = p[2] if free_b else 0.0
        phi = math.exp(max(-5.0, min(8.0, lphi)))
        return -bb_loglik(ks, n, [min(1 - 1e-9, max(1e-9, expit(a + b * x))) for x in xs], phi)
    p0 = [math.log(max(sum(ks), 0.5) / max(n * len(ks) - sum(ks), 0.5)), math.log(5.0)] + ([0.0] if free_b else [])
    best, val = _nelder_mead(nll, p0)
    return {"a": best[0], "b": best[2] if free_b else 0.0, "phi": math.exp(max(-5.0, min(8.0, best[1]))), "loglik": -val}

def posterior(ks, n, fit, xs=None, level=0.95):
    xs = xs or [0.0] * len(ks); out = []
    for k, x in zip(ks, xs):
        mu = expit(fit["a"] + fit["b"] * x); a0, b0 = mu * fit["phi"], (1 - mu) * fit["phi"]
        a, b = a0 + k, b0 + n - k; t = (1 - level) / 2
        out.append((a / (a + b), beta_ppf(t, a, b), beta_ppf(1 - t, a, b), a, b))
    return out
```


#### newstats.py

```python
"""Pure standard library: trend permutation test, Holm and Benjamini-Yekutieli adjustments,
simultaneous Wilson intervals, ratio adjusted tier gap, tie safe max-gap comparison."""
import math, random
from statistics import NormalDist


def avg_ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i]); rk = [0.0] * len(v); i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]: j += 1
        for k in range(i, j + 1): rk[order[k]] = (i + j) / 2
        i = j + 1
    return rk


def _corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    sa = sum((u - ma) ** 2 for u in a); sb = sum((u - mb) ** 2 for u in b)
    if sa == 0 or sb == 0: return 0.0
    return sum((u - ma) * (w - mb) for u, w in zip(a, b)) / math.sqrt(sa * sb)


def trend_permutation_test(rates, x, n_iter=5000, seed=20261005, eps=1e-12):
    """Spearman correlation between per-language break rate and a continuous resource measure x
    (for example log10 Common Crawl share). The language is the unit. The p-value shuffles x across
    languages, add-one so it is never 0. Two sided; rho below 0 means less resource, more breaks."""
    n = len(rates)
    if n < 5 or n != len(x): return {"rho": None, "p": None, "n": n}
    ry, rx = avg_ranks(rates), avg_ranks(x)
    obs = _corr(ry, rx); rng = random.Random(seed); ge = 0; rx = rx[:]
    for _ in range(n_iter):
        rng.shuffle(rx)
        if abs(_corr(ry, rx)) >= abs(obs) - eps: ge += 1
    my, mx = sum(rates) / n, sum(x) / n
    sxx = sum((u - mx) ** 2 for u in x)
    slope = sum((u - mx) * (r - my) for u, r in zip(x, rates)) / sxx if sxx else None
    return {"rho": obs, "p": (ge + 1) / (n_iter + 1), "slope_per_unit_x": slope, "n": n, "n_iter": n_iter}


def bootstrap_slope_ci(rates, x, n_boot=2000, seed=7, conf=0.95):
    """Percentile interval for the OLS slope, resampling LANGUAGES (the unit)."""
    rng = random.Random(seed); n = len(rates); out = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        xs, ys = [x[i] for i in idx], [rates[i] for i in idx]
        mx, my = sum(xs) / n, sum(ys) / n; sxx = sum((u - mx) ** 2 for u in xs)
        if sxx > 0: out.append(sum((u - mx) * (r - my) for u, r in zip(xs, ys)) / sxx)
    out.sort(); t = (1 - conf) / 2
    return out[int(t * len(out))], out[min(len(out) - 1, int((1 - t) * len(out)))]


def holm_adjust(ps):
    """Holm step-down adjusted p-values, in input order. Never below the raw p, never above 1."""
    m = len(ps); order = sorted(range(m), key=lambda i: ps[i]); adj = [0.0] * m; run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i])); adj[i] = run
    return adj


def by_adjust(ps):
    """Benjamini-Yekutieli adjusted p-values: BH times the harmonic number, valid under any dependence."""
    m = len(ps); h = sum(1 / i for i in range(1, m + 1))
    order = sorted(range(m), key=lambda i: ps[i]); adj = [0.0] * m; prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]; prev = min(prev, ps[i] * m * h / rank, 1.0); adj[i] = prev
    return adj


def simultaneous_wilson(k, n, m, alpha=0.05):
    """Continuity corrected Wilson interval at level 1 - alpha/m (Bonferroni over m languages).
    Needs engine.wilson_ci_cc, imported lazily so this file stays standalone."""
    import engine
    z = NormalDist().inv_cdf(1 - alpha / (2 * m))
    return engine.wilson_ci_cc(k, n, z=z)


def ratio_adjusted_gap(rate_lo, ctrl_lo, rate_hi, ctrl_hi, floor=1 / 12):
    """Exploratory: tier mean break rate divided by tier mean control rate (capped at 1), low minus high.
    Reads as 'attack success among attacks the bot understood', under the assumptions in section 5."""
    m = lambda v: sum(v) / len(v)
    adj = lambda r, c: min(1.0, m(r) / max(m(c), floor))
    return adj(rate_lo, ctrl_lo) - adj(rate_hi, ctrl_hi)


def same_or_more_extreme(g, observed, tol=1e-12):
    """The tie safe comparison for max_gap_permutation_test: replaces `g >= observed`."""
    return g >= observed - tol
```


#### test_new_stats_properties.py

```python
"""Property tests for the proposed methods. Run: python test_new_stats_properties.py"""
import math, random, sys
import engine, newstats as N, anytime as A, shrink as H

RNG = random.Random(20261005)
CASES = []


def prop(name, ok):
    CASES.append((name, bool(ok)))


def close(a, b, t=1e-9):
    return abs(a - b) <= t


# --- e-process and confidence sequence (anytime.py)
ok_nonneg = ok_dir = True
for _ in range(200):
    b = A.Betting(m0=0.5)
    prev = 1.0
    for t in range(RNG.randint(1, 30)):
        x = RNG.random()
        e = b.update(x)
        ok_nonneg &= e >= 0
        ok_dir &= (e >= prev - 1e-12) if x > 0.5 else (e <= prev + 1e-12)
        prev = e
prop("the e-process is never negative", ok_nonneg)
prop("a data point above the null mean never lowers the e-process, below never raises it", ok_dir)
b = A.Betting(m0=0.5)
for _ in range(20):
    b.update(0.5)
prop("data exactly at the null mean leave the e-process at 1", close(b.e0, 1.0))

fa, N_RUN = 0, 1500
for r in range(N_RUN):
    rg = random.Random(r)
    b = A.Betting(m0=0.5, alpha=0.05, c=0.75, grid=1)
    hit = False
    for t in range(28):
        d = rg.gauss(0, 0.25)             # symmetric null with sd .25, clipped like the real scan
        if b.update((1 + max(-1.0, min(1.0, d / 0.3))) / 2) >= 40:
            hit = True
            break
    fa += hit
prop(f"under a symmetric null the e-process crosses 1/alpha=40 at ANY time in at most 2.5% of runs (saw {fa / N_RUN:.3%})",
     fa / N_RUN <= 0.025 + 3 * math.sqrt(0.025 * 0.975 / N_RUN))

miss, N_CS = 0, 600
for r in range(N_CS):
    rg = random.Random(10_000 + r)
    b = A.Betting(alpha=0.05, c=0.5, grid=101)
    bad = False
    for t in range(30):
        b.update(rg.betavariate(2, 3))     # true mean 0.4
        lo, hi = b.cs()
        if lo is None or not (lo - 0.5 / 101 <= 0.4 <= hi + 0.5 / 101):
            bad = True
            break
    miss += bad
prop(f"the 95% confidence sequence misses the true mean at some time in at most 5% of runs (saw {miss / N_CS:.3%})",
     miss / N_CS <= 0.05 + 3 * math.sqrt(0.05 * 0.95 / N_CS))
s = A.SignBet()
for _ in range(15):
    s.update(1)
prop("the sign e-process after 15 favourable discordant pairs stays within the cap 1.75^15", s.e <= 1.75 ** 15 + 1e-6)

# --- shrinkage (shrink.py)
ok_cdf = all(abs(H.beta_cdf(H.beta_ppf(q, a, b), a, b) - q) < 1e-9
             for q in (0.025, 0.5, 0.975) for a in (0.7, 2.5, 9) for b in (0.9, 4.0, 11))
prop("beta_ppf inverts beta_cdf", ok_cdf)
ks = [RNG.randint(0, 15) for _ in range(40)]
f = H.fit_eb(ks, 15)
post = H.posterior(ks, 15, f)
mu = H.expit(f["a"])
prop("each shrunk rate lies between its raw rate and the prior mean",
     all(min(k / 15, mu) - 1e-9 <= p[0] <= max(k / 15, mu) + 1e-9 for k, p in zip(ks, post)))
prop("a shrunk interval contains its own posterior mean", all(p[1] <= p[0] <= p[2] for p in post))
prop("more breaks never gives a lower shrunk rate (same prior)",
     all(post[i][0] <= post[j][0] + 1e-12 for i in range(40) for j in range(40) if ks[i] <= ks[j]))
perm = ks[:]
RNG.shuffle(perm)
fp = H.fit_eb(perm, 15)
prop("the fit does not depend on the order of the languages",
     close(fp["phi"], f["phi"], 1e-3 * f["phi"]) and close(fp["a"], f["a"], 1e-3))
same = H.fit_eb([5] * 30, 15)
prop("identical languages shrink almost fully to the common rate",
     abs(H.posterior([5] * 30, 15, same)[0][0] - 1 / 3) < 0.01)

# --- trend test, multiplicity, controls (newstats.py)
ok_inv = ok_flip = ok_range = True
for _ in range(80):
    n = RNG.randint(8, 40)
    x = [RNG.gauss(0, 1) for _ in range(n)]
    y = [RNG.randint(0, 15) / 15 for _ in range(n)]
    t1 = N.trend_permutation_test(y, x, 400, seed=1)
    t2 = N.trend_permutation_test(y, [math.exp(v) for v in x], 400, seed=1)
    t3 = N.trend_permutation_test(y, [-v for v in x], 400, seed=1)
    ok_inv &= close(t1["p"], t2["p"], 1e-12) and close(t1["rho"], t2["rho"], 1e-9)
    ok_flip &= close(t1["rho"], -t3["rho"], 1e-9) and close(t1["p"], t3["p"], 1e-12)
    ok_range &= 1 / 401 <= t1["p"] <= 1 and -1 <= t1["rho"] <= 1
prop("the trend test depends on ranks only: any increasing transform of the resource measure changes nothing", ok_inv)
prop("reversing the resource measure flips the sign of rho and leaves the two sided p alone", ok_flip)
prop("trend p is within [1/(B+1), 1] and rho within [-1, 1]", ok_range)
xs = list(range(60))
perfect = N.trend_permutation_test([-v / 60 for v in xs], xs, 999, seed=3)
prop("a perfect monotone relationship gives rho = -1 and the smallest possible p",
     close(perfect["rho"], -1.0) and close(perfect["p"], 1 / 1000, 1e-12))
nul = sum(N.trend_permutation_test([RNG.randint(0, 15) / 15 for _ in range(87)],
                                   [RNG.gauss(0, 1) for _ in range(87)], 199, seed=i)["p"] < 0.05
          for i in range(300))
prop(f"with no relationship the trend test rejects about 5% of the time (saw {nul / 300:.1%})", 0.02 <= nul / 300 <= 0.09)

ok_h = ok_bonf = ok_by = ok_bh = True
for _ in range(300):
    ps = [RNG.random() ** 2 for _ in range(RNG.randint(1, 30))]
    m = len(ps)
    h, by, bh = N.holm_adjust(ps), N.by_adjust(ps), engine.benjamini_hochberg(ps)
    ok_h &= all(a + 1e-12 >= p and a <= 1 for a, p in zip(h, ps))
    ok_bonf &= all(a <= min(1, m * p) + 1e-12 for a, p in zip(h, ps))
    ok_bh &= all(b <= a + 1e-12 for a, b in zip(h, bh))
    ok_by &= all(b <= y + 1e-12 for b, y in zip(bh, by))
prop("Holm adjusted p is never below raw nor above 1", ok_h)
prop("Holm is never more conservative than Bonferroni", ok_bonf)
prop("Benjamini-Hochberg adjusted p is never above Holm adjusted p", ok_bh)
prop("Benjamini-Yekutieli adjusted p is never below Benjamini-Hochberg", ok_by)
lo1, hi1 = engine.wilson_ci_cc(4, 15)
lo2, hi2 = N.simultaneous_wilson(4, 15, 87)
prop("the simultaneous interval is wider than the single interval and still contains the estimate",
     lo2 <= lo1 and hi2 >= hi1 and lo2 <= 4 / 15 <= hi2)
prop("with perfect controls the ratio adjusted gap equals the naive gap",
     close(N.ratio_adjusted_gap([.4, .2], [1, 1], [.2, .1], [1, 1]), .3 - .15))
prop("the ratio adjusted gap never uses a rate above 1", abs(N.ratio_adjusted_gap([.9], [.1], [.1], [1.0])) <= 1.0)
prop("the tie safe comparison counts 9/15-3/15 as tied with 8/15-2/15 where plain >= does not",
     N.same_or_more_extreme(9 / 15 - 3 / 15, 8 / 15 - 2 / 15) and not (9 / 15 - 3 / 15 >= 8 / 15 - 2 / 15))

passed = sum(ok for _, ok in CASES)
for n, ok in CASES:
    print(f"  [{'PASS' if ok else 'FAIL'}] {n}")
print(f"\n{passed}/{len(CASES)} properties hold")
sys.exit(0 if passed == len(CASES) else 1)
```


#### ccshare.py

```python
import csv, math
from languages_catalog import CATALOG
M = dict(en='eng',es='spa',hi='hin',gu='guj',zh='zho',tl='tgl',vi='vie',ar='ara',ko='kor',fr='fra',ru='rus',pt='por',de='deu',it='ita',ja='jpn',pl='pol',tr='tur',id='ind',uk='ukr',el='ell',nl='nld',sv='swe',no='nor',da='dan',fi='fin',cs='ces',sk='slk',hu='hun',ro='ron',bg='bul',hr='hrv',sr='srp',sl='slv',lt='lit',lv='lav',et='est',mk='mkd',sq='sqi',is_='isl',ga='gle',cy='cym',eu='eus',ca='cat',gl='glg',he='heb',fa='fas',ps='pus',az='aze',kk='kaz',uz='uzb',ky='kir',tg='tgk',mn='mon',ka='kat',hy='hye',bn='ben',ur='urd',pa='pan',ta='tam',te='tel',mr='mar',kn='kan',ml='mal',or_='ori',ne='nep',si='sin',th='tha',ms='msa',km='khm',lo='lao',my='mya',jv='jav',su='sun',ceb='ceb',sw='swa',am='amh',ha='hau',yo='yor',ig='ibo',zu='zul',xh='xho',so='som',sn='sna',rw='kin',ny='nya',af='afr',ht='hat')
M['is']=M.pop('is_'); M['or']=M.pop('or_')
rows=list(csv.DictReader(open('cc_languages.csv',encoding='utf-8')))
crawls=sorted({r['crawl'] for r in rows})[-6:]
d={}
for r in rows:
    if r['crawl'] in crawls:
        d.setdefault(r['primary_language'],[]).append(float(r['%pages/crawl']))
avg={k:sum(v)/len(v) for k,v in d.items()}
miss=[c for c in CATALOG if c not in M]
print('unmapped',miss)
notin=[(c,M[c]) for c in CATALOG if M[c] not in avg]
print('not in CC data',notin)
share={c:avg.get(M[c]) for c in CATALOG}
if __name__=='__main__':
    from collections import defaultdict
    t=defaultdict(list)
    for c,v in share.items():
        if v: t[CATALOG[c]['tier']].append(math.log10(v))
    for k,v in t.items(): print(k,len(v),round(sum(v)/len(v),2),round(min(v),2),round(max(v),2))
    low=sorted((v,c) for c,v in share.items() if v)[:12]; print(low)
```


#### sim_power.py (run as sim_power2.py)

```python
"""Power and size of four tests on the 87-language design. numpy used for speed only."""
import math, sys, random
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, '.')
from languages_catalog import CATALOG
from ccshare import share
import engine

CODES = list(CATALOG)                       # 'en' first
TIER = np.array([CATALOG[c]['tier'] for c in CODES])
LOGX = np.array([math.log10(share[c]) for c in CODES])
Z = (LOGX - LOGX.mean()) / LOGX.std()       # high resource = positive
HI, LO = TIER == 'high', TIER == 'low'
N_ATT = 15
GH = np.random.default_rng(1).standard_normal(5000)

def exp_rate(m, s):                         # E[logistic(m + s N)]
    return float(np.mean(1 / (1 + np.exp(-(m + s * GH)))))

def calibrate(p_hi, gap, s_tot, dgp):
    """Pick intercept and slope so that E[rate | high tier] = p_hi and
    E[low tier] - E[high tier] = gap, averaged over the real language set."""
    def means(a, b):
        eta = a + (-b * Z if dgp == 'trend' else b * (np.where(LO, 1, 0) - np.where(HI, 1, 0)) / 2)
        r = np.array([exp_rate(e, s_tot) for e in eta])
        return r[HI].mean(), r[LO].mean()
    lo_b, hi_b = 0.0, 8.0
    a = 0.0
    for _ in range(40):                     # nested bisection, monotone in each argument
        b = (lo_b + hi_b) / 2
        a_lo, a_hi = -6.0, 4.0
        for _ in range(30):
            a = (a_lo + a_hi) / 2
            if means(a, b)[0] < p_hi: a_lo = a
            else: a_hi = a
        h, l = means(a, b)
        if l - h < gap: lo_b = b
        else: hi_b = b
    return a, (lo_b + hi_b) / 2

def draw(a, b, tau, sig_a, sig_e, dgp, rng):
    eta = a + (-b * Z if dgp == 'trend' else b * (np.where(LO, 1, 0) - np.where(HI, 1, 0)) / 2)
    eta = eta + tau * rng.standard_normal(len(CODES))                       # language effect
    att = sig_a * rng.standard_normal(N_ATT)                                 # attack difficulty
    inter = sig_e * rng.standard_normal((len(CODES), N_ATT))                 # translation quirks
    p = 1 / (1 + np.exp(-(eta[:, None] + att[None, :] + inter)))
    return (rng.random(p.shape) < p).astype(np.int8)

def maxgap(Y):
    r = Y.mean(1); return r[1:].max() - r[0]

def perm_maxgap(Y, B, rng, strat):
    obs = maxgap(Y); ge = 0
    flat = Y.ravel().copy()
    for _ in range(B):
        if strat: P = rng.permuted(Y, axis=0)
        else:
            rng.shuffle(flat); P = flat.reshape(Y.shape)
        ge += maxgap(P) >= obs - 1e-12
    return (ge + 1) / (B + 1)

def perm_trend(r, B, rng, spearman=True):
    x = Z
    if spearman:
        rank = lambda v: np.argsort(np.argsort(v)).astype(float)   # ties: see note in doc
        # average ranks for ties
        def avgrank(v):
            order = np.argsort(v, kind='stable'); rk = np.empty(len(v)); rk[order] = np.arange(len(v))
            for u in np.unique(v):
                m = v == u
                if m.sum() > 1: rk[m] = rk[m].mean()
            return rk
        r = avgrank(r); x = avgrank(x)
    r = r - r.mean(); xc = x - x.mean()
    obs = float(r @ xc) / math.sqrt((r @ r) * (xc @ xc) + 1e-18)
    ge = 0
    for _ in range(B):
        xp = rng.permutation(xc)
        s = float(r @ xp) / math.sqrt((r @ r) * (xp @ xp) + 1e-18)
        ge += (-s) >= (-obs) - 1e-12            # one-sided: lower resource, higher rate
    return (ge + 1) / (B + 1)

def one_cell(args):
    cell, p_hi, gap, tau, sig_a, sig_e, dgp, n_sims, B, seed = args
    s_tot = math.sqrt(tau ** 2 + sig_a ** 2 + sig_e ** 2)
    a, b = calibrate(p_hi, gap, s_tot, dgp)
    rng = np.random.default_rng(seed)
    hit = dict(mw=0, pooled=0, strat=0, trend=0, trend025=0)
    for _ in range(n_sims):
        Y = draw(a, b, tau, sig_a, sig_e, dgp, rng)
        r = Y.mean(1)
        mw = engine.mann_whitney_u(list(r[LO]), list(r[HI]))
        # primary preregistered test is two sided; direction check: low must be higher
        hit['mw'] += (mw['p'] is not None and mw['p'] < 0.05 and r[LO].mean() > r[HI].mean())
        hit['pooled'] += perm_maxgap(Y, B, rng, False) < 0.05
        hit['strat'] += perm_maxgap(Y, B, rng, True) < 0.05
        pt = perm_trend(r, B, rng); hit['trend'] += pt < 0.05; hit['trend025'] += pt < 0.025
    return cell, {k: v / n_sims for k, v in hit.items()}, (round(a, 3), round(b, 3))

if __name__ == '__main__':
    n_sims, B = int(sys.argv[1]), int(sys.argv[2])
    scen = {'binomial only': (0.0, 0.0, 0.0), 'realistic': (0.5, 1.0, 0.5),
            'attack effects only': (0.0, 1.0, 0.0), 'language effects only': (0.5, 0.0, 0.0)}
    jobs, k = [], 0
    for dgp in ('trend', 'step'):
        for sname, (tau, sa, se) in scen.items():
            full = sname in ('binomial only', 'realistic')
            for p_hi in ((0.15, 0.30) if full else (0.30,)):
                for gap in ((0.0, 0.05, 0.10, 0.15, 0.20, 0.30) if full else (0.0, 0.10, 0.20)):
                    k += 1
                    jobs.append(((dgp, sname, p_hi, gap), p_hi, gap, tau, sa, se, dgp, n_sims, B, 20261005 + k))
    with Pool(10) as pool:
        for cell, res, ab in pool.imap(one_cell, jobs):
            print(cell, {kk: float(v) for kk, v in res.items()}, ab, flush=True)
```


#### sim_mde.py

```python
import sys
from multiprocessing import Pool
import sim_power2 as P
if __name__ == '__main__':
    n_sims, B = int(sys.argv[1]), int(sys.argv[2]); jobs = []; k = 0
    for sname, (tau, sa, se) in {'binomial only': (0.0, 0.0, 0.0), 'realistic': (0.5, 1.0, 0.5)}.items():
        for p_hi in (0.15, 0.30):
            for gap in (0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22, 0.26):
                k += 1; jobs.append((('trend', sname, p_hi, gap), p_hi, gap, tau, sa, se, 'trend', n_sims, B, 20261600 + k))
    with Pool(15) as pool:
        for cell, res, ab in pool.imap(P.one_cell, jobs): print(cell, {a: float(b) for a, b in res.items()}, flush=True)
```


#### sim_float.py

```python
"""Null size of the pooled max-gap test with exact float comparison (as in engine.py) versus a 1e-12 tolerance."""
import sys, numpy as np
from multiprocessing import Pool
def run(seed, n_sims=300, B=499, p=0.25, L=87, n=15):
    rng = np.random.default_rng(seed); a = b = 0
    for _ in range(n_sims):
        Y = (rng.random((L, n)) < p).astype(np.int8)
        r = Y.mean(1); obs = r[1:].max() - r[0]
        flat = Y.ravel().copy(); g1 = g2 = 0
        for _ in range(B):
            rng.shuffle(flat); q = flat.reshape(L, n).mean(1); g = q[1:].max() - q[0]
            g1 += g >= obs; g2 += g >= obs - 1e-12
        a += (g1 + 1) / (B + 1) < 0.05; b += (g2 + 1) / (B + 1) < 0.05
    return a, b, n_sims
if __name__ == '__main__':
    with Pool(15) as pool: res = pool.map(run, range(20261100, 20261100 + 15))
    A = sum(r[0] for r in res); Bv = sum(r[1] for r in res); N = sum(r[2] for r in res)
    print('sims', N, 'size float compare', A / N, 'size tolerance', Bv / N)
```


#### sim_seq.py

```python
import sys, math, random
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, '.')
import sim_power as S
from anytime import Betting, SignBet
from math import comb

def tier_sequential(Y, rng, alpha=0.025, delta=0.10, scale=0.30, futility=True):
    """Pairs of (low, high) languages in random order. Efficacy: e-process on the odd, bounded
    transform f(D)=clip(D/scale,-1,1), valid for the null that tier labels do not matter.
    Futility: confidence sequence for the MEAN of D (not clipped), stop if its top end is below delta."""
    r = Y.mean(1)
    hi = list(np.where(S.HI)[0]); lo = list(np.where(S.LO)[0])
    rng.shuffle(hi); rng.shuffle(lo)
    eff = Betting(m0=0.5, alpha=0.05, c=0.75, grid=1)
    fut = Betting(m0=0.5, alpha=0.05, c=0.75, grid=101)
    stop, reason = None, 'ran to the end'
    for k in range(len(hi)):
        d = r[lo[k]] - r[hi[k]]
        e = eff.update((1 + max(-1.0, min(1.0, d / scale))) / 2)
        if e >= 1 / alpha:
            stop, reason = k + 1, 'efficacy'; break
        if futility:
            fut.update((d + 1) / 2)
            if k >= 5:
                _, hi_m = fut.cs()
                if hi_m is not None and 2 * hi_m - 1 < delta:
                    stop, reason = k + 1, 'futility'; break
    return (stop or len(hi)), reason, eff.e0_max >= 1 / alpha

def mcnemar_p_greater(fav, n):                    # exact one sided binomial p(X >= fav | n, 1/2)
    return sum(comb(n, i) for i in range(fav, n + 1)) / 2 ** n

def per_language(Y, alpha_fdr=0.10):
    L = Y.shape[0]; m = L - 1; en = Y[0]
    pv, ev, calls = [], [], 0
    for l in range(1, L):
        sb = SignBet(); fav = n = 0
        for i in range(Y.shape[1]):
            calls += 1
            if Y[l, i] != en[i]:
                z = int(Y[l, i] == 1); sb.update(z); fav += z; n += 1
            if sb.e >= m / alpha_fdr: break       # certain rejection at the strictest e-BH level, stop firing
        pv.append(mcnemar_p_greater(fav, n) if n else 1.0); ev.append(sb.e)
    # Holm at 0.05
    order = sorted(range(m), key=lambda i: pv[i]); holm = 0
    for rank, i in enumerate(order):
        if pv[i] <= 0.05 / (m - rank): holm += 1
        else: break
    # BH at alpha_fdr
    bh = 0
    for rank, i in enumerate(order, 1):
        if pv[i] <= alpha_fdr * rank / m: bh = rank
    # e-BH at alpha_fdr
    es = sorted(ev, reverse=True); ebh = 0
    for k in range(1, m + 1):
        if es[k - 1] >= m / (alpha_fdr * k): ebh = k
    return holm, bh, ebh, calls

def cell(args):
    p_hi, gap, sname, tau, sa, se, n_sims, seed = args
    s_tot = math.sqrt(tau ** 2 + sa ** 2 + se ** 2)
    a, b = S.calibrate(p_hi, gap, s_tot, 'trend')
    rng = np.random.default_rng(seed); pyr = random.Random(seed)
    used, eff, fut, ever = [], 0, 0, 0
    ph = []
    h = bhh = eb = cl = 0
    for _ in range(n_sims):
        Y = S.draw(a, b, tau, sa, se, 'trend', rng)
        u, why, e_ever = tier_sequential(Y, rng)
        used.append(u); eff += why == 'efficacy'; fut += why == 'futility'
        x, y, z, c = per_language(Y); h += x; bhh += y; eb += z; cl += c
    full_pairs = 28
    return (sname, p_hi, gap, dict(
        mean_pairs=sum(used) / n_sims, pct_stop_eff=eff / n_sims, pct_stop_fut=fut / n_sims,
        calls_saved_vs_63_langs=1 - (2 * 15 * sum(used) / n_sims) / (63 * 15),
        holm=h / n_sims, bh=bhh / n_sims, ebh=eb / n_sims, per_lang_calls_share=cl / n_sims / (86 * 15)))

if __name__ == '__main__':
    n_sims = int(sys.argv[1]); jobs = []; k = 0
    for sname, (tau, sa, se) in {'binomial only': (0, 0, 0), 'realistic': (0.5, 1.0, 0.5)}.items():
        for p_hi in (0.15, 0.30):
            for gap in (0.0, 0.05, 0.10, 0.15, 0.20, 0.30):
                k += 1; jobs.append((p_hi, gap, sname, tau, sa, se, n_sims, 20261200 + k))
    with Pool(6) as pool:
        for r in pool.imap(cell, jobs): print(r, flush=True)
```


#### sim_null_seq.py

```python
"""False alarm rate of the sequential tier test when there is NO tier effect (gap 0), several kinds of language heterogeneity."""
import sys, math
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, '.')
import sim_power as S, sim_seq as Q

def run(args):
    name, p_hi, tau, sa, se, n, seed = args
    a, b = S.calibrate(p_hi, 0.0, math.sqrt(tau**2 + sa**2 + se**2), 'trend')
    rng = np.random.default_rng(seed); eff = fut = 0
    for _ in range(n):
        u, why, ever = Q.tier_sequential(S.draw(a, b, tau, sa, se, 'trend', rng), rng)
        eff += why == 'efficacy'; fut += why == 'futility'
    return name, p_hi, n, eff / n, fut / n

if __name__ == '__main__':
    n = int(sys.argv[1]); jobs = []; k = 0
    for name, (tau, sa, se) in {'binomial only': (0, 0, 0), 'realistic': (0.5, 1.0, 0.5), 'strong language heterogeneity': (1.0, 1.0, 0.5)}.items():
        for p_hi in (0.15, 0.30):
            for rep in range(4):
                k += 1; jobs.append((name, p_hi, tau, sa, se, n, 20261500 + k))
    with Pool(10) as pool:
        res = list(pool.imap(run, jobs))
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0.0, 0.0])
    for name, p_hi, n_, e, f in res:
        g = agg[(name, p_hi)]; g[0] += n_; g[1] += e * n_; g[2] += f * n_
    for key, (N, e, f) in agg.items(): print(key, 'sims', N, 'false efficacy stops', round(e / N, 4), 'futility stops', round(f / N, 4))
```


#### sim_cap.py

```python
"""Capability controls: what each handling choice does to the estimated low-minus-high gap."""
import sys, math
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, '.')
import sim_power as S
import engine

def run(args):
    name, gamma, c_hi, c_gap, u_floor, n_sims, seed = args
    rng = np.random.default_rng(seed)
    L = len(S.CODES)
    est = {k: [] for k in ['naive', 'exclude_confirmed', 'exclude_screen', 'ratio_adjust', 'ratio_by_tier', 'oracle']}
    excl = []
    for _ in range(n_sims):
        # understanding of a benign request: falls with log resource share (high ~ .97, lowest ~ u_floor)
        t = (S.Z - S.Z.min()) / (S.Z.max() - S.Z.min())
        u = u_floor + (0.97 - u_floor) * t ** 0.6 + 0.05 * rng.standard_normal(L)
        u = np.clip(u, 0.02, 0.99)
        c = np.where(S.LO, c_hi + c_gap, np.where(S.HI, c_hi, c_hi + c_gap / 2))         # conditional compliance
        ctrl = rng.binomial(6, u)                                                        # 6 controls per language
        ua = u ** gamma                                                                  # attacks harder to parse when gamma>1
        brk = rng.binomial(15, ua * c)
        rate = brk / 15; cr = ctrl / 6
        gap = lambda m: (rate[S.LO & m].mean() / 1 - rate[S.HI & m].mean()) if (m & S.LO).any() and (m & S.HI).any() else np.nan
        allm = np.ones(L, bool)
        est['naive'].append(rate[S.LO].mean() - rate[S.HI].mean())
        ref = cr[0]; thr = 0.5 * ref
        conf = np.array([engine.wilson_ci_cc(int(k), 6)[1] < thr for k in ctrl])         # engine's 'capability_limited'
        scr = cr < thr                                                                   # point estimate under threshold
        est['exclude_confirmed'].append(rate[S.LO & ~conf].mean() - rate[S.HI & ~conf].mean())
        est['exclude_screen'].append(rate[S.LO & ~scr].mean() - rate[S.HI & ~scr].mean())
        adj = np.minimum(1.0, rate / np.maximum(cr, 1 / 12))                             # break rate / control rate, floor 1/12
        est['ratio_adjust'].append(adj[S.LO].mean() - adj[S.HI].mean())
        rl = rate[S.LO].mean() / max(cr[S.LO].mean(), 1 / 12); rh = rate[S.HI].mean() / max(cr[S.HI].mean(), 1 / 12)
        est['ratio_by_tier'].append(min(1.0, rl) - min(1.0, rh))
        est['oracle'].append(c[S.LO].mean() - c[S.HI].mean())
        excl.append((conf & S.LO).sum())
    return name, {k: (float(np.nanmean(v)), float(np.nanstd(v))) for k, v in est.items()}, float(np.mean(excl))

if __name__ == '__main__':
    n = int(sys.argv[1])
    jobs = [('A: attacks as easy to parse as controls (gamma 1), lowest-resource understanding .30', 1.0, 0.30, 0.15, 0.30, n, 1),
            ('B: attacks harder to parse than controls (gamma 2)', 2.0, 0.30, 0.15, 0.30, n, 2),
            ('C: mild capability loss only (understanding floor .70), gamma 1', 1.0, 0.30, 0.15, 0.70, n, 3),
            ('D: no true conditional gap (0), gamma 1, floor .30', 1.0, 0.30, 0.0, 0.30, n, 4)]
    with Pool(4) as pool:
        for name, res, ex in pool.imap(run, jobs):
            print(name, '| mean #low languages excluded as confirmed-limited:', round(ex, 1))
            for k, (m, s) in res.items(): print(f'   {k:18s} mean {m:+.3f}  sd {s:.3f}')
```


#### sim_pool.py

```python
import sys, math
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, '.')
import sim_power as S
import shrink as H
import engine

def truth_rates(a, b, tau_unused, sig_a, sig_e, eta_noise):
    """Universe rate for each language: E over attacks of expit(eta_l + a_i + e_il)."""
    s = math.sqrt(sig_a ** 2 + sig_e ** 2)
    return np.array([S.exp_rate(e, s) if s > 0 else 1 / (1 + math.exp(-e)) for e in eta_noise])

def run(args):
    name, tau, sa, se, n_sims, seed = args
    s_tot = math.sqrt(tau ** 2 + sa ** 2 + se ** 2)
    a, b = S.calibrate(0.30, 0.15, s_tot, 'trend')
    rng = np.random.default_rng(seed)
    acc = {k: [] for k in ['rmse_raw', 'rmse_eb', 'rmse_ebx', 'cov_wil', 'cov_eb', 'cov_ebx', 'w_wil', 'w_eb', 'w_ebx',
                           'top5_cov_wil', 'top5_cov_eb', 'top5_err_raw', 'top5_err_eb', 'bonf_cov', 'slope']}
    for _ in range(n_sims):
        u = tau * rng.standard_normal(len(S.CODES))                       # language effect, kept so truth is known
        eta0 = a + (-b * S.Z)
        eta = eta0 + u
        att = sa * rng.standard_normal(S.N_ATT); inter = se * rng.standard_normal((len(S.CODES), S.N_ATT))
        p = 1 / (1 + np.exp(-(eta[:, None] + att[None, :] + inter)))
        Y = (rng.random(p.shape) < p).astype(np.int8)
        truth = truth_rates(a, b, tau, sa, se, eta)
        ks = [int(v) for v in Y.sum(1)]
        raw = np.array(ks) / S.N_ATT
        f0 = H.fit_eb(ks, S.N_ATT); post0 = H.posterior(ks, S.N_ATT, f0)
        xs = list(S.Z); f1 = H.fit_eb(ks, S.N_ATT, xs); post1 = H.posterior(ks, S.N_ATT, f1, xs)
        eb0 = np.array([q[0] for q in post0]); eb1 = np.array([q[0] for q in post1])
        wil = [engine.wilson_ci_cc(k, S.N_ATT) for k in ks]
        wb = [engine.wilson_ci_cc(k, S.N_ATT, z=2.9) for k in ks]            # roughly Bonferroni over 87 (alpha/87 -> z=3.0)
        cov = lambda lo, hi: (np.array(lo) <= truth) & (truth <= np.array(hi))
        cw = cov([w[0] for w in wil], [w[1] for w in wil])
        c0 = cov([q[1] for q in post0], [q[2] for q in post0]); c1 = cov([q[1] for q in post1], [q[2] for q in post1])
        cb = cov([w[0] for w in wb], [w[1] for w in wb])
        top = np.argsort(-raw)[:5]
        acc['rmse_raw'].append(np.sqrt(np.mean((raw - truth) ** 2))); acc['rmse_eb'].append(np.sqrt(np.mean((eb0 - truth) ** 2)))
        acc['rmse_ebx'].append(np.sqrt(np.mean((eb1 - truth) ** 2)))
        acc['cov_wil'].append(cw.mean()); acc['cov_eb'].append(c0.mean()); acc['cov_ebx'].append(c1.mean())
        acc['w_wil'].append(np.mean([w[1] - w[0] for w in wil])); acc['w_eb'].append(np.mean([q[2] - q[1] for q in post0]))
        acc['w_ebx'].append(np.mean([q[2] - q[1] for q in post1]))
        acc['top5_cov_wil'].append(cw[top].mean()); acc['top5_cov_eb'].append(c0[top].mean())
        acc['top5_err_raw'].append(np.mean(raw[top] - truth[top])); acc['top5_err_eb'].append(np.mean(eb0[top] - truth[top]))
        acc['bonf_cov'].append(cb.all())
        acc['slope'].append(f1['b'])
    return name, {k: float(np.mean(v)) for k, v in acc.items()}

if __name__ == '__main__':
    n_sims = int(sys.argv[1])
    scen = {'language effects only (model well specified)': (0.8, 0.0, 0.0),
            'realistic (language + attack + translation noise)': (0.5, 1.0, 0.5),
            'attack effects only (shared across languages)': (0.0, 1.0, 0.0)}
    jobs = [(k, *v, n_sims, 20261300 + i) for i, (k, v) in enumerate(scen.items())]
    with Pool(3) as pool:
        for name, res in pool.imap(run, jobs):
            print(name); print({k: round(v, 3) for k, v in res.items()}, flush=True)
```


#### sim_repeat.py

```python
"""What do repeats (same attack again) and extra phrasings (new attacks) buy? Power of MW and trend tests."""
import sys, math
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, '.')
import sim_power as S
import engine

def cell(args):
    scen, tau, sa, se, gap, n_att, r, n_sims, B, seed = args
    s_tot = math.sqrt(tau ** 2 + sa ** 2 + se ** 2)
    a, b = S.calibrate(0.30, gap, s_tot, 'trend')
    rng = np.random.default_rng(seed); L = len(S.CODES); mw = tr = 0
    for _ in range(n_sims):
        eta = a - b * S.Z + tau * rng.standard_normal(L)
        att = sa * rng.standard_normal(n_att); inter = se * rng.standard_normal((L, n_att))
        q = 1 / (1 + np.exp(-(eta[:, None] + att[None, :] + inter)))
        k = rng.binomial(r, q).sum(1)                       # r repeats of each attack, sampling temperature above 0
        rate = k / (n_att * r)
        res = engine.mann_whitney_u(list(rate[S.LO]), list(rate[S.HI]))
        mw += (res['p'] < 0.05 and rate[S.LO].mean() > rate[S.HI].mean())
        tr += S.perm_trend(rate, B, rng) < 0.025
    return scen, gap, n_att, r, mw / n_sims, tr / n_sims

if __name__ == '__main__':
    n_sims = int(sys.argv[1]); jobs = []; k = 0
    for scen, (tau, sa, se) in {'moderate within-attack randomness': (0.5, 1.0, 0.5), 'near-deterministic attacks': (0.5, 1.0, 2.0)}.items():
        for gap in (0.05, 0.10):
            for n_att, r in ((15, 1), (15, 3), (15, 5), (30, 1), (45, 1), (75, 1)):
                k += 1; jobs.append((scen, tau, sa, se, gap, n_att, r, n_sims, 199, 20261400 + k))
    with Pool(8) as pool:
        for res in pool.imap(cell, jobs): print(res, flush=True)
```

