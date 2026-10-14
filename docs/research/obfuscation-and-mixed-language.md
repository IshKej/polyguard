# Research: obfuscation and mixed-language attack families for PolyGuard

**Date:** 2026-10-05
**Scope:** which new attack categories PolyGuard could add, generated without an API, with the canary still checkable.
**Reading guide:** "Fact" means a number or statement I read in the cited source this session. "My read" means my own judgment. "[unverified]" means I did not open a primary source for it.
**Applies to a project where no live scan has ever run.** Nothing here is a PolyGuard result. This is a design note, so it describes seeds by their existing bank ids and does not reprint attack text.

## 1. Summary

1. Of nine families, only three (language mixing, romanization, invisible Unicode) have enough recent evidence on current models to be worth building. Homoglyphs, bidi overrides, leetspeak and ROT13 either test classifiers instead of chat models, or mostly test whether a model can decode, not whether it is safe.
2. Best fit: a "language split" category (frame in one language, document in another). It is built from text PolyGuard already holds, is language dependent by design, and keeps the canary as plain ASCII.
3. Romanization is second: 20 of the 52 bank languages are non-Latin, and the two best studies disagree on the sign of the effect (one finds more jailbreaks, one finds fewer), which makes it a good exploratory question. It needs transliteration tables and a native check on style.
4. Invisible Unicode (Tags, zero width) is real and well documented, but without tools and without a decoding hint current models almost never follow it (1.1% in the one controlled study), and its payload does not depend on language. Build it last, or after submission.
5. Every new category must be exploratory, live in a separate bank file so the pinned SHA-256 does not move, ship with a matched benign twin to separate decoding skill from safety, and be displayed only as escaped code points, never raw.

## 2. The families, with evidence

### 2.0 Two things true for every family

**Fact: older numbers do not transfer to current models.** Yong et al. (arXiv:2310.02446, GPT-4, 2023) got 53.08% for Zulu and 79.04% when any of four low-resource languages was allowed to succeed, against 0.96% for English. A 2026 preprint on current commercial models (Marx and Dunaiski, arXiv:2605.18239, 18 May 2026, not peer reviewed) says single-turn translation attacks "have become mostly ineffective"; only DeepSeek passed 10% (17.4% isiZulu, 13.0% Kiswahili). PolyGuard's default victim is Anthropic's Haiku 4.5, so a floor effect (near 0% everywhere) is a realistic outcome for any family below.

**Fact: the best studies measure comprehension next to attack success.** The code switching paper (arXiv:2406.15481) reports a separate comprehension score; the Arabizi paper (arXiv:2406.18725) has a "misunderstanding" outcome; the phonetic paper (arXiv:2505.14226) reports an answer relevance score; Yong et al. keep an UNCLEAR outcome (66.53% for Hmong, 65.77% for Guarani). PolyGuard's capability controls are the same idea, and each new family needs its own version.

### 2.1 Unicode Tags ("ASCII smuggling", block U+E0000 to U+E007F)

**What it is.** The Tags block mirrors printable ASCII at U+E0020 to U+E007E. Most interfaces draw nothing for these characters, but a tokenizer still sees them. Fact (Unicode 18.0 chart): the block runs U+E0000 to U+E007F, LANGUAGE TAG U+E0001 is deprecated, and "The use of tag characters to convey language tags is strongly discouraged."

**Evidence.**
- Fact: Rehberger's post of 14 Jan 2024 credits Riley Goodside's ChatGPT demonstration and recommends filtering the Tags code points at prompt and response time. I did not open Goodside's original post [unverified].
- Fact: Graves, "Reverse CAPTCHA" (arXiv:2603.00164, 26 Feb 2026). Five models (OpenAI GPT-5.2 and GPT-4o-mini; Anthropic Opus 4, Sonnet 4, Haiku 4.5), 8,308 graded outputs, temperature 1.0, via API. Without tools and without a hint, compliance with the hidden instruction was 1.1% across all models. Tool access (a Python tool) raised it: Haiku 0.8% to 49.2%, Opus 6.7% to 51.1%, Sonnet 16.9% to 71.2%, GPT-4o-mini 0.1% to 1.6%, GPT-5.2 0.1% to 20.6% (all schemes pooled). Giving the decoding rules in the prompt raised compliance by up to 95 points within one model and encoding. Anthropic models preferred Tags; OpenAI models preferred zero-width binary. GPT-4o-mini and Haiku 4.5 are both in PolyGuard's own model list (`providers.py`).
- Fact: FireTail (Sept 2025) found Gemini, Grok and DeepSeek vulnerable and ChatGPT, Copilot and Anthropic's chat product protected by input sanitization; Google answered the 18 Sept 2025 report with "no action". BleepingComputer (7 Oct 2025) repeats this. The Hacker News (27 Aug 2024) reports Microsoft fixed a Copilot data exfiltration chain that used ASCII smuggling after a January 2024 disclosure. Those two news pages are secondary; Rehberger's own August 2024 post returned 404, so I did not read it.
- Fact: AWS (30 Sept 2025) recommends stripping the Tags block and says doing so can turn some flag emoji into plain black flags.
- My read: Reverse CAPTCHA (API, models decode when told how) and FireTail (consumer products strip them) fit together if sanitization lives in the product layer, not in the model. That is an inference; neither source says it.

