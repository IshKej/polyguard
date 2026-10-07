# Zero cost live data for PolyGuard

Researched 2026-10-05. Everything marked "measured" was read from this PC that day. Every license, clause, price, limit and size below was copied from a page opened that day (URLs in section 5). Anything I could not open is marked [unverified]. Anything I worked out myself is marked [estimate] with the arithmetic shown. No model or program was downloaded or installed.

## 1. Summary

* **Run real scans on this PC with llama.cpp (MIT license, no terms of service) and a small open weight model.** Best first pair: Qwen3.5 4B (Apache 2.0, "201 languages and dialects", 2.74 GB download) as the victim, and Gemma 4 (Apache 2.0, 140+ pretraining languages) as a second victim or as the judge. The 6 GiB RTX 3060 Laptop GPU holds a 4B model at 4 bit with room to spare, so a full 87 language scan is roughly half an hour to an hour of compute [estimate], not days.
* **Most hosted free tiers are closed to a 15 year old.** Gemini API, Groq, OpenRouter and Cohere all say 18 or older (or age of majority) in their current terms, Ollama's terms say 18, and GitHub Models was shut down on July 30, 2026. Llama 3.2 and Gemma 3 weights carry "age required to give legal consent" clauses, so skip them unless a parent accepts the license. Hugging Face (13+) and Cloudflare Workers AI (no age clause found) are the only open doors, and Cloudflare should be a parent's account.
* **The code change is small.** A `local` provider in `providers.py` using `httpx` (already installed) and a small judge adapter that mimics the Anthropic `messages.create` call, so `engine.py` itself does not change. About 4 hours.
* **A local result is real data about small open models, not about production chatbots.** It can validate the whole pipeline, measure the judge, and test whether language matters for small models. It cannot say anything about the Anthropic, OpenAI or Google bots people actually deploy.
* **Two facts change the plan.** The judge only runs when a reply contains the canary or control token (at most 1566 judge calls for 87 languages, not 1827), and this PC had only 385 MB of RAM available when measured, so close browsers and editors before any run.

## 2. This PC's hardware (measured, read only)

| Part | Value |
|---|---|
| Machine | ASUS ROG Zephyrus G15 GA503RM, Windows 11 Home build 26300, on AC power, Windows power plan "Silent" |
| CPU | AMD Ryzen 9 6900HS, 8 cores, 16 threads, 3.3 GHz base, 4 MB L2, 16 MB L3 |
| RAM | 16,366,272,512 bytes visible (15.2 GiB). Two 8 GB modules (Samsung, Micron), DDR5 at 4800 MT/s, so dual channel. **Only 385 MB was available and the CPU sat at 100 percent when I measured** (other work was running; Memory Compression held 2.3 GB) |
| Dedicated GPU | NVIDIA GeForce RTX 3060 Laptop, 6144 MiB VRAM per nvidia-smi (Windows reports 4 GB because that field is 32 bit), driver 596.36, CUDA 13.2. The desktop already used about 1.8 GiB, leaving about 4.1 GiB free. Max memory clock 7001 MHz |
| Integrated GPU | AMD Radeon 680M, shares system RAM |
| Disk | 114.2 GB free on C: |
| Python | 3.14.3 |
| Already installed | None of: ollama, llama-server, torch, transformers, llama_cpp, onnxruntime_genai. Present: anthropic 0.86.0, httpx 0.28.1, requests, numpy, scipy, huggingface_hub. **Not present: the openai SDK** |
| Build tools | No Visual C++ compiler, no cmake (so nothing that builds from source). git and winget are present |

Memory bandwidth, worked out from the numbers above [estimate]: DDR5 at 4800 MT/s, 8 bytes per transfer, 2 channels = 4800 x 8 x 2 = 76.8 GB/s peak. I did not find a published CPU benchmark for this exact chip, and AMD's product page timed out when I tried it.

## 3. Findings

### 3.1 Runtimes: install friction on this PC

