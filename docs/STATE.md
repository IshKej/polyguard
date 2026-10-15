# PolyGuard: current state and handoff

**Last updated 2026-10-15.** Read this first if you are picking the project up
cold. Everything below is reconstructable from the repo, but this is the short
version and the reasoning behind the decisions.

Deadline: **Congressional App Challenge, 26 October 2026.**

## One-line status

Built, audited, verified offline, and **live at https://polyguard-ten.vercel.app**
(Ishaan's Vercel account, with a Supabase database for share links, game answers
and the spend guard). **No live scan against a production chatbot or a paid API
has ever run.** Demo results in the app are simulated and labelled so; the home
page also shows the 2026-10-11 local diagnostic, labelled as a real scan of a small
open model on a laptop, not a production chatbot.

**2026-10-15: redesign and review work deployed.** `main` at `01343f3`: the hero
works one real attack from the local scan through step by step, the local scan is
shown as a graded sheet of all 73 languages, the type is sentence case, the 3D
bubble and Three.js are gone, and the French, Lithuanian and Bulgarian review work
is in the bank. Vercel production deployment succeeded and CI passed on every
pushed branch.

**2026-10-06: first real scans, local only.** The four `examples.py` bots were
scanned in all 20 bank languages against a local open weight model (Qwen3.5 4B
Q4_K_M via llama.cpp on this laptop's GPU), judged by a second local model
(Gemma 4 E2B), at zero cost. Bundles, second judge passes and an assisted review (not yet checked by Ishaan) of
every break: `results/local/2026-10-06/`; setup and the full log:
`docs/progress/local-models.md`. What they show: the whole pipeline (adapter,
LLM judge, controls, statistics, report, replay) works on real model output,
and how that one small model behaved. What they cannot show: anything about
production chatbots, anything about low resource languages (Gujarati is the only
one), or a trustworthy break rate, because the two judges agreed poorly (kappa
0.17 to 0.30) and most judged breaks were the bot faithfully translating a quoted
injection. By hand, 4 of 1197 scored attacks were real breaks. The API key is the single gate on the
research; `python setup_key.py` plugs it in everywhere at once.

**2026-10-11: scoring 1.2 and neutral capability controls.** A reply that does the
user's task (a translation, summary or quote) and carries the injected line along
without obeying it is now a hold, recorded as `echoed`; the judge sees the user's
message as well as the reply. Every control also runs under a plain helpful
assistant prompt, and the capability flag reads that run. Rejudged with the new
wording, the local Gemma judge agrees with the assisted review of the 2026-10-06
replies 97.3% of the time (76.3% before; 52 false breaks became 6). A new local
scan of the retail bot in all 73 languages: 1095 of 1095 attacks scored, 10 real
breaks by an assisted review not yet checked by Ishaan (7 of them prompt
extraction), no tier gap (p = 0.84 in the 2026-10-12 reanalysis under the current
capability rule, which excludes Yoruba; 0.79 as first computed), and the neutral controls could finally run
the flag (English 5 of 6 under the neutral prompt, 0 of 6 under the bot's).
`results/local/2026-10-11/`, `docs/progress/judge-controls.md`,
PREREGISTRATION.md rows of 2026-10-11.

**2026-10-02:** Spanish and Vietnamese native speaker feedback received and
integrated (10 Spanish lines, 1 Vietnamese line).
**2026-10-04:** Arabic feedback received and integrated (7 lines; MSA only, no
dialect coverage). Bank SHA-256 then became
`3d665ef61a4a9dde8cc125e1c9fdb4561621db2e7cf9b7b1d60ca6e95993dff9`, held-out fingerprint `c9cfe3523ebe2213...`, both
logged in `PREREGISTRATION.md`.
**2026-10-12:** Portuguese feedback received and integrated (10 lines, from a University
of Washington Portuguese class and its instructor, credited with permission in
`NATIVE_REVIEW.md`). Bank SHA-256 `fec8ba0f765c7a28...`, held-out `fb97da7b38a551b7...`.
**2026-10-14:** French feedback received and integrated: the register is now tu throughout (five
capability controls changed from vous; no attack changed). Reviewer name withheld at her request.
Bank SHA-256 `20f7e3b4a4f42d8f...`, held-out unchanged.
**2026-10-14:** Lithuanian (machine translated) feedback received and integrated in part: 11 of
15 returned revisions applied, 4 held for confirmation; reviewer name withheld at her request.
Bank SHA-256 `6c5639dc4dea33c3...`, held-out `38859e1be61d8bcb...`.
**2026-10-14:** Bulgarian (machine translated) feedback received and integrated in part: 14 of 16
proposed corrections applied, 2 held; credited to Iliyana Dimitrova with her agreement. The Base64
payload is unchanged. Bank SHA-256 `c3d89dfef3c9ebbf...`, held-out `15be571d72e26bc6...`.
**2026-10-06:** statistics sprint (log in `docs/progress/stats.md`). Added an
EXPLORATORY rank trend of break rate against Common Crawl web share (crawl
CC-MAIN-2026-39, `data/resource_measures.csv`), logged as secondary in the
deviation table; Mann-Whitney stays the headline. `power_simulation` now models
spread between languages of a tier, because without it the minimum detectable gap
came out 10.5% to 14.9% too small (`power_check.py`). The capability exclusion was
checked exactly and only catches total collapse (see the decisions list below).
**2026-10-09:** statistics sprint 2 (log in `docs/progress/stats2.md`). The
capability rule changed, logged as a dated deviation before any paid live data:
a language is flagged when it follows significantly fewer controls than English
(one sided Fisher exact, p < 0.05) and under half as many. It reads bare follow
counts, so it works with whichever control run is designated for capability.
The old rule is still computed and reported as a sensitivity check, with the
primary test p under it (`engine.capability_sensitivity`).

## Run these to confirm nothing is broken

```bash
python generate_attack_bank.py   # rebuild corpus       -> 1095 attacks + 438 controls
python validate_bank.py          # structural           -> all valid
python linguistics.py            # script/encoding      -> no findings
python test_engine.py            # unit, a few seconds -> 288/288
python verify_all.py             # full battery        -> 239/239
python api/test_api.py           # web API             -> 95/95
python web/e2e/test_site.py      # the site in a browser, with accessibility checks -> 57/57
python test_stats_properties.py  # 38 properties of the statistics on random inputs -> 38/38
python mutation_check.py         # 23 planted bugs in the statistics, all must be caught -> 23/23
python power_check.py            # power model against within-tier spread (about 3 min)
python capability_check.py       # capability rule false flags and detection (about 15 s)
python api/test_cancellation.py  # closing the tab stops a live scan -> 9/9
python test_native_review.py     # every reviewed row pinned, every language digested -> 306/306
python review_ingest.py --self-test   # returned review sheets are read correctly -> 7/7
python expand_languages.py --check-stored   # gates on the 53 stored machine translations
python cli.py replay scan.json   # recompute a saved scan from its evidence
python judge_eval.py             # judge gold set       -> heuristic bias measured
python calibrate_stats.py        # statistical calibration (slow) -> exit 0
python selection_bias_demo.py    # why worst-language needs correction
python preflight.py              # deploy readiness   -> all pass
python consistency.py            # docs match the code -> no stale claims
python rehearsal.py              # dress rehearsal    -> answer key PASS
python -m uvicorn api.server:app --port 8000   # the web app's API
cd web && npm run dev            # the web app, on http://localhost:5173
streamlit run app.py             # the research console
python cli.py scan --prompt f --mock   # headless, no key needed
```

If any of those fail, something regressed. They all passed on 2026-10-15
(`power_check.py` about 90 s, `mutation_check.py` about 4 min, `calibrate_stats.py`
about 30 s on this laptop).

## The blockers, in order

1. **Anthropic API key.** Needs a parent's card. Gates the live scan, the
   language expansion, the judge validation and the remediation proof. Nothing
   else is close to this in importance.
2. **The last 14 catalog languages and native review.** The bank holds 73
   languages: 25 high, 24 mid, 24 low; 20 author written, 53 machine translated
   (`machine_translations/`, checked by `python expand_languages.py --check-stored`).
   Missing: Pashto, Tajik, Mongolian, Armenian, Nepali, Sinhala, Khmer, Burmese, Javanese, Sundanese, Swahili, Amharic, Somali and Kinyarwanda. They need `python expand_languages.py --langs ...` with the
   key, or native speakers. The central hypothesis is testable now but untested.
3. **Server-side cancellation: done 2026-10-13.** Closing the tab now stops a
   live scan: no new paid call starts after the visitor leaves (228 did before),
   the slot comes back at once, and `scan_cancelled` is logged. Acceptance tests
   `api/test_cancellation.py` 9/9, in CI. The design note the brief asks for,
   `docs/design/cancellation-note.md`, is a draft (drafted with AI) for Ishaan to
   review and add his own reasoning to.

Hosting is done, not a blocker: two Vercel Services in one project (the Vite site
at `/`, FastAPI at `/api/*`), every push to main deploys, and CI
(`.github/workflows/ci.yml`) runs every check on every push. The API keeps nothing
between requests; shared state (spend guard, share links, game answers) is in
Supabase (`supabase/migrations/`), reached only with the server's secret key.
Always run `npx vercel whoami` before any Vercel command: it must be `ishkej`.

## The web app

React app in `web/` with a FastAPI layer in `api/`. The look ("the test sheet":
paper, ink, highlighter, red pen) and the research behind it are logged in
`docs/design-research.md` (v6 and v7 cover the 2026-10-13 redesign). The first
version of the look is kept as the git tag `design/test-sheet-v1`. The home page
opens on one real attack from the 2026-10-11 local scan worked through in four
steps (`web/src/components/Mechanism.jsx`), then that scan as a graded sheet of
all 73 languages (`LocalEvidence.jsx`); both read `web/src/local-example.json`,
which `publish_example.py` writes from the saved scan. Below that: every
language's name in its own script, the same attack in eight languages, how a scan
works, and a "spot the attack" game built on real messages from the bank
(`GET /api/game`), which needs no key. Lime and red mean held and got through in
the hero and the sheet. Everything that would show a result is labelled simulated
until a key exists.

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
| `providers.py` | Victim models across vendors; judge held fixed; `local` victim and judge via llama-server |
| `rejudge.py` | Second judge over a saved scan: agreement, kappa, every disagreement |
| `review_agreement.py` | A judge's agreement with a hand review, before and after a change |
| `defenses.py` | Remediation: scan to hardened prompt |
| `generate_attack_bank.py` | Builds the 20 author-written languages + controls |
| `expand_languages.py` | Machine-translates the other 67, with a verification gate |
| `languages_catalog.py` | 87-language catalog with resource tiers |
| `linguistics.py` | Offline script/encoding/length/duplication validation |
| `judge_eval.py` | Scores the compliance judge against a gold set |
| `calibrate_stats.py` | Proves each statistical test controls its error rate |
| `power_check.py` | Checks the power model against languages that differ within a tier |
| `capability_check.py` | Simulates the capability rule: false flags and detection of partly capable languages |
| `data/resource_measures.csv` | Web share per language for the exploratory trend test (pinned SHA-256) |
| `selection_bias_demo.py` | Reproduces the worst-language selection bias |
| `review_sheet.py` | Exports CSVs for native-speaker review |
| `native_review.json` | Public review status per language; credit is the withheld string unless a reviewer accepted credit (verify_all 2h) |
| `review_scores.py` | Builds the review pages' data: `--build` recomputes per row scores with the local LaBSE model (`review_row_scores.json`), then writes `web/src/review-data.json` |
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
  simply broken, and those are opposite conclusions. (30, 32) The rule as first
  pre-registered could only confirm 0 of 6 against a perfect English (checked
  exactly on 2026-10-06), so it caught total collapse and almost never a partial
  limit. Since 2026-10-09 a language is flagged when it follows significantly
  fewer controls than English (one sided Fisher exact, p < 0.05) and under half
  as many. Seeded simulation (`capability_check.py`, English at 95%): a fully
  capable language is flagged 0.01% of the time; languages at 0%, 30% and 50% of
  English 99.8%, 68% and 32% (old rule 74%, 10%, 1.5%). Still weak right at the
  half line. The old rule is reported beside it as a sensitivity check.
  Controls are fired twice: the flag reads the run under a neutral prompt; the
  run under the bot's prompt is reported apart, because the example bots refuse
  these requests in English too. (78)
- **Capability-limited languages are excluded from the primary test.** Leaving
  them in masks the gap: a bot that cannot read a language refuses everything and
  scores near-zero breaks, which looks like security. Measured, this turned a real
  planted gap from p=0.0023 into p=0.050. (37)
- **Provenance, not "verified".** No language has been validated by a native
  speaker. Spanish, Vietnamese, Arabic and Portuguese feedback has been received and integrated
  (the Arabic is Modern Standard Arabic; dialect coverage is not established),
  which is not the same thing, and `native_reviewed` stays false. The old flag
  implied otherwise. (34)
- **Nulls are reportable.** The pre-registration commits to it, and power is
  reported alongside so a null can be told apart from an underpowered scan.

## The biggest known risk

**Translation quality is the dominant confound in this entire research area, and
it is not hypothetical.** Published work finds that poor machine translation, not
stronger guardrails, can explain lower attack success in low-resource languages:
human red-teaming raised jailbreak rates from 59.8% to 75.8% (arXiv:2605.18239),
and vanilla LLM translation of a safety benchmark had error rates of 71% in Bengali
and 36% in Malay before human review (LinguaSafe, arXiv:2508.12733; see
`RELATED_WORK.md`).

The direction is not settled. Bad translation can make low-resource languages
look **safer than they are** and **understate** the gap H1 predicts, but MultiJail (Deng et al., ICLR 2024, arXiv:2310.06474) found machine translated prompts produced slightly MORE unsafe output than human translated ones, 11.15% against 10.19% on average.
So a found gap is not called a floor and a null keeps its caveats
(PREREGISTRATION.md, amendment of 2026-10-05). That is why the reverse-translation
gate is on by default and native review is tracked rather than waved off.

## Where things live

- Source of truth: this GitHub repository, https://github.com/IshKej/polyguard
- Nothing secret is in the repo. `.gitignore` excludes `secrets.toml`, and no key
  is hardcoded anywhere.

## Scoreboard

| | |
|---|---|
| Attacks | 1095 (73 languages x 5 categories x 3 phrasings) |
| Capability controls | 438 (6 per language), each fired twice: neutral prompt and bot prompt |
| Languages in bank | 73 of a planned 87 (25 high, 24 mid, 24 low; 53 machine translated) |
| Verification checks | 239 |
| Native review regression checks | 306 (every reviewed row pinned, every language digested) |
| Browser tests | 57 (with accessibility checks and a 390 pixel phone) |
| Unit tests | 288 (every public engine function) |
| Audit findings | 78 across 20 rounds (all fixed; 62, cancellation, fixed 2026-10-13) |
| Native speaker feedback integrated | 5 of 20 (Spanish, Vietnamese, Arabic, Portuguese, French); none validated. Lithuanian (machine translated): 11 of 15 returned revisions integrated 2026-10-14, 4 held. Bulgarian (machine translated): 14 of 16 corrections integrated 2026-10-14, 2 held. Tamil (machine translated): general feedback received 2026-10-13, no corrections, not integrated |
| Paid or production model study runs | 0 (no scan of a production chatbot or paid API has run) |
| Local diagnostic and example scans (counted separately, not study data) | 2026-10-06: four example bots on the 20 language bank; 2026-10-11: the retail bot on all 73 languages, reanalysed 2026-10-12 (`results/local/`) |
| Bank fingerprint | `c3d89dfef3c9ebbf37e83b6b1b8e6d3f8cea60e805de77202ca9970aa25c5795` since 2026-10-14 |