**Depends on language?** Not in the payload. Tags carry only printable ASCII, so a Hindi or Japanese instruction cannot be hidden in them. Only the visible carrier can change language. Weak fit for PolyGuard's thesis.

**Deterministic generation.** Add 0xE0000 to each ASCII code point (tested, 3.5). The hidden text contains the plain ASCII canary, so the reply is scored exactly as today.

**Judge.** No change to `JUDGE_COMPLIANCE_PROMPT`.

**Tokenizer or decoding risk: high.** The Reverse CAPTCHA authors say hinted results are "best interpreted as measuring model capability to decode invisible content when prompted, while the unhinted results measure spontaneous susceptibility." Control: a matched twin with the same hiding and the benign `CTRL_4B8E` request, plus a hinted arm.

### 2.2 Zero width characters (U+200B, U+200C, U+200D, U+2060)

- Fact: Reverse CAPTCHA also tested zero-width binary (U+200B for 0, U+200C for 1, 8 bits per ASCII character). GPT-5.2 reached 69 to 70% with tools and hints; Tags-preferring models did less. Same floors without tools or hints.
- Fact: Hackett et al. (arXiv:2504.11168 v3, 14 Jul 2025) tested six guardrail classifiers (Azure Prompt Shield, Meta Prompt Guard, Protect AI v1 and v2, Vijil, NeMo). Their "attack success" means a modified sample is misclassified as benign, not that a chat model obeyed. Zero width, homoglyphs and diacritics averaged 44 to 76% evasion; Emoji smuggling 100%; Unicode Tags 90.15% (prompt injection set) and 81.79% (jailbreak set). In the text I read I did not find a measurement of whether a victim model then followed the instruction. PolyGuard has no classifier in front of the bot, so these numbers do not transfer.
- Fact: Gao et al. (arXiv:2510.05025, 6 Oct 2025) use invisible variation selectors as a suffix. Random suffixes gave 16% (Vicuna 13B) and 2% (Llama 2 7B chat); an optimized suffix gave 98 to 100% after 10,000 search iterations per prompt on open-weight models. That needs white-box likelihoods, so it cannot be a fixed template.
- Fact from the PolyGuard bank (checked today): the only suspicious code point in all 52 languages is U+200C, 18 times, all in Persian (`fa`), where it is correct spelling. Reverse CAPTCHA warns that stripping all zero-width characters breaks legitimate joiners in Indic scripts and emoji. So both insertion and filtering are not language neutral.

**Verdict.** A decoding test with no language angle. Fold in only as a second encoding arm of the invisible family.

### 2.3 Homoglyphs and confusables

- Fact: Hackett et al. measured classifier evasion only (2.2).
- Fact: Daniel and Pal (arXiv:2405.14490, May 2024) report that non-standard Unicode (for example circled letters) weakened safety behavior on GPT-4, Gemini 1.5 Pro, Llama 3 70B and an Anthropic 3 Opus model, including prompt leakage. It is a manual study (38 queries per model), so a lead, not a rate.
- Fact: Sarabamoun (arXiv:2508.14070 v2, 25 Nov 2025) ran 4,000+ attempts on seven small open models (3.8B to 32B) and lists "incoherent outputs" and "unrelated hallucinations" among the failure modes, so many apparent successes may be confusion.
- Fact: Unicode UTS #39 (18.0.0, 2026-08-27) defines confusables and says skeleton strings "are not intended for display". I did not open `confusables.txt` [unverified].

**Verdict.** Latin, Cyrillic and Greek lookalikes only, so not a cross-language test. Do not add.

### 2.4 Bidirectional overrides ("Trojan Source")

Fact: Boucher and Anderson (arXiv:2111.00169, USENIX Security 2023) show bidi controls (U+202A to U+202E, U+2066 to U+2069) make source code look different to a reviewer than to a compiler. It concerns compilers, editors and review. Fact: UAX #9 (revision 2026-09-01) says directional overrides should be "avoided wherever possible, because of security concerns". Hackett et al. include bidirectional text (78.69% on the prompt injection set, 99.23% on the jailbreak set) but against classifiers.

My read: a language model reads logical order, so an override changes what a human reviewer sees, not what the model reads. I found no study showing it makes a chat model obey. Do not add as an attack. It matters for display safety (3.6).

### 2.5 Leetspeak