| Runtime | Verdict | Why (source) |
|---|---|---|
| **llama.cpp, prebuilt zip** | **Use this** | Release b11418 (2026-10-05) ships Windows zips: `win-cpu-x64` 19.4 MB, `win-vulkan-x64` 33.3 MB, `win-cuda-12.4-x64` 264.5 MB (plus a separate `cudart` zip of 391.4 MB), `win-cuda-13.4-x64` 153.1 MB (plus 423.5 MB cudart). MIT license, no account, no installer, no terms of service. nvidia-smi reports CUDA 13.2 on this driver, so pick the 12.4 build [inference]. `llama-server` gives an OpenAI compatible `/v1/chat/completions`, `-np` parallel slots, JSON schema output via `response_format`, per request `chat_template_kwargs`, and a router mode that can hold several models (`--models-max`) |
| Ollama | Avoid | Install is easy (no administrator, API on localhost:11434), but its Terms of Service (last updated May 2026) say "You must be at least 18 years old to use our services" and define services as "our website, software, APIs, and related services". llama.cpp does the same job without that clause |
| llama-cpp-python | Skip | PyPI has only a 76.6 MB source tarball for 0.3.36, and this PC has no compiler. The project's own wheel index does list `py3-none-win_amd64` wheels for 0.3.36, so it would work, but it adds a Python dependency for nothing, and I could not confirm that version supports the newest model architectures [unverified] |
| transformers on CPU | Skip | torch 2.14.1 has a cp314 Windows wheel (124 MB), but unquantized weights for a 4B model are about 8 GB (bf16 file for Qwen3.5 4B is 8.42 GB), and only 385 MB of RAM was available. Very slow and memory bound |
| ONNX Runtime GenAI | Skip for now | 0.17.1 has a cp314 Windows wheel (4.4 MB), but it needs models converted to ONNX. Microsoft publishes one for Phi 4 mini (linked from its model card); for Qwen3.5 and Gemma 4 I did not find one [unverified] |
| LM Studio | Possible, not needed | A one fetch summary of its app terms (version August 23, 2026) found no age clause; I could not read the full text directly [partly verified] |

Downloads need no account for the models I recommend: the Hugging Face API reports `gated: False` for Qwen3.5 4B and Gemma 4 E4B, and the GGUF repos from unsloth and ggml-org are ungated.

### 3.2 Candidate models

Sizes are the Q4_K_M file in the named Hugging Face repo (Q4_0 where no Q4_K_M exists). "Fits" means fully inside about 4.1 GiB of free VRAM with a small cache. Benchmarks are vendor reported on the model cards, probably in thinking mode, so treat them as rough.

| Model | Params | Download | Official languages (card wording) | License and age terms | Fits GPU | Vendor MMMLU |
|---|---|---|---|---|---|---|
| **Qwen3.5 4B** | 4B | 2.74 GB | "Expanded support to 201 languages and dialects" | Apache 2.0, ungated | Yes | 76.1 |
| Qwen3.5 2B | 2B | 1.28 GB | same | Apache 2.0 | Yes | 63.1 |
| Qwen3.5 0.8B | 0.8B | 0.53 GB | same | Apache 2.0 | Yes | 44.3 |
| Qwen3.5 9B | 9B | 5.68 GB | same | Apache 2.0 | No (partial offload) | 81.2 |
| **Gemma 4 E4B** | 4.5B effective, 8B with embeddings | 4.59 GB (Q4_0) | "Out-of-the-box support for 35+ languages, pre-trained on 140+ languages" | Apache 2.0 (license page is the standard Apache text), ungated | Tight | 76.6 |
| Gemma 4 E2B | 2.3B effective | 3.11 GB | same | Apache 2.0 | Yes | 67.4 |
| Phi 4 mini instruct | 3.8B | 2.49 GB | 23 listed: Arabic, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Hebrew, Hungarian, Italian, Japanese, Korean, Norwegian, Polish, Portuguese, Russian, Spanish, Swedish, Thai, Turkish, Ukrainian | MIT | Yes | n/a |
| Qwen3 4B Instruct 2507 | 4.0B | 2.50 GB | card says "long-tail knowledge coverage across multiple languages"; no count | Apache 2.0 | Yes | n/a |
| Llama 3.2 3B | 3.21B | 2.02 GB | 8 official: English, German, French, Italian, Portuguese, Hindi, Spanish, Thai | **Licensee is a person "of the age required under applicable laws, rules or regulations to provide legal consent"**; gated | Yes | n/a |
| Gemma 3 4B | 4B | 2.49 GB | language count not opened [unverified] | **Gemma Terms of Use 2.1: "You represent and warrant that you have the legal capacity to enter into this Agreement (including being of sufficient age of consent)"**; gated (manual approval) | Yes | n/a |
| Aya Expanse 8B | 8B | 5.06 GB | 23 languages | CC-BY-NC 4.0 plus Cohere acceptable use policy; gated, you must share contact information | No | n/a |
| gpt-oss-20b | 21B, 3.6B active | 12.11 GB | not stated on card | Apache 2.0 | No (needs 16 GB memory by its own card) | n/a |

Notes that matter:

