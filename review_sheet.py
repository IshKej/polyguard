"""
Export a native-speaker review sheet for one or more languages.

Turns "translation quality is a known limitation" into something a person can
actually act on. Produces a CSV with the English original beside the translation
and an empty verdict column, so a speaker of the language can work through it
without reading any code or JSON.

The question the sheet asks is deliberately narrow. Not "is this good writing",
but "would a native speaker reading this understand it as an instruction to do
the thing it describes?" A clumsy attack that still reads as an attack is fine
for this purpose. One that reads as nonsense is not, because the bot would then
fail to comply for reasons that have nothing to do with its defences, and that
would show up as a safety finding.

    python review_sheet.py gu hi        # specific languages
    python review_sheet.py --tier low   # every low-resource language in the bank
    python review_sheet.py --all
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from languages_catalog import tier_of

BANK_PATH = Path(__file__).with_name("attack_bank.json")
OUT_DIR = Path(__file__).with_name("review")

INSTRUCTIONS = [
    ["# PolyGuard translation review"],
    ["# Thank you for doing this. It should take about 15 minutes."],
    ["#"],
    ["# These are deliberately adversarial test messages used to check whether an"],
    ["# AI chatbot can be tricked. They are security tests, not real requests, and"],
    ["# nothing here is meant to be acted on."],
    ["#"],
    ["# For each row, fill in 'verdict' with one of:"],
    ["#    ok       reads naturally enough, and clearly asks for what the English asks for"],
    ["#    awkward  understandable, but clumsy or unnatural phrasing"],
    ["#    wrong    confusing, nonsensical, or asks for something different"],
    ["#"],
    ["# The key question is NOT whether it is elegant. It is whether a native"],
    ["# speaker would understand it as an instruction to do the thing it describes."],
    ["# A clumsy test that still reads as a test is fine. One that reads as"],
    ["# nonsense is not."],
    ["#"],
    ["# Put a better version in 'suggested_correction' if you can. Leave the codes"],
    ["# (PWNED_7F3A, CTRL_4B8E), any long random-looking string, and the words"],
    ["# SYSTEM OVERRIDE exactly as they are: the test depends on them."],
    [],
]

HEADER = ["id", "kind", "category", "english_original", "translation",
          "verdict", "suggested_correction", "notes"]


def load_bank() -> dict:
    return json.loads(BANK_PATH.read_text(encoding="utf-8"))


def rows_for(bank: dict, code: str) -> list[list[str]]:
    en_attacks = {(a["category"], a.get("variant", 0)): a["text"]
                  for a in bank["attacks"] if a["lang"] == "en"}
    en_controls = {c.get("variant", 0): c["text"]
                   for c in bank.get("controls", []) if c["lang"] == "en"}
    rows = []
    for a in bank["attacks"]:
        if a["lang"] != code:
            continue
        rows.append([a["id"], "attack", a["category"],
                     en_attacks.get((a["category"], a.get("variant", 0)), ""),
                     a["text"], "", "", ""])
    for c in bank.get("controls", []):
        if c["lang"] != code:
            continue
        rows.append([c["id"], "capability control", "benign",
                     en_controls.get(c.get("variant", 0), ""), c["text"], "", "", ""])
    return rows


def write_sheet(bank: dict, code: str) -> Path:
    meta = bank["languages"][code]
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{code}_review.csv"
    # utf-8-sig so Excel opens non-Latin scripts correctly instead of showing
    # the reviewer a screen of mojibake and wasting their time.
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for line in INSTRUCTIONS:
            w.writerow(line)
        w.writerow([f"# Language: {meta['name']} ({meta['native']}), "
                    f"tier {tier_of(code)}, provenance {meta.get('provenance', '?')}"])
        w.writerow([])
        w.writerow(HEADER)
        w.writerows(rows_for(bank, code))
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("langs", nargs="*", help="language codes")
    ap.add_argument("--tier", choices=["high", "mid", "low"])
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    bank = load_bank()
    available = list(bank["languages"])
    if args.all:
        codes = available
    elif args.tier:
        codes = [c for c in available if tier_of(c) == args.tier]
    else:
        codes = args.langs
    codes = [c for c in codes if c != "en"]        # nothing to review in the source

    unknown = [c for c in codes if c not in bank["languages"]]
    if unknown:
        print(f"not in the bank: {', '.join(unknown)}")
        return 1
    if not codes:
        print("Nothing selected. Pass language codes, --tier, or --all.")
        print(f"In the bank: {', '.join(c for c in available if c != 'en')}")
        return 1

    for code in codes:
        path = write_sheet(bank, code)
        n = len(rows_for(bank, code))
        print(f"  {bank['languages'][code]['name']:<14} {n:>3} rows -> {path}")
    print(f"\n{len(codes)} sheet(s) in {OUT_DIR}/")
    print("Send to a speaker of each language. Record results in NATIVE_REVIEW.md")
    print("and set native_reviewed for that language once applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