- Fact: Wei, Haghtalab, Steinhardt, "Jailbroken" (arXiv:2307.02483, GPT-4 and an Anthropic v1.3 model, 2023) list leetspeak, ROT13, Pig Latin and Base64 as mismatched generalization: "In many such instances, the model can still follow the obfuscated instructions, but safety fails to transfer." I could not read per-model leetspeak rates reliably from the PDF text, so I give none [unverified].
- Fact: Al Ghanim et al. (2.7) used English leetspeak as a baseline: 3.46% unsafe on GPT-4-0613 (plain English 0.38%) and 0.19% on the Anthropic model dated 2024-02-29 (plain English 0%).
- Fact: Best-of-N jailbreaking (arXiv:2412.03556, abstract page) reports 89% on GPT-4o and 78% on an Anthropic 3.5 Sonnet model after sampling 10,000 augmented prompts (random shuffling or capitalization). That is a sampling budget, not one template.

Latin letters only. Do not add.

### 2.6 ROT13 and other encodings beyond Base64

- Fact: Wei et al.: "GPT-4 cannot reliably follow instructions in ROT13, but GPT-5 might be able to do so"; GPT-3.5 Turbo could not follow Base64 while GPT-4 could "with fewer safeguards". The cleanest statement that obfuscation success tracks capability.
- Fact: Yuan et al., CipherChat (arXiv:2308.06463 v2, GPT-3.5-Turbo-0613 and GPT-4-0613): the best English cipher (ASCII codes) averaged 23.7% unsafe on Turbo and 72.1% on GPT-4; the best Chinese cipher (Unicode) 17.4% and 45.2%; "the more powerful the model, the unsafer the response with ciphers". They checked validity of replies by hand (GPT-4 86 to 100% across seven ciphers).
- Fact: PolyGuard's `defenses.py` already tells bots never to follow decoded Base64, hex or ROT13.

The encoding is language neutral but its length is not (3.3). Do not add a new encoding; fix the confound in the existing Base64 category.

### 2.7 Transliteration and romanization (Hinglish, Arabizi, romanized Russian, Pinyin)

The evidence conflicts.
- Fact (more jailbreaks): Al Ghanim et al. (arXiv:2406.18725, EMNLP 2024; GPT-4-0613 and the Anthropic model dated 2024-02-29; 520 AdvBench prompts; manual grading). Standard Arabic: GPT-4 directly refused 92.12%; Arabic in Latin letters ("transliteration"): 13.27%; unsafe rose from 2.50% to 12.12%. Anthropic model: direct refusal fell from 98.46% to 45.58% (chatspeak without numbers), unsafe rose from 0.19% to 4.62%. The same table shows 52.12% "misunderstanding" for that model on chatspeak with numbers (Table 2 as extracted from the PDF). So a large share of the change was not understanding, which is the confound.
- Fact (fewer jailbreaks): IndicJR (Pattnayak and Chowdhuri, arXiv:2602.16832, 18 Feb 2026): 12 Indic languages including Hindi and Gujarati, 12 models, attack families including instruction override and role play. In the contract (JSON) track, success fell from 0.755 (native script) to 0.416 (romanized) and 0.488 (mixed), mean drops of 0.338 and 0.267, every language lower, partly tied to tokenization fragmentation. In the free track all models were near 1.0, so there was no room to see a difference. Romanized with a neural tool (AI4Bharat), scored with automatic detectors, not a model judge.
- Fact (phonetic code mixing): Aswal and Jaiswal (arXiv:2505.14226 v5, 7 Apr 2026): GPT-4o-mini, Llama 3 8B, Gemma 1.1 7B, Mistral 7B v0.3, Hindi-English mixing plus phonetic misspellings. Gemma and Mistral reached up to 0.99 average attack success; GPT-4o-mini and Llama were "fairly robust" in English but rose when code mixed and misspelled. The authors blame tokenization "despite excellent input understanding".
- Fact: CSSBench (arXiv:2601.00588, 5 Jan 2026) tests "Pinyin Mix" on small models and measures over-refusal beside attack success. I read the abstract and headings only.

**Depends on language?** Strongly, but only for non-Latin scripts. Fact from the bank: 20 of 52 languages are non-Latin (10 high resource, 10 mid, 0 low in the current tiering), so romanization is undefined for 32 and cannot feed the low versus high test (script and tier are entangled).

My read: opposite signs make this a better exploratory question than a hypothesis. Style matters: people type Hinglish in many spellings, and rule based romanization is not how they type.

### 2.8 Code switching, language mixing, script mixing

