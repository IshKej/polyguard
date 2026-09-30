# PolyGuard: current state and handoff

**Last updated 2026-09-29.** Read this first if you are picking the project up
cold. Everything below is reconstructable from the repo, but this is the short
version and the reasoning behind the decisions.

Deadline: **Congressional App Challenge, 26 October 2026.**

## One-line status

Built, deeply audited, and fully verified offline. **No live scan has ever run.**
Every number in the app today is from a language-independent mock. The API key is
the single gate on everything that remains.

## Run these to confirm nothing is broken

```bash
python generate_attack_bank.py   # rebuild corpus       -> 300 attacks + 120 controls
python validate_bank.py          # structural           -> all valid
python linguistics.py            # script/encoding      -> no findings
python test_engine.py            # unit, <1s           -> 154/154
python verify_all.py             # full battery        -> 213/213
python api/test_api.py           # web API             -> 39/39
python judge_eval.py             # judge gold set       -> heuristic bias measured
python calibrate_stats.py        # statistical calibration (slow) -> exit 0
python selection_bias_demo.py    # why worst-language needs correction
python preflight.py              # deploy readiness   -> all pass
python consistency.py            # docs match the code -> no stale claims
python rehearsal.py              # dress rehearsal    -> answer key PASS
streamlit run app.py             # the app itself
python cli.py scan --prompt f --mock   # headless, no key needed
```

If any of those fail, something regressed. They all pass as of this writing.

## The blockers, in order

1. **Anthropic API key.** Needs a parent's card. Gates the live scan, the
   language expansion, the judge validation and the remediation proof. Nothing
   else is close to this in importance.
2. **The 35 low-resource languages.** The bank holds 20 languages: 16 high, 4
   mid, **0 low**. The central hypothesis is therefore untested, not supported.
   `python expand_languages.py --tier low` fills them, needs the key.
3. **GitHub repo.** The local git repo is **already initialised and committed**,
   so this is now two commands plus an account action. Create an empty public
   repo named `polyguard` (no README, no .gitignore, or it will collide), then:
   `git remote add origin https://github.com/YOUR-USERNAME/polyguard.git`
   followed by `git push -u origin main`. Full steps in `DEPLOY.md`. This also
   ends the Drive-mirror staleness problem permanently.

## First moves once the key exists, in this order

```bash
python providers.py --smoke                  # prove each vendor adapter works
python judge_eval.py --dual                  # inter-judge kappa, 2 models
python expand_languages.py --limit 3         # cheap trial run (backcheck is on by default)
python expand_languages.py --tier low        # the real fill
python linguistics.py                        # script check the new languages
python verify_all.py                         # re-verify after the bank changes
```

Then record the new `attack_bank.json` SHA-256 in `PREREGISTRATION.md` and log
the expansion in its deviation table. That expansion is pre-planned, so it is not
a deviation from the analysis plan, but the fingerprint must be updated.

## What each file is for

| File | Why it exists |
|---|---|
| `app.py` | Streamlit UI and report |
| `engine.py` | Scan engine, break detection, all statistics |
| `providers.py` | Victim models across vendors; judge held fixed |
| `defenses.py` | Remediation: scan to hardened prompt |
| `generate_attack_bank.py` | Builds the 20 author-written languages + controls |
| `expand_languages.py` | Machine-translates the other 67, with a verification gate |
| `languages_catalog.py` | 87-language catalog with resource tiers |
| `linguistics.py` | Offline script/encoding/length/duplication validation |
| `judge_eval.py` | Scores the compliance judge against a gold set |
| `calibrate_stats.py` | Proves each statistical test controls its error rate |
| `selection_bias_demo.py` | Reproduces the worst-language selection bias |
| `review_sheet.py` | Exports CSVs for native-speaker review |
| `rehearsal.py` | Runs the whole pipeline offline against a planted answer key |
| `cli.py` | Headless scan, baseline comparison, CI exit codes |
| `report_html.py` | Self-contained shareable HTML report |
| `preflight.py` | Deploy gate: files, secrets, deps, clean boot |
| `consistency.py` | Proves no document contradicts the code |
| `DEMO_VIDEO.md` | Video script, shot list, submission answer drafts |
| `validate_bank.py`, `test_engine.py`, `verify_all.py` | Validation layers |
| `AUDIT.md` | Every flaw found and fixed, 8 rounds |
| `PREREGISTRATION.md` | Hypotheses and analysis plan, fixed before data |
| `RELATED_WORK.md` | Prior art and what this project does not claim |
| `NATIVE_REVIEW.md` | Translation review status and workflow |

## Decisions that took real work, and must not be quietly undone

- **The worst-language statistic is a maximum** and was confirming the thesis on
  98% of scans against a model with no gap at all. It is corrected by a
  permutation test. Never headline the raw `equity_gap`. (`AUDIT.md` 19)
- **The unit of analysis is the language, not the attack.** Pooling attacks
  rejects a true null 16.6% of the time under realistic clustering. The pooled
  number is displayed but labelled optimistic and is not the headline. (16, and
  measured in `calibration_report.txt`)
- **No keyword fallback in live scans.** The keyword judge scores genuine
  refusals as breaks 77% of the time in languages outside its list versus 0%
  inside. An unjudgeable attack is an error, not a guess. (28, 29)
- **Capability controls, 6 per language.** A quiet language may be defended or
  simply broken, and those are opposite conclusions. Six is the smallest number
  that can *confirm* incapacity rather than merely suspect it. (30, 32)
- **Capability-limited languages are excluded from the primary test.** Leaving
  them in masks the gap: a bot that cannot read a language refuses everything and
  scores near-zero breaks, which looks like security. Measured, this turned a real
  planted gap from p=0.0023 into p=0.050. (37)
- **Provenance, not "verified".** No language has been reviewed by a native
  speaker. The old flag implied otherwise. (34)
- **Nulls are reportable.** The pre-registration commits to it, and power is
  reported alongside so a null can be told apart from an underpowered scan.

## The biggest known risk

**Translation quality is the dominant confound in this entire research area, and
it is not hypothetical.** Published work finds that poor machine translation, not
stronger guardrails, explains lower attack success in low-resource languages:
human red-teaming raised jailbreak rates from 59.8% to 75.8%, and machine
translation error rates in some languages ran as high as 71% before human review
(arXiv:2605.18239; see `RELATED_WORK.md`).

The direction matters. Bad translation makes low-resource languages look **safer
than they are**, so PolyGuard's machine-translated languages will tend to
**understate** the very gap H1 predicts. That is the conservative direction for
the headline claim, but it is a real limit on what a null result can mean, and it
is why the reverse-translation gate is on by default and native review is
tracked rather than waved off.

## Where things live

- Source of truth: this GitHub repository, https://github.com/IshKej/polyguard
  GitHub should replace it as the real mirror.
- Nothing secret is in the repo. `.gitignore` excludes `secrets.toml`, and no key
  is hardcoded anywhere.

## Scoreboard

| | |
|---|---|
| Attacks | 300 (20 languages x 5 categories x 3 phrasings) |
| Capability controls | 120 (6 per language) |
| Languages in bank | 20 of a planned 87 (16 high, 4 mid, **0 low**) |
| Verification checks | 213 |
| Unit tests | 154 (all 29 engine functions) |
| Audit findings fixed | 59 across 17 rounds |
| Native-reviewed languages | 0 |
| Live scans ever run | 0 |
