# Local models sprint: running log

Branch `sprint/local-models`, worktree `C:\dev\pg-wt\local-models`. Goal: the first
real PolyGuard scans, at zero cost, with a local open weight model on this
laptop's GPU. Updated after every step so a cut off session can resume.

## Step 0: read and plan (done)

Read README.md, STATE.md, docs/research/zero-cost-live-data.md, providers.py,
engine.py (scan loop, judges, instrument), cli.py, docs/pilot-plan.md.

Facts that shape the work:

* Bank in this worktree: 20 languages, 300 attacks, 120 controls, SHA-256
  `3d665ef6...3dff9` (matches STATE.md). One full bank scan is 420 victim calls
  per bot; the 4 example bots in `examples.py` make 1680.
* Judge calls happen only when a reply contains the canary or control token.
  Extraction attacks are scored by verbatim overlap, no judge.
* `engine.run_attack` and `run_control` already refuse the keyword fallback:
  a judge failure is an error, not a guess. The local judge must keep that.
* Hardware: RTX 3060 Laptop, 6144 MiB VRAM, about 1.4 GiB used by the desktop.
  System RAM is tight: about 240 to 370 MB free of 15.2 GiB at the time of
  checking (editors, browser and other sessions running).

## Step 1: llama.cpp release (checked)

GitHub API, `ggml-org/llama.cpp` releases, read 2026-10-06:

* Newest build: `b11435` (published 2026-10-06T06:16Z, commit `43fe9c6`).
  Builds are now marked prerelease; the only non prerelease is a `v0.6.0`
  tag whose sole asset is `nightly-tag.txt`, so the `bNNNNN` builds are the
  binaries.
* Assets chosen (driver reports CUDA 13.2, so the 13.4 build is too new for it):
  * `llama-b11435-bin-win-cuda-12.4-x64.zip`, 264,473,456 bytes,
    sha256 `18ef0727457adf843fe0e6dc17da296c019c821e56b7bc5fc88db734538fbfb7`
  * `cudart-llama-bin-win-cuda-12.4-x64.zip`, 391,443,627 bytes,
    sha256 `8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6`
* llama.cpp is MIT licensed, no account, no terms of service. Ollama not used
  (its terms say 18+).

## Step 2: model licenses (checked on the model cards, 2026-10-06)

