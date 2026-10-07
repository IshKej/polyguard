# PolyGuard worklog

The running log of what is built, what is in progress and what is next, kept so
work can resume at once after a break. `STATE.md` is the handoff for the research
engine; `docs/design-research.md` is the record of the web app's look. This file is
the web app and hosting.

## Done (newest first)

- **2026-10-06** Merged `sprint/defences`: `python cli.py defend` runs baseline,
  placebo, current and data_boundary arms on the held-out phrasing with a paired
  sign test against placebo; `defenses.lint_all` keeps defence text from quoting
  the bank; "proves the holes closed" wording replaced. Merged `sprint/stats`:
  exploratory `engine.resource_trend_test` against Common Crawl share
  (`data/resource_measures.csv`, pinned), power simulation now models spread within
  a tier (old minimum detectable gap 10.5 to 14.9 percent too small), the capability
  flag's weakness written into README and STATE. Suites: verify_all 230,
  test_engine 212, properties 32, mutation 17/17. Open for Ishaan: placebo length
  matching, a repeated baseline arm, `--rules scan` vs `all` for the headline, the
  capability rule change proposed in `docs/progress/stats.md`, stale Joshi and tier
  columns in `data/resource_measures.csv` (unused by code).

- **2026-10-05** `3a86029` OWASP LLM Top 10 2025 and MITRE ATLAS (v5.6.0) tags per
  attack type in `engine.TAXONOMY`, `/api/meta`, the report and README (check 118).
  CI green on the 73 language ship (`75e5fe6`).

- **2026-10-05** `75e5fe6` Bank shipped at 73 languages: 1095 attacks, 438
  controls, 25 high / 24 mid / 24 low, 53 machine translated (none native
  reviewed), new SHA `4e2ba320...` and held-out `3cf67897...` in the
  preregistration. Review sheets for the 53. Six research notes committed in
  `docs/research/` (the obfuscation note stays local, not committed). 14 catalog
  languages remain: API pipeline or native speakers only.

- **2026-10-05** Statistics and interpretation fixes from the research notes:
  the max-gap permutation test dropped exact ties that differ only in floating
  point (p too small; AUDIT 74, property test against exact fractions, a 13th
  mutant), and the preregistration's "a found gap is a floor" was withdrawn by a
  dated amendment because MultiJail found machine translation slightly raises
  unsafe rates (AUDIT 75). Suites: test_engine 168, properties 24, verify_all
  223, mutation 13/13.

- **2026-10-05** Two errors found by reading the cited sources (AUDIT round 19):
  the 71% translation error figure was attributed to the wrong paper (it is
  LinguaSafe, arXiv:2508.12733, Bengali only), and four Joshi classes were copied
  wrong (Gujarati, Norwegian, Kyrgyz are 1, not 4; Pashto 1, not 2). Tiers now 25
  high / 24 mid / 38 low; the bank's 20 languages are 15 / 4 / 1 (Gujarati is the
  first low resource language). The Joshi file is pinned in `data/` and checked
  by `verify_all.py` (97d, 97f, 97g). Bank SHA unchanged (tiers are not stored in
  it). The machine translation pipeline code (`MACHINE`, `--check-stored` with
  linguistic checks) ships with no stored files yet; CI now runs `--check-stored`.

