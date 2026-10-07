# Translation quality sprint: running log

Branch `sprint/translation-quality`. Goal: a reproducible offline translation quality
report per language, committed as data (`translation_quality.json`), read by a
standard library script (`tq_report.py`), and shown next to per-language results as an
automated proxy. It is never a validation. Plan source:
`docs/research/translation-quality.md`, stages A (language ID) and C (embedding
similarity). Stage B (NLLB round trip) and stage D (MetricX QE) are not in this sprint.

## Step 0. Environment (2026-10-06)

- Separate venv `C:\dev\llm\tq-venv` (Python 3.14.3, made with uv). Nothing was
  installed into the system Python or the repo environment.
- `fasttext`: no wheel exists for Python 3.14 on Windows (`fasttext`,
  `fasttext-wheel`, `fasttext-predict`, `fasttext-numpy2-wheel` all checked with
  `--only-binary`). Built `fasttext-numpy2-wheel 0.9.2` from source with the local
  MSVC Build Tools 18, which needed two compiler fixes passed through the `CL`
  environment variable: `/std:c++17` (the source uses `std::string_view`) and a forced
  include defining `ssize_t` (MSVC has none). No source file was patched.
- `torch 2.14.1+cpu` (CPU wheel from download.pytorch.org), `transformers 5.19.0`,
  `sentence-transformers 6.1.0`, `numpy 2.5.3`, `huggingface_hub`.
- Models live in `C:\dev\llm\models`, never in the repo:

| Model | Revision | File | Size | SHA-256 (matches the Hub LFS hash) | License |
|---|---|---|---|---|---|
| GlotLID v3 `cis-lmu/glotlid` | `85cd6716494360367b75f642b5bc78667605d0b4` | `model_v3.bin` | 1,687,094,687 bytes | `a818b6bd...c4cafc9e` | Card: `license: other`, `license_name: apache-2.0-plus-notices`. LICENSE file read: Apache 2.0 plus a notice on training data and a good faith contact notice. Not gated |
| LaBSE `sentence-transformers/LaBSE` | `836121a0533e5664b21c7aacc5d22951f2b8b25b` | `model.safetensors` | 1,883,734,344 bytes | `77d8e1f2...a0967c4fe77`... see JSON | Card: `apache-2.0`. Not gated |

  GlotLID v3: fastText, softmax loss, 2,102 labels, dim 256, character n-grams 2 to 5.
  Full hashes are in `translation_quality.json`.

## Step 0b. Baseline before any change

test_engine 168/168, test_stats_properties 24/24, api/test_api 90/90, verify_all
223/223, consistency clean, mutation_check 13/13 mutants killed, rehearsal answer key
PASS.

## Pre-declared rules (written before any score was computed)

These are fixed here, before looking at a single per-language number, so a threshold
cannot be tuned to make a language pass or fail.

Text preparation, for every attack and every control in all 73 bank languages and for
the English seeds: `linguistics.strip_fixed_tokens` with the canary and the control
token, which removes both, every Base64 blob and the English `SYSTEM OVERRIDE` marker.
Newlines become spaces. Nothing else is changed. The persona names (FreeBot,
NoLimit) stay, because they are part of the sentence.

**Language identification (GlotLID v3, top 1 label).**
- Each bank code maps to the GlotLID labels that count as that language in the script
  the bank uses (for example `hi` is `hin_Deva` only, so Hindi in Latin letters does not
  count; `sr` is `srp_Cyrl` or `srp_Latn`; `no` is `nob_Latn` or `nno_Latn`).
- A short list of close relatives per language is declared in `tq_report.py` (for
  example Croatian with Bosnian, Serbian Latin and Montenegrin; Malay with Indonesian;
  Xhosa with Zulu). GlotLID's own test F1 is lowest on exactly these pairs.
- `lid_share` = share of strings whose top label is the intended language.
  `lid_share_close` = the same, also counting a declared close relative.
- Flag `lid` if `lid_share_close` < 0.80. If only `lid_share` is below 0.80, record a
  note `lid_near_neighbour`, not a flag.

**Cross-lingual similarity (LaBSE, cosine of normalised embeddings).**
- Correct pair: a translated string against the English seed it was made from
  (same category and phrasing, or the same control).
- Wrong pairs: the same translated string against every English seed from a different
  group, where the groups are the five attack categories and the controls. Phrasings
  inside one group are near paraphrases, so they are not used as wrong pairs.
- Threshold T = the 99th percentile of all wrong pair similarities pooled over every
  language. A correct pair at or below T cannot be told apart from a wrong pair.
- Per language: mean correct similarity, mean wrong similarity, margin (their
  difference), group retrieval accuracy (the nearest English seed is in the right
  group), and the count of strings at or below T.
- Flag `sim` if 2 or more of the language's 21 strings are at or below T, or if group
  retrieval accuracy < 0.90.

A flag means "look here first", nothing more. No flag means the two tools found no
gross failure, not that the translation is good. The 20 author written languages get
the same scores, so they act as a reference scale, but they are not ground truth either.