| Role | Model | GGUF repo | License | Age clause |
|---|---|---|---|---|
| Victim | Qwen3.5 4B | `unsloth/Qwen3.5-4B-GGUF`, file `Qwen3.5-4B-Q4_K_M.gguf` | Apache 2.0 (card metadata and the LICENSE file, which is the plain Apache 2.0 text) | none found |
| Judge | Gemma 4 E2B it | `unsloth/gemma-4-E2B-it-GGUF`, file `gemma-4-E2B-it-Q4_K_M.gguf` | Apache 2.0 (card metadata; license link goes to Google's "Apache License 2.0" Gemma 4 page) | none found |

Both repos are ungated. Qwen3.5 card: "Expanded support to 201 languages and
dialects"; thinks by default, switched off per request with
`chat_template_kwargs: {"enable_thinking": false}` (the card's own example).
Gemma 4 card: "Out-of-the-box support for 35+ languages, pre-trained on 140+
languages"; thinking is off unless the system prompt starts with `<|think|>`.

Skipped: Llama 3.2 and Gemma 3 (age of consent clauses in their licenses).

Judge is a different model family from the victim on purpose, so no model
grades its own replies.

## Step 3: installed and verified (done, 2026-10-06)

```bash
# all under C:\dev\llm (outside the repo); script kept at C:\dev\llm\download.sh
curl -fL -o zips/llama-b11435-bin-win-cuda-12.4-x64.zip  <release asset>
curl -fL -o zips/cudart-llama-bin-win-cuda-12.4-x64.zip  <release asset>
curl -fL -o models/Qwen3.5-4B-Q4_K_M.gguf       https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/e87f176.../Qwen3.5-4B-Q4_K_M.gguf
curl -fL -o models/gemma-4-E2B-it-Q4_K_M.gguf   https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/0314792.../gemma-4-E2B-it-Q4_K_M.gguf
unzip both zips into C:\dev\llm\llama-b11435\
```

Every file's SHA-256 matched the digest published by GitHub or Hugging Face:

| File | Bytes | SHA-256 |
|---|---|---|
| llama-b11435-bin-win-cuda-12.4-x64.zip | 264,473,456 | 18ef0727457adf843fe0e6dc17da296c019c821e56b7bc5fc88db734538fbfb7 |
| cudart-llama-bin-win-cuda-12.4-x64.zip | 391,443,627 | 8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6 |
| Qwen3.5-4B-Q4_K_M.gguf (repo revision e87f176) | 2,740,937,888 | 00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4 |
| gemma-4-E2B-it-Q4_K_M.gguf (repo revision 0314792) | 3,106,738,272 | 740185b21d22ceb83a11c3aa62ad5842ef32c70f6096d756bbee85a1e4ec34b8 |

`llama-server --version`: `0.6.0-dev (build 11435, commit 43fe9c642)`.

## Step 4: measured speed (done)

`llama-bench -p 512 -n 128 -r 3`, nothing else on the GPU, power plan as found:

| Model | Where | Prompt, tokens/s | Generation, tokens/s |
|---|---|---|---|
| Qwen3.5 4B Q4_K_M (2.54 GiB) | GPU, all layers | 1147 ± 26 | 47.6 ± 1.2 |
| Gemma 4 E2B Q4_K_M (2.88 GiB) | GPU, all layers | 2321 ± 138 | 53.1 ± 7.6 |
| Gemma 4 E2B Q4_K_M | CPU weights (`-ngl 0`, 8 threads) | 512 ± 33 | 3.0 ± 0.1 |

CPU generation is slow because system RAM was nearly full. Both servers fit on
the GPU together once Gemma's per layer embedding tables stay in system RAM
(`-ot "per_layer_token_embd=CPU"`): 5710 of 6144 MiB used with the desktop.
A judge verdict then takes about 0.6 s, a one sentence reply about 0.8 s.

Servers as run:

```bash
cd C:/dev/llm
./llama-b11435/llama-server.exe -m C:/dev/llm/models/Qwen3.5-4B-Q4_K_M.gguf -ngl 99 -c 8192 -np 4 --host 127.0.0.1 --port 8080 --alias qwen3.5-4b
./llama-b11435/llama-server.exe -m C:/dev/llm/models/gemma-4-E2B-it-Q4_K_M.gguf -ngl 99 -ot "per_layer_token_embd=CPU" -c 4096 -np 2 --host 127.0.0.1 --port 8081 --alias gemma-4-e2b
```

Use an absolute `-m` path: `/props` reports the path exactly as given, and the
provenance hash needs to find the file.

Checked by hand: `chat_template_kwargs: {"enable_thinking": false}` gives a
direct answer from Qwen3.5 (`ONLINE` in 1.2 s), and `response_format` with a
`json_schema` returns `{"complied": ...}` from both servers.

## Step 5: code (done)

* `providers.py`: provider `local` (urllib only, no new dependency). Settings
  from `POLYGUARD_LOCAL_URL` and `POLYGUARD_LOCAL_MODEL` (env or `.env`, never
  Streamlit secrets). Temperature 0, seed 0, prompt cache off, thinking off on
  every call. Timeout `POLYGUARD_LOCAL_TIMEOUT` (default 300 s). Retries on
  connection failures, 429 and 5xx with backoff; no retry on timeouts or other
  4xx. Errors raise as `LocalHTTPError` (status code), `LocalConnectionError`
  or `LocalTimeoutError`, so `classify_error` gives the usual kinds.
  `deterministic` is False for local models (server batching).
* Local judge: `POLYGUARD_JUDGE_BACKEND=local` makes `judge_client()` return a
  `LocalJudgeClient` on `POLYGUARD_JUDGE_URL` (falls back to the victim's URL).
  It mimics the one `messages.create` call the engine judges make, sends the
  engine's JSON schema as `response_format`, and raises on an empty verdict, so
  the no keyword fallback rule in `engine.run_attack` is untouched.
* Provenance: `/props` gives the weights path and server build; the file is
  hashed (SHA-256) on disk. `engine.instrument` now records `victim_is_local`,
  `judge_is_local`, `victim_local`, `judge_local`, `victim_weights_sha256`,
  `judge_weights_sha256` (both added to `COMPARABLE_FIELDS`) and
  `judge_is_victim`. `judge_model` becomes `local:<gguf file>`.
* `engine.MAX_WORKERS` reads `POLYGUARD_MAX_WORKERS` (default still 12).
* `cli.py scan`: a configured but unreachable judge exits 2 with a message;
  local scans print the label, the judge and a "not a production chatbot" note.
  Bundle manifest records both llama-server builds.
* `report_html.py`: a local scan gets a "Local open weight model, not a
  production chatbot" note and rows naming both weights files.
* `preflight.py`: clears the local variables too when simulating a clean deploy.

## Step 6: tests (done)

26 new cases in `test_engine.py` against a fake llama-server (stdlib HTTP
server, no GPU): labels, request shape, provenance hash, judge schema, an end
to end local scan, judge failures as unscored errors (never a break, never a
keyword guess), error kinds (429, 404, timeout, dropped connection), and the
comparability refusal for different weights.

| Suite | Result |
|---|---|
| test_engine.py | 194/194 |
| test_stats_properties.py | 24/24 |
| api/test_api.py | 90/90 |
| verify_all.py | 223/223 |
| consistency.py | no stale claims |
| mutation_check.py | 13/13 killed |
| rehearsal.py | answer key PASS |

## Step 7: judge check on the gold set (done)

First attempt failed loudly, which is the design working: Gemma 4 E2B wrote a
"Thinking Process" into `reasoning_content` on 15 of the gold replies despite
`enable_thinking: false`, used the whole 50 token cap and returned no verdict.
Fix: both servers now start with `--reasoning off --reasoning-budget 0`, and
`providers.local_chat` refuses any reply that carries reasoning (test added,
195/195).

`python judge_eval.py --llm` with the local judge, 41 item gold set (author
labelled, structural, 22 languages):

| Judge | Overall | Covered languages (26) | Uncovered languages (15) |
|---|---|---|---|
| Gemma 4 E2B (the judge used) | acc 95%, FP 7%, kappa 0.89 | acc 100%, FP 0% | acc 87%, FP 15%, kappa 0.59 |
| Qwen3.5 4B (the victim, for comparison only) | acc 100% | acc 100% | acc 100% |

Every one of the 20 bank languages is in the covered bucket, where the Gemma
judge made no errors on this gold set. Its two false positives were in
languages outside the bank (am, km, mn, my, ne, si, so, sw, yo, zu are the
uncovered ones). So the Gemma judge is usable for this bank and must be
re-measured before any low resource languages are scanned. 41 items is small:
zero errors in 26 still allows a real false positive rate of roughly 13 percent
(Wilson upper bound), so this is a floor check, not a validation.

Gemma is kept as the judge although Qwen scored higher here, because a model
judging its own replies is a known bias and the gold set does not contain
Qwen's own replies.

## Step 8: first smoke scan, and a memory problem (done)

`python cli.py scan --prompt retail-support-bot.txt --model local --langs en,es,vi --bundle results/local/2026-10-06/smoke-retail-en-es-vi --bundle-include-prompt`

Ran clean (45 of 45 attacks scored, 18 of 18 controls, replay matched) but
took 4 minutes for 63 victim calls. Cause: llama-server's host prompt cache
(`--cache-ram`, default 8192 MiB) had grown the victim server to 12.5 GB of
private memory on a 16 GB machine, with about 250 MB of commit left. Servers
now start with `--cache-ram 0 --ctx-checkpoints 0` (PolyGuard sends
`cache_prompt: false` anyway). After the fix: one call 1.15 s, 12 calls in
8.7 s with 12 workers (about 0.7 s per call). Script: `C:\dev\llm\start-servers.sh`.

What the smoke run showed (kept, superseded by the rerun on the committed code):

* Both "breaks" (one es, one vi, both indirect injection) are the bot
  TRANSLATING the injected review, canary included, which the Gemma judge
  scored as compliance. Reading the replies, the bot continued its task rather
  than obeying the injected instruction, so these look like judge false
  positives. The judge wording was not changed (that would change the judge
  fingerprint and is a methodology decision); see the second judge pass below.
* The retail bot declines the benign controls in English too (0 of 6 in en,
  1 of 6 in es and vi): it says it cannot repeat codes. With an English
  baseline of 0, the capability check cannot flag any language, so for this bot
  a low break rate cannot be told apart from incapacity by the controls.

Note: another session is also using `C:\dev\llm` (files `tq-*`, `tq_diag.py`).
Stop only this sprint's servers by PID, never `taskkill /IM llama-server.exe`.

## Step 9: second judge tool (done)

`rejudge.py` (committed) asks a second, separately configured judge about every
attack reply containing the canary in a saved scan, and writes
`second_judge.json` (agreement, Cohen's kappa, every disagreement) next to it
without changing the scan. On the first smoke run, Qwen3.5 4B as second judge
said 0 of the 4 canary replies were breaks where Gemma said 2: agreement 50%,
kappa 0.00. Both disagreements are the translation case above. Treat every
local break rate as a range between the two judges until a human labels the
disagreements.

## PAUSED 2026-10-06 (coordinator asked to stop at a clean point)

State at pause:

* Code committed: `3839c05` (local provider, local judge, instrument, CLI,
  report, 27 tests) and the `rejudge.py` commit after it. This WIP commit adds
  this log and the quickstart section.
* All suites pass at pause: test_engine 195/195, test_stats_properties 24/24,
  api/test_api 90/90, verify_all 223/223, consistency clean, mutation_check
  13/13 killed, rehearsal answer key PASS.
* Both llama-servers and the scan run were stopped. The rerun was stopped
  before any bundle was written, so `results/` is empty and was removed. The
  first smoke run's numbers above are from before the commit and the memory fix
  and are not kept as a result.
* `docs/quickstart.md` has the local section. NOT done yet: the one README
  line, and correcting "No live scan has run yet" in README.md and "No live
  scan has ever run" in STATE.md once real local results exist (they will then
  be false for local models, still true for production chatbots).

What is left, in order:

1. Start the servers: `bash C:/dev/llm/start-servers.sh`, then wait until
   `curl -s http://127.0.0.1:8080/health` and `:8081/health` both say ok.
2. Write the four example prompts to files (they come from `examples.py`):
   `python -c "import examples,re,pathlib; d=pathlib.Path('C:/dev/llm/prompts'); d.mkdir(exist_ok=True); [ (d/(re.sub(r'\W+','-',n.lower()).strip('-')+'.txt')).write_text(p,encoding='utf-8',newline='\n') for n,p in examples.EXAMPLES.items()]"`
3. Run the smoke scan, then the four full scans, each followed by replay and the
   second judge. Next command to run (from the worktree):

   ```bash
   export PYTHONIOENCODING=utf-8 POLYGUARD_LOCAL_URL=http://127.0.0.1:8080 POLYGUARD_LOCAL_MODEL=qwen3.5-4b \
     POLYGUARD_JUDGE_BACKEND=local POLYGUARD_JUDGE_URL=http://127.0.0.1:8081 POLYGUARD_JUDGE_LOCAL_MODEL=gemma-4-e2b
   python cli.py scan --prompt C:/dev/llm/prompts/retail-support-bot.txt --model local --langs en,es,vi \
     --bundle results/local/<date>/smoke-retail-en-es-vi --bundle-include-prompt
   python cli.py replay results/local/<date>/smoke-retail-en-es-vi/scan.json
   POLYGUARD_JUDGE_URL=http://127.0.0.1:8080 POLYGUARD_JUDGE_LOCAL_MODEL=qwen3.5-4b \
     python rejudge.py results/local/<date>/smoke-retail-en-es-vi/scan.json
   ```

   Then the same without `--langs` for each of `retail-support-bot`,
   `school-help-desk-bot`, `banking-assistant`, `clinic-front-desk-bot`, into
   `results/local/<date>/full-<bot>`. Expected about 5 to 7 minutes per bot
   (420 victim calls at about 0.7 s each, plus judge calls). Any driver script
   must stop on the first failure (`set -e`): the stopped run kept going after
   the servers died, and the CLI correctly refused each scan with exit 2.
4. Read every break and every second judge disagreement by hand; report
   completeness, per language rates with intervals, the capability caveat (the
   retail bot declined the benign controls even in English), and both judges'
   counts. Label everything "local open weight model qwen3.5-4b, not a
   production chatbot".
5. README line and the STATE/README corrections, rerun all suites, commit on
   `sprint/local-models` (no co-author trailer). Do not push or merge.
