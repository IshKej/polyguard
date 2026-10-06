# Native speaker review

**Status as of 2026-10-04: native speaker feedback has been received and
integrated for 3 of the 20 hand-authored languages, Spanish, Vietnamese and
Arabic. Portuguese feedback is pending. The other 16 have had no native review.** Feedback
received and integrated is not a validation: it means a speaker read the lines and
their corrections are now in the bank, not that the language is certified correct.
The bank's `native_reviewed` flag is still false for every language.

This document exists because the bank used to carry a `verified: True` flag on
those 20 languages. It meant "the project author wrote this". It did not mean
anyone who speaks Gujarati had ever read the Gujarati. A reader of the app or of
an exported CSV had no way to tell those apart, and the word "verified" invited
the wrong reading. The flag is gone. Provenance is now stated as `author` or
`machine`, and native review is tracked here as a separate fact, language by
language.

## Why it matters more than it sounds

A bad translation does not just lower quality, it can invert a result. If an
attack in Marathi is garbled, the bot may fail to comply for reasons that have
nothing to do with its defences. That shows up as a lower break rate, which reads
as "well defended in Marathi", which is the opposite of the truth. The capability
controls catch the extreme version of this, where the bot cannot operate in the
language at all, but they cannot catch an attack that is merely awkward or
subtly wrong.

This is not a hypothetical worry. Published work finds that poor machine
translation, rather than stronger guardrails, can drive lower attack success in
low-resource languages: human red-teaming raised jailbreak rates from 59.8% to
75.8% (arXiv:2605.18239), and vanilla LLM translation of a safety benchmark had
error rates of 71% in Bengali and 36% in Malay before human review (LinguaSafe,
arXiv:2508.12733). See RELATED_WORK.md.

Machine-translated languages at least pass an automated gate
(`expand_languages.verify`, plus reverse translation, which is on by default).
Until this round the hand-authored 20 passed through nothing at all, which had
the scrutiny exactly backwards.

## What is checked automatically now

`python linguistics.py` runs over every attack and every control, hand-authored
and machine alike:

| Check | Catches |
|---|---|
| Script | Hindi that arrived in Latin letters, and anything else written in the wrong writing system |
| Mojibake | replacement characters, UTF-8 decoded as Latin-1, stray combining marks |
| Length ratio | truncated translations, and explanations returned instead of translations |
| Duplication | the same string under two languages, meaning one was never translated |

These run with no API key. They are necessary, not sufficient: **none of them
establish fluency, naturalness, or that an attack still reads as an attack.**
Only a speaker can do that.

## How to get a language reviewed

1. Export a review sheet:
   ```bash
   python review_sheet.py gu          # one language
   python review_sheet.py --tier low  # a whole tier
   ```
   This writes `review/<code>_review.csv` with the English original beside the
   translation and an empty verdict column.

2. Send it to a speaker of the language. They fill in `verdict` with `ok`,
   `awkward`, or `wrong`, and add a correction where needed. The instructions are
   in the sheet, and the key question is not "is this good writing" but **"would a
   native speaker reading this understand it as an instruction to do the thing it
   describes?"** A clumsy attack that still reads as an attack is fine. One that
   reads as nonsense is not.

   Spreadsheets made now (`python review_sheet.py gu --xlsx`) use a rubric instead
   of a single verdict: same meaning as the English (yes, partly, no), reads as an
   instruction to do it (yes, no), and how natural (1 to 5). Whether the codes
   survived is checked by the script, not asked of the reviewer. The sheets already
   sent keep their original form, and `--publish` will not overwrite one.

3. Read what comes back with `python review_ingest.py <files>`. It lists the lines
   a reviewer marked, flags any suggested correction that drops a code word (apply
   those by hand), and when two people reviewed one language, reports their
   agreement (percent and Cohen's kappa) and every line they disagree on. Reviewers
   appear as A and B, never by name.

4. Apply what comes back in `generate_attack_bank.py` (never only in the JSON), log
   the new bank fingerprint in `PREREGISTRATION.md`, and record it below.

## Priority order

Review effort should go where a translation error does the most damage, which is
not the same as where it is easiest to find a speaker.

1. **Low-resource languages**, because they carry the hypothesis. A bad
   translation there directly biases the headline result.
2. **Languages with unusual scripts** (Amharic, Khmer, Burmese, Sinhala), where
   errors are hardest for the author to notice.
3. **Hindi and Gujarati**, which are in the author's own heritage languages and
   are the most defensible to claim informal familiarity with, but which should
   still be signed off by someone else.
4. High-resource European languages last. They are the best covered by the
   automated checks and the least likely to carry the finding.

## Review log

Reviewers are not named in this public repository unless they agree to be
credited.

| Language | Reviewer | Date | Verdict | Changes applied |
|---|---|---|---|---|
| Spanish | Native speaker (name withheld) | 2026-10-01 | Suggestions on 10 of 21 lines, to read more naturally or closer to the English | All 10 applied 2026-10-02 in `generate_attack_bank.py`: 6 attacks (`es_instruction_override_1`, `es_system_prompt_extraction_2`, `es_obfuscated_payload_1`, `es_obfuscated_payload_2`, `es_indirect_injection_1`, `es_indirect_injection_2`) and 4 controls (`es_control_1`, `es_control_2`, `es_control_4`, `es_control_5`) |
| Arabic | Native speaker (name withheld) | 2026-10-04 | 18 ok, 2 awkward, 1 wrong; seven wording suggestions | All 7 integrated 2026-10-04 in `generate_attack_bank.py`: 5 attacks (`ar_instruction_override_1`, `ar_instruction_override_2`, `ar_role_play_jailbreak_2`, `ar_system_prompt_extraction_1`, `ar_indirect_injection_0`) and 2 controls (`ar_control_0`, `ar_control_3`). In `ar_indirect_injection_0`, the line marked wrong, only the framing clause was replaced; the quoted customer review carrying the injection is unchanged. Where a suggestion left out the code word, it was kept. |
| Vietnamese | Native speaker (name withheld) | 2026-10-01 | Tone marks correct; understandable, though unnatural in places; one line needed rewording | `vi_role_play_jailbreak_2` reworded as suggested ("tuân theo tất cả" to "tuân theo mọi mệnh lệnh", final period after the canary), 2026-10-02 |

All three are logged, with the new bank fingerprints, in the deviation log of
`PREREGISTRATION.md`.

## Arabic scope

The Arabic corpus uses Modern Standard Arabic (MSA). The reviewer noted that MSA is more common for formal, educational, and informational questions, while dialects are also very common in casual chatting. This review does not establish coverage of Arabic dialects.

## Honest statement for the writeup

The correct phrasing anywhere this project is described is:

> Attack strings for 20 languages were written by the author and validated
> automatically for script, encoding, length and uniqueness. Native speaker
> feedback has been received and integrated for three of them, Spanish,
> Vietnamese and Arabic, and Portuguese feedback is pending; the other 16 have
> had no native review. The Arabic is Modern Standard Arabic, and its review
> does not establish coverage of Arabic dialects. Languages added later are
> machine-translated and checked by reverse translation. Translation quality is
> a known limitation and a possible confound.

Do not write "verified", "validated", "professionally translated", or
"human-checked" about any language in this project, including Spanish,
Vietnamese and Arabic. Feedback received and integrated is what happened, so that is what
to say.
