# PolyGuard worklog

The running log of what is built, what is in progress and what is next, kept so
work can resume at once after a break. `STATE.md` is the handoff for the research
engine; `docs/design-research.md` is the record of the web app's look. This file is
the web app and hosting.

## Done (newest first)

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

- Supabase (see Next, item 2).

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