* **Qwen3.5 4B and 9B think by default.** The card says they "operate in thinking mode by default", while 0.8B and 2B do not. A thinking victim spends its 300 token cap reasoning and may return nothing. Send `chat_template_kwargs: {"enable_thinking": false}` on every call (llama-server accepts this per request). Gemma 4 turns thinking on only if a `<|think|>` token is in the system prompt, so it is off by default.
* **Language coverage is a variable, not a nuisance.** Phi 4 mini lists 23 languages and Llama 3.2 lists 8, against a bank of 87. A model scored on languages it was never trained for will fail the benign controls there. PolyGuard already reports those as capability limited, which is the right handling, and it makes "official language list length" a useful covariate when comparing models.
* **Qwen3.5 4B and Gemma 4 E4B are close on the vendors' own multilingual benchmark** (76.1 versus 76.6 on MMMLU). Two vendors, two training recipes, both Apache 2.0, which supports a cross model comparison on the cheap.
* The Qwen2.5 3B model uses the non Apache "qwen-research" license; skip it.

### 3.3 Speed

Published numbers I could open (llama.cpp CUDA scoreboard, Llama 2 7B Q4_0, 3.56 GiB, no flash attention):

| GPU | Prompt (pp512, tokens/s) | Generation (tg128, tokens/s) |
|---|---|---|
| RTX 3060 desktop, 12 GB, 192 bit | 2137.50 | 75.57 |
| RTX 4050 Laptop, 6 GB, 96 bit | 1725.85 | 43.72 |
| RTX 3080 Laptop | 2875.02 | 90.60 |

This PC's RTX 3060 Laptop is the desktop's GA106 chip with a lower power cap (80 W, plan "Silent" right now). NVIDIA's page lists 6 GB GDDR6 and 3840 CUDA cores but not the bus width, so I treat the laptop part as roughly 85 to 100 percent of the desktop's generation speed [estimate, bus width unverified]. Generation is memory bound, so speed scales with file size: a 2.55 GiB model is about 1.4 times smaller than the 3.56 GiB benchmark model. Working that through and knocking off a third for small model overhead and the newer architectures gives **about 50 to 70 tokens/s for a 4B Q4 model, single stream, about 90 to 110 for a 2B** [estimate]. I found no published number for the Ryzen 9 6900HS. From 76.8 GB/s peak, a realistic 50 to 60 percent gives roughly 10 to 15 tokens/s for a 4B Q4 model on CPU [estimate]; CPU prompt processing is the real bottleneck at about 60 tokens/s [estimate, a guess]. **Replace every estimate with `llama-bench` numbers before trusting a time budget** (step 2 below, 10 minutes).

### 3.4 The judge

What the code does today: `engine.llm_judge_compliance` sends the reply to an Anthropic client and expects JSON `{"complied": bool}`. It runs only after the canary is already present in the reply. The existing gold set in `judge_eval.py` has 41 replies in 22 languages, labelled by the author on structure, and `judge_eval.py --llm` and `--dual` already compute false positive rate and Cohen's kappa. The keyword heuristic had a 77 percent false positive rate outside its 20 languages (judge_report.txt), which is why live scans must use an LLM judge.

**Candidates.** Qwen3.5 4B or Gemma 4 E4B (whichever is not the victim, so a model never grades its own output; the LLM evaluator literature finds models favor their own generations, arXiv 2404.13076). Qwen3.5 9B is stronger (MMMLU 81.2) but does not fit the GPU next to anything else. Qwen3Guard Gen (0.6B, 4B, 8B, Apache 2.0, "119 languages and dialects") is a safe/unsafe/controversial moderation classifier; it answers a different question than "did the bot obey the injected instruction", so I would not use it as the judge.

**Why not just trust it.** Published work on multilingual LLM judges found an average Fleiss' kappa of about 0.3 across languages, "particularly poor performance in low-resource languages", with neither multilingual training nor scale fixing it (arXiv 2505.12201). That is the same direction as the effect PolyGuard measures, so the judge must be measured per language tier before any rate is reported.

**Measurement protocol (all with existing code: `engine.classification_metrics`, `engine.cohens_kappa`, `engine.wilson_ci`):**

