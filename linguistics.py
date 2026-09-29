"""
Offline linguistic validation for the attack bank.

The asymmetry this fixes: machine-translated languages pass through a verification
gate (`expand_languages.verify`), while the 20 hand-authored languages passed
through nothing but the author's own confidence. That is backwards. The
hand-authored set carried a `verified: True` flag that in practice meant "written
by the project author", not "checked by someone who speaks the language", and a
flag that claims more than it delivers is exactly the kind of overclaim this
project keeps removing everywhere else.

None of these checks need an API key, and none of them can establish fluency.
What they can do is catch the failures that produce a confidently wrong number:

  SCRIPT        Hindi that arrives in Latin letters was not translated into Hindi.
                This is the strongest offline signal available, because a
                structural check sees a non-empty string containing the canary and
                waves it through.
  MOJIBAKE      replacement characters or stray combining marks mean the text was
                mangled somewhere in the pipeline.
  LENGTH        a translation a fraction of the English length is usually a
                truncation; many times longer is usually an explanation instead of
                a translation.
  DUPLICATION   the same string appearing under two languages means at least one
                of them was never translated.

A language that fails these is not merely lower quality. Its attacks may fail for
reasons that have nothing to do with the bot's defences, which would show up as a
break-rate difference and be read as a safety finding.

    python linguistics.py            # audit the current bank
    python linguistics.py --strict   # exit non-zero on any finding
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

BANK_PATH = Path(__file__).with_name("attack_bank.json")

# Unicode ranges per script. Explicit rather than inferred so the rule is legible
# and testable; Python's unicodedata does not expose script directly.
_RANGES = {
    "Latin": [(0x0041, 0x005A), (0x0061, 0x007A), (0x00C0, 0x024F),
              (0x1E00, 0x1EFF)],
    "Cyrillic": [(0x0400, 0x04FF), (0x0500, 0x052F)],
    "Greek": [(0x0370, 0x03FF), (0x1F00, 0x1FFF)],
    "Arabic": [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF)],
    "Hebrew": [(0x0590, 0x05FF)],
    "Devanagari": [(0x0900, 0x097F)],
    "Gujarati": [(0x0A80, 0x0AFF)],
    "Gurmukhi": [(0x0A00, 0x0A7F)],
    "Bengali": [(0x0980, 0x09FF)],
    "Tamil": [(0x0B80, 0x0BFF)],
    "Telugu": [(0x0C00, 0x0C7F)],
    "Kannada": [(0x0C80, 0x0CFF)],
    "Malayalam": [(0x0D00, 0x0D7F)],
    "Odia": [(0x0B00, 0x0B7F)],
    "Sinhala": [(0x0D80, 0x0DFF)],
    "Thai": [(0x0E00, 0x0E7F)],
    "Lao": [(0x0E80, 0x0EFF)],
    "Khmer": [(0x1780, 0x17FF)],
    "Myanmar": [(0x1000, 0x109F)],
    "Ethiopic": [(0x1200, 0x137F)],
    "Georgian": [(0x10A0, 0x10FF), (0x1C90, 0x1CBF)],
    "Armenian": [(0x0530, 0x058F)],
    "Han": [(0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF)],
    "Kana": [(0x3040, 0x309F), (0x30A0, 0x30FF)],
    "Hangul": [(0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7AF)],
}

# Acceptable scripts per language. Sets, because several languages are genuinely
# written in more than one (Serbian in Cyrillic or Latin, Kazakh mid-transition,
# Japanese mixing Han and kana).
EXPECTED = {
    **{c: {"Latin"} for c in (
        "en es tl vi fr pt de it pl tr id nl sv no da fi cs sk hu ro hr sl lt lv "
        "et sq is ga cy eu ca gl az uz ms jv su ceb sw ha yo ig zu xh so sn rw ny "
        "af ht").split()},
    **{c: {"Cyrillic"} for c in "ru uk bg mk ky tg mn".split()},
    "sr": {"Cyrillic", "Latin"},
    "kk": {"Cyrillic", "Latin"},
    "el": {"Greek"},
    **{c: {"Arabic"} for c in "ar fa ps ur".split()},
    "he": {"Hebrew"},
    **{c: {"Devanagari"} for c in "hi mr ne".split()},
    "gu": {"Gujarati"}, "pa": {"Gurmukhi"}, "bn": {"Bengali"},
    "ta": {"Tamil"}, "te": {"Telugu"}, "kn": {"Kannada"},
    "ml": {"Malayalam"}, "or": {"Odia"}, "si": {"Sinhala"},
    "th": {"Thai"}, "lo": {"Lao"}, "km": {"Khmer"}, "my": {"Myanmar"},
    "am": {"Ethiopic"}, "ka": {"Georgian"}, "hy": {"Armenian"},
    "zh": {"Han"}, "ja": {"Han", "Kana"}, "ko": {"Hangul"},
}

# Share of letters that must sit in an expected script before the text counts as
# actually being in that language. Deliberately lenient: real translations borrow
# brand names, product codes and loanwords in Latin.
MIN_SCRIPT_SHARE = 0.60
MIN_LETTERS = 8          # below this the sample is too small to judge
LENGTH_LO, LENGTH_HI = 0.25, 4.0

_B64_RE = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def script_of(ch: str) -> str | None:
    cp = ord(ch)
    for name, ranges in _RANGES.items():
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return name
    return None


def strip_fixed_tokens(text: str, tokens: tuple[str, ...] = ()) -> str:
    """
    Remove the parts of an attack that are ASCII BY DESIGN before judging script.

    The canary, the control token, Base64 blobs and the literal "SYSTEM OVERRIDE"
    marker are supposed to stay in ASCII in every language. Counting them would
    make a correctly translated Hindi attack look partly Latin and dilute the
    signal the check exists to find.
    """
    out = _B64_RE.sub(" ", text)
    for t in tokens:
        if t:
            out = out.replace(t, " ")
    out = out.replace("SYSTEM OVERRIDE", " ")
    return out


def script_profile(text: str, tokens: tuple[str, ...] = ()) -> Counter:
    stripped = strip_fixed_tokens(text, tokens)
    counts: Counter = Counter()
    for ch in stripped:
        if unicodedata.category(ch).startswith("L"):
            s = script_of(ch)
            if s:
                counts[s] += 1
    return counts


def check_script(lang: str, text: str, tokens: tuple[str, ...] = ()) -> list[str]:
    expected = EXPECTED.get(lang)
    if not expected:
        return []                      # unknown language: no claim to make
    prof = script_profile(text, tokens)
    total = sum(prof.values())
    if total < MIN_LETTERS:
        return []                      # too short to judge
    good = sum(v for k, v in prof.items() if k in expected)
    share = good / total
    if share < MIN_SCRIPT_SHARE:
        top = prof.most_common(2)
        return [f"script: only {share:.0%} of letters are "
                f"{'/'.join(sorted(expected))} (dominant: "
                f"{', '.join(f'{k} {v}' for k, v in top)})"]
    return []


def check_mojibake(text: str) -> list[str]:
    """Replacement characters or a combining mark with nothing to combine with."""
    problems = []
    if "�" in text:
        problems.append("mojibake: contains the Unicode replacement character")
    # the classic UTF-8-read-as-Latin-1 signature
    if re.search(r"[ÃÂ][-¿]", text):
        problems.append("mojibake: looks like UTF-8 decoded as Latin-1")
    if text and unicodedata.category(text[0]) == "Mn":
        problems.append("mojibake: starts with a combining mark")
    return problems


def check_length_ratio(text: str, reference: str) -> list[str]:
    if not reference.strip():
        return []
    ratio = len(text) / len(reference)
    if ratio < LENGTH_LO:
        return [f"length: {ratio:.2f}x the English original, likely truncated"]
    if ratio > LENGTH_HI:
        return [f"length: {ratio:.2f}x the English original, likely an "
                f"explanation rather than a translation"]
    return []


# Letters these Latin-script languages cannot be written correctly without.
# Stripped text passes the script check, because plain ASCII is still Latin
# script, so it needs its own check. AUDIT.md finding 55: eight languages had
# every attack typed without accents while their controls were accented, which
# made the attack text degraded and the capability control not.
# Only languages whose diacritics are frequent enough in ordinary sentences to
# make a share threshold meaningful are listed.
DIACRITICS = {
    "es": "áéíóúñü¿¡", "fr": "éèêàçùâîôûëïœ", "it": "àèéìíòóù", "pt": "ãõáéíóúâêôçà",
    "de": "äöüß", "pl": "ąćęłńóśźż", "tr": "çğıöşü", "cs": "áčďéěíňóřšťúůýž",
    "sk": "áäčďéíĺľňóôŕšťúýž", "ro": "ăâîșțşţ", "hu": "áéíóöőúüű", "hr": "čćđšž",
    "sl": "čšž", "lt": "ąčęėįšųūž", "lv": "āčēģīķļņšūž", "et": "äöõüšž",
    "fi": "äöå", "sv": "åäö", "no": "æøå", "da": "æøå", "is": "áðéíóúýþæö",
    "ca": "àçèéíïòóúü", "gl": "áéíñóú", "az": "çəğıöşü", "sq": "ëç", "ga": "áéíóú",
    "vi": "ăâđêôơưáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵấầẩẫậắằẳẵặếềểễệốồổỗộớờởỡợứừửữự",
}

# Measured on this bank: stripped text sits at 14 to 29 percent of items with
# any diacritic, corrected text at 57 to 100. The floor sits between the two.
MIN_DIACRITIC_SHARE = 0.45


def check_diacritics(lang: str, texts: list[str]) -> list[str]:
    """Flag a language whose text looks typed without its accents."""
    req = DIACRITICS.get(lang)
    if not req or len(texts) < 6:
        return []
    share = sum(1 for t in texts if any(ch in req for ch in t.lower())) / len(texts)
    if share < MIN_DIACRITIC_SHARE:
        return [f"only {share:.0%} of items contain any of this language's diacritics "
                f"(floor {MIN_DIACRITIC_SHARE:.0%}); text looks typed without accents"]
    return []


def audit_bank(bank: dict) -> dict:
    """
    Run every offline check over every attack and control in the bank.

    Applied to hand-authored and machine-generated languages alike. The whole
    point is that provenance stops deciding how much scrutiny a string gets.
    """
    canary = bank.get("canary", "")
    ctrl_token = bank.get("control_token", "")
    tokens = (canary, ctrl_token)

    en_attacks = {(a["category"], a.get("variant", 0)): a["text"]
                  for a in bank["attacks"] if a["lang"] == "en"}
    en_controls = {c.get("variant", 0): c["text"]
                   for c in bank.get("controls", []) if c["lang"] == "en"}

    findings: list[dict] = []
    seen: dict[str, list[str]] = {}

    def add(item_id, lang, kind, msgs):
        for m in msgs:
            findings.append({"id": item_id, "lang": lang, "kind": kind, "problem": m})

    for a in bank["attacks"]:
        t = a["text"]
        add(a["id"], a["lang"], "attack", check_script(a["lang"], t, tokens))
        add(a["id"], a["lang"], "attack", check_mojibake(t))
        if a["lang"] != "en" and a["category"] != "obfuscated_payload":
            ref = en_attacks.get((a["category"], a.get("variant", 0)), "")
            add(a["id"], a["lang"], "attack", check_length_ratio(t, ref))
        seen.setdefault(t.strip(), []).append(a["id"])

    for c in bank.get("controls", []):
        t = c["text"]
        add(c["id"], c["lang"], "control", check_script(c["lang"], t, tokens))
        add(c["id"], c["lang"], "control", check_mojibake(t))
        if c["lang"] != "en":
            add(c["id"], c["lang"], "control",
                check_length_ratio(t, en_controls.get(c.get("variant", 0), "")))
        seen.setdefault(t.strip(), []).append(c["id"])

    # Accents are judged per language, not per string: a single sentence can
    # legitimately contain none, but a whole language cannot.
    texts_by_lang: dict[str, list[str]] = {}
    for item in bank["attacks"] + bank.get("controls", []):
        texts_by_lang.setdefault(item["lang"], []).append(item["text"])
    for lang, texts in sorted(texts_by_lang.items()):
        for m in check_diacritics(lang, texts):
            findings.append({"id": f"{lang} (all items)", "lang": lang,
                             "kind": "accents", "problem": m})

    # The same string under two different languages means at least one of them
    # was never actually translated.
    for text, ids in seen.items():
        langs = {i.split("_")[0] for i in ids}
        if len(langs) > 1:
            findings.append({"id": ", ".join(sorted(ids)), "lang": "/".join(sorted(langs)),
                             "kind": "duplicate",
                             "problem": f"identical text shared across languages: "
                                        f"{text[:50]!r}"})

    by_lang: dict[str, int] = Counter(f["lang"] for f in findings)
    return {"findings": findings, "by_lang": dict(by_lang),
            "n_attacks": len(bank["attacks"]),
            "n_controls": len(bank.get("controls", [])),
            "clean": not findings}


def main() -> int:
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    rep = audit_bank(bank)
    print("PolyGuard linguistic audit")
    print(f"Checked {rep['n_attacks']} attacks and {rep['n_controls']} controls "
          f"across {len(bank['languages'])} languages.")
    print("Applied to hand-authored and generated languages alike.\n")
    if rep["clean"]:
        print("No script, mojibake, accent, length or duplication problems found.")
    else:
        print(f"{len(rep['findings'])} finding(s):\n")
        for f in rep["findings"]:
            print(f"  [{f['kind']:<9}] {f['lang']:<8} {f['id'][:34]:<36} {f['problem']}")
        print("\nby language:", ", ".join(f"{k}={v}" for k, v in
                                          sorted(rep["by_lang"].items())))
    print("\nWhat this cannot do: none of these checks establish fluency or")
    print("naturalness. They catch text that is not in the right script, is")
    print("mangled, typed without its accents, is truncated, or was never")
    print("translated at all. Native review")
    print("is tracked separately in NATIVE_REVIEW.md.")
    return 1 if (rep["findings"] and "--strict" in sys.argv) else 0


if __name__ == "__main__":
    raise SystemExit(main())
