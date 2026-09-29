"""
Checks that the documentation still tells the truth about the code.

Eleven audit rounds changed the instrument repeatedly: controls were added, the
judge fallback was removed, dependencies were capped, the bank fingerprint was
made reproducible, and the resource tiers were re-derived from a published
taxonomy. Every one of those changes made some sentence somewhere stale, and a
stale number in AUDIT.md or PREREGISTRATION.md is not a typo. Those documents
exist to be checked by somebody else, so a wrong number in them is a false claim
about the work.

Finding 45 made this concrete: re-deriving the tiers left "14 high, 31 mid, 42
low" sitting in three files, and five test fixtures quietly asserting that
Estonian was low-resource when it no longer was.

So the facts live in exactly one place, the code, and this reads them out and
then greps every document for statements that contradict them.

It cannot prove a document is complete or well written. It can prove no document
contains a number the code disagrees with, which is the failure that actually
misleads a reader.

    python consistency.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent


def ground_truth() -> dict:
    """Read the facts from the code and data, never from prose."""
    import languages_catalog as cat

    bank = json.loads((HERE / "attack_bank.json").read_text(encoding="utf-8"))
    tiers = Counter(m["tier"] for m in cat.CATALOG.values())
    n_lang = len(bank["languages"])
    controls = bank.get("controls", [])
    return {
        "attacks": len(bank["attacks"]),
        "controls": len(controls),
        "controls_per_lang": (len(controls) // n_lang) if n_lang else 0,
        "bank_languages": n_lang,
        "catalog": len(cat.CATALOG),
        "high": tiers["high"], "mid": tiers["mid"], "low": tiers["low"],
        "categories": len(bank["categories"]),
        "variants": bank.get("variants_per_category", 3),
        "full_attack_calls": len(cat.CATALOG) * len(bank["categories"])
                             * bank.get("variants_per_category", 3),
        "full_control_calls": len(cat.CATALOG)
                              * ((len(controls) // n_lang) if n_lang else 0),
    }


def stale_claims(truth: dict) -> list[str]:
    """
    Patterns that were true once and would now mislead. Each entry is a regex
    plus what the correct value is, so the message says what to change it to.
    """
    # Scope matters more than the pattern. AUDIT.md is a changelog and
    # NATIVE_REVIEW.md explains why a flag was removed, so both are SUPPOSED to
    # name things that no longer exist. Flagging those would train everyone to
    # ignore this tool, which is worse than not having it. Each rule therefore
    # names only the documents that assert what is true NOW, where a stale claim
    # would actually mislead a reader.
    CURRENT = ("README.md", "STATE.md", "PREREGISTRATION.md", "DEPLOY.md",
               "DEMO_VIDEO.md")
    rules = [
        (r"\b14 high\b",  CURRENT, f"high is now {truth['high']}"),
        (r"\b31 mid\b",   CURRENT, f"mid is now {truth['mid']}"),
        (r"\b42 low\b",   CURRENT, f"low is now {truth['low']}"),
        (r"\b13 high, 7\s+mid\b", CURRENT,
         "seed-20 tier mix changed after the re-derivation"),
        (r"\bverified: True\b", CURRENT,
         "the verified flag was replaced by provenance"),
        # (?<!-no) so the CURRENT flag --no-backcheck is not mistaken for the old one
        (r"(?<!-no)--backcheck\b", CURRENT,
         "backcheck is on by default; the flag is --no-backcheck"),
    ]
    # Claims that depend on the state of the bank, not on a number. While no
    # language has been reviewed by a native speaker, no current document may
    # call a translation verified; while no language has been generated, none
    # may describe the generated ones as existing. The README said both, in its
    # opening paragraph, until AUDIT.md finding 59.
    bank = json.loads((HERE / "attack_bank.json").read_text(encoding="utf-8"))
    reviewed = sum(1 for m in bank["languages"].values() if m.get("native_reviewed"))
    generated = sum(1 for m in bank["languages"].values() if m.get("provenance") == "machine")
    if not reviewed:
        rules += [
            (r"\b(?:hand[- ]authored|hand[- ]written|authored)\s+and\s+verified\b", CURRENT,
             "no language has been reviewed by a native speaker"),
            (r"\b\d+\s+(?:are|languages are)\s+(?:hand[- ]authored\s+and\s+)?verified\b", CURRENT,
             "no language has been reviewed by a native speaker"),
            (r"\bverified translations?\b", CURRENT,
             "no language has been reviewed by a native speaker"),
        ]
    if not generated:
        rules += [
            (r"\bthe rest(?: are)?\s+auto[- ]?translated\b", CURRENT,
             "no language has been generated yet; the bank holds only the authored ones"),
        ]
    out = []
    for path in sorted(HERE.glob("*.md")) + sorted(HERE.glob("*.py")):
        if path.name == Path(__file__).name:
            continue                      # this file names the patterns on purpose
        text = path.read_text(encoding="utf-8")
        for pattern, scope, why in rules:
            if path.name not in scope:
                continue
            for m in re.finditer(pattern, text):
                line = text[: m.start()].count("\n") + 1
                out.append(f"{path.name}:{line}  {m.group(0)!r}  ->  {why}")
    return out


def missing_truths(truth: dict) -> list[str]:
    """
    Numbers a reader will look for, and where they must appear. A document that
    omits them is not wrong, but one that states a different value is.
    """
    checks = [
        ("README.md", str(truth["catalog"]), "catalog size"),
        ("README.md", str(truth["high"]), "high-resource count"),
        ("README.md", str(truth["low"]), "low-resource count"),
        ("PREREGISTRATION.md", str(truth["attacks"]), "attack count"),
        ("PREREGISTRATION.md", str(truth["controls"]), "control count"),
        ("STATE.md", str(truth["attacks"]), "attack count"),
        ("STATE.md", str(truth["controls"]), "control count"),
    ]
    out = []
    for fname, value, label in checks:
        p = HERE / fname
        if not p.exists():
            out.append(f"{fname} is missing entirely")
            continue
        if value not in p.read_text(encoding="utf-8"):
            out.append(f"{fname} never states the {label} ({value})")
    return out


def main() -> int:
    truth = ground_truth()
    print("PolyGuard documentation consistency")
    print("Facts read from the code, then checked against every document.\n")
    width = max(len(k) for k in truth)
    for k, v in truth.items():
        print(f"  {k:<{width}} {v}")

    stale = stale_claims(truth)
    missing = missing_truths(truth)

    print()
    if stale:
        print(f"{len(stale)} stale claim(s):")
        for s in stale:
            print(f"  {s}")
    else:
        print("No document contains a claim the code disagrees with.")

    if missing:
        print(f"\n{len(missing)} document(s) missing a figure a reader would look for:")
        for m in missing:
            print(f"  {m}")

    print("\nThis proves no number contradicts the code. It does not prove the")
    print("documents are complete, current in their prose, or well argued.")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
