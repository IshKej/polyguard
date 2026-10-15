# Deploying PolyGuard

The site is live at https://polyguard-ten.vercel.app, on Ishaan's own Vercel account
(`ishkej`). This file is how it is hosted, how a change gets there safely, and what
it costs once live scans are switched on.

## 1. How it is hosted

- **One Vercel project, two services** (`vercel.json`): the Vite site from `web/`
  at `/`, and the FastAPI app (`api/server.py`) at `/api/*`. They build and deploy
  together, so the site and its API can never be out of step.
- **Supabase** keeps the little shared state there is: saved scans behind share
  links, game answers, and the spend guard's counters. The schema is
  `supabase/migrations/`. The API reaches it only with the server's secret key; the
  browser never talks to it.
- **GitHub Actions** (`.github/workflows/ci.yml`) runs every offline suite and the
  browser tests on every push, to any branch.
- **Every push to `main` deploys production. Every push to another branch makes a
  preview** at its own address, protected by Vercel's login so only the account
  owner can open it.

Run `npx vercel whoami` before any Vercel command: it must say `ishkej`. The Vercel
connector in claude.ai belongs to a different team and is never used for this
project.

## 2. Before pushing anything

```bash
python preflight.py        # files present, no key in any committed file, the app boots with no key
python verify_all.py       # the full battery
python test_native_review.py
python api/test_cancellation.py
python web/e2e/test_site.py   # needs `npm run build` in web/ first
```

STATE.md lists the rest. All of them must pass; CI runs them again after the push.

## 3. Preview first, then production

1. Push the change to a branch, not to `main`. Vercel builds a preview of it.
2. Check the preview. It sits behind Vercel's login, so read it through the CLI,
   which carries your login:
   ```bash
   npx vercel curl /review/coverage --deployment <preview URL> -- -s -o /dev/null -D -
   ```
   In Git Bash on Windows, put `MSYS_NO_PATHCONV=1` in front, or the path `/` is
   rewritten into a Windows folder before it reaches the CLI. Do not use the CLI's
   `-d` (debug) flag here: it prints the deployment's protection bypass secret.
3. When the preview is right, fast-forward `main` to that branch and push it. The
   production deployment's state shows on GitHub (the commit's deployments) and in
   the Vercel dashboard.

**Rolling back.** In the Vercel dashboard, promote the previous production
deployment (instant, no rebuild); then revert the commit on `main` so the next push
does not bring the change back. The tag `backup-2026-10-13` marks the last
production commit before the redesign.

## 4. Environment variables (Vercel, Production)

None of these is ever committed. Locally they can live in a `.env` file, which is
ignored by git.

| Variable | Needed for | Default when unset |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_SECRET_KEY` | share links, game answers, the spend guard | on Vercel: no saving, and no live scans either, because the spend guard has nowhere to count; locally an in-memory store stands in |
| `ANTHROPIC_API_KEY` | live scans (and the default judge) | every scan is simulated and says so |
| `POLYGUARD_PASSCODE` | live scans on the hosted site | **no live scans at all**: with a key but no passcode the site fails closed |
| `POLYGUARD_DAILY_CALL_BUDGET` | paid calls per UTC day, every visitor together | 2000 |
| `POLYGUARD_LIVE_PER_HOUR` | live scans per visitor per hour | 4 |
| `POLYGUARD_MAX_LIVE` | live scans running at once, site wide | 2 |
| `POLYGUARD_HOSTED_LIVE_MAX` | attacks in one hosted live scan, so it ends inside the 300 second limit | 60 |
| `POLYGUARD_VICTIM_MODEL`, `POLYGUARD_JUDGE_MODEL` | which models are attacked and which judges | `claude-haiku-4-5` for both |
| `POLYGUARD_WEB_ORIGINS` | cross-origin callers of the API, comma separated | the local Vite addresses only |
| `POLYGUARD_SIGNING_KEY` | signing saved results | derived from `SUPABASE_SECRET_KEY` |
| `POLYGUARD_IP_SALT` | salting the visitor hash used for rate limits | derived from `SUPABASE_SECRET_KEY` |

Other vendors' models appear in the picker only when their own key is set
(`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`); see section 6 before trusting
any of them.

## 5. What every page is sent with

`vercel.json` adds these to every page, not to `/api/`: a content security policy
(scripts only from the site itself, styles from the site and Google Fonts, no
framing), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a referrer
policy and a permissions policy. Vercel adds HTTPS-only (`Strict-Transport-Security`)
itself. The local server applies the same block when it serves the built site, so
the browser tests run under it and fail on anything it blocks. Confirmed on a preview
deployment on 2026-10-15.

The research console (`app.py`, Streamlit) is not deployed; run it locally with
`streamlit run app.py`.

## 6. Before trusting a new provider, smoke-test it

The Anthropic path is covered by the test suite. The OpenAI, Google and
OpenAI-compatible adapters are written to each vendor's documented request shape
but have never run against a live key, so prove them before you believe a number
that comes out of them:

```bash
python providers.py            # which models are ready, and what each one still needs
python providers.py --smoke    # one harmless call per configured provider
```

Every configured model must print PASS. A FAIL means that adapter's request shape
needs fixing, not that the model is vulnerable.

## 7. Cost sanity check

One live scan fires **5 categories × 3 phrasings = 15 short calls to the victim model per language**, plus a judge call only when a reply actually contains the canary. So a 12-language demo scan is ~180 calls, and a full 87-language scan is ~1,305 calls. On the default victim (Claude Haiku) that lands in the low tens of cents even for the full scan, and the phrasings slider drops it to a third if you set it to 1.

Each scan also fires **6 benign capability controls per language**, each one twice: once under a plain helpful assistant prompt, to check the model can follow ordinary instructions in that language at all, and once under the bot's own prompt, to see what the bot allows. Without them a quiet language cannot be told apart from a broken one.

So a full 87-language scan is **1,305 attack calls plus 1,044 control calls (522 controls, twice), 2,349 total**, and the 73 languages in the bank today make 1,971, plus a judge call only where a reply actually contains the token. The judge also reads the attack message, so a judge call costs a little more than the reply alone. Budget for the total, not the attack line alone.

Scanning several vendors multiplies all of that by the number of models, and each vendor bills separately. Start with one model and one tier of languages before running the full cross-model sweep.

The thing that could actually add up is a public link with no gate, where every visitor spends your credits. That is why a live scan on the hosted site needs the passcode, the spend guard caps paid calls per day across every visitor, and one hosted live scan is capped at 60 attacks (section 4).
