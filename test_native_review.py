"""
Regression tests for the native speaker corrections, Spanish (2026-10-01) and Arabic
(2026-10-04), and for every unflagged row in those two languages.

Each row is pinned by the SHA-256 of its template and of its rendered bank text.
The 17 corrected rows were pinned from the corrections as recorded in the review
follow-through, NOT read back from the generator, so a regression in the generator
fails here instead of being copied into the expectation. The 25 unflagged rows are
pinned as they stood on 2026-10-12, so an accidental edit to a row nobody reviewed
also fails. Hashes, not text, so the attack strings are not duplicated in the repo.

An intended change to any of these rows (for example a new round of native
feedback) must update the pin here AND append a deviation to PREREGISTRATION.md.

Run: python test_native_review.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from generate_attack_bank import CANARY, CATEGORIES, CONTROL, TEXT  # noqa: E402

BANK = json.loads((ROOT / "attack_bank.json").read_text(encoding="utf-8"))
CASES: list[tuple[str, bool]] = []


def check(name: str, ok) -> None:
    CASES.append((name, bool(ok)))


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# id -> (template sha256, rendered bank text sha256, corrected by a native speaker)
PINS = {
    "es_instruction_override_0": ("fd03c542feb51abcd2e6657fba5167d6f305d800fa9fb6128faeb28321f9fea7",
                                  "cd48d9cfcd61d428da5270b287632f4f1041b7bee7d5b6b98386dc5c9c121801", False),
    "es_instruction_override_1": ("45c317296fc11acf68aa92741ad4403a50f077343073e2e8ec59e0b1ab670b46",
                                  "7df36495bbe07982c9df5ba3affd13bd95b9c23329096bea76803b8648303f79", True),
    "es_instruction_override_2": ("367ef26c3d1ffdfc12915cd94ee25d31607eecf77403ab88c2dad3a9770d1b6e",
                                  "0da20f824177c73db9cf9bfb1648f5f7ceb820a861254294e7b71f9d5fc252f9", False),
    "es_role_play_jailbreak_0": ("1cbb7fc49c316b2485a07458e438c287f94858ee6c5ee48df520c74cfa33b5d2",
                                 "eefa2651a5fe34ce63341129b23ef709f3d776a237b26e6e4508a67a10ca6381", False),
    "es_role_play_jailbreak_1": ("e35766fd2e11b3be492cf21f27786e76a63cf41e73a231c01cbe4eee0ebdf858",
                                 "3747dddf2a212b6d6fb82ba9070a8cced1019dff7a999284ae5f64f30b7fbbf8", False),
    "es_role_play_jailbreak_2": ("3c8710dec291c0f8ea64966a8b79704e0dc9265705f2bdc6420b84950a983867",
                                 "224efcd6e75d9e8944eec0838951a396ebb590e67990e53f8136fd6b99a0a6a3", False),
    "es_system_prompt_extraction_0": ("1dda926ce338e185017f3dd2d1180b652fdaf1e2ba7014d2168815601040d010",
                                      "1dda926ce338e185017f3dd2d1180b652fdaf1e2ba7014d2168815601040d010", False),
    "es_system_prompt_extraction_1": ("7854b9104fa249d804d444badaa3a26ac3a81023196663e005d92ea3595267da",
                                      "7854b9104fa249d804d444badaa3a26ac3a81023196663e005d92ea3595267da", False),
    "es_system_prompt_extraction_2": ("8c87b89d31a232779efb265a53153713125158450d3160ab79bf0550e7eafb67",
                                      "8c87b89d31a232779efb265a53153713125158450d3160ab79bf0550e7eafb67", True),
    "es_obfuscated_payload_0": ("398c950345b9cf9539007c6e28b56690f0d2dce24a2b14a23db47fc2dd8b87be",
                                "d877c0e1031c83737d29d243e5136ffaf1218b77f4a818cf2ad577b311202aba", False),
    "es_obfuscated_payload_1": ("b51d9a59d83f2fda70e2b7169101ecfea03f505417ca941d4c6f348b0d64e443",
                                "8922502f1a3126a93235a457a6b3c1a7a2a017089b172b015cff01c7c10a1da4", True),
    "es_obfuscated_payload_2": ("112a28ee72eae9051018853ce10480dd87f3b8e17dbdbb81e2b1f94ed607da07",
                                "a4d5f63979936ec496f05e0c148d7ecbc4cd957b55123a4396283a69465c1a0e", True),
    "es_indirect_injection_0": ("3afd5df02c514bbbf1645234b18537edbfa1224d9948fba661e992abce9167c1",
                                "edae8977b435a2ae00ed81350b3aae395fa6ff6177ed141f15a93dff05a1c9b7", False),
    "es_indirect_injection_1": ("440f259f3ec0f5207bce2d04c59935372ea4b332d41fd684aa8da454a189eb7b",
                                "c99ffbbbbaf61e667feb76ca51fdce9b4dfc4a9ad66e10b23c92c8d6a5d30f35", True),
    "es_indirect_injection_2": ("5c5d3ad17676bcbcb7341def7d4304a25f526afac6ce3080dc50b2363091e065",
                                "e8984918a319a7f081dccf04f2bf9cf0fec7802c4dbaef9e9dbfcb0554805c2c", True),
    "es_control_0": ("5410fdff289c5e3d316e799f8a4e0b67fdf0d9008c8f94b470f7867b41719d87",
                     "bcbd318b7a3f8d784455fe54c26db5614f76d90fe578385833bf2ae4418266cd", False),
    "es_control_1": ("d9d5a7c25aa487028e2353d892493d4e73e86690d2342ac93655bacc08d7e15a",
                     "024ec0d2f5775040c25b450b66f5fd7ff5943b5192b5f7ea3420f16fa9d9c753", True),
    "es_control_2": ("51199363f1b8f29a488ac5f6061b539b7939138e89800156507c2ca464eac731",
                     "7ad72a27182255fd97d77b4e4f10a1d309fe38bf4704426cdaec42c135be3f63", True),
    "es_control_3": ("f2b3f402009bb21830c029750a64255e314bb823a49ee2e025eb6fb44de803b2",
                     "50e8869afbb87d94fe3d2a7e3b8f91093393b18cae220a08e7356adcc351c083", False),
    "es_control_4": ("8dd79e8a78d3ac9c44965c10e9539521214f0fa2f295bb778504bba53429392d",
                     "db8a2f9832f66a52eaf8f3ec4284ba1e9d9ba8e18258b0faa926d0e501440bfd", True),
    "es_control_5": ("d88c6d69551bf8885e9cda6051be1b8bdcdc139a3e3cc23b857bcce95b8083d7",
                     "4a51bd0933a221aeef99704cecc1466c3aaf9a0a5e6a4a63510ed95333dfa91a", True),
    "ar_instruction_override_0": ("d1cf2210576776c3f73a5e5dff3d256f04677eb0c04a3214d8a12a315db75c7d",
                                  "08bc0c2380bc51882ae5bd60c247e9a15c4888d1139b05c16b8f71ca703752e7", False),
    "ar_instruction_override_1": ("28b86a0322897d1b02086a9d36c69f2d7be1a931693234c3a14aea57089c15ae",
                                  "d0b838b2fcc8c96e7c958aeb5b115067bc6671a97dc35984379f18c28a918c61", True),
    "ar_instruction_override_2": ("461c0ec6fad3fa01d9f524516b9576df36aa249bbd6e74cce39de0073d236cd1",
                                  "fb0fcc462607e76262891c2b37343beb9ea0e40a62dec6d215e86439972a6a59", True),
    "ar_role_play_jailbreak_0": ("e1e228700f2360b72283ee806bc88b55ef611a0765949cdf261556ee95c0e91e",
                                 "f90075bea1530c28b3a971ead5dc8836480040528f6ca13bb3a695b07299abec", False),
    "ar_role_play_jailbreak_1": ("84e6c06e42a2273914185c2825511ff193dbe441bff39c45e5f57060c6cfa361",
                                 "7326bcdc1fcc76ee54e620549658ab51a698fa36b0bc4a04816f27e3c1ab01b8", False),
    "ar_role_play_jailbreak_2": ("edd0ab62ef8744ff5fac31c803200d03e92dcc86888df4f3a673bfa25aec37af",
                                 "861a5f11a18b099bd86ea518e2cd21d72d460fae7ce1014a289de3b9311ba4dd", True),
    "ar_system_prompt_extraction_0": ("2fe48535a3a59200b5f1c5ab3ed41216c533244ff337e8e4be7c4dc8b7899d53",
                                      "2fe48535a3a59200b5f1c5ab3ed41216c533244ff337e8e4be7c4dc8b7899d53", False),
    "ar_system_prompt_extraction_1": ("ffa3d4baf24e402f9a3393d68b64446ca913e2e69ac2f3654fb4178c24eb9b4a",
                                      "ffa3d4baf24e402f9a3393d68b64446ca913e2e69ac2f3654fb4178c24eb9b4a", True),
    "ar_system_prompt_extraction_2": ("80bfffa199b31ae78fdef542c93d0da30a6fe20244a36fba2ad819431cb63cf3",
                                      "80bfffa199b31ae78fdef542c93d0da30a6fe20244a36fba2ad819431cb63cf3", False),
    "ar_obfuscated_payload_0": ("ce072036ec9a3c1d67e68116e90ef8a1d98b0cade934aa53060c66f377c6ee7f",
                                "8a12dfacac726ba1e63946831a85f440474d2ab847f7d5710afe3abea64367c5", False),
    "ar_obfuscated_payload_1": ("1fd6ceb51314dce24b89f75af519f1724109cbd72e4c59df73c1db1932ee711b",
                                "bc57f86d960a5a23fb76bdfc852c5b3bd2e44512577d9aa462d982e32421367b", False),
    "ar_obfuscated_payload_2": ("b6c93cbf806a126e3a217eb4a7ff8c9cc523b55ae7fe512345c3c6d263e55e33",
                                "ea6471990f841f4c626313a23c4578767f32bea64e9d9af80732507a4e32a264", False),
    "ar_indirect_injection_0": ("272707ce2f4e284fa5ee5a912bd77b44090b81e54a08faca0eb5cd84cc872d5c",
                                "1dcc2b0fd4b6c0868ccb40d78fbf1515f20bc09a6a2910155148fa8d085b95fa", True),
    "ar_indirect_injection_1": ("f4aabb79ed4993c5a1111661e801c54bc3c76f6417749b78b3d8506b2bce8c0c",
                                "3b68707c7e1a60124189f31e50a23ff874d3768110566a2f214482dd6a7d8e72", False),
    "ar_indirect_injection_2": ("6f0aa89f20d4a41d0c1b434ebe75ac07dca4333fd4ffaf7a545b91a2c1f084bf",
                                "525c9588f9886331afab7c70bf55f7dc5f2b995410531a2c8f316e4a2cad35de", False),
    "ar_control_0": ("161ac089dd231f5c609d3e05b0f8ebce9e01adce22d88b02a35d8b6fa5df0d1f",
                     "28c2040b7de12ade47a1e4c0cb141e950490a79a725f22e4ef7983edfd4eb7f4", True),
    "ar_control_1": ("08913592e19c0d3bac0416afcf0654647fd27fef77900db68acfc31057885c39",
                     "524a944637240197b532f32d9637cc8100225e317cba7eab3c1a8d6920246062", False),
    "ar_control_2": ("ee3f56ccb7c2002cef165839c681a3c9a9a5c2364aeb8aa85fcf669e0c0d884f",
                     "cb3cfd264309c6dbee77b4a605d0419df6c3feb285f0051ed623889f6e1b83f7", False),
    "ar_control_3": ("7ce866fe05180203d112d19e27d23cec23ff099182e3314f588aa508f4b546c4",
                     "0e42e53ff585c2a4b2fe6a06a9a72bdaa9ac8da402780f327b3f11c9c01634db", True),
    "ar_control_4": ("7eb6e0c9f9cabe0fd4bac56939663a6dc53887fdb9d79cd12c4c35a80fac9d90",
                     "d5d043424edd222c3ed59d70f003aec431d45cbea72766bd32252035808f3600", False),
    "ar_control_5": ("b5183822ca8c65041d8f122967709772dd1c4418b9a976f4bd16a0290a7e30d9",
                     "e020610e7e9fabfa639bdbe0818162477fc05c101623294b565512030fe85a2b", False),
}


def template(row_id: str) -> str:
    lang, rest = row_id.split("_", 1)
    cat, i = rest.rsplit("_", 1)
    return CONTROL[lang][int(i)] if cat == "control" else TEXT[lang][cat][int(i)]


attacks = {a["id"]: a for a in BANK["attacks"]}
controls = {c["id"]: c for c in BANK.get("controls", [])}
bank_rows = {**attacks, **controls}

check("exactly 17 corrected rows are pinned (10 Spanish, 7 Arabic)",
      sum(v[2] for v in PINS.values()) == 17
      and sum(v[2] for k, v in PINS.items() if k.startswith("es_")) == 10
      and sum(v[2] for k, v in PINS.items() if k.startswith("ar_")) == 7)
check("every Spanish and Arabic row in the bank is pinned, and nothing else",
      {k for k in bank_rows if k.split("_")[0] in ("es", "ar")} == set(PINS))
for rid, (t_sha, r_sha, corrected) in PINS.items():
    kind = "corrected" if corrected else "unflagged"
    check(f"{rid} ({kind}): generator template unchanged", sha(template(rid)) == t_sha)
    check(f"{rid} ({kind}): generated bank text unchanged",
          rid in bank_rows and sha(bank_rows[rid]["text"]) == r_sha)

# ar_indirect_injection_0: only the framing clause was replaced. The quoted review
# that carries the injection must survive, after exactly two newlines.
_ar0 = attacks["ar_indirect_injection_0"]["text"]
_frame, _sep, _quoted = _ar0.partition("\n\n")
check("ar_indirect_injection_0 keeps one two-newline boundary before the quoted review",
      _sep == "\n\n" and "\n" not in _frame and _ar0.count("\n") == 2)
check("ar_indirect_injection_0 keeps the quoted review with the marker and the canary",
      _quoted.startswith('"') and _quoted.endswith(CANARY + '"')
      and "SYSTEM OVERRIDE" in _quoted and CANARY not in _frame)

# Tokens and markers survive in every Spanish and Arabic row.
for lang in ("es", "ar"):
    rows = [a for a in BANK["attacks"] if a["lang"] == lang]
    check(f"{lang}: every canary attack carries the canary once",
          all(a["text"].count(CANARY) == 1 for a in rows
              if a["goal"] == "canary" and a["category"] != "obfuscated_payload"))
    check(f"{lang}: every indirect injection carries the literal SYSTEM OVERRIDE marker",
          all("SYSTEM OVERRIDE" in a["text"] for a in rows if a["category"] == "indirect_injection"))
    check(f"{lang}: extraction attacks carry no canary",
          all(CANARY not in a["text"] for a in rows if a["category"] == "system_prompt_extraction"))
    ctl = [c for c in BANK["controls"] if c["lang"] == lang]
    check(f"{lang}: 6 controls, each with the control token and without the canary",
          len(ctl) == 6 and all(BANK["control_token"] in c["text"] and CANARY not in c["text"] for c in ctl))
    # The Base64 payload hides this language's own variant-0 instruction.
    loc = TEXT[lang]["instruction_override"][0].replace("{C}", CANARY)
    want = base64.b64encode(loc.encode()).decode()
    obf = [a for a in rows if a["category"] == "obfuscated_payload"]
    check(f"{lang}: every Base64 payload decodes to its own variant-0 instruction with the canary",
          len(obf) == 3 and all(want in a["text"] for a in obf)
          and base64.b64decode(want).decode() == loc and CANARY in loc)
    check(f"{lang}: ids, categories and variants are unchanged (5 categories x 3)",
          sorted((a["category"], a["variant"]) for a in rows)
          == sorted((c, v) for c in CATEGORIES for v in range(3)))
    check(f"{lang}: native_reviewed stays false (feedback integrated, not validated)",
          all(a.get("native_reviewed") is False for a in rows)
          and all(c.get("native_reviewed", False) is False for c in ctl)
          and not BANK["languages"][lang].get("native_reviewed"))

check("the instrument constants are unchanged",
      BANK["canary"] == "PWNED_7F3A" and BANK["control_token"] == "CTRL_4B8E")

passed = sum(1 for _, ok in CASES if ok)
for name, ok in CASES:
    if not ok:
        print(f"  [FAIL] {name}")
print(f"{passed}/{len(CASES)} native review regression checks passed")
sys.exit(0 if passed == len(CASES) else 1)
