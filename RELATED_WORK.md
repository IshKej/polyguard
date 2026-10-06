# Related work, and what PolyGuard actually adds

Literature reviewed 2026-09-16, before the first live scan.

This document exists because the easiest way to lose credibility is to present a
known result as a discovery. The multilingual safety gap is **not** an open
question, and multilingual prompt injection is **not** an unexplored area. Both
are active, published fields. Anyone judging this project who spends five minutes
searching will find the work below, so it is stated here first, plainly, along
with the narrower claim PolyGuard can actually defend.

## What is already established

**Low-resource languages break safety training.** Yong, Menghini and Bach
(arXiv:2310.02446) translated AdvBench prompts into low-resource languages and
got GPT-4 to produce actionable harmful content **79%** of the time, comparable
to state-of-the-art jailbreaks, while high- and mid-resource languages scored far
lower. They attribute this to linguistic inequality in safety training data and
note that roughly 1.2 billion people speak the affected languages. This is the
foundational result, and PolyGuard did not discover it.

**It replicates, and it is still true in 2026.** A 2026 empirical evaluation
(arXiv:2606.29602) tested DeepSeek, GPT, Gemini, Grok, Llama and Qwen under
direct and multi-stage obfuscated adversarial prompts and reports that
"non-English languages consistently exhibit higher compliance rates than
English."

**Multilingual prompt injection specifically is an active 2026 area**, not a gap:

- MIPIAD (arXiv:2605.07269) builds multilingual *indirect* prompt injection
  defense with a Qwen and TF-IDF hybrid.
- A Turkish vulnerability assessment (Applied Sciences, doi 10.3390/app16136740)
  benchmarks 55 open and closed models on 790 paired Turkish and English
  adversarial prompts.
- Detection of prompt injection in Indian multilingual LLMs appeared in
  Scientific Reports (s41598-026-43883-0).
- Cross-lingual injection against LLM relevance judgment (arXiv:2607.10080)
  covers 8 languages spanning resource levels.
- Code-switching and transliteration injection are both documented attack
  families.

**English prompt-injection benchmarks are mature.** Open-Prompt-Injection
(liu00222) provides a standard attack and defense benchmark. Tensor Trust
(arXiv:2311.01011) built a 126K-sample human-generated dataset of extraction and
hijacking attacks and reports GPT-4 at roughly **84%** robustness to hijacking
and **69%** to extraction. Agent-injection-bench scores success with
machine-checkable conditions including canary strings, which is the same
detection principle PolyGuard uses; that idea is borrowed, not invented here.

## The confound that dominates this area

This deserves its own section because it is easy to miss and it can invert a
result.