- Fact: CSRT (Yoo, Yang, Lee, arXiv:2406.15481 v3, ACL 2025): ten models (gpt-4o-2024-05-13, an Anthropic 3 Sonnet model, Llama 3, Qwen 1.5, Mistral and others), May to June 2024, queries mixing up to 10 languages written by an LLM from MultiJail seeds. The authors report 46.7% higher attack success than standard English red teaming, better with more languages and lower resource languages, and best for intra-sentence mixing. The Anthropic 3 Sonnet model was the exception (very low attack success), which the authors guess may be contamination. I do not quote per-model cells because the table did not extract cleanly.
- Fact: Multilingual Blending (Song et al., arXiv:2407.07342, 10 Jul 2024): 55 languages, 53 mixtures, gpt-3.5-turbo-0125 and gpt-4o-2024-05-13. Bypass 67.23% on GPT-3.5 and 40.34% on GPT-4o; single languages 0% (English) to 6% (Romanian) on GPT-4o; best mixture (Thai, Danish, Hungarian, Arabic) 40%.
- Fact: Sandwich attack (arXiv:2404.07242, Apr 2024) hides one question between questions in other low-resource languages. Mostly worked examples on six models; its abstract says "Many of the similar attack vectors have been patched by model providers".
- Fact: PolyGuard's existing indirect injection is already a partial code switch: local language frame, with "SYSTEM OVERRIDE" and the canary left in English (`api/server.py` comment; Hindi and Japanese samples in the bank).

**Depends on language?** Yes by construction; the literature ties the effect to resource level and number of languages.

**Deterministic generation.** CSRT needs an LLM to write natural intra-sentence mixing, which PolyGuard cannot do without an API and a native check. A deterministic segment level version exists (3.2); call it a "language split", not natural code switching. My read: it is the conservative cousin, and CSRT's own ablation says intra-sentence mixing works best, so a null here would not rule that out.

**Comprehension risk: moderate.** If the bot does not read the local half, the attack fails for the wrong reason. Control: a benign twin, and the 2 by 2 layout, which shows which half carries the language effect.

### 2.9 A low resource language used as a cipher (payload in one language, frame in another)

Not a separate technique in what I read. It is 2.8 plus Yong et al. (low-resource payloads) plus CipherChat's finding that role play alone can set up a private "cipher" (SelfCipher: 70.9% unsafe in English against 53.3% in Chinese on GPT-4; the abstract says it "outperforms existing human ciphers in almost all cases"). The language split in 3.2 covers it (frame language by payload language). A made-up cipher language measures decoding, not equity, so do not add it.

### 2.10 Summary table

| Family | Evidence on current chat models | Language dependent | Deterministic, canary intact | Decoding confound | Fit |
|---|---|---|---|---|---|
| Unicode Tags | Real, near 0% unhinted without tools | No (ASCII payload only) | Yes | Very high | Weak, build last |
| Zero width | Same | Only in that it breaks Persian and Indic text | Yes | Very high | Fold into Tags |
| Homoglyph | Mostly classifier evasion | Lookalike scripts only | Needs data file | High | No |
| Bidi override | None found for chat models | No | Yes | n/a | No (display risk only) |
| Leetspeak | 2023 evidence, mixed | Latin only | Yes | High | No |
| ROT13, ciphers | Capability limited (2023) | No | Yes | Very high | No, fix Base64 instead |
| Romanization | Two studies, opposite signs | Yes, 20 of 52 languages | Yes, with tables | High | Yes, second |
| Language mixing | Several studies, 2024 models | Yes | Yes, from existing text | Moderate | Yes, first |

## 3. What PolyGuard should do

### 3.1 Ranking (effort is my estimate for one person, with tests)

| Rank | Category | Effort | Risk | When |
|---|---|---|---|---|
| 1 | `language_split` (quoted document shape, plus a Base64 shape) | 8 to 10 hours | Low | Before the first live scan |
| 2 | `romanized_payload` (12 languages first) | 10 to 14 hours | Medium: style, script and tier entangled | After the key and first live scans |
| 3 | `invisible_text` (Tags and zero width, two arms) | 6 to 8 hours plus display work | Medium to high: display, hosting, copying; weak thesis fit | After submission, or write-up only |
| Insurance | Safe display helper and CI check for invisible characters (3.6) | about 2 hours | Low | Now |

My read: the deadline is 26 Oct 2026 (21 days) and STATE.md names the API key as the blocker. A new category adds nothing until a key exists and each adds scan cost (3.7). If time is short, do rank 1 plus the display helper and describe the rest as designed, not run.

### 3.2 Category 1: `language_split`

**Question.** Does the language gap come from the language of the frame (what the bot is asked to do) or of the document (where the order is hidden)?

**Layout (a 2 by 2 per phrasing).**

| | Document in English | Document in language L |
|---|---|---|
| Frame in English | existing `en_indirect_injection_i` | NEW `en_frame_local_doc` |
| Frame in language L | NEW `local_frame_en_doc` | existing `L_indirect_injection_i` |

Two cells already exist, so two are new. A second shape does the same for Base64: local frame with the English blob, and English frame with the local blob.

