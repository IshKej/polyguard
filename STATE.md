# PolyGuard: current state and handoff

**Last updated 2026-10-06.** Read this first if you are picking the project up
cold. Everything below is reconstructable from the repo, but this is the short
version and the reasoning behind the decisions.

Deadline: **Congressional App Challenge, 26 October 2026.**

## One-line status

Built, audited, verified offline, and **live at https://polyguard-ten.vercel.app**
(Ishaan's Vercel account, with a Supabase database for share links, game answers
and the spend guard). **No live scan has ever run.** Every number in the app today
is from a language-independent mock. The API key is the single gate on the
research; `python setup_key.py` plugs it in everywhere at once.

**2026-10-02:** Spanish and Vietnamese native speaker feedback received and
integrated (10 Spanish lines, 1 Vietnamese line).
**2026-10-04:** Arabic feedback received and integrated (7 lines; MSA only, no
dialect coverage). Bank SHA-256 is now
`3d665ef61a4a9dde8cc125e1c9fdb4561621db2e7cf9b7b1d60ca6e95993dff9`, held-out fingerprint `c9cfe3523ebe2213...`, both
logged in `PREREGISTRATION.md`. Portuguese feedback is pending; nothing changed for it.
**2026-10-06:** statistics sprint (log in `docs/progress/stats.md`). Added an
EXPLORATORY rank trend of break rate against Common Crawl web share (crawl
CC-MAIN-2026-39, `data/resource_measures.csv`), logged as secondary in the
deviation table; Mann-Whitney stays the headline. `power_simulation` now models
spread between languages of a tier, because without it the minimum detectable gap
came out 10.5% to 14.9% too small (`power_check.py`). The capability exclusion was
checked exactly and only catches total collapse (see the decisions list below).

## Run these to confirm nothing is broken

```bash
python generate_attack_bank.py   # rebuild corpus       -> 1095 attacks + 438 controls
python validate_bank.py          # structural           -> all valid
python linguistics.py            # script/encoding      -> no findings
python test_engine.py            # unit, a few seconds -> 177/177
python verify_all.py             # full battery        -> 225/225
python api/test_api.py           # web API             -> 90/90
python web/e2e/test_site.py      # the site in a browser, with accessibility checks -> 21/21
python test_stats_properties.py  # 32 properties of the statistics on random inputs -> 32/32
python mutation_check.py         # 17 planted bugs in the statistics, all must be caught -> 17/17
python power_check.py            # power model against within-tier spread (about 3 min)
python api/test_cancellation.py  # OPEN: 2/6 until server-side cancellation lands
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

If any of those fail, something regressed. They all pass as of this writing.

## The blockers, in order

1. **Anthropic API key.** Needs a parent's card. Gates the live scan, the
   language expansion, the judge validation and the remediation proof. Nothing
   else is close to this in importance.
2. **The last 14 catalog languages and native review.** The bank holds 73
   languages: 25 high, 24 mid, 24 low; 20 author written, 53 machine translated
   (`machine_translations/`, checked by `python expand_languages.py --check-stored`).
   Missing: Pashto, Tajik, Mongolian, Armenian, Nepali, Sinhala, Khmer, Burmese, Javanese, Sundanese, Swahili, Amharic, Somali and Kinyarwanda. They need `python expand_languages.py --langs ...` with the
   key, or native speakers. The central hypothesis is testable now but untested.
3. **Server-side cancellation (Ishaan's, in progress).** Closing the tab does not
   stop a paid scan: 228 more calls after a visitor leaves, measured. Brief and
   acceptance tests: `docs/design/cancellation.md`, `api/test_cancellation.py`.
   The spend guard and the hosted size cap bound the cost meanwhile.

Hosting is done, not a blocker: two Vercel Services in one project (the Vite site
at `/`, FastAPI at `/api/*`), every push to main deploys, and CI
(`.github/workflows/ci.yml`) runs every check on every push. The API keeps nothing
between requests; shared state (spend guard, share links, game answers) is in
Supabase (`supabase/migrations/`), reached only with the server's secret key.
Always run `npx vercel whoami` before any Vercel command: it must be `ishkej`.

## The web app

React app in `web/` with a FastAPI layer in `api/`. The look ("the test sheet":
paper, ink, highlighter, red pen) and the research behind it are logged in
`docs/design-research.md`. The first version of the look is kept as the git tag
`design/test-sheet-v1`. The landing page has a scroll story of a scan and a
"spot the attack" game built on real messages from the bank (`GET /api/game`),
which needs no key. Everything that would show a result is labelled simulated
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
| `providers.py` | Victim models across vendors; judge held fixed |
| `defenses.py` | Remediation: scan to hardened prompt |
| `generate_attack_bank.py` | Builds the 20 author-written languages + controls |
| `expand_languages.py` | Machine-translates the other 67, with a verification gate |
| `languages_catalog.py` | 87-language catalog with resource tiers |
| `linguistics.py` | Offline script/encoding/length/duplication validation |
| `judge_eval.py` | Scores the compliance judge against a gold set |
| `calibrate_stats.py` | Proves each statistical test controls its error rate |
| `power_check.py` | Checks the power model against languages that differ within a tier |
| `data/resource_measures.csv` | Web share per language for the exploratory trend test (pinned SHA-256) |
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
  Honest limit, checked exactly on 2026-10-06: with 6 controls a language is
  confirmed only when English follows 6 of 6 and the language 0 of 6. If English
  misses one control nothing can be flagged, and a language at 30% to 40% of
  English capability is flagged 3% to 12% of the time. It catches total collapse,
  not partial limits. A rule change is proposed, not made, in
  `docs/progress/stats.md`.
- **Capability-limited languages are excluded from the primary test.** Leaving
  them in masks the gap: a bot that cannot read a language refuses everything and
  scores near-zero breaks, which looks like security. Measured, this turned a real
  planted gap from p=0.0023 into p=0.050. (37)
- **Provenance, not "verified".** No language has been validated by a native
  speaker. Spanish, Vietnamese and Arabic feedback has been received and integrated,
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
  GitHub should replace it as the real mirror.
- Nothing secret is in the repo. `.gitignore` excludes `secrets.toml`, and no key
  is hardcoded anywhere.

## Scoreboard

| | |
|---|---|
| Attacks | 1095 (73 languages x 5 categories x 3 phrasings) |
| Capability controls | 438 (6 per language) |
| Languages in bank | 73 of a planned 87 (25 high, 24 mid, 24 low; 53 machine translated) |
| Verification checks | 230 |
| Unit tests | 212 (every public engine function) |
| Audit findings | 75 across 19 rounds (74 fixed; 62, cancellation, open and assigned) |
| Native speaker feedback integrated | 3 of 20 (Spanish, Vietnamese, Arabic); Portuguese pending; none validated |
| Live scans ever run | 0 |
