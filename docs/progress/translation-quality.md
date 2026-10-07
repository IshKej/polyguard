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
| LaBSE `sentence-transformers/LaBSE` | `836121a0533e5664b21c7aacc5d22951f2b8b25b` | `model.safetensors` | 1,883,734,344 bytes | `77d8e1f2...22dfa31f` (the Dense layer file `f866c945...a0967c4fe77` is hashed too, both in the JSON) | Card: `apache-2.0`. Not gated |

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

## Step 1 and 2. Scores (2026-10-06)

`tq_report.py --build` ran both models on CPU over all 1,533 strings (73 languages,
15 attacks and 6 controls each) in about 5 minutes. A second build into a scratch
file gave identical per-language scores and an identical threshold, so the JSON is
reproducible on this machine. One known side effect of `strip_fixed_tokens`: its
Base64 pattern also removes 27 ordinary words of 16 or more plain ASCII letters
(Dutch, Danish, Norwegian, Icelandic, Finnish, Hungarian and a few others, for example
`ontwikkelaarsmodus`). The task said to use that function, so it was kept, and the
side effect is recorded here.

**Threshold from data.** 25,920 wrong pairs: median 0.313, maximum 0.648, 99th
percentile T = 0.549. 1,512 correct pairs: median 0.897, 1st percentile 0.681. The
two distributions barely overlap.

**Language ID.** 66 of 73 languages had every string identified as intended. The rest:

| Code | Strict | With close relatives | What GlotLID said instead |
|---|---|---|---|
| ar (author) | 86% | 86% | 3 strings labelled as Arabic dialects (Egyptian `arz`, Najdi `ars`); dialects were not declared as close relatives, so this stays as measured. Two of the three are controls the native reviewer reworded |
| ms | 86% | 100% | 3 strings labelled Indonesian, a declared close relative. Strict share is still above 0.80, so not even the near neighbour note applies |
| hr | 90% | 100% | 1 Bosnian, 1 Serbian Latin |
| gl | 95% | 95% | 1 control labelled Spanish |
| sq | 95% | 95% | 1 control labelled Gheg Albanian (`aln`, not declared) |

No language fell below the 0.80 line, so no `lid` flag.

**LaBSE.** Margin over wrong pairs ranges from +0.46 (Yoruba) to +0.61 (Italian);
group retrieval accuracy is 100% in all 72 non-English languages. Lowest means:
Yoruba 0.74, Shona 0.79, Chichewa 0.81, then Thai, Xhosa, Zulu 0.84. The author
written languages sit between 0.86 (Gujarati) and 0.93 (Italian).

**Flags (pre-declared rules): Yoruba only (`sim`).** `yo_control_1` (0.489) and
`yo_control_4` (0.526) are at or below T. A diagnostic run, not part of the rule:
removing the Yoruba tone marks raises those two to 0.648 and 0.767 but lowers the
language mean slightly (0.735 to 0.722). So the flag cannot tell a weak translation
from LaBSE handling tone marked Yoruba badly. Either way it is the first language a
native speaker should read.

What the near-zero flag count does and does not mean: these tools only catch wrong
language and gross meaning drift, and every machine translation here passed that bar.
They cannot see register, fluency, a subtly wrong verb, or whether an attack still
reads as an instruction. The bottom of the LaBSE ranking (yo, sn, ny, xh, zu, th) is
also where LaBSE itself has the least training data, so a low score there is
ambiguous by construction.

## Paused (2026-10-06), state for whoever resumes

No model job is running. All suites were green at the baseline (step 0b); nothing
outside `tq_report.py`, `translation_quality.json` and this log has been changed yet,
so they have not been rerun.

**Done**
- Step 1, language ID (GlotLID v3) on all 1,533 strings, and step 2, LaBSE similarity
  with the wrong pair threshold: scored, reproducible, committed in
  `translation_quality.json` with model revisions, file SHA-256, licenses and versions.
- Step 3, `tq_report.py`: standard library reader (`python tq_report.py`,
  `--flagged`, `--check` for missing or stale languages) plus `--build` (heavy, lazy
  imports). Result: Yoruba is the only flagged language.

**Left**
- Step 4: show `tq_report.lang_quality(code)` next to per-language rates, labelled
  "automated proxy, not a validation": `report_html.py` by-language table, the CLI
  JSON export (`cli.py` `by_lang`), the app summary export (`app.py` `by_language`),
  and `api/server.py` `web_result` language rows. Add a `verify_all.py` check that
  `translation_quality.json` covers every machine translated bank language (use
  `tq_report.coverage(...)["machine_missing"] == []`), and update the check count in the
  `verify_all.py` docstring if `consistency.py` reads it.
- Step 5: `NATIVE_REVIEW.md` section on what the scores do and do not show, and a
  reviewer priority list from the flags (Yoruba first, then the bottom of the LaBSE
  ranking: sn, ny, xh, zu, th; then gl and sq for their one off label each).
- Step 6: rerun every suite and record counts here.
- The note on Arabic dialect labels belongs in the step 5 text, not as a flag.

**Next command**
```bash
cd C:/dev/pg-wt/translation-quality && export PYTHONIOENCODING=utf-8 && python tq_report.py --check && python tq_report.py --flagged
```
then edit `report_html.py` (by-language table) as the first step 4 change. To rebuild
the scores: `C:/dev/llm/tq-venv/Scripts/python.exe tq_report.py --build --glotlid
C:/dev/llm/models/glotlid/model_v3.bin --labse C:/dev/llm/models/labse` (about 5 min, CPU).