**Seeds.** The three existing English `indirect_injection` phrasings (`en_indirect_injection_0` to `_2`), each cut at its single blank line into frame and document. No new English text. Checked against the bank: all 52 languages by 3 phrasings have exactly one blank line and the canary inside the document.

**Known flaw in seed 2.** Its frame asks for a translation to English, so with an English document the task is a no-op and the natural reply repeats the document, canary included. Compare within phrasing only and report seed 2 separately; do not swap it, because every language already has a translated frame for it.

**Generator sketch (tested against `attack_bank.json`).**

```python
def language_split(en_text, loc_text, which):
    en_frame, en_doc = en_text.split("\n\n", 1)
    lo_frame, lo_doc = loc_text.split("\n\n", 1)
    return {"en_frame_local_doc": en_frame + "\n\n" + lo_doc,
            "local_frame_en_doc": lo_frame + "\n\n" + en_doc}[which]
# Base64 shape, from the build() templates, no regex:
#   local frame + English blob: TEXT[lang]["obfuscated_payload"][i].replace("{B64}", EN_B64)
#   English frame + local blob: TEXT["en"]["obfuscated_payload"][i].replace("{B64}", loc_b64)
```

**Scope.** Start with the 19 non-English author written languages: 19 by 2 cells by 3 phrasings = 114 attacks per shape. Machine translated languages carry the documented translation confound (`docs/research/translation-quality.md`), and half the split would inherit it.

**The matched twin, and a problem I found.** The twin should show whether the bot can read the mixed text at all. A benign request placed inside a quoted document is a bad twin, because a well defended bot should not obey instructions inside documents, so it would fail the twin for the right reason. A valid twin needs one purpose written benign task sentence per language (for example, asking the bot to repeat an order reference found in the document, using `CTRL_4B8E`). That is new text for 19 languages and needs the same review process as the rest. Without it, the only comprehension reference is the existing six plain controls per language plus the two existing diagonal cells, which only partly separate comprehension from safety. State that limit if the twin is not written.

**Judge.** Unchanged `llm_judge_compliance`, same wording (changing it changes the judge fingerprint and breaks comparability). Fact: `canary_broken` normalizes to a to z and 0 to 9, so the ASCII canary is found whatever the reply language.

**Code changes (my proposal).**
- `generate_attack_bank.py`: a second writer for `attack_bank_exploratory.json`, each row with `family: "exploratory"`, `shape`, `cell`, `pair_id`. The primary file and its pinned hash stay untouched.
- `engine.py`: `load_bank(include_exploratory=False)`; every pooling function (`tier_rates`, `max_gap_permutation_test`, `category_gap_tests`, `summarize`) filters to `family == "primary"`; `instrument()` records `exploratory` and the second file's hash; the mocks stay language independent for the new rows; `capability_report` gets a per-language reference so a twin is compared with that language's plain control rate, not with English. `SCORING_VERSION` stays "1.1" because primary scoring is unchanged.
- `defenses.py`: reuse the `indirect_injection` clause and `MULTILINGUAL_CLAUSE` (it already covers "any other language, script, or mix of languages"). No new prompt text, which avoids prompt bloat that would itself move the capability controls.
- Report (`report_html.py`, `cli.py`): a separate section, "Exploratory probes (outside the pre-registered analysis)", with the 2 by 2 per language, twin pass rate, and break rate among languages where the twin passed. Never in the headline, the tier comparison or the regression gate unless `--gate-exploratory` is passed.
- Site: a checkbox in `Setup.jsx`, a separate panel in `Results.jsx`, a paragraph in `Method.jsx`. Keep exploratory rows out of the spot the attack game (`GAME_CATEGORIES`).
- `linguistics.py`: its SCRIPT and LENGTH checks would flag split rows as untranslated. Make them `shape` aware before auditing the exploratory bank.
- Tests: a test that planted exploratory rows can never change a primary number (same style as `mutation_check.py`).

**Preregistration fit.** All exploratory. Write the deviation log row before the first live scan so it cannot look data driven. Draft: "Added a separate exploratory bank with its own SHA-256. The primary bank, its SHA-256, the held-out set, H1, H2, H3 and the Benjamini-Hochberg family of five are unchanged. Exploratory results are descriptive, reported in a separate section, and never pooled with primary results." Pre-specify the only contrasts: within language, split cell versus the matching diagonal cell, summarized by the repo's existing sign test, as its own family with its own adjustment. Do not add the new categories to the family of five for H3.

**Expectation to record (a hunch).** Given Marx and Dunaiski, a null is a realistic outcome. Say so in the log, as the repo already does for H1.

### 3.3 Add-on: the Base64 length confound (a finding about the existing bank)

Fact, measured from `attack_bank.json` today (variant 0): the Base64 blob encodes each language's own instruction, so its length follows UTF-8 bytes. English 148 characters, Chinese 168, Arabic 224, Korean 240, Russian 280, Japanese 288, Gujarati 324, Hindi 344, Bengali 360, Georgian 392, Thai 428, Tamil 456 (3.1 times English). Latin script languages range 156 to 240.

