"""
Validate attack_bank.json. Run after generating or expanding the bank.

Checks every attack for the things that, if wrong, would silently corrupt results:
no leftover template placeholders, the canary present (or decodable) where required,
the SYSTEM OVERRIDE marker in indirect attacks, no field left untranslated, and that
the variants inside each (language, category) cell are actually distinct — duplicate
variants would fake statistical depth that isn't there.

    python validate_bank.py            # exits non-zero if anything is wrong
"""
import base64
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from generate_attack_bank import CANARY, CATEGORIES, GOAL, TEXT

BANK = json.loads(Path(__file__).with_name("attack_bank.json").read_text(encoding="utf-8"))
B64_RE = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
EN = {c: [v.replace("{C}", CANARY) for v in TEXT["en"][c]] for c in CATEGORIES}


def decodes_to_canary(text):
    for tok in B64_RE.findall(text):
        try:
            if CANARY in base64.b64decode(tok + "===").decode("utf-8", "ignore"):
                return True
        except Exception:
            pass
    return False


def main():
    problems = []
    langs = BANK["languages"]
    attacks = BANK["attacks"]

    # ---- bank level ----
    if BANK.get("canary") != CANARY:
        problems.append("bank canary mismatch")
    ids = [a["id"] for a in attacks]
    if len(ids) != len(set(ids)):
        problems.append("duplicate attack ids")
    for code, m in langs.items():
        for k in ("name", "native", "provenance", "native_reviewed"):
            if k not in m:
                problems.append(f"language {code} missing '{k}'")

    # ---- attack level ----
    cells = defaultdict(list)
    for a in attacks:
        aid, cat, text, lang = a["id"], a["category"], a["text"], a["lang"]
        cells[(lang, cat)].append(text)

        if cat not in CATEGORIES:
            problems.append(f"{aid}: unknown category")
            continue
        if "{C}" in text or "{B64}" in text:
            problems.append(f"{aid}: leftover template placeholder")
        if not text.strip():
            problems.append(f"{aid}: empty text")
        if a["goal"] != GOAL[cat]:
            problems.append(f"{aid}: goal mismatch")
        if "variant" not in a:
            problems.append(f"{aid}: missing variant index")

        if cat == "obfuscated_payload":
            if not decodes_to_canary(text):
                problems.append(f"{aid}: Base64 does not decode to the canary")
        elif GOAL[cat] == "canary" and CANARY not in text:
            problems.append(f"{aid}: canary missing")
        if cat == "indirect_injection" and "SYSTEM OVERRIDE" not in text:
            problems.append(f"{aid}: SYSTEM OVERRIDE marker missing")

        # untranslated: identical to the matching English variant
        if lang != "en" and cat != "obfuscated_payload":
            vi = a.get("variant", 0)
            if vi < len(EN[cat]) and text.strip() == EN[cat][vi].strip():
                problems.append(f"{aid}: identical to English (untranslated?)")

    # ---- cell level: variants must be distinct and deep enough ----
    for (lang, cat), texts in cells.items():
        if len(texts) < 2:
            problems.append(f"{lang}/{cat}: only {len(texts)} variant(s), needs >= 2")
        if len({t.strip() for t in texts}) != len(texts):
            problems.append(f"{lang}/{cat}: duplicate variants (fake depth)")

    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for p in problems[:40]:
            print("  -", p)
        sys.exit(1)

    depth = len(attacks) / max(len(cells), 1)
    print(f"OK: {len(attacks)} attacks across {len(langs)} languages, "
          f"{len(cells)} cells, avg {depth:.1f} variants/cell. All valid.")


if __name__ == "__main__":
    main()
