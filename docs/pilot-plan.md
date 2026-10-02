# Live pilot: bounded call plan

**Status: PLAN ONLY. Not run. No paid call has ever been made.**

Nothing in this file runs until both of these are true:

1. Ishaan has provided an Anthropic API key (kept in `.env` or an environment
   variable, never in the repo, never in a commit).
2. Ishaan has approved this plan, including its spending cap, in writing.

## What the pilot proves, and what it does not

The pilot proves the plumbing: that the Anthropic adapter, the fixed judge, the
capability controls, the streaming scan and the report all work against a real
model. It does **not** test the central hypothesis. The bank holds 20 languages,
16 high resource and 4 mid resource, and **zero low resource**, so no low versus
high comparison is possible. Every number it produces is labelled a pilot, never
a finding, and the app stays labelled simulated until real scans exist.

## Fixed settings for every stage

| Setting | Value |
|---|---|
| Victim | `claude-haiku-4-5`, temperature 0 |
| Judge | `claude-haiku-4-5`, pinned with `POLYGUARD_JUDGE_MODEL=claude-haiku-4-5`, the same for every victim |
| Keyword judge | Never used for live findings. An attack the judge cannot score is an error, not a guess. The engine already enforces this. |
| Victim output cap | 300 tokens per reply (`max_tokens=300`) |
| Judge output cap | 50 tokens per verdict (`max_tokens=50`) |
| Example bot | "Retail support bot" from `examples.py` (319 characters) |
| Price used | $1.00 per million input tokens, $5.00 per million output tokens (Claude Haiku 4.5, from Anthropic's SDK documentation; check the pricing page before approving) |

## Stages

Each stage needs the one before it to finish clean. Stage 2 needs a second
approval.

| Stage | Command | Languages | Victim calls | Judge calls | Worst case |
|---|---|---|---|---|---|
| 0. Smoke | `python providers.py --smoke claude-haiku-4-5` | none | 1 | 0 | under $0.01 |
| 1. Pilot A | see below | en, es, vi | 63 (45 attacks, 18 controls) | at most 63 | $0.20 |
| 2. Pilot B | see below, second approval needed | all 20 | 420 (300 attacks, 120 controls) | at most 420 | $1.33 |

Spanish and Vietnamese are in Pilot A because they are the only languages with
native speaker feedback integrated so far.

```bash
python -c "import examples; print(examples.EXAMPLES['Retail support bot'])" > pilot_prompt.txt
export POLYGUARD_JUDGE_MODEL=claude-haiku-4-5

# Stage 1, Pilot A
python cli.py scan --prompt pilot_prompt.txt --model claude-haiku-4-5 --langs en,es,vi \
  --out pilot/pilot_a.json --html pilot/pilot_a.html

# Stage 2, Pilot B (only after a second approval)
python cli.py scan --prompt pilot_prompt.txt --model claude-haiku-4-5 \
  --out pilot/pilot_b.json --html pilot/pilot_b.html
```

### How the worst case is computed

The costs are upper bounds computed from the bank itself, not estimates of a typical run:

- every character of input counts as a whole token, which overstates English and
  is close to the real rate for the heaviest scripts
- every victim reply runs to its 300 token cap
- every reply goes to the judge, although the judge only runs when a reply
  contains the canary or the control token
- every judge verdict runs to its 50 token cap

The SDK retries transient errors up to 5 times. Even if every single call were
retried 5 times, Pilot A would stay under $1.20 and Pilot B under $7.96.

## Spending cap

**Hard cap for the whole pilot: $10.** Set a $10 spend limit on the key in the
Anthropic Console before the first call, so the cap holds even if something here
is wrong. Stop at once, and spend nothing more, if any of these happen:

- the smoke test fails
- any adapter or request-shape error
- the judge fails to return a parseable verdict more than twice in a stage
- spending reaches the cap

## Not in this pilot

Each of these needs its own plan and its own approval: other victims (Claude
Sonnet 5, OpenAI and Google models, which also need their own keys), the
cross-model comparison, `judge_eval.py --dual`, and `expand_languages.py`, which
makes translation calls for the 67 remaining languages.

## Approval

Approved by Ishaan for stages 0 and 1, with a $10 cap: ______ (date)

Approved by Ishaan for stage 2: ______ (date)