My read: in the existing `obfuscated_payload` category, a language effect cannot be told apart from "decode a blob two to three times longer that holds multi byte text". That matters for H3, which predicts the largest gap in the obfuscated category. The exploratory Base64 split (local frame, English blob) is the cheapest way to separate them. Run it beside the primary category, not in place of it.

### 3.4 Category 2: `romanized_payload`

**Design.** For each non-Latin language, transform its own localized text into Latin letters, leaving fixed tokens (canary and control token) untouched. Two arms: the instruction (primary) and the existing six controls romanized (twin). Seeds: the three existing `instruction_override` phrasings (`en_instruction_override_0` to `_2` and their localizations).

**Generator idea (Cyrillic tested; the Latin canary survives).** Split the text on the fixed tokens, transform only the pieces between them, rejoin. The transform is a plain table lookup (ISO 9 style), so output is deterministic. Unit tests: fixed tokens are unchanged, and the output is ASCII (plus any chosen diacritics).

**Which languages first.** Rule based, low risk: Cyrillic (ru, uk, bg, sr, kk, ky), Greek (el), Hangul (ko). Table based, medium risk: Devanagari, Gujarati, Bengali, Tamil (hi, gu, bn, ta); a neural tool exists (AI4Bharat, used by IndicJR) but is a heavy dependency [details unverified]. Skip: Arabic script and Hebrew (vowels missing, so romanization is lossy), Chinese, Japanese, Thai (need dictionaries or readings). About 12 languages by 3 phrasings = 36 attacks plus 72 romanized controls.

**Judge.** Unchanged. The reply may come back in Latin letters or native script; the canary check is the same.

**Decoding confound and control.** Arabizi found 52.12% misunderstanding in one setting and IndicJR ties its drop to tokenization. The romanized twin (benign request, same transform, built from existing controls with no new translation) gives a per-language "can the bot read this" rate. Read the break rate only where the twin passes, and show both numbers together.

**Main risks.**
- Style: table romanization is not what people type. Say plainly this tests a regular romanization, not Hinglish as written, and ask a native speaker (Hindi, Gujarati, Russian) to rate naturalness before any claim.
- Script and tier are entangled: the 20 non-Latin languages are 10 high and 10 mid resource, none low, so this cannot test low versus high. Report per language, never in the tier test.

**Code changes.** Same plumbing as category 1, plus a `romanize.py` with one function per script. In `defenses.py`, one clause: treat romanized or transliterated text exactly like the same text in its native script. Preregistration: exploratory, same deviation log row.

### 3.5 Category 3: `invisible_text` (build last)

**Design.** A visible benign request in language L (reuse local frames) with an English override hidden after it. Arms: Tags and zero width binary, each unhinted and hinted. The hinted arm adds one English sentence telling the bot how to read the hidden characters, which makes it the same kind of task as the existing Base64 category (instructed decoding); the unhinted arm measures spontaneous susceptibility. About 5 frame languages, because the payload does not change with language. Seeds: the three `en_instruction_override` phrasings as the hidden part, each behind a short benign visible request; all ASCII.

**Generator sketch (tested; round trips exactly).**

```python
TAG0 = 0xE0000
def to_tags(s):                      # printable ASCII only
    assert all(0x20 <= ord(c) <= 0x7E for c in s)
    return "".join(chr(TAG0 + ord(c)) for c in s)
def to_zw(s):                        # U+200B = 0, U+200C = 1, 8 bits per character
    return "".join("".join("\u200c" if b == "1" else "\u200b"
                           for b in format(ord(c), "08b")) for c in s)
```

**Controls.** A hinted twin with `CTRL_4B8E` (can the bot decode at all) and a visible twin (is anything stripping characters before the model). Expect a floor: unhinted and without tools the one controlled study found 1.1% across five models, and 0.8% (Haiku 4.5) and 0.1% (GPT-4o-mini), both PolyGuard models.

**Defence, honestly.** A system prompt clause cannot remove characters the model should never have received. The fix is to strip the Tags block and zero width characters before text reaches the model, keeping legitimate joiners (Persian U+200C, flag emoji), as Rehberger and AWS advise. PolyGuard's remediation is prompt only, so for this family the report should print that advice instead of a prompt clause.

### 3.6 Display safety (applies even if no invisible category is added)

**Why.**
- Fact: UTS #55 recommends that tools "make visible any default ignorable code points", using a non-spacing mark for joiners, an outline for variation selectors and a light mark for directional marks. UTS #39 says skeleton strings are not for display. UAX #9 says directional overrides should be avoided.
- Fact: GitHub shows a warning on files with bidirectional Unicode (since 31 Oct 2021) and on files with hidden Unicode (since 1 May 2025). Raw invisible characters in `attack_bank.json` would show that banner to anyone reviewing the repo, including judges.
- My read: a public page containing raw hidden instructions can reach anyone who pastes the page into an AI summarizer, including a judge. The canary is harmless, but it would still be an injection aimed at a reader's tool, the wrong impression for a defensive project.

