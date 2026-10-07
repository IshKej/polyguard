# Measuring the quality of PolyGuard's machine translated attack strings

**Date:** 2026-10-05
**Scope:** research only. No model was installed or downloaded. Every number below was read from a primary source opened in this session (URLs in section 4), computed by me from the repository files (marked "computed"), or is marked [estimate] or [unverified].

## 1. Summary

1. Round trip scoring by the same model that translated is only a gross failure detector. On the 53 stored files, correct pairs score a mean chrF of 0.77 and wrong pairs 0.26, but the spread between languages (SD 0.05) is smaller than the spread inside one language's own three strings (SD 0.069), so it cannot rank languages (computed).
2. What fits this laptop (15.2 GB RAM, 6 GB GPU, 8 core CPU) and costs nothing: GlotLID or OpenLID-v2 for language ID (87 of 87 codes), NLLB-200 600M as an independent back-translator (87 of 87), LaBSE embeddings (86 of 87), and MetricX-24 Large in reference-free mode (84 of 87, Apache-2.0). The 3.5B and larger models (CometKiwi XL, xCOMET XL) do not fit.
3. No automatic metric has published human-agreement evidence for most of our 87 languages. Being on a model's language list does not mean it works: CometKiwi (2022) scored about zero against human ratings on English to Xhosa even though Xhosa is on its list. Use the tools to flag gross failures and to build a covariate, never to certify a language.
4. A citation error needs fixing before submission: the "71% machine translation error rate" is from LinguaSafe (arXiv:2508.12733, Bengali only; Malay was 36%), not from arXiv:2605.18239 as README.md, NATIVE_REVIEW.md, PREREGISTRATION.md and expand_languages.py say.
5. Structural confound: all 35 low tier languages are machine translated, while 16 of the 28 high tier languages are author written (computed). Tier and translation method are tangled, so the plan is: run the checks once locally and commit one JSON file, report them as a covariate and as pre-registered sensitivity analyses, add a provenance contrast, and get 8 to 12 languages human checked with a 10 minute sheet by Oct 26.

## 2. Findings

### 2.1 What PolyGuard has today (read from the repo)

- 87 codes in languages_catalog.CATALOG (28 high, 24 mid, 35 low). 20 are author written. 53 machine translation files existed on 2026-10-05, 14 are still missing (all low tier: ps tg mn hy ne si km my jv su sw am so rw).
- Each machine file holds 15 attacks, 6 benign controls, and a `backcheck` block with only 3 English back-translations (variant 0 of instruction_override, role_play_jailbreak and system_prompt_extraction). 12 of 15 attacks and all 6 controls have no back-translation.
- The files state that the back-translations "were written by the same model, so that check cannot catch an error the translator believes is correct."
- The automatic semantic gate in expand_languages.py is a keyword test, not a similarity score (BACKCHECK_INTENT). Computed on the stored files: all 159 correct pairings pass (expected, since files that failed would not have been stored), and 39 of 318 deliberately wrong pairings also pass. The role_play_jailbreak gate is the weak one: 36 of 53 back-translations of the instruction_override attack pass it, because the substring "act" matches "exactly" and "reply" is in the second list. Plain unrelated text such as "The weather will be sunny tomorrow ... please reply exactly when you can" passes it too.
- linguistics.py already checks script, mojibake, length ratio and duplication. None of that tests meaning.
- The primary test (PREREGISTRATION.md) is a Mann-Whitney U on per-language break rates, low versus high tier. So any quality score has to enter at the per-language level. No live scan has run yet, which is the right moment to fix the quality rules.

### 2.2 Round trip (back-translation) scoring with chrF or BLEU

What it is: translate the English seed into language X, translate that back into English, then score the back-translation against the seed.