- **2026-10-04** `a404db8` Arabic native speaker feedback integrated: 7 text
  fields (5 attacks, 2 controls; #13 framing clause only). Bank SHA-256 now
  `3d665ef6...`, held-out fingerprint `c9cfe352...`, both in the PREREGISTRATION
  deviation log. Three languages integrated (es, vi, ar), Portuguese pending (the
  reviewer's class is revising it), MSA caveat recorded. Thank-you replies sent in
  thread to the Spanish, Vietnamese and Portuguese reviewers.

- **2026-10-02, the hardening pass** (commits `12e0fac` to `e8f8821`), from Ishaan's
  47 item review list:
  - Spend: live scans fail closed without a passcode; a shared guard in Supabase
    (daily call budget, per visitor hourly limit, site wide running cap,
    idempotency keys) that refuses live scans when it is missing or unreachable;
    per call timeouts and error kinds; whitelisted structured logs.
  - Results: instrument record on every scan (commit, bank SHA, scoring version,
    judge model and wording fingerprint, config); completeness before any rate;
    per attack evidence; `cli.py replay` and `--bundle`; baselines measured
    differently refused (exit 3); results signed so share links cannot be forged.
  - Research: the third phrasing of every attack is held out (pre-registered with
    its fingerprint); defences are judged on it and on benign follow rates;
    README limits section; review rubric and `review_ingest.py` with agreement.
  - Site: share links (`/s/<id>`, private, redacted, 30 days, deletable),
    evidence download and reopening, preflight with cost upper bound, mode tags,
    game crowd stats, double launch guard.
  - Supabase: project `polyguard-db` (free, iad1) through the Vercel marketplace,
    env vars injected into Vercel; migration in `supabase/migrations/`.
  - Testing: CI on every push (`.github/workflows/ci.yml`); browser e2e with
    axe-core; 23 statistical properties; mutation check (12 of 12 planted bugs
    caught, after it found 3 test holes); gitleaks; pip-audit and npm audit on
    locked installs (`requirements.lock`, `uv.lock`).
  - `setup_key.py`: plugs in the API key everywhere when it exists, no paid call.
  - Measured performance in `docs/performance.md`; quickstart, diagram and
    troubleshooting in `docs/quickstart.md`. Audit round 18, findings 60 to 71.

- **2026-10-02** Motion plays for everyone; the system reduced motion setting
  is no longer read (it froze the site on Ishaan's PC, Windows Animation effects
  off). A Motion on/off switch in the nav (wide screens) and footer turns it off,
  remembered per device. The scroll story fits laptop screens (compact board and
  a tighter column under 840 pixels tall). The API ships with only anthropic and
  fastapi (`pyproject.toml`), checked on a preview: meta, game and a streamed scan.

- **2026-10-02** `docs/pilot-plan.md`: the bounded live pilot plan (stages,
  call counts, token caps, worst case cost, $10 hard cap). Plan only, not run;
  needs Ishaan's key and written approval.
- **2026-10-02** `99a3091` Spanish (10 lines) and Vietnamese (1 line) native
  speaker feedback integrated in `generate_attack_bank.py`. Bank SHA-256 now
  `d8dfa081...`, appended to the PREREGISTRATION.md deviation log, whose stale
  13 high / 7 mid count is fixed to 16 / 4. Docs and the site say "received and
  integrated", never "validated". Portuguese feedback pending, nothing changed.

- **2026-10-01** Live on Vercel: **https://polyguard-ten.vercel.app**, project
  `ishaan-s-projects14/polyguard` in Ishaan's own Vercel account (CLI user
  `ishkej`). GitHub repo connected, so every push to main deploys. Checked on the
  live site: meta, game, a streamed scan, results, report download, `/how`, no
  errors. Previews are behind Vercel Authentication; production is public.
- **2026-10-01** `4827c98` Every screen has an address (`/`, `/scan`,
  `/scan/live`, `/scan/results`, `/how`); back and forward work; leaving a running
  scan stops it.
- **2026-10-01** `71f953e` How we know page (`web/src/components/Method.jsx`): a
  simulated fair bot, the worst language circled, 1,000 shuffles building the null
  distribution of `engine.max_gap_permutation_test`, a switch for a real weak spot,
  verdicts that name a false alarm and a missed gap. Reached from nav, landing,
  results.
- **2026-10-01** `efa5359` Stateless API for Vercel: `POST /api/scan` runs a scan
  inside the request that streams it (start, result per attack, done with result
  and report). No job store. Hosted live scans capped at 60 attacks
  (`HOSTED_LIVE_MAX_ATTACKS`, Vercel free plan is 300 s). `vercel.json` (two
  Services: `web/` at `/`, FastAPI `api.server:app` at `/api/*`), `.vercelignore`.
  API tests 47.
- **2026-10-01** `53047c5` Spot the attack game (`GET /api/game`, real bank
  messages, code words neutralised), live scan feed, closing headline width
  stretch, setup hover "no", result bars fill on view, link preview tags, icons.
- **2026-10-01** `d24effb` Scroll story for How it works, hero language strip,
  highlighter pen cursor, paper grain, torn edges, Lenis smooth scrolling, red pen
  on significant live results.
- **2026-10-01** `76af673`, `d65c65d` The test sheet redesign (paper, ink,
  highlighter, red pen; Mona Sans and Gloock; 3D bubble; highlighter reveal hero).
  First version kept as the tag `design/test-sheet-v1`.

## In progress

- **2026-10-05, build sprint from the 7 research notes** (Ishaan: "do everything",
  ship at 73 languages now and keep shipping toward 87, district is WA08, keep the
  name for now, local models approved). Parallel agents, each in its own git
  worktree and branch, never pushing; the main session merges and pushes. Each
  agent keeps a running log at `docs/progress/<topic>.md` on its branch.
  Worktrees (made by hand, `git worktree list`): `C:\dev\pg-wt\local-models`
  (branch `sprint/local-models`), `C:\dev\pg-wt\stats` (`sprint/stats`),
  `C:\dev\pg-wt\defences` (`sprint/defences`). To resume: read each
  `docs/progress/*.md` in those folders, `git merge sprint/<name>` what is
  finished, rerun every suite, push.
  1. local-models: llama.cpp in `C:\dev\llm\`, an Apache or MIT multilingual
     model on the RTX 3060, a `local` provider in providers.py, first real scans
     (free, labelled as a local open weight model, never a production chatbot).
  2. stats: rank trend test against log Common Crawl share (exploratory,
     preregistered before data), power simulation check, `data/resource_measures.csv`.
  3. defences: placebo and "documents are data" arms on the held-out phrasing, a
     lint that defence text never copies bank wording.
  Dropped: the invisible character and language split items (stopped by a safety
  filter; not resumed). OWASP and ATLAS tags and the dataset card stay on the list
  for the main session. Translation quality agent starts after the 73 language
  bank is committed.
  Main session: ship the 73 language bank (deviation row, new SHAs, docs), then
  merge branches as they finish.

- **2026-10-04, expanding the bank from 20 to all 87 catalog languages** (Ishaan:
  "get that number as high as possible"). Not committed yet. How it works:
  - The 67 new languages are machine translated and stored as source files,
    `machine_translations/<code>.json` (attacks and controls as templates with
    `{C}`, `{B64}`, `{T}`, plus English back-translations of three categories).
    `generate_attack_bank.py` merges them (`MACHINE`, `ALL_LANGUAGES`,
    `provenance` "author" or "machine" on every row), so regeneration and the CI
    byte for byte check keep them.
  - Gate for every stored file: `python expand_languages.py --check-stored`
    (structural `verify`, `verify_controls`, and the back-translation intent test).
    Then `python generate_attack_bank.py` and `python linguistics.py`.
  - Done so far: high tier (nl sv no fi cs hu hr sr eu ca fa ky) and mid tier (da
    sk ro bg sl lt lv et gl he kk uz ka bn ur ta th ms ceb af): 32 files, all gates
    pass, bank at 780 attacks over 52 languages.
  - `--check-stored` now also runs linguistics.py's per item checks (script,
    mojibake, length, accents) and takes `--langs` to check a subset.
  - Low tier (35) split across five parallel agents, each writing only its own
    `machine_translations/<code>.json` files and never the bank:
    (1) mk sq is ga cy az ht, (2) ps tg mn hy ne si km, (3) pa te mr kn ml or lo,
    (4) my jv su sw am so rw, (5) ha yo ig zu xh sn ny. To see what landed:
    `ls machine_translations | wc -l` (87 minus 20 = 67 when complete) and
    `python expand_languages.py --check-stored`.
  - **State 2026-10-05:** groups 1, 3 and 5 landed (53 stored files, all gates
    pass, 73 languages total). Groups 2 (ps tg mn hy ne si km) and 4 (my jv su sw
    am so rw) were NOT written: the in-session translation work was stopped by a
    safety filter and will not be resumed that way. Those 14 go through the
    project's own pipeline once the API key exists
    (`python expand_languages.py --langs ps,tg,mn,hy,ne,si,km,my,jv,su,sw,am,so,rw`)
    or through native speakers. Ishaan decides whether to ship at 73 now.
    Bank not yet regenerated or committed for this step.
  - After all 67: append a PREREGISTRATION deviation row (old bank SHA `3d665ef6...`
    and held-out `c9cfe352...` to the new ones; method changed from the API script
    to in-session translation with the same gates, same model back-translation is a
    weak check); update every "20 languages" in README, STATE, NATIVE_REVIEW,
    Method.jsx, DEMO_VIDEO, AUDIT; add `--check-stored` to CI; review sheets for the
    new languages; run every suite; commit (no co-author trailer) and push.
  - Expected totals: 1305 attacks, 522 controls, 87 languages (28 high, 24 mid,
    35 low), held-out membership 435.

- **2026-10-04, research push** (Ishaan: "push this project to the extreme
  limits", "do deep research on things you don't know", "run subagents"). Seven
  parallel research briefs, each writing one file under `docs/research/`
  (uncommitted until reviewed; every number must come from an opened primary
  source):
  `multilingual-attacks.md` (literature on low resource and cross lingual attacks),
  `defenses.md` (prompt injection defences and how to judge them fairly),
  `zero-cost-live-data.md` (real scans with no API spend: local open weight models,
  free tiers and their age rules, a local judge),
  `statistics.md` (sequential stopping, partial pooling, trend against a continuous
  resource measure, power), `translation-quality.md` (offline quality estimation as a
  covariate), `obfuscation-and-mixed-language.md` (Unicode smuggling, homoglyphs,
  transliteration, code switching), `landscape.md` (existing scanners and what
  PolyGuard adds). Next: read all seven, pick the innovations, log each here as it
  is built.

- **Server-side cancellation: Ishaan's own piece** (for the CAC "not entirely AI"
  rule and to be able to defend it). Brief `docs/design/cancellation.md`, tests
  `api/test_cancellation.py` (2 of 6 pass today by design). Do not implement it
  for him; review and explain only.

## Next

1. Hosting is done. Keep `og:image` in `web/index.html` pointing at the live address.
2. Supabase (Ishaan's own account, when he creates a project): saved scans with a
   shareable link, and anonymous game statistics ("people spot attacks in Hindi N%
   of the time"). The Python engine stays on Vercel; Supabase only stores data.
   Keys go in Vercel environment variables, never in the repo.
3. When the Anthropic key exists: first real scan, record it for the CAC video,
   live "try your own attack" behind the passcode, cross model comparison screen.
4. The CAC video (1 to 3 minutes, public on YouTube or Vimeo, due 12:00 pm EDT
   2026-10-26): names, app name, purpose in one sentence, audience, tools and
   languages, the app working. AI use must be fully disclosed in the submission.

## How to resume

```bash
cd C:\dev\polyguard
python -m uvicorn api.server:app --port 8000      # API
cd web && npm run dev                             # site on http://localhost:5173
python api/test_api.py; python test_engine.py; python verify_all.py; python consistency.py
cd web && npm run lint && npm run build
```