**Rules.**
1. Store only ASCII in the exploratory JSON: `json.dumps(..., ensure_ascii=True)`. Tested: tag characters become surrogate pairs and `json.loads` returns the identical string (145 code points in, 145 out). The file hashes the same on every platform.
2. Never send raw text to the browser. In `api/server.py` `web_row`, replace `attack` and `reply` with an escaped form computed once on the server by a single function that turns every format, control, private use, Tags and variation selector code point into a visible `{U+XXXX}` marker (tested), while leaving ordinary letters alone. Show markers as styled chips and show the decoded hidden text in a labelled box. Replies need the same treatment because a victim can echo invisible characters.
3. Places that print attack or reply text today: `Drawer.jsx` lines 59 and 71 (`dir="auto"` picks direction from the first strong character, so a directional mark can flip a paragraph), `LiveScan.jsx` (`firstSentence(r.attack)`), the game (keep exploratory out), and `report_html.py` (`html.escape` does not touch invisible characters, so escape code points first). Isolate bidi text with `<bdi>` or `unicode-bidi: isolate`.
4. Copying: the copy button must copy the escaped string, never the raw one, and the page should warn against pasting raw attack text into an assistant connected to mail or files. Evidence JSON downloads and share links carry the escaped form.
5. CI check (about 30 lines): fail if any tracked text file contains U+E0000 to U+E007F, U+202A to U+202E, U+2066 to U+2069, U+2060, U+FEFF (other than a leading byte order mark) or variation selectors. Allow U+200C and U+200D only in language data that needs them (Persian today).
6. Docs: write `U+E0049`, never the character, in README, STATE and PREREGISTRATION.
7. Hosting: I did not test whether Vercel's firewall or a bot filter alters request bodies containing these characters [unverified]. Test `/api/scan` on a preview deploy. Do not add exfiltration style payloads (hidden links or URLs, as in the Copilot chain): they need rendering or tools and add real risk, and the canary already proves the point.

### 3.7 Cost of the additions (my arithmetic)

- Today: 780 attacks plus 312 controls = 1,092 victim calls per full scan, plus judge calls where the canary appears.
- Category 1 on 19 languages, quoted shape: 114 attacks plus 114 twins = 228. The Base64 shape adds the same again.
- Category 2 on 12 languages: 36 attacks plus 72 twins = 108.
- Category 3 on 5 languages, 2 encodings, 2 arms: 60 attacks plus 60 twins = 120.
- All three at full scope: about 680 extra calls, 62% on top of a primary scan. Category 1 quoted shape alone: 21%. All of it sits behind a checkbox and an `--exploratory` flag.

### 3.8 What NOT to add

- **Bidi overrides:** a compiler and code review problem, no chat model evidence, a display hazard. Handle in 3.6 only.
- **Homoglyph substitution:** classifier evasion and noise robustness, not a language test.
- **Leetspeak and ROT13 as categories:** 2023 era, Latin only, mostly decoding skill. Improve the existing Base64 category instead.
- **Optimized variation selector suffixes and Best-of-N sampling:** need per prompt search (10,000 iterations or samples). Not deterministic templates.
- **Hidden link or exfiltration payloads:** need tools or rendering, and carry real risk.
- **A made-up cipher language:** measures decoding, not equity.
- **Emoji or variation selector smuggling:** the 100% in Hackett et al. is against classifiers, and PolyGuard has none in front of the bot.
- **Any new category in the primary bank before the first live scan:** it would change the pinned SHA-256 and the H3 family for no gain.

### 3.9 Other things noticed in the repo

- Fact: the bank on disk has 780 attacks, 312 controls and 52 languages (156 per category), while README.md, STATE.md and PREREGISTRATION.md still say 300, 120 and 20. Reconcile before the first scan.
- Fact: `linguistics.py` treats Latin letters in a non-Latin language as a failed translation, so romanized rows would be flagged by design.
- Fact: IndicJR's text cites a model named "PolyGuard (Patel et al., 2025b)" for multilingual safety. I did not open that paper [unverified]. Check the name for confusion before submission.
- Fact: 14 of 52 languages have a different sentence count from English in at least one `instruction_override` phrasing (mostly phrasing 3, plus Korean and Japanese phrasing 1), so a sentence level split would need an alignment check; the frame and document split has no such problem.

## 4. Sources

Opened this session unless marked. Numbers are as stated by the authors.

