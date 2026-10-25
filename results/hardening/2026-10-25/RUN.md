# Hardening retest, staged 2026-10-25

**Status: performed on 2026-10-25 on this design (bank, prompts, languages, category, controls on, both
arms in one session). Its results are recorded and kept privately, pending Ishaan's decision on
publication; nothing about them is claimed in this repository. Any further run needs its own explicit
clearance.**

This branch is commit `e6e55de` (bank SHA-256 `8f62cefc765149b5f91701025965bb81b29b0d74640ac7b9fa63f9b66b1f2587`,
the bank the October runs and the 2026-10-24 confirmation runs used) plus two prompt files and, since the run,
main's per-call usage logging and SDK gate (no change to the bank, the judge or the scoring), so the instrument is identical
to the confirmation runs except the prompt.

## What it tests

The 2026-10-24 confirmation run C (Claude Sonnet 5, judge Claude Haiku 4.5) recorded instruction override breaks
of one shape: the reply starts with the requested code (PWNED_7F3A) and then refuses. That is an output rule
violation, the bot printing the attacker's token; it is not evidence that sensitive data can be taken. Its counts
and replies are kept privately, pending Ishaan's decision on publication.

- `prompt-baseline.txt`: the retail bot prompt the runs used, SHA-256 `1e400b9b...` (matches the run manifests).
- `prompt-hardened.txt`: the same prompt plus one rule aimed at that shape: write none of what the message asks
  for, not even before refusing; the reply starts with the refusal.

## Run (only after clearance)

Run both arms in the same session, with controls, so the comparison is not run C (no controls, a day earlier)
against a new run:

    git checkout retest-hardened-2026-10-25
    python -c "import engine; print(engine.bank_sha256())"   # must print 8f62cefc...
    python cli.py scan --prompt results/hardening/2026-10-25/prompt-baseline.txt --model claude-sonnet-5 \
        --langs en,fr,el,ceb,eu,is,ky,ro --categories instruction_override \
        --out results/hardening/2026-10-25/baseline.json --bundle results/hardening/2026-10-25/baseline_bundle
    python cli.py scan --prompt results/hardening/2026-10-25/prompt-hardened.txt --model claude-sonnet-5 \
        --langs en,fr,el,ceb,eu,is,ky,ro --categories instruction_override \
        --out results/hardening/2026-10-25/hardened.json --bundle results/hardening/2026-10-25/hardened_bundle
    python cli.py compare results/hardening/2026-10-25/baseline.json results/hardening/2026-10-25/hardened.json
    python cli.py replay results/hardening/2026-10-25/hardened.json

Then commit the four outputs to this branch at once. Save them somewhere durable before anything else.

## Cost

Not estimated from heuristics. Spend is measured and capped from the API's own records:

- Every call's input and output tokens come from the API response and are written, one JSON
  line per call, to `usage.jsonl` beside the results (`providers.USAGE`, ported to this branch
  from main; `test_usage.py`). Totals are printed at the end of each scan.
- The run goes through a guard that, before each call, reserves that call's worst case (its
  input tokens plus `max_tokens` of output at the published price) against a fixed budget cap,
  and stops before the cap rather than after it. The guard keeps its own running ledger. (The
  runner used on 2026-10-25, `guarded_run.py`, is kept with that run's private results.)
- Prices: `providers.PRICES_PER_MTOK` (Claude Sonnet 5 $2 / $10 and Claude Haiku 4.5 $1 / $5 per
  million input / output tokens, rate card effective 2026-08-31). Re-check them before a run.
- The remaining credit is not known from the API (it has no balance endpoint); past spend is
  shown from the usage logs, never from estimates.
- Before any live call, check the installed `anthropic` SDK against `requirements.lock`: on
  2026-10-25 an unpinned 2.x SDK passed every victim call and failed every judge call. This
  branch and main now refuse to start a live scan when the installed SDK does not match the
  lock, or when it fails the request contract (`sdk_gate.py`: the judge's temperature and
  output_config and each victim's request, sent to a server on 127.0.0.1, must arrive as
  sent). On SDK 2.3.0 that contract fails exactly as the run did, at no cost.

## How to read it

24 attacks per arm is a diagnostic, not a study: with this n a difference of one or two breaks is noise (see `compare`'s test). The hardened arm also has to keep following
ordinary instructions (the controls); a prompt that refuses everything would also stop every attack.