1. Keep the 41 item gold set as a floor. It only tests structure, so also build a real set: after the first pilot, collect every local reply that contains the canary, sample at least 100 genuine refusals and 30 genuine compliances stratified by tier, and label them blind to the judge's answer. Ishaan reads English, Spanish, Hindi and Gujarati; the Vietnamese and Arabic reviewers already helped with the bank and could label a short batch.
2. Report the false positive rate (refusals scored as breaks) per tier with 95 percent Wilson intervals. Sample size decides how much a clean result proves: zero errors in 30 refusals still allows up to 11.4 percent, 60 allows 6.0 percent, 100 allows 3.7 percent (computed with `engine.wilson_ci`). Three errors in 100 is 1.0 to 8.5 percent.
3. Run two judges on the same replies and report kappa and every disagreement, split by tier (existing `--dual`, pointed at two local models).
4. Run the judge twice at temperature 0 with `cache_prompt` off and report self agreement, because batching can change results (llama-server docs: logits are "not guaranteed to be bit-for-bit identical for different batch sizes").
5. Report honestly: print the judge model, its quantization, the prompt hash (already in the instrument record), the per tier false positive rate with intervals, kappa, and the count of replies where the two judges disagreed. A tier where the judge's false positive rate cannot be bounded under about 10 percent should be marked "not scoreable", the same way capability limited languages already are.
6. Keep the canary string as a cross check only: if the judge says "complied" on a reply that does not contain the canary, that is a judge bug. This does not change the rule that findings come from the LLM judge.

### 3.5 Free hosted tiers and age terms

Short version for a 15 year old: **only Hugging Face (13+) and Cloudflare (no age clause found) are open, and neither gives a free scan's worth of calls on its own account without a parent.**

| Service | Age clause, current terms | Free limit | For Ishaan alone |
|---|---|---|---|
| Gemini API / Google AI Studio | Additional Terms effective March 23, 2026: "You must be 18 years of age or older to use the APIs. You also will not use the Services as part of a website, application, or other service (collectively, "API Clients") that is directed towards or is likely to be accessed by individuals under the age of 18." | Free tier on several Flash and Flash-Lite models; limits are shown only inside AI Studio, none stated in the docs. Free tier content is "used to improve our products" | **No.** Even with a parent's account, a public hosted PolyGuard is a site teens may use, which the second sentence bars |
| Groq | Services Agreement (last modified June 22, 2026), section 2: "You must be 18 years of age or older to access or use the Cloud Services. By using the Cloud Services, you represent that you are age 18 or older." Also "not for consumer use" | Not stated on the pages I opened | **No** |
| OpenRouter | Terms section 2: "You must be at least 18 years of age to use the Service." | Free (":free") models: 20 requests per minute; 50 per day with under 10 credits bought, 1000 per day after buying 10 | **No** |
| Cohere | "YOU HAVE REACHED THE AGE OF MAJORITY IN YOUR JURISDICTION" | Trial key: 1,000 API calls a month, 20 requests per minute | **No**, and 1,000 calls is under one scan anyway |
| Hugging Face Inference Providers | Terms of Service: "you must be a natural person of at least age 13, or a legal entity duly registered." | Free users get "$0.10, subject to change" of credits per month | Allowed, but $0.10 is not enough for a scan. Routed providers may add their own terms [unverified] |
| Cloudflare Workers AI | Self-Serve Subscription Agreement (last updated September 12, 2025): no age clause in the text; it is "effective when you click to accept it, use or access the Services" | 10,000 Neurons per day free, resets 00:00 UTC; text generation 300 requests per minute | **Unclear. Use a parent's account.** See the budget below |
| Mistral | AI Studio API falls under the Commercial Terms (effective September 25, 2026), which send individual consumers to the consumer terms. Consumer terms: "You must be at least thirteen (13) years old... you must have parental or legal guardian permission, where required, if you are a minor" | Docs: "Free mode: API access is enabled by default with no credit card required. Usage and rate limits apply." Numbers are in the admin console, which I could not open [unverified] | **Unclear. Use a parent's account** |
| Cerebras | Website Terms: "at least 13 years of age or the minimum age of digital consent" | $5 credit, expires in 30 days, only after adding "a verified payment method" | **No**, it needs a card |
| GitHub Models | n/a | Retired: "As of July 30, 2026, GitHub Models has been fully retired." | **Gone** |