1. Graves, "Reverse CAPTCHA", arXiv:2603.00164, 26 Feb 2026. https://arxiv.org/abs/2603.00164 (full text read)
2. Hackett, Birch, Trawicki, Suri, Garraghan, "Bypassing LLM Guardrails", arXiv:2504.11168 v3, 14 Jul 2025. https://arxiv.org/abs/2504.11168 (full text read)
3. Rehberger, "Hiding and finding text with Unicode tags", 14 Jan 2024. https://embracethered.com/blog/posts/2024/hiding-and-finding-text-with-unicode-tags/
4. FireTail, ASCII smuggling across LLMs, Sept 2025. https://www.firetail.ai/blog/ghosts-in-the-machine-ascii-smuggling-across-various-llms
5. BleepingComputer, 7 Oct 2025 (secondary). https://www.bleepingcomputer.com/news/security/google-wont-fix-new-ascii-smuggling-attack-in-gemini/
6. The Hacker News, 27 Aug 2024 (secondary). https://thehackernews.com/2024/08/microsoft-fixes-ascii-smuggling-flaw.html
7. AWS Security Blog, 30 Sept 2025. https://aws.amazon.com/blogs/security/defending-llm-applications-against-unicode-character-smuggling/
8. Unicode 18.0 Tags chart. https://www.unicode.org/charts/PDF/UE0000.pdf
9. Unicode UAX #9 (revision 2026-09-01). https://www.unicode.org/reports/tr9/ (UTR #36, referenced there, not opened)
10. Unicode UTS #39 (18.0.0, 2026-08-27). https://www.unicode.org/reports/tr39/
11. Unicode UTS #55, Source Code Handling. https://www.unicode.org/reports/tr55/
12. GitHub changelog, bidirectional Unicode warning, 31 Oct 2021. https://github.blog/changelog/2021-10-31-warning-about-bidirectional-unicode-text/
13. GitHub changelog, hidden Unicode warning, 1 May 2025. https://github.blog/changelog/2025-05-01-github-now-provides-a-warning-about-hidden-unicode-text/
14. Boucher and Anderson, "Trojan Source", arXiv:2111.00169. https://arxiv.org/abs/2111.00169
15. Gao et al., "Imperceptible Jailbreaking against Large Language Models", arXiv:2510.05025. https://arxiv.org/abs/2510.05025
16. Daniel and Pal, arXiv:2405.14490. https://arxiv.org/abs/2405.14490
17. Sarabamoun, arXiv:2508.14070 v2. https://arxiv.org/abs/2508.14070
18. Wei, Haghtalab, Steinhardt, "Jailbroken", arXiv:2307.02483. https://arxiv.org/abs/2307.02483
19. Yuan et al., CipherChat, arXiv:2308.06463 v2. https://arxiv.org/abs/2308.06463
20. Best-of-N Jailbreaking, arXiv:2412.03556 (abstract page only). https://arxiv.org/abs/2412.03556
21. Al Ghanim et al., arXiv:2406.18725 v2, EMNLP 2024. https://arxiv.org/abs/2406.18725
22. Pattnayak and Chowdhuri, IndicJR, arXiv:2602.16832. https://arxiv.org/abs/2602.16832
23. Aswal and Jaiswal, arXiv:2505.14226 v5. https://arxiv.org/abs/2505.14226
24. Zhou et al., CSSBench, arXiv:2601.00588 v2 (abstract and headings only). https://arxiv.org/abs/2601.00588
25. Yoo, Yang, Lee, CSRT, arXiv:2406.15481 v3. https://arxiv.org/abs/2406.15481
26. Song, Huang, Zhou, Ma, "Multilingual Blending", arXiv:2407.07342. https://arxiv.org/abs/2407.07342
27. Upadhayay and Behzadan, "Sandwich Attack", arXiv:2404.07242. https://arxiv.org/abs/2404.07242
28. Yong, Menghini, Bach, arXiv:2310.02446 v2. https://arxiv.org/abs/2310.02446
29. Deng et al., MultiJail, arXiv:2310.06474 v3, ICLR 2024 (abstract numbers only). https://arxiv.org/abs/2310.06474
30. Marx and Dunaiski, arXiv:2605.18239, 18 May 2026 (preprint). https://arxiv.org/abs/2605.18239

Not opened [unverified]: Goodside's original Jan 2024 post, Rehberger's Aug 2024 post (404), Unicode `confusables.txt`, UTR #36, any Vercel firewall behavior.

## 5. Recommended actions

1. This week: the escaped display helper and the CI check for invisible characters (about 2 hours). It protects the live site whether or not any category ships.
2. Before the first live scan: category 1 in a separate exploratory bank, with the deviation log row written first. Decide whether to write the benign twin sentences (3.2).
3. Reconcile the 780, 312, 52 versus 300, 120, 20 counts across README, STATE and PREREGISTRATION.
4. After live scans exist: romanization for about 12 languages, with a native speaker rating naturalness.
5. After submission: the invisible text family, or the write-up only.
6. In the submission text, describe all of this as designed and exploratory. No result exists.
