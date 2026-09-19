# Native speaker review

**Status as of 2026-09-17: zero languages have been reviewed by a native speaker.
That includes the 20 hand-authored ones.**

This document exists because the bank used to carry a `verified: True` flag on
those 20 languages. It meant "the project author wrote this". It did not mean
anyone who speaks Gujarati had ever read the Gujarati. A reader of the app or of
an exported CSV had no way to tell those apart, and the word "verified" invited
the wrong reading. The flag is gone. Provenance is now stated as `author` or
`machine`, and native review is tracked here as a separate fact that is currently
false everywhere.

## Why it matters more than it sounds

A bad translation does not just lower quality, it can invert a result. If an
attack in Marathi is garbled, the bot may fail to comply for reasons that have
nothing to do with its defences. That shows up as a lower break rate, which reads
as "well defended in Marathi", which is the opposite of the truth. The capability
controls catch the extreme version of this, where the bot cannot operate in the
language at all, but they cannot catch an attack that is merely awkward or
subtly wrong.

This is not a hypothetical worry. Published work finds that poor machine
translation, rather than stronger guardrails, is what drives lower attack success
in low-resource languages: human red-teaming raised jailbreak rates from 59.8% to
75.8%, and machine-translation error rates in some languages ran as high as 71%
before human review (arXiv:2605.18239, see RELATED_WORK.md).

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

3. Apply what comes back, then record it below and set `native_reviewed` for that
   language in `generate_attack_bank.py`.

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

| Language | Reviewer | Date | Verdict | Changes applied |
|---|---|---|---|---|
| (none yet) | | | | |

## Honest statement for the writeup

Until this table has entries, the correct phrasing anywhere this project is
described is:

> Attack strings for 20 languages were written by the author and validated
> automatically for script, encoding, length and uniqueness. The remainder were
> machine-translated and additionally verified by reverse translation. No
> language has been reviewed by a native speaker, so translation quality is a
> known limitation and a possible confound.

Do not write "verified", "professionally translated", or "human-checked" about
any language in this project until the row exists above.