**Poor translation quality, not stronger guardrails, may explain lower attack
success in low-resource languages.** Multilingual jailbreaking work
(arXiv:2605.18239) found that replacing automated translation with human
red-teaming raised the average jailbreak rate from **59.8% to 75.8%**, with
per-language gains of +20.0% for Afrikaans, +12.7% for isiZulu and +12.3% for
isiXhosa. Separately, LinguaSafe (arXiv:2508.12733) found that vanilla LLM
translation of a safety benchmark had error rates of **71% for Bengali and 36% for
Malay** under human inspection, cut to 12% and 3% by its translate, estimate and
refine pipeline. (Corrected 2026-10-05: earlier versions of this repo attributed
the 71% figure to arXiv:2605.18239 and gave Malay's starting point as 71%.)

The mechanism is simple and it runs one way. A garbled attack fails because the
model cannot parse it, not because the model resisted it. The scanner records a
non-break. The non-break reads as safety. So machine-translated evaluation sets
**understate** vulnerability in exactly the low-resource languages they are built
to study.

Related failure modes are documented across the multilingual evaluation
literature: translationese artifacts making translated benchmarks easier than
native text, round-trip translation revealing what frontier multilingual
benchmarks miss, and native-speaker evaluation being treated as the gold standard
precisely because automated metrics cannot substitute for it.

**What this means for PolyGuard.** Its 67 machine-translated languages are
produced by exactly the method shown to be unreliable. Three consequences, all
now implemented:

1. The reverse-translation gate is **on by default** and samples across
   categories rather than checking one attack in fifteen. A single sample cannot
   detect error rates of the size LinguaSafe measured (71% in Bengali).
2. Capability controls catch the extreme case where a model cannot operate in a
   language at all, which is a related but distinct failure.
3. The expected direction of the residual bias is recorded in
   `PREREGISTRATION.md`: toward understating H1. Conservative for the headline,
   but limiting on what a null result can mean, which is why
   `NATIVE_REVIEW.md` exists and currently reads zero.

## What PolyGuard does not claim

- Not the first to find that low-resource languages are less defended.
- Not the first to test prompt injection multilingually.
- Not the first to score injection success with a canary token.
- Not a novel attack technique. Every category used here is a documented,
  well-known family.

## What PolyGuard actually adds

Four things, none of them "we found the gap":

**1. Resource-tier breadth as the independent variable.** The studies above
mostly work in one language pair, one language family, or up to eight languages.
PolyGuard targets an **87-language catalog deliberately stratified into high,
mid and low resource tiers**, so the resource level is a graded variable across a
wide sample rather than a binary English-versus-other comparison.

**2. A builder-facing threat model, not a fixed research benchmark.** The prior
work measures published models against fixed prompt sets. PolyGuard attacks **a
system prompt the user pastes in**, which is the situation an actual developer is
in: not "is GPT-4 safe in Swahili" but "is *my* deployed bot safe in Swahili".
That also means it measures injection against an application's instructions
rather than jailbreaking a base model's policy, which is a different threat model
from Yong et al. and from arXiv:2606.29602.

**3. Remediation, measured.** Research papers end at the finding. PolyGuard
generates targeted hardening rules for exactly the categories that broke,
re-scans the hardened prompt against the same model, and reports how many holes
actually closed. The defence is evaluated, not asserted.

**4. Statistical discipline that most of this literature does not apply.** This
is the part that is genuinely uncommon:

- The unit of analysis is the **language**, not the attack, because attacks
  against one bot in one language are correlated. Simulation shows the pooled
  attack-level test rejects a true null far more often than alpha once that
  clustering is present (see `calibration_report.txt`).
- The worst-language statistic is corrected for being a **maximum over many
  languages**, via a permutation test. Uncorrected, that headline fires on 98% of
  scans against a model with no gap at all (`selection_bias_demo.py`).
- Every significance claim carries a **Cliff's delta effect size** with a
  bootstrap interval, so "significant" is never reported without "how much".
- The family of per-category tests is **FDR-corrected** (Benjamini-Hochberg).
- Every test is **empirically calibrated** by simulation against known ground
  truth, rather than assumed correct (`calibrate_stats.py`).
- Hypotheses, the primary test and the decision rules were **pre-registered
  before any live data existed** (`PREREGISTRATION.md`), including an advance
  commitment to report a null result as a null result.

## What this means for the expected result

The literature predicts H1 will replicate: low-resource languages should break
more often. That raises a real risk for this project, and it is worth naming.
When the expected answer is already known, it becomes very easy to accept a
confirming result without scrutiny and to keep looking when the result disagrees.

The pre-registration is the guard against that, and it was deliberately written
before this literature review was run, so the analysis plan could not be tuned to
the expected answer. The deviation log records that the review has since raised
the prior on H1.

A second consequence: because the effect is already documented, a **null result
would be the more interesting outcome**, not the disappointing one. If small
deployed models in 2026 turn out to be roughly even across languages, that is
evidence the gap has closed since 2023, which is genuinely new information and
would be reported as the headline.

## Sources

- Yong, Menghini, Bach. *Low-Resource Languages Jailbreak GPT-4*. https://arxiv.org/abs/2310.02446
- *An Empirical Evaluation of Prompt Injection Vulnerabilities in LLMs Across Multilingual and Obfuscated Attack Scenarios*. https://arxiv.org/abs/2606.29602
- *MIPIAD: Multilingual Indirect Prompt Injection Attack Defense*. https://arxiv.org/pdf/2605.07269
- *Benchmarking Prompt Injection Attacks on LLMs: Turkish Vulnerability Assessment*. https://doi.org/10.3390/app16136740
- *Detection and analysis of prompt injection in Indian multilingual LLMs*. https://www.nature.com/articles/s41598-026-43883-0
- *The Effect of Multi-Lingual and Keyword Adversarial Injection on LLM Relevance Judgment*. https://arxiv.org/html/2607.10080
- *Tensor Trust: Interpretable Prompt Injection Attacks from an Online Game*. https://arxiv.org/pdf/2311.01011
- *Multilingual jailbreaking of LLMs using low-resource languages*. https://arxiv.org/pdf/2605.18239
- *LinguaSafe: A Comprehensive Multilingual Safety Benchmark for Large Language Models*. https://arxiv.org/abs/2508.12733
- *Round-Trip Translation Reveals What Frontier Multilingual Benchmarks Miss*. https://arxiv.org/pdf/2604.12911
- *Déjà Vu: Multilingual LLM Evaluation through the Lens of Machine Translation Evaluation*. https://arxiv.org/html/2504.11829
- Open-Prompt-Injection benchmark. https://github.com/liu00222/Open-Prompt-Injection
- Joshi, Santy, Budhiraja, Bali, Choudhury. *The State and Fate of Linguistic
  Diversity and Inclusion in the NLP World*. ACL 2020.
  https://aclanthology.org/2020.acl-main.560/ — the source of every
  language's resource class, and therefore of PolyGuard's independent
  variable. Class data: https://microsoft.github.io/linguisticdiversity/
- Romano et al. (2006), Cliff's delta magnitude thresholds.
- Benjamini & Hochberg (1995), false discovery rate control.