Evidence that it carries signal:
- Zhuo et al. (ACL Findings 2023) find that for modern neural MT the round trip score tracks forward translation quality once the copy mechanism of old statistical MT is removed, and that a regressor can predict forward scores from round trip scores on FLORES-101 languages. They also say the relation can be non-linear and that very low resource languages were not tested, and they advise auditing against a small validation set for any new language. They propose cross-system verification (a different MT system does the other direction) to catch systems that look good only because they copy [17].
- Marx and Dunaiski (2026) used exactly this idea on jailbreak prompts: Google Translate round trips scored with BLEU, METEOR and BERTScore. Mean round trip BLEU was 0.67 (Afrikaans), 0.52 (Kiswahili), 0.50 (isiZulu), 0.48 (isiXhosa), and across the four languages the quality score correlated with jailbreak success at Pearson r of 0.92 (BLEU), 0.91 (METEOR), 0.87 (BERTScore). That is apparently four language level points [my inference from the paper's four languages], and the authors read it as poor translation, not stronger guardrails, driving the lower rates in isiXhosa and isiZulu [18].
- Computed on our files (my own chrF, n-gram order 6, beta 2, spaces removed, which matches the sacreBLEU default signature `chrF2|nc:6|nw:0|space:no` [16]; canary and "SYSTEM OVERRIDE" stripped): correct pairing mean 0.768 (minimum 0.566); back-translation scored against the seed of a different category mean 0.26 (maximum 0.378); half the words deleted mean 0.30. So there is a wide gap between "right content" and "wrong content".

Weaknesses, with what applies to PolyGuard:
1. Same model both ways. Shared blind spots survive: a wrong but fluent translation that the model itself reads back correctly scores high. The stored files say this themselves. A related result: language model judges recognise and favour their own outputs (Panickssery et al. 2024, [27]); I use it only as an analogy, it is not about back-translation. Also the back-translations were written in a working session that very likely had the English seeds in view [inference, not checkable], which would make them recall rather than translate.
2. It measures overlap, not meaning, and the scale is not absolute. Faithful back-translations vary in wording ("Disregard" for "Ignore"), so faithful strings score anywhere from about 0.6 to 0.99 here. Per language means run 0.631 (eu) to 0.855 (sv), but the within language SD across just three strings is 0.069, larger than the between language SD of 0.05 (computed). With 3 strings per language, ranking languages by this score is noise.
3. It cannot see fluency, register or dialect. A stilted but understandable translation reads back fine. Arabic here is Modern Standard Arabic only (NATIVE_REVIEW.md).
4. Protected tokens inflate it: FreeBot, NoLimit, the canary, "SYSTEM OVERRIDE" and Base64 survive any translation. Mask them on both sides before scoring.
5. Direction and independence: the check only helps if the back-translator is a different system. NLLB-200 is the free, offline candidate (section 2.7). Its into-English direction is usually stronger than out-of-English: the SONAR paper, whose decoders are from the NLLB family, averages about 33 spBLEU for X to English against about 21 for English to X over 200 languages (its Table 1, rows partly garbled in the text extraction, so treat as approximate) [10b].
6. BLEU versus chrF: tokenisation is not an issue because scoring happens in English, so either works; chrF is the safer default and is what sacreBLEU recommends reporting alongside. On African pairs against human ratings, chrF++ averaged Spearman 0.277 against 0.328 for COMET22, and CometKiwi (reference free) averaged 0.274 (AfriCOMET Tables 2 and 3) [24]. Surface metrics are not far behind learned ones in low resource settings.

### 2.3 Reference free quality estimation (QE)

Facts from model cards and papers (sizes from the Hugging Face file listing; "ckpt" is the checkpoint file size):

| Model | Size | License and gate | Languages (of our 87) | Fits this laptop? |
|---|---|---|---|---|
| CometKiwi 2022 (wmt22-cometkiwi-da) | InfoXLM-large encoder, 550M parameters (paper), ckpt 2.26 GB | cc-by-nc-sa-4.0; gated, auto approval, "Acknowledge license" plus Hugging Face login | 78 of 87 | Yes, CPU or GPU |
| CometKiwi 2023 XL | 3.5B, ckpt 13.94 GB, card: "requires a minimum of 15GB of GPU memory" | same | 78 of 87 | No (6 GB GPU, 15.2 GB RAM) |
| CometKiwi 2023 XXL | 10.5B on the card (10.7B in the paper), card: 44 GB GPU | same | 78 of 87 | No |
| xCOMET-XL / XXL | about 3.5B / about 10.7B, XL ckpt 13.94 GB | cc-by-nc-sa-4.0, gated; card: commercial services must contact Unbabel | 78 of 87 | No |
| MetricX-24 Hybrid Large (reference free with the QE flag) | mT5-large, 1.2B (mT5 README), 4.92 GB fp32, 2.46 GB bfloat16 | Apache-2.0, not gated | 84 of 87 (missing hr or rw) | Yes, GPU in bfloat16 or CPU |
| MetricX-24 Hybrid XL | mT5-XL 3.7B, 14.97 GB fp32, 7.49 GB bf16 | Apache-2.0, not gated | 84 of 87 | No on GPU (6 GB); CPU is too tight |
| MetricX-23 QE Large / XL | same sizes as MetricX-24 | Apache-2.0 | 84 of 87 | Large yes |

- The word "age" does not appear in any of these cards. The gate is a license acknowledgement. Hugging Face's terms require an account holder to be "a natural person of at least age 13" [26], so a 15 year old can accept it. The non-commercial and share-alike terms are fine for a contest entry; keep the weights out of the repo and commit only the scores [legal reading unverified]. The COMET code is Apache-2.0 [6]; the weights are not.
- Coverage lists are for the encoder, not proof of validation. CometKiwi's card itself says results for uncovered languages "are unreliable". MetricX's card publishes agreement only for en-de, en-es and ja-zh; there is no published validation on most of our languages. CometKiwi 2023 was trained and tested on WMT23 pairs that include en-mr, en-hi, en-ta, en-te, en-gu (DA) plus en-de, zh-en, he-en (MQM) [4]. xCOMET's training data spans 36 language pairs with DA and 14 with MQM, and it was tested on zh-en, en-de and en-ru [5].
- Low resource evidence is mixed to poor. AfriCOMET Table 3 (sentence level Spearman against human ratings, CometKiwi 2022): English to Swahili 0.756, Somali 0.357, Hausa 0.245, Yoruba 0.231, Igbo 0.188, Luo 0.161, Twi 0.026, Xhosa -0.030 (average over the table 0.274). The authors attribute this to limited encoder coverage and no human rating data for these languages [24]. ITEM (six Indian languages, 29 metrics) finds weak segment level agreement for most metrics and that embedding based metrics are more sensitive to outliers than neural ones [25].
- Domain shift: all of these were trained on news style translation. Attack strings are imperatives wrapped in fake emails, reviews and Base64. Score only the natural language part with the canary and Base64 masked, and treat the 6 benign controls (ordinary polite sentences) as the cleanest QE inputs.
- CPU runtime [estimate, not measured; I did not install torch]. Workload about 1,200 to 1,800 strings (67 to 87 languages, 18 to 21 strings each). A numpy float32 matrix multiply on this CPU measured 70 GFLOPS (computed, a floor for torch). CometKiwi 2022: about 1 to 3 seconds a string, so 20 to 90 minutes. MetricX-24 Large: about 2 to 6 seconds a string, so 1 to 3 hours on CPU, minutes on the GPU in bfloat16. Run overnight, once.
- Software friction [unverified]: the MetricX repo pins transformers 4.30.2 and sentencepiece 0.1.99, and the system Python here is 3.14.3 with none of torch, transformers, sentence-transformers, fasttext, sacrebleu or comet installed (checked). Use a separate Python 3.10 or 3.11 environment (the repo already uses uv).

### 2.4 Sentence embedding similarity (English seed versus translation)

| Model | Size | License | Coverage of our 87 | Notes |
|---|---|---|---|---|
| LaBSE (sentence-transformers port) | 471M parameters (safetensors count), 1.88 GB | Apache-2.0 | 86 of 87 (missing ps) | Plain `sentence-transformers`, works on Windows. 109 languages. Paper: 83.7% Tatoeba retrieval over 112 languages versus 65.5% for the earlier best (LASER 2019) [9] |
| SONAR text encoder | encoder file 3.06 GB; 200 languages (all NLLB-200 languages) | Code MIT; text encoder, decoder and BLASER 2.0 models are non-commercial (CC-BY-NC-4.0) | 87 of 87 | Needs fairseq2, which "does not have native support for Windows" (use WSL). An unofficial transformers port exists (cointegrated/SONAR_200_text_encoder, CC-BY-NC-4.0, 3.06 GB) [10] |
| BLASER 2.0 QE (on SONAR) | 69 MB head | CC-BY-NC-4.0 | 87 of 87 (via SONAR) | Reference free, trained to predict human XSTS similarity scores (1 to 5). Same loader problem. [10] |
| LASER2 / LASER3 | LASER2 one encoder; LASER3 147 language specific encoders | BSD | LASER2 66, LASER3 49, together 87 of 87 | Many separate downloads and fairseq era dependencies; not worth it over LaBSE [11] |

- Known weakness: embeddings reward topical sameness and miss small meaning edits. In SONAR's xsim++ test (hard negatives made by changing a number, an entity or a cause), over the 98 languages shared by all three models the error rates were SONAR 9.3%, LaBSE 15.4%, LASER3 27.5% (Table 4) [10b]. A translation that flips "ignore" to "remember" could still score high.
- Human agreement for low resource languages: I found no published per-language correlation of plain embedding cosine with human adequacy ratings covering our languages. The closest evidence is ITEM (six Indian languages, LaBSE and LASER among the 29 metrics, weak agreement) [25]. BLASER 2.0 is trained on human ratings, but I did not open the SeamlessM4T paper that evaluates it [unverified].
- A better use than raw cosine: a retrieval test in the style of xsim. For each language, embed the 15 attacks and 6 controls, embed the 21 English seeds, and check that each translation's nearest seed is in its own category (5 attack categories plus controls). A failure means the meaning drifted far enough to look like another thing. Phrasings inside a category are near duplicates, so score at category level, not phrasing level.

### 2.5 Language identification as a sanity check

| Tool | Size | License | Coverage of our 87 | Notes |
|---|---|---|---|---|
| GlotLID v3 | model.bin 1.69 GB (fastText) | Apache-2.0 plus notices (card says "license: other"; LICENSE file read) | 87 of 87 (2,102 labels; Estonian is ekk_Latn, Persian is fas_Arab, Chinese is cmn_Hani, Tagalog is fil_Latn) | Per label test F1 published in languages-v3.md; for our languages it is 0.76 to 1.00 |
| OpenLID-v2 | model.bin 1.22 GB (fastText) | GPL-3.0 (card) | 87 of 87 (200 varieties, FLORES labels: cmn_Hans, fil_Latn, ekk_Latn) | Original paper: macro F1 0.93 over 201 languages. Clean text first with its normaliser |
| fastText lid.176 | lid.176.bin 126 MB; lid.176.ftz 917 kB | CC-BY-SA 3.0 | 80 of 87 (missing ha ig zu xh sn rw ny) | Fast and tiny but misses seven low tier languages |
| NLLB LID (facebook/fasttext-language-identification) | 1.18 GB | CC-BY-NC-4.0 | not tested here | Not needed |

- GlotLID F1 below 0.90 for our codes: hr 0.76, zh 0.83, id 0.83, ar 0.85, hi 0.86, es 0.86, en 0.88, pt 0.89 (computed from languages-v3.md). These are near-neighbour confusions (Croatian with Serbian and Bosnian, Indonesian with Malay), measured on GlotLID's own test sentences, not on short attack strings.
- What LID can and cannot do: it catches "not translated", "wrong language", "code switched" and wrong script variants (Serbian Cyrillic or Latin). It says nothing about meaning. Short strings and leftover English tokens fool it, so strip the canary, Base64 and fixed English markers first, then compare GlotLID and OpenLID-v2 top-1; disagreement is a flag, not a verdict. linguistics.py already covers script; LID adds same-script confusions (Malay or Indonesian, Danish or Norwegian, Serbian or Croatian, Persian or Urdu).
- Both fastText models need the `fasttext` package; GlotLID's README says to use `fasttext-numpy2-wheel` on newer Python [unverified on Windows].

### 2.6 How published safety and red-teaming datasets validated translations

| Work | Method | Validation |
|---|---|---|
| MultiJail (Deng et al. 2023) [20] | 315 prompts translated by native speakers into 9 languages (3 high, 3 mid, 3 low resource) | A separate group of native speakers checked a random subset; target pass rate over 97%. Ablation: machine translated prompts gave slightly more unsafe output (11.15%) than human translated (10.19%) on average, so the machine versus human gap was small there |
| XSafety (Wang et al. 2023) [21] | Google Translate, then professional proofreading | Two rounds (15.5% then 3.4% of items modified), then a random 10% inspection with over 99% pass; USD 3,000 |
| Aya red-teaming (Aakanksha et al. 2024) [22] | Native speakers wrote about 900 prompts each in 8 languages and supplied English translations | Human authored, no translation step to validate; their separate "Translated" test set used NLLB 3.3B |
| LinguaSafe (Ning et al. 2025) [19] | LLM transcreation with an "Estimate then Refine" loop, then human review | 500 sampled items per language for Bengali and Malay: error rate under human inspection 71% (Bengali) and 36% (Malay) for vanilla LLM translation, 12% and 3% after the full pipeline |
| PolyGuard, Carnegie Mellon (Kumar et al. 2025) [23] | Open weight translation models for training data, a stronger model in an agentic loop for the test set, of an English safety set | 50 items per language, 3 annotators each (recruited through Prolific), a 0 to 100 translation quality score, average 81.15, and a check that safety labels survive translation (Krippendorff alpha 0.94 between source and target labels) |
| Marx and Dunaiski 2026 [18] | Google Translate, back-translation quality filter, then native speaker red-teamers | 3 native speakers per language (1 for Kiswahili); human prompts raised average harmful rate from 59.84% to 75.82%, but humans also adapted the conversation, so this is not a pure translation effect |

- The pattern: a random sample of 50 to 500 items per language, by native speakers, with a pass threshold. Nobody validated 87 languages. Cheap automatic checks were used as filters, not as certification.
- The effect of translation quality looks non-linear. Where machine translation is decent (MultiJail's bn, sw, jv with Google Translate) the human versus machine gap was about 1 point. Where it is bad (isiXhosa, isiZulu) the gap was large. So the risk is concentrated in the worst translated languages, and the tools in this report are best at finding those.
- Name clash to disclose: a different, published "PolyGuard" (Carnegie Mellon, COLM 2025, arXiv:2504.04377) is a multilingual safety classifier for 17 languages. I searched README.md, RELATED_WORK.md and STATE.md for its arXiv id and first author and found no mention. Say in the writeup that the names coincide and the projects are unrelated.

### 2.7 Independent back-translator: NLLB-200

- facebook/nllb-200-distilled-600M: CC-BY-NC-4.0, pytorch_model.bin 2.46 GB, 200 languages, trained for inputs up to 512 tokens; the card says it is "a research model and is not released for production deployment" and that translations "can not be used as certified translations" [12]. The 1.3B distilled model is 5.48 GB. Coverage of our codes equals the SONAR table: 87 of 87 (SONAR README: its languages are "all the 202 languages from the NLLB-200 models").
- Role: translate the stored X text back to English with NLLB, then chrF against the English seed. This is the cross-system check Zhuo et al. recommend. NLLB is weaker in the lowest resource languages, so a low score is ambiguous (translation bad, or NLLB bad). That is why the other signals and a human sample are needed.
- Runtime on CPU [estimate]: 2 to 4 seconds a string for about 1,000 strings (67 languages x 15 attacks), so 30 to 90 minutes, once.

### 2.8 Coverage of the 87 catalog codes

Src: A = author written, M = machine file present on 2026-10-05, M* = machine file not generated yet. "Y" = language is on the tool's published list. Counts: CometKiwi and xCOMET 78 (28 of 28 high, 23 of 24 mid, 27 of 35 low); MetricX via mT5 84 (27, 24, 33); LaBSE 86; SONAR and NLLB-200 87; LASER2 66, LASER3 49, either 87; GlotLID 87; OpenLID-v2 87; lid.176 80 (28, 24, 28).
CometKiwi and xCOMET are missing: tg ceb yo ig zu sn rw ny ht. MetricX is missing: hr or rw. Remember the Xhosa warning: a "Y" is permission to run, not evidence of accuracy.

| Code | Language | Tier | Src | CometKiwi, xCOMET | MetricX (mT5) | LaBSE | SONAR, NLLB-200 | LASER | GlotLID v3 (F1) | OpenLID-v2 | lid.176 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| en | English | high | A | Y | Y | Y | Y | 2 | Y (0.88) | Y | Y |
| es | Spanish | high | A | Y | Y | Y | Y | 2 | Y (0.86) | Y | Y |
| hi | Hindi | high | A | Y | Y | Y | Y | 2+3 | Y (0.86) | Y | Y |
| gu | Gujarati | high | A | Y | Y | Y | Y | 3 | Y (1.00) | Y | Y |
| zh | Chinese | high | A | Y | Y | Y | Y | 2 | Y (0.83) | Y | Y |
| tl | Tagalog | mid | A | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| vi | Vietnamese | high | A | Y | Y | Y | Y | 2 | Y (1.00) | Y | Y |
| ar | Arabic | high | A | Y | Y | Y | Y | 2 | Y (0.85) | Y | Y |
| ko | Korean | high | A | Y | Y | Y | Y | 2 | Y (1.00) | Y | Y |
| fr | French | high | A | Y | Y | Y | Y | 2 | Y (0.93) | Y | Y |
| ru | Russian | high | A | Y | Y | Y | Y | 2 | Y (0.92) | Y | Y |
| pt | Portuguese | high | A | Y | Y | Y | Y | 2 | Y (0.89) | Y | Y |
| de | German | high | A | Y | Y | Y | Y | 2 | Y (0.96) | Y | Y |
| it | Italian | high | A | Y | Y | Y | Y | 2 | Y (0.91) | Y | Y |
| ja | Japanese | high | A | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| pl | Polish | high | A | Y | Y | Y | Y | 2 | Y (0.97) | Y | Y |
| tr | Turkish | high | A | Y | Y | Y | Y | 2+3 | Y (0.97) | Y | Y |
| id | Indonesian | mid | A | Y | Y | Y | Y | 2+3 | Y (0.83) | Y | Y |
| uk | Ukrainian | mid | A | Y | Y | Y | Y | 2 | Y (0.97) | Y | Y |
| el | Greek | mid | A | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| nl | Dutch | high | M | Y | Y | Y | Y | 2 | Y (0.92) | Y | Y |
| sv | Swedish | high | M | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| no | Norwegian | high | M | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| da | Danish | mid | M | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| fi | Finnish | high | M | Y | Y | Y | Y | 2 | Y (0.93) | Y | Y |
| cs | Czech | high | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| sk | Slovak | mid | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| hu | Hungarian | high | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| ro | Romanian | mid | M | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| bg | Bulgarian | mid | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| hr | Croatian | high | M | Y | no | Y | Y | 2 | Y (0.76) | Y | Y |
| sr | Serbian | high | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| sl | Slovenian | mid | M | Y | Y | Y | Y | 2 | Y (0.97) | Y | Y |
| lt | Lithuanian | mid | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| lv | Latvian | mid | M | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| et | Estonian | mid | M | Y | Y | Y | Y | 2 | Y (0.97) | Y | Y |
| mk | Macedonian | low | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| sq | Albanian | low | M | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| is | Icelandic | low | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| ga | Irish | low | M | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| cy | Welsh | low | M | Y | Y | Y | Y | 3 | Y (1.00) | Y | Y |
| eu | Basque | high | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| ca | Catalan | high | M | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| gl | Galician | mid | M | Y | Y | Y | Y | 2 | Y (0.98) | Y | Y |
| he | Hebrew | mid | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| fa | Persian | high | M | Y | Y | Y | Y | 2+3 | Y (0.92) | Y | Y |
| ps | Pashto | low | M* | Y | Y | no | Y | 3 | Y (0.99) | Y | Y |
| az | Azerbaijani | low | M | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| kk | Kazakh | mid | M | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| uz | Uzbek | mid | M | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| ky | Kyrgyz | high | M | Y | Y | Y | Y | 3 | Y (1.00) | Y | Y |
| tg | Tajik | low | M* | no | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| mn | Mongolian | low | M* | Y | Y | Y | Y | 3 | Y (0.99) | Y | Y |
| ka | Georgian | mid | M | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| hy | Armenian | low | M* | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| bn | Bengali | mid | M | Y | Y | Y | Y | 2+3 | Y (0.98) | Y | Y |
| ur | Urdu | mid | M | Y | Y | Y | Y | 2+3 | Y (0.97) | Y | Y |
| pa | Punjabi | low | M | Y | Y | Y | Y | 3 | Y (1.00) | Y | Y |
| ta | Tamil | mid | M | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| te | Telugu | low | M | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| mr | Marathi | low | M | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| kn | Kannada | low | M | Y | Y | Y | Y | 3 | Y (0.99) | Y | Y |
| ml | Malayalam | low | M | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| or | Odia | low | M | Y | no | Y | Y | 3 | Y (1.00) | Y | Y |
| ne | Nepali | low | M* | Y | Y | Y | Y | 3 | Y (0.99) | Y | Y |
| si | Sinhala | low | M* | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| th | Thai | mid | M | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| ms | Malay | mid | M | Y | Y | Y | Y | 2+3 | Y (0.91) | Y | Y |
| km | Khmer | low | M* | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| lo | Lao | low | M | Y | Y | Y | Y | 3 | Y (1.00) | Y | Y |
| my | Burmese | low | M* | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| jv | Javanese | low | M* | Y | Y | Y | Y | 3 | Y (0.98) | Y | Y |
| su | Sundanese | low | M* | Y | Y | Y | Y | 3 | Y (0.98) | Y | Y |
| ceb | Cebuano | mid | M | no | Y | Y | Y | 3 | Y (0.99) | Y | Y |
| sw | Swahili | low | M* | Y | Y | Y | Y | 2+3 | Y (0.93) | Y | Y |
| am | Amharic | low | M* | Y | Y | Y | Y | 2+3 | Y (1.00) | Y | Y |
| ha | Hausa | low | M | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | no |
| yo | Yoruba | low | M | no | Y | Y | Y | 3 | Y (1.00) | Y | Y |
| ig | Igbo | low | M | no | Y | Y | Y | 3 | Y (1.00) | Y | no |
| zu | Zulu | low | M | no | Y | Y | Y | 3 | Y (0.94) | Y | no |
| xh | Xhosa | low | M | Y | Y | Y | Y | 3 | Y (0.98) | Y | no |
| so | Somali | low | M* | Y | Y | Y | Y | 2+3 | Y (0.99) | Y | Y |
| sn | Shona | low | M | no | Y | Y | Y | 3 | Y (0.98) | Y | no |
| rw | Kinyarwanda | low | M* | no | no | Y | Y | 3 | Y (0.96) | Y | no |
| ny | Chichewa | low | M | no | Y | Y | Y | 3 | Y (0.95) | Y | no |
| af | Afrikaans | mid | M | Y | Y | Y | Y | 2 | Y (0.99) | Y | Y |
| ht | Haitian Creole | low | M | no | Y | Y | Y | 3 | Y (0.99) | Y | Y |

## 3. What PolyGuard should do

### Ranked steps

| # | What | File | Effort | Cost | Risk |
|---|---|---|---|---|---|
| 1 | Fix the 71% citation. Replace with LinguaSafe (arXiv:2508.12733: Bengali 71%, Malay 36% for vanilla LLM translation; 12% and 3% after refinement plus human review). Keep 59.8% to 75.8% attributed to arXiv:2605.18239. Note RELATED_WORK.md's "71% to between 3% and 12%" merges two languages. Log it in the PREREGISTRATION.md deviation log | README.md, NATIVE_REVIEW.md, PREREGISTRATION.md (2026-09-17 row), expand_languages.py docstring and backcheck docstring, RELATED_WORK.md | 0.5 h | free | Low. Leaving it wrong is the real risk: judges can check |
| 2 | Pre-register the quality rules now, before any live scan: which scores, the flag rule, and the three sensitivity analyses in section 3.3 | PREREGISTRATION.md deviation log | 1 h | free | Low |
| 3 | New script `translation_quality.py` stage A: mask protected tokens, run GlotLID v3 and OpenLID-v2 on every string of all 87 languages, record top-1, probability, agreement | new file, output `translation_quality.json` | 3 h | free | Low |
| 4 | Stage B: NLLB-200 600M back-translation of all stored attack strings (not Base64), chrF against the seeds, plus negative controls (wrong-pair and half-deleted) to set a gross failure threshold in advance | same script | 4 h plus 30 to 90 min runtime | free | Medium: NLLB errors in the lowest resource languages cause false flags |
| 5 | Stage C: LaBSE category retrieval (accuracy and margin) for 86 languages; use SONAR (WSL or the port) only for ps | same script | 2 h plus minutes | free | Low |
| 6 | Stage D, optional: MetricX-24 Hybrid Large QE on the 6 controls and the masked attack text (second opinion where A to C disagree); CometKiwi 2022 only if you accept its non-commercial gate | same script, separate environment | 3 h plus 1 to 3 h runtime | free | Medium: environment problems on Python 3.14; metric unvalidated for most languages |
| 7 | Run once locally, commit only `translation_quality.json` (per language: scores, flags, tool versions, sha256 of the machine_translations file and of the seeds). In CI only check that the stored hashes still match the bank; do not run the models in CI | preflight.py or verify_all.py hook | 1 h | free | Low. CI would need about 6 GB of downloads and the NC licensed weights |
| 8 | Provenance contrast: also machine translate the 20 author written languages with the same pipeline and compare break rates author written versus machine inside each language | generate_attack_bank.py / expand_languages.py (new output dir), engine analysis | 4 to 6 h plus scan cost | cost of the extra scan | Medium. It needs a translator session, and it understates the artefact because MT is best in high resource languages |
| 9 | Human check with the 10 minute sheet (section 3.4) for 8 to 12 languages; log rows in NATIVE_REVIEW.md | review_sheet.py (add a `--short` option), review_ingest.py | 3 h build, then about 15 min per reviewer | free | Medium. Recruiting is the bottleneck |
| 10 | Report per language quality next to every break rate in the app and exports, and word the writeup per section 3.5 | report_html.py, README.md | 3 h | free | Low |

Suggested order if time is short (21 days to Oct 26, school continues): 1, 2, 3, 4, 5, 9, 7, 10, then 8 and 6 if there is room. Steps 3 to 5 are about 9 hours of work.

### 3.1 How the signals combine

- Keep them separate in the JSON: LID agreement, NLLB round trip chrF, LaBSE retrieval, optional QE. Do not average them into one number; they measure different failures and their errors differ by language.
- A language is **flagged** if it fails any gross failure gate (LID top-1 wrong script or wrong language on most strings; round trip chrF below the negative control ceiling of about 0.38 on this scale; retrieval below chance) or fails two independent soft gates. Thresholds are fixed from the negative controls and from the anchor languages (Spanish, Vietnamese, Arabic, the three with native feedback), before looking at any break rate.
- A language with only the NLLB signal low and the others fine is "inconclusive", not flagged; it goes first in the human queue.
- Also run every tool on the 20 author written languages so all 87 sit on one scale (the 20 get no stored back-translation today).

### 3.2 Using the score in the analysis: exclude, weight, or covariate

| Choice | What it does | Bias it introduces |
|---|---|---|
| Exclude flagged languages | Drops them from the Mann-Whitney test | Selection on a variable tied to tier: quality falls with resource level, so the low tier becomes "the low resource languages that machine translate well", which is not representative. Removes false safety from garbled attacks, but also removes languages the bot may truly struggle in. Loses power (35 low tier languages shrink). A threshold chosen after seeing results is a researcher degree of freedom |
| Weight by quality | Weighted regression or weighted rates | Does not remove the garble bias in languages that stay in; it only reduces their influence. Weighted rank tests are non-standard, so you lose the pre-registered test. Noisy weights add noise |
| Covariate | Per language break rate on tier plus quality score (or ordinal flag) | Uses all data, but (a) measurement error in quality means under-correction, so some bias remains; (b) every metric is itself less reliable in low resource languages (see Xhosa and Twi above), so quality partly proxies for tier and adjusting can over-correct and absorb the real tier effect, biasing toward no gap; (c) collinearity widens the interval; (d) assumes a linear effect and overlap between tiers, which is thin at the bottom |
| Provenance contrast (step 8) | Author written versus machine inside the same language | Cleanest for translation method because the language is held fixed; limited to 20 high and mid languages, so it says little about the lowest resource ones |
| Dose response plot | Break rate against quality score, by tier | Not a test, but shows whether break rates rise with quality inside a tier, which is what the confound predicts. Marx and Dunaiski's r of 0.87 to 0.92 is this idea with apparently four points |

Recommendation: keep the pre-registered primary test unconditional and unchanged (all languages). Add, pre-registered as sensitivity analyses: S1 drop flagged languages, S2 add the quality covariate (use the cross-system chrF plus LaBSE retrieval, not QE alone), S3 the provenance contrast, S4 the dose response plot. Report all four next to the primary. If the tier gap survives S1 and S2 it is more credible; if it shrinks a lot it is confounded by translation; if S1 and S2 disagree say so. This matches the direction already recorded in PREREGISTRATION.md (translation error biases toward understating the gap).

### 3.3 Existing gates to treat carefully

- Do not report "reverse translation pass rate" as validation. The keyword gate has passed 159 of 159 and the role_play branch accepts unrelated text containing "exactly" and "reply" (computed). If it is reported at all, report it as a smoke test.
- Do not describe any language as "verified", "validated" or "human-checked" without a NATIVE_REVIEW.md row (existing rule, keep it).

### 3.4 A cheap human check: the 10 minute sheet

For one bilingual volunteer per language, 12 items:
- 10 attack strings (the 5 categories, 2 phrasings each; for the Base64 category rate only the surrounding sentence) plus 2 controls, shown beside the English.
- Three quick questions per item, the same rubric the repo already uses: same meaning as the English (yes, partly, no); would a native speaker read it as an instruction to do that thing (yes, no); natural (1 to 5). The codes and Base64 are checked by script, not by the reviewer.
- Timing: 12 items at about 45 seconds is 9 minutes, plus a minute to read the instructions.
- Score per language: the share of items with "same meaning = yes" and "instruction = yes" (the intent preserved rate). Suggested reading, my own rule and not validated: 11 or 12 of 12 pass; 8 to 10 caution; 7 or fewer fail. MultiJail aimed for over 97% pass on a random subset, which 12 items cannot show, so say "12 item spot check" in the writeup, not "validated". CMU PolyGuard used 50 items and 3 annotators per language; this is a smaller version of the same design.
- One reviewer per language gives no agreement statistic; say so. Keep reviewers anonymous in public files, as NATIVE_REVIEW.md already does.
- Use of results: (1) a sanity check that flagged languages are worse than unflagged ones, (2) anchors to set thresholds, (3) rows in NATIVE_REVIEW.md. With about 10 languages you cannot validate a metric statistically; you can only catch gross disagreement.
- Account hygiene (from your own notes): this is a personal contest entry, so recruit and collect with personal accounts, not the HopeBridge email, Drive or tracker.

How many languages by Oct 26: the bottleneck is finding people, not the 10 minutes. Realistically 8 to 12 languages with one reviewer each (the 3 existing feedback rounds are separate, so that would be about 11 to 15 of 87 with some human look); 20 would need a classmate or community network that I cannot verify exists. Do not plan on 87, and do not plan on more than 1 reviewer per language. Prioritise: (1) languages flagged or inconclusive in step 4, (2) the lowest tier languages with the weakest tool coverage (yo ig zu sn rw ny ceb tg ht, which CometKiwi does not list), (3) at least two high tier machine languages as controls, (4) languages in unusual scripts the author cannot read (Khmer, Burmese, Sinhala, Amharic, Georgian, Armenian).

### 3.5 What to say in the writeup

> Attack strings for 67 languages were machine translated by the same language model and checked by script, language identification, a round trip through an independent translation system (NLLB-200), and embedding retrieval. None of these tests fluency. Per language scores are published in translation_quality.json. N of these languages also had a 12 item spot check by one bilingual volunteer. The tier comparison is reported with and without flagged languages, with a quality covariate, and, for 20 languages, against author written text.

### What NOT to do

- Do not average the tools into one composite score, and do not set thresholds after seeing break rates.
- Do not treat a language list as validation (CometKiwi on Xhosa).
- Do not use the translating model again to judge or back-translate as the only evidence. If a session translator re-checks, call it a smoke test.
- Do not try the 3.5B and larger models (CometKiwi XL and XXL, xCOMET XL and XXL, MetricX XL and XXL); they do not fit this machine.
- Do not commit model weights or paste NC licensed outputs as a product; commit scores only. Do not redistribute the GPL-3.0 OpenLID model.
- Do not plan on paid translation, Prolific or an API key path; no budget, and crowd platforms usually require adults [unverified].
- Do not claim a language is "verified" or "human-checked" unless NATIVE_REVIEW.md has its row.
- Do not read a low NLLB round trip score as proof of a bad translation in the lowest resource languages, and do not read a high one as proof of a good one.

## 4. Sources

1. CometKiwi 2022 model card: https://huggingface.co/Unbabel/wmt22-cometkiwi-da (raw: .../resolve/main/README.md)
2. CometKiwi 2023 XL card: https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xl
3. CometKiwi 2023 XXL card: https://huggingface.co/Unbabel/wmt23-cometkiwi-da-xxl
4. Rei et al. 2023, Scaling up CometKiwi: https://arxiv.org/abs/2309.11925
5. xCOMET model cards https://huggingface.co/Unbabel/XCOMET-XL and https://huggingface.co/Unbabel/XCOMET-XXL ; Guerreiro et al. 2023 paper https://arxiv.org/abs/2310.10482
6. COMET code (Apache-2.0): https://github.com/Unbabel/COMET
7. MetricX-24 card https://huggingface.co/google/metricx-24-hybrid-large-v2p6 ; MetricX-23 QE card https://huggingface.co/google/metricx-23-qe-large-v2p0 ; repo https://github.com/google-research/metricx ; mT5 README (101 languages; 1.2B, 3.7B, 13B) https://github.com/google-research/multilingual-t5
8. Hugging Face file listings (sizes, licenses, gating) from https://huggingface.co/api/models/<model id>?blobs=true for each model named above
9. LaBSE card https://huggingface.co/sentence-transformers/LaBSE ; paper https://arxiv.org/abs/2007.01852
10. SONAR repo https://github.com/facebookresearch/SONAR ; SONAR card https://huggingface.co/facebook/SONAR ; BLASER 2.0 QE card https://huggingface.co/facebook/blaser-2.0-qe ; unofficial port https://huggingface.co/cointegrated/SONAR_200_text_encoder ; fairseq2 README https://github.com/facebookresearch/fairseq2
10b. Duquenne et al. 2023, SONAR paper: https://arxiv.org/abs/2308.11466
11. LASER repo https://github.com/facebookresearch/LASER and https://github.com/facebookresearch/LASER/blob/main/nllb/README.md
12. NLLB-200 distilled 600M card https://huggingface.co/facebook/nllb-200-distilled-600M
13. GlotLID card https://huggingface.co/cis-lmu/glotlid ; repo https://github.com/cisnlp/GlotLID ; labels and F1 https://github.com/cisnlp/GlotLID/blob/main/languages-v3.md ; license text https://huggingface.co/cis-lmu/glotlid/blob/main/LICENSE
14. OpenLID-v2 model https://huggingface.co/laurievb/OpenLID-v2 ; dataset and labels https://huggingface.co/datasets/laurievb/OpenLID-v2 ; paper https://aclanthology.org/2023.acl-short.75/ (abstract quoted from the dataset card)
15. fastText language identification page https://fasttext.cc/docs/en/language-identification.html
16. sacreBLEU README (chrF signature) https://github.com/mjpost/sacrebleu
17. Zhuo et al. 2023, Rethinking Round-Trip Translation for MT Evaluation: https://arxiv.org/abs/2209.07351
18. Marx and Dunaiski 2026, Multilingual jailbreaking of LLMs using low-resource languages: https://arxiv.org/abs/2605.18239
19. Ning et al. 2025, LinguaSafe: https://arxiv.org/abs/2508.12733
20. Deng et al. 2023, MultiJail: https://arxiv.org/abs/2310.06474
21. Wang et al. 2023, XSafety: https://arxiv.org/abs/2310.00905
22. Aakanksha et al. 2024, Multilingual Alignment Prism (Aya red-teaming): https://arxiv.org/abs/2406.18682
23. Kumar et al. 2025, PolyGuard (CMU): https://arxiv.org/abs/2504.04377
24. Wang et al. 2023, AfriCOMET: https://arxiv.org/abs/2311.09828
25. Yari et al., ITEM: https://arxiv.org/abs/2510.07061
26. Hugging Face Terms of Service (age 13): https://huggingface.co/terms-of-service
27. Panickssery et al. 2024, LLM Evaluators Recognize and Favor Their Own Generations: https://arxiv.org/abs/2404.13076
28. Repository files read: README.md, NATIVE_REVIEW.md, PREREGISTRATION.md, RELATED_WORK.md, linguistics.py, expand_languages.py, languages_catalog.py, review_sheet.py, machine_translations/ka.json and ceb.json (and all 53 files for the computed numbers)

Items marked [estimate] are my arithmetic from parameter counts and a measured 70 GFLOPS numpy matrix multiply on this laptop; nothing was run with the actual models.