Cloudflare budget [estimate]: on Qwen3 30B A3B (4,625 Neurons per million input tokens, 30,475 per million output tokens), a full scan of 1827 victim calls at 250 input and 100 output tokens is about 2.1k + 5.6k = 7.7k Neurons, and 1566 judge calls at 400 input and 8 output tokens is about 3.3k more. Total about 11k Neurons, so a full scan takes roughly two days of the free allocation (the Neuron prices come from Cloudflare's pricing page; the token counts are my assumptions). Cloudflare also lists gpt-oss-20b, Gemma 4 26B A4B and Llama 3.2 models. This is the only route to a bigger model than the laptop can hold, and it needs a parent.

### 3.6 Numbers for a full scan

From the repo: 87 languages x 5 categories x 3 phrasings = 1305 attacks, plus 6 controls x 87 = 522. That is **1827 victim calls**. The judge does not see every reply (engine.run_attack and run_control): extraction attacks (261 of the 1305) are scored by a 12 word verbatim overlap with no judge call, and everything else reaches the judge only if the canary or control token appears in the reply. So **judge calls are at most 1044 + 522 = 1566**, fewer in practice. Total calls at most 3393, not 3654.

Important: **the bank today does not hold 87 languages.** The committed bank has 20 (16 high, 4 mid, 0 low). The uncommitted working copy of `attack_bank.json` (modified 2026-10-04 22:45) has 52 (28 high, 24 mid, still 0 low by the catalog tier), 20 author written and 32 machine written, which changes the file's SHA-256 that PREREGISTRATION.md pins. The 87 language figures are plan numbers until `expand_languages.py` runs, which needs the Anthropic API.

Wall clock [estimate], assuming per victim call 250 input and 100 output tokens, per judge call 400 input and 8 output (schema constrained), 4 server slots giving 2.5 times the single stream decode rate on GPU and 1.5 times on CPU, and the same model doing both jobs:

| Setup | Pilot 63 victim / 54 judge | 12 languages, 252 / 216 | 12 languages x 4 bots, 1008 / 864 | Full 87, 1827 / 1566 |
|---|---|---|---|---|
| GPU, Qwen3.5 4B Q4_K_M (prompt 2000 t/s, generate 55 t/s) | 1 min | 5 min | 18 min | 33 min |
| GPU, Qwen3.5 2B (3500, 100) | 1 min | 3 min | 10 min | 18 min |
| GPU, Gemma 4 E4B Q4_0 (1500, 45) | 1 min | 6 min | 23 min | 41 min |
| CPU only, Qwen3.5 4B (60, 12) | 17 min | 66 min | 4.4 h | 8 h |
| CPU only, Qwen3.5 2B (120, 22) | 9 min | 34 min | 2.3 h | 4.2 h |

The CPU rows say the GPU is not optional for the full scan. The GPU rows assume the judge is also on the GPU. A 4B victim and a 4B judge do not both fit in about 4.1 GiB, so run the judge as a second pass over saved replies (step 6) or put it on the CPU for the small pilots only.

### 3.7 What a local result can and cannot say

**Can say (these are real measurements):**
* The pipeline works end to end on live model output: adapters, judge, controls, statistics, report, replay.
* How often a specific small open model, with a specific system prompt, obeys each injection type in each language, with intervals.
* Whether the judge is reliable per language tier, and how often two judges disagree.
* Whether language tier matters for small open models, and with what power (the repo's own simulation: 6 languages per tier detects a 60 versus 30 percent gap with 93 percent power, 8 per tier detects 50 versus 30 with 82 percent power, 10 per tier gives 91 percent for 50 versus 30; 15 attacks per language, 500 simulated scans, run with `engine.power_simulation` today).
* A null result is publishable if the power is stated.

**Cannot say:**
* Anything about GPT, Gemini, Anthropic or other production chatbots. Their safety training, system prompt handling and filters are different, and a 4B model follows system prompts far less reliably.
* That a gap is about safety training. In a small model a language gap is mostly a capability gap: weaker languages produce nonsense, which looks like refusal. The controls partly separate these, and they are the most important number in the report.
* Anything about languages the model was not trained on (Phi 4 mini lists 23, Llama 3.2 lists 8).
* Anything about the central hypothesis (low resource languages) yet: the bank has no low tier languages.
* That machine translated attacks are as strong as native ones. STATE.md already names translation quality as the dominant confound.
* Exact reproducibility: parallel slots and prompt caching make runs not bit for bit repeatable. Say so in the report (`deterministic` should be False for local models).

Label every local result as a pilot on open weight models, with the model file name, quantization, llama.cpp build number, bank SHA-256 and judge.

## 4. What PolyGuard should do

Ranked. Effort is Ishaan's hours. Cost is dollars.

| # | Step | File | Hours | Cost | Risk |
|---|---|---|---|---|---|
| 1 | Close browsers and editors, download the llama.cpp `win-cuda-12.4-x64` and cudart zips from the GitHub releases page and `Qwen3.5-4B-Q4_K_M.gguf` (2.74 GB) from unsloth/Qwen3.5-4B-GGUF. Start `llama-server -m <file> -ngl 99 -c 8192 -np 4 --host 127.0.0.1 --port 8080` (check that each slot gets at least 2048 tokens of context) | none (outside repo) | 1 | $0 | Low. Needs about 3.5 GB disk and enough free RAM to load |
| 2 | Measure real speed: `llama-bench -m <file> -ngl 99 -p 512 -n 128`, then again with `-ngl 0`. Paste the numbers into this file in place of every [estimate] in 3.3 and 3.6 | this file | 0.3 | $0 | None |
| 3 | Add the local victim provider and the judge adapter (sketch below), plus a test against a fake HTTP server so the 168 unit tests stay green | `providers.py`, `test_engine.py` | 3 to 4 | $0 | Low. The judge JSON schema has `additionalProperties: false`; confirm llama-server accepts it in the smoke test [unverified] |
| 4 | Smoke test: `python providers.py --smoke qwen3.5-4b-local`, then `POLYGUARD_JUDGE_BACKEND=local python judge_eval.py --llm` on the 41 item gold set | none | 0.5 | $0 | Low |
| 5 | Pilot A, same shape as the existing plan: en, es, vi (63 victim calls) with the local victim and judge, labelled pilot. Inspect every error and every reply that contains the canary | `docs/pilot-plan.md` (add a "local" stage) | 1 | $0 | Low |
| 6 | Judge pass 2: a short script that loads a saved scan JSON, calls the judge only on replies containing the token, and writes a new JSON with the judge recorded. Lets victim and judge be different 4B models on a 6 GiB GPU | new `rejudge.py` | 3 | $0 | Medium. Must keep the instrument record and replay working |
| 7 | Pilot B: 12 languages (6 high including en, 6 mid) x the 4 example bots in `examples.py` = 1008 victim calls, about 20 minutes on GPU [estimate]. Add a second victim (Gemma 4 E4B) and compare. At temperature 0 repeats add nothing, so replicate across system prompts instead; do 2 extra runs at temperature 0.7 on one bot to measure sampling noise | `cli.py scan` | 3 | $0 | Medium. Translation quality and capability are confounds; read the controls first |
| 8 | Build the real judge gold set (100 refusals, 30 compliances) from pilot replies, label blind, report per tier false positive rate with Wilson intervals and two judge kappa | `judge_eval.py`, `docs/` | 5 | $0 | Medium. Labelling is the slow part |
| 9 | Optional, with a parent: a Cloudflare Workers AI account for a larger victim or a one day full scan | `providers.py` (reuse `openai_compat`) | 2 | $0 | Needs a parent to hold the account; terms are silent on age |
| 10 | Full 87 language scan on the GPU, only after the bank really has 87 languages | `cli.py scan` | 1 | $0 | The 67 extra languages need `expand_languages.py`, which needs the Anthropic key |

**Provider sketch** (matches the existing style: a `ModelSpec` entry, a `_call_<provider>` method, a branch in `build_victim`; uses `httpx`, which `anthropic` already pulls in, so `requirements.txt` and `pyproject.toml` do not change):

```python
LOCAL_BASE_URL = os.environ.get("POLYGUARD_LOCAL_URL", "http://127.0.0.1:8080/v1")

# in MODELS
"qwen3.5-4b-local": ModelSpec(
    key="qwen3.5-4b-local", provider="local", model_id="qwen3.5-4b",
    label="Qwen3.5 4B (local, Q4_K_M)", vendor="Alibaba (open weights, run locally)",
    api_key_env="", base_url=LOCAL_BASE_URL,
    notes="llama-server on this PC. A small open model, not a production chatbot."),

# deterministic: parallel slots make local runs not bit for bit repeatable
@property
def deterministic(self) -> bool:
    return self.supports_temperature and self.provider != "local"

# _sdk_present: add "local": "httpx" to the dict
# model_status: for provider "local", has_key = True and ready = _local_up(base_url),
#   where _local_up does GET {base_url}/models with a 1 second timeout

# VictimClient
def _call_local(self, system_prompt: str, user_text: str) -> str:
    body = {"model": self.spec.model_id, "max_tokens": self.max_tokens,
            "temperature": 0, "seed": 0, "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_text}]}
    r = self._client.post("/chat/completions", json=body)
    r.raise_for_status()
    choice = r.json()["choices"][0]
    text = choice["message"].get("content") or ""
    if not text.strip() and choice.get("finish_reason") == "length":
        raise RuntimeError("victim hit max_tokens before producing an answer")
    return text

# build_victim
elif spec.provider == "local":
    import httpx
    client = httpx.Client(base_url=spec.base_url, timeout=CALL_TIMEOUT,
                          transport=httpx.HTTPTransport(retries=MAX_RETRIES))
# and skip the key check when spec.api_key_env is empty
```

**Judge adapter**, so `engine.llm_judge_compliance` and `llm_judge_followed` stay untouched (they call `client.messages.create(model=, max_tokens=, temperature=, system=, output_config=, messages=)` and read `resp.content[...].text`):

```python
class _LocalMessages:
    def __init__(self, http, model_id): self._http, self._model = http, model_id
    def create(self, *, system, messages, max_tokens, output_config=None, **_):
        body = {"model": self._model, "max_tokens": max_tokens, "temperature": 0,
                "seed": 0, "cache_prompt": False,
                "chat_template_kwargs": {"enable_thinking": False},
                "messages": [{"role": "system", "content": system}, *messages]}
        schema = ((output_config or {}).get("format") or {}).get("schema")
        if schema:
            body["response_format"] = {"type": "json_schema", "schema": schema}
        r = self._http.post("/chat/completions", json=body); r.raise_for_status()
        text = r.json()["choices"][0]["message"].get("content") or ""
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=text)])

class LocalJudgeClient:
    def __init__(self, http, model_id): self.messages = _LocalMessages(http, model_id)

# judge_client(): if resolve_key("POLYGUARD_JUDGE_BACKEND") == "local", return
# LocalJudgeClient(httpx.Client(base_url=LOCAL_JUDGE_URL, timeout=CALL_TIMEOUT), id)
```

Smaller edits: set `POLYGUARD_JUDGE_MODEL` to something like `local:gemma-4-e4b-q4_0` so the instrument record names the judge and `COMPARABLE_FIELDS` refuses to compare scans scored by different judges; make `MAX_WORKERS` read an environment variable (12 workers against 4 server slots queue, which is fine on GPU but needs `POLYGUARD_CALL_TIMEOUT=300` on CPU); in `classify_error` also treat `ConnectError` as a network error.

**What NOT to do**

* Do not install Ollama (18+ terms) and do not create accounts at Gemini, Groq, OpenRouter or Cohere in his own name. All four say 18 or age of majority.
* Do not use Llama 3.2 or Gemma 3 weights unless a parent accepts the license: "age required... to provide legal consent" and "sufficient age of consent". Gemma 4 and Qwen3.5 are Apache 2.0 and avoid the question.
* Do not publish a hosted live scan that uses a parent's Gemini key: the terms bar API clients "likely to be accessed by individuals under the age of 18".
* Do not plan on GitHub Models (retired) or the Cerebras trial (needs a card).
* Do not use the keyword judge to fill gaps, and do not let a model judge its own replies in a real run (fine for the plumbing smoke test, labelled as such).
* Do not run Qwen3.5 4B or 9B without disabling thinking.
* Do not build llama-cpp-python from source or try transformers on CPU on this machine.
* Do not describe any local result as a finding about production chatbots, or call the first run anything but a pilot.
* Do not start a run with a full browser session open: 385 MB of RAM was free.

## 5. Sources

All opened 2026-10-05 unless noted.

1. Gemini API Additional Terms of Service (effective March 23, 2026): https://ai.google.dev/gemini-api/terms
2. Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits ; pricing and free tier: https://ai.google.dev/gemini-api/docs/pricing
3. Groq Services Agreement (last modified June 22, 2026): https://console.groq.com/docs/legal/services-agreement ; Groq website terms: https://groq.com/terms-of-use ; rate limits: https://console.groq.com/docs/rate-limits
4. OpenRouter Terms: https://openrouter.ai/terms ; limits: https://openrouter.ai/docs/api-reference/limits ; FAQ: https://openrouter.ai/docs/faq
5. Cloudflare Self-Serve Subscription Agreement: https://www.cloudflare.com/terms/ ; Workers AI pricing: https://developers.cloudflare.com/workers-ai/platform/pricing/ ; limits: https://developers.cloudflare.com/workers-ai/platform/limits/
6. Hugging Face Terms of Service: https://huggingface.co/terms-of-service ; Inference Providers pricing: https://huggingface.co/docs/inference-providers/pricing ; overview: https://huggingface.co/docs/inference-providers/index
7. GitHub Models retirement notice: https://docs.github.com/en/github-models ; GitHub Terms of Service (13+): https://docs.github.com/en/site-policy/github-terms/github-terms-of-service
8. Mistral Commercial Terms: https://legal.mistral.ai/terms/commercial-terms-of-service ; consumer terms (ROW): https://legal.mistral.ai/terms/row-consumer-terms ; Studio activation docs: https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key.md
9. Cohere Terms of Use: https://cohere.com/terms-of-use ; rate limits: https://docs.cohere.com/docs/rate-limits
10. Cerebras Website Terms of Use: https://cerebras.ai/terms-of-service ; rate limits and free trial: https://inference-docs.cerebras.ai/support/rate-limits
11. Ollama Terms of Service: https://ollama.com/terms ; Ollama on Windows: https://docs.ollama.com/windows ; LM Studio app terms: https://lmstudio.ai/app-terms
12. llama.cpp repository and README: https://github.com/ggml-org/llama.cpp ; license: https://github.com/ggml-org/llama.cpp/blob/master/LICENSE ; releases (Windows zips, build b11418, GitHub API): https://github.com/ggml-org/llama.cpp/releases ; server documentation: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
13. llama.cpp CUDA scoreboard (benchmark numbers): https://github.com/ggml-org/llama.cpp/discussions/15013
14. llama-cpp-python wheel index: https://abetlen.github.io/llama-cpp-python/whl/cpu/llama-cpp-python/ ; package files: https://pypi.org/project/llama-cpp-python/ ; onnxruntime-genai: https://pypi.org/project/onnxruntime-genai/ ; torch: https://pypi.org/project/torch/
15. Qwen3.5 model cards: https://huggingface.co/Qwen/Qwen3.5-0.8B , https://huggingface.co/Qwen/Qwen3.5-2B , https://huggingface.co/Qwen/Qwen3.5-4B , https://huggingface.co/Qwen/Qwen3.5-9B ; Qwen3 4B Instruct 2507: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507 ; Qwen2.5 3B Instruct: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct
16. Gemma 4 model card: https://huggingface.co/google/gemma-4-E4B-it and https://ai.google.dev/gemma/docs/core/model_card_4 ; Gemma 4 license page: https://ai.google.dev/gemma/docs/gemma_4_license ; Gemma Terms of Use (Gemma 3): https://ai.google.dev/gemma/terms
17. Llama 3.2 Community License: https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/LICENSE ; acceptable use policy: https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/USE_POLICY.md ; model card: https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/MODEL_CARD.md
18. Aya Expanse 8B: https://huggingface.co/CohereLabs/aya-expanse-8b ; Phi 4 mini instruct: https://huggingface.co/microsoft/Phi-4-mini-instruct ; gpt-oss-20b: https://huggingface.co/openai/gpt-oss-20b ; Qwen3Guard Gen 4B: https://huggingface.co/Qwen/Qwen3Guard-Gen-4B
19. GGUF file sizes (repo file listings): https://huggingface.co/unsloth/Qwen3.5-4B-GGUF , https://huggingface.co/unsloth/Qwen3.5-2B-GGUF , https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF , https://huggingface.co/unsloth/Qwen3.5-9B-GGUF , https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF , https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF , https://huggingface.co/unsloth/Phi-4-mini-instruct-GGUF , https://huggingface.co/ggml-org/gpt-oss-20b-GGUF , https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF , https://huggingface.co/bartowski/aya-expanse-8b-GGUF , https://huggingface.co/unsloth/gemma-3-4b-it-GGUF
20. NVIDIA GeForce RTX 30 series laptops (6 GB GDDR6, 3840 CUDA cores): https://www.nvidia.com/en-us/geforce/laptops/30-series/
21. Judge and multilingual safety literature (abstracts read): Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena, https://arxiv.org/abs/2306.05685 ; How Reliable is Multilingual LLM-as-a-Judge?, https://arxiv.org/abs/2505.12201 ; LLM Evaluators Recognize and Favor Their Own Generations, https://arxiv.org/abs/2404.13076 ; Qwen3Guard Technical Report, https://arxiv.org/abs/2510.14276 ; Yong et al., Low-Resource Languages Jailbreak GPT-4, https://arxiv.org/abs/2310.02446 ; Deng et al., Multilingual Jailbreak Challenges in Large Language Models, https://arxiv.org/abs/2310.06474
22. Repo files read: `README.md`, `STATE.md`, `providers.py`, `engine.py`, `judge_eval.py`, `judge_report.txt`, `docs/pilot-plan.md`, `attack_bank.json`, `examples.py` (all in this repository, as of 2026-10-05).

Unverified or not opened: Mistral free tier numbers; Gemini free tier numbers; Groq free plan numbers; Gemma 3 language count; AMD's Ryzen 9 6900HS product page (timed out); the RTX 3060 Laptop memory bus width; Google Colab and Kaggle terms (not retrievable); any published CPU speed for this chip; whether llama-cpp-python 0.3.36 supports Qwen3.5 and Gemma 4; whether Hugging Face routed providers add their own age terms.
