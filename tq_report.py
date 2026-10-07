"""
Automated translation quality proxy for every language in the attack bank.

53 of the 73 bank languages were machine translated and none has been read by a
native speaker. A garbled attack can fail for reasons that have nothing to do with
the bot's defences, so translation quality is the main confound in any per-language
break rate. This file reports two cheap, offline signals per language. They catch
gross failures. They do NOT validate a translation, and nothing here may be
described as validation, verification or a human check.

  LID   GlotLID v3 (fastText) reads each attack and control, with the canary, the
        control token, Base64 blobs and the English SYSTEM OVERRIDE marker stripped
        first (linguistics.strip_fixed_tokens). Share of strings identified as the
        intended language, strictly and with declared close relatives.
  SIM   LaBSE cosine similarity between each translated string and the English seed
        it was made from, against a wrong pair baseline (the same string against
        seeds from a different category). The threshold is the 99th percentile of
        the pooled wrong pairs, so it is set from data, not guessed.

The rules were fixed before any score was computed; see
docs/progress/translation-quality.md.

Reading the report needs only the standard library. It reads the committed
translation_quality.json:

    python tq_report.py              # per-language table, weakest first
    python tq_report.py --check      # exit 1 if a bank language is missing or stale
    python tq_report.py --flagged    # only the flagged languages

Regenerating the JSON needs the heavy models, which are never committed (about
3.6 GB, see the JSON for revisions and SHA-256):

    python tq_report.py --build --glotlid PATH/model_v3.bin --labse PATH/labse_dir
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
TQ_PATH = HERE / "translation_quality.json"
BANK_PATH = HERE / "attack_bank.json"

SCHEMA = 1

# The GlotLID labels that count as the intended language, in the script the bank
# uses. Hindi in Latin letters is not Hindi for this purpose: linguistics.py already
# treats that as a failed translation. Covers the whole catalog so a new language
# needs no edit here.
GLOTLID_LABELS: dict[str, tuple[str, ...]] = {
    "en": ("eng_Latn",), "es": ("spa_Latn",), "hi": ("hin_Deva",),
    "gu": ("guj_Gujr",), "zh": ("cmn_Hani",), "tl": ("fil_Latn",),
    "vi": ("vie_Latn",), "ar": ("arb_Arab",), "ko": ("kor_Hang",),
    "fr": ("fra_Latn",), "ru": ("rus_Cyrl",), "pt": ("por_Latn",),
    "de": ("deu_Latn",), "it": ("ita_Latn",), "ja": ("jpn_Jpan",),
    "pl": ("pol_Latn",), "tr": ("tur_Latn",), "id": ("ind_Latn",),
    "uk": ("ukr_Cyrl",), "el": ("ell_Grek",), "nl": ("nld_Latn",),
    "sv": ("swe_Latn",), "no": ("nob_Latn", "nno_Latn"), "da": ("dan_Latn",),
    "fi": ("fin_Latn",), "cs": ("ces_Latn",), "sk": ("slk_Latn",),
    "hu": ("hun_Latn",), "ro": ("ron_Latn",), "bg": ("bul_Cyrl",),
    "hr": ("hrv_Latn",), "sr": ("srp_Cyrl", "srp_Latn"), "sl": ("slv_Latn",),
    "lt": ("lit_Latn",), "lv": ("lvs_Latn",), "et": ("ekk_Latn",),
    "mk": ("mkd_Cyrl",), "sq": ("als_Latn",), "is": ("isl_Latn",),
    "ga": ("gle_Latn",), "cy": ("cym_Latn",), "eu": ("eus_Latn",),
    "ca": ("cat_Latn",), "gl": ("glg_Latn",), "he": ("heb_Hebr",),
    "fa": ("fas_Arab",), "ps": ("pbt_Arab",), "az": ("azj_Latn",),
    "kk": ("kaz_Cyrl",), "uz": ("uzn_Latn",), "ky": ("kir_Cyrl",),
    "tg": ("tgk_Cyrl",), "mn": ("khk_Cyrl",), "ka": ("kat_Geor",),
    "hy": ("hye_Armn",), "bn": ("ben_Beng",), "ur": ("urd_Arab",),
    "pa": ("pan_Guru",), "ta": ("tam_Taml",), "te": ("tel_Telu",),
    "mr": ("mar_Deva",), "kn": ("kan_Knda",), "ml": ("mal_Mlym",),
    "or": ("ory_Orya",), "ne": ("npi_Deva",), "si": ("sin_Sinh",),
    "th": ("tha_Thai",), "ms": ("zsm_Latn",), "km": ("khm_Khmr",),
    "lo": ("lao_Laoo",), "my": ("mya_Mymr",), "jv": ("jav_Latn",),
    "su": ("sun_Latn",), "ceb": ("ceb_Latn",), "sw": ("swh_Latn",),
    "am": ("amh_Ethi",), "ha": ("hau_Latn",), "yo": ("yor_Latn",),
    "ig": ("ibo_Latn",), "zu": ("zul_Latn",), "xh": ("xho_Latn",),
    "so": ("som_Latn",), "sn": ("sna_Latn",), "rw": ("kin_Latn",),
    "ny": ("nya_Latn",), "af": ("afr_Latn",), "ht": ("hat_Latn",),
}

# Close relatives that a language identifier confuses on short text, declared before
# scoring. A string identified as one of these is a near-neighbour confusion, which
# is reported, not a wrong-language failure. Mostly the pairs where GlotLID's own
# test F1 is lowest (Croatian 0.76, Indonesian 0.83).
CLOSE: dict[str, tuple[str, ...]] = {
    "hr": ("bos_Latn", "srp_Latn", "cnr_Latn"),
    "sr": ("hrv_Latn", "bos_Latn", "cnr_Latn"),
    "ms": ("ind_Latn",), "id": ("zsm_Latn",),
    "no": ("dan_Latn", "swe_Latn"), "da": ("nob_Latn", "nno_Latn"),
    "sv": ("nob_Latn", "nno_Latn", "dan_Latn"),
    "gl": ("por_Latn",), "pt": ("glg_Latn",),
    "cs": ("slk_Latn",), "sk": ("ces_Latn",),
    "bg": ("mkd_Cyrl",), "mk": ("bul_Cyrl",),
    "af": ("nld_Latn",), "nl": ("afr_Latn",),
    "zh": ("yue_Hani", "lzh_Hani"),
    "xh": ("zul_Latn",), "zu": ("xho_Latn",),
}

# Pre-declared flag rules (docs/progress/translation-quality.md).
LID_MIN = 0.80              # flag "lid" below this share, close relatives counted
SIM_PERCENTILE = 99         # threshold T = this percentile of pooled wrong pairs
SIM_MAX_AT_OR_BELOW = 1     # flag "sim" when MORE than this many strings sit at or below T
RETRIEVAL_MIN = 0.90        # flag "sim" when group retrieval accuracy is below this

PROXY_LABEL = "automated proxy, not a validation"


# --------------------------------------------------------------------------- #
# Reading (standard library only)
# --------------------------------------------------------------------------- #
def load(path: Path = TQ_PATH) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


_CACHE: dict = {}


def _cached() -> dict | None:
    if "data" not in _CACHE:
        _CACHE["data"] = load()
    return _CACHE["data"]


def lang_quality(code: str, data: dict | None = None) -> dict | None:
    """
    A compact per-language summary for display next to a break rate, or None when
    there is no score. Always carries the proxy label, so a consumer cannot show the
    numbers without it.
    """
    data = data if data is not None else _cached()
    entry = ((data or {}).get("languages") or {}).get(code)
    if not entry:
        return None
    lid, sim = entry.get("lid") or {}, entry.get("sim") or {}
    return {"label": PROXY_LABEL,
            "lid_share": lid.get("share"), "lid_share_close": lid.get("share_close"),
            "sim_mean": sim.get("mean"), "sim_margin": sim.get("margin"),
            "flags": list(entry.get("flags") or []),
            "notes": list(entry.get("notes") or []),
            "summary": short(entry)}


def short(entry: dict) -> str:
    """One line: 'LID 100%, LaBSE 0.86 (+0.62 over wrong pairs)' plus any flag."""
    lid, sim = entry.get("lid") or {}, entry.get("sim") or {}
    bits = []
    if lid.get("share") is not None:
        bits.append(f"LID {lid['share']:.0%}")
    if sim.get("mean") is not None:
        bits.append(f"LaBSE {sim['mean']:.2f} ({sim['margin']:+.2f} over wrong pairs)")
    text = ", ".join(bits) or "no score"
    if entry.get("flags"):
        text += " [flagged: " + ", ".join(entry["flags"]) + "]"
    return text


def machine_codes(bank: dict) -> list[str]:
    return sorted(c for c, m in bank["languages"].items()
                  if m.get("provenance") == "machine")


def text_sha256(bank: dict, code: str) -> str:
    """Fingerprint of one language's attack and control texts, in id order."""
    rows = sorted([*(a for a in bank["attacks"] if a["lang"] == code),
                   *(c for c in bank["controls"] if c["lang"] == code)],
                  key=lambda r: r["id"])
    h = hashlib.sha256()
    for r in rows:
        h.update(r["id"].encode("utf-8") + b"\x00" + r["text"].encode("utf-8") + b"\x00")
    return h.hexdigest()


def coverage(data: dict | None, bank: dict) -> dict:
    """Which bank languages lack a score, and which scores are for older text."""
    langs = (data or {}).get("languages") or {}
    missing = [c for c in bank["languages"] if c not in langs]
    stale = [c for c in bank["languages"]
             if c in langs and langs[c].get("text_sha256") != text_sha256(bank, c)]
    machine_missing = [c for c in machine_codes(bank) if c not in langs]
    return {"missing": missing, "stale": stale, "machine_missing": machine_missing}


def _order_key(item):
    code, e = item
    lid, sim = e.get("lid") or {}, e.get("sim") or {}
    return (-len(e.get("flags") or []), sim.get("margin", 9) if sim.get("margin") is not None
            else 9, lid.get("share", 1), code)


def print_report(data: dict, bank: dict, flagged_only: bool = False) -> None:
    langs = data["languages"]
    th = data.get("threshold") or {}
    print(f"Translation quality ({PROXY_LABEL}), generated {data.get('generated_on')}")
    print(f"  models: " + "; ".join(f"{m['repo']}@{m['revision'][:8]}"
                                     for m in data["models"].values()))
    if th.get("sim_T") is not None:
        print(f"  LaBSE threshold T = {th['sim_T']:.3f} (p{SIM_PERCENTILE} of "
              f"{th['wrong_pairs_n']} wrong pairs; correct pairs median "
              f"{th['correct_pairs_p50']:.3f})")
    print(f"\n{'code':<5}{'language':<16}{'src':<8}{'LID':>5}{'+close':>8}"
          f"{'LaBSE':>7}{'wrong':>7}{'margin':>8}{'retr':>6}{'<=T':>5}  flags")
    for code, e in sorted(langs.items(), key=_order_key):
        if flagged_only and not e.get("flags"):
            continue
        lid, sim = e.get("lid") or {}, e.get("sim") or {}
        f = lambda v, p="{:.2f}": "-" if v is None else p.format(v)
        print(f"{code:<5}{e.get('name', code)[:15]:<16}{e.get('provenance', '?'):<8}"
              f"{f(lid.get('share'), '{:.0%}'):>5}{f(lid.get('share_close'), '{:.0%}'):>8}"
              f"{f(sim.get('mean')):>7}{f(sim.get('mean_wrong')):>7}"
              f"{f(sim.get('margin'), '{:+.2f}'):>8}{f(sim.get('retrieval'), '{:.0%}'):>6}"
              f"{f(sim.get('n_at_or_below_T'), '{}'):>5}  "
              f"{', '.join(e.get('flags') or []) or ''}"
              f"{(' (' + ', '.join(e['notes']) + ')') if e.get('notes') else ''}")
    s = data.get("summary") or {}
    print(f"\nFlagged: {', '.join(s.get('flagged') or []) or 'none'}")
    cov = coverage(data, bank)
    if cov["missing"] or cov["stale"]:
        print(f"Missing: {', '.join(cov['missing']) or 'none'}; "
              f"stale (text changed since scoring): {', '.join(cov['stale']) or 'none'}")
    print("A flag means look here first. No flag means no gross failure was found, "
          "not that the translation is good.")


# --------------------------------------------------------------------------- #
# Building (needs fasttext, sentence-transformers and the model files)
# --------------------------------------------------------------------------- #
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _prepare(text: str, bank: dict) -> str:
    import linguistics
    out = linguistics.strip_fixed_tokens(text, (bank["canary"], bank["control_token"]))
    return " ".join(out.split())


def _percentile(xs: list[float], p: float) -> float:
    """Linear interpolation between closest ranks (numpy's default method)."""
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def build(glotlid: Path, labse: Path, out_path: Path = TQ_PATH) -> dict:
    import platform

    import fasttext
    import numpy as np
    import sentence_transformers
    import torch
    import transformers
    from sentence_transformers import SentenceTransformer

    import engine
    from languages_catalog import tier_of

    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    codes = list(bank["languages"])
    unmapped = [c for c in codes if c not in GLOTLID_LABELS]
    if unmapped:
        raise SystemExit(f"no GlotLID label declared for: {', '.join(unmapped)}")

    # one record per string: (lang, id, group, seed key, prepared text)
    rows = []
    for a in bank["attacks"]:
        rows.append((a["lang"], a["id"], a["category"],
                     (a["category"], a["variant"]), _prepare(a["text"], bank)))
    for c in bank["controls"]:
        rows.append((c["lang"], c["id"], "control",
                     ("control", c["variant"]), _prepare(c["text"], bank)))

    # ---- language ID ----
    lid_model = fasttext.load_model(str(glotlid))
    labels = {l.replace("__label__", "") for l in lid_model.get_labels()}
    declared = {l for v in GLOTLID_LABELS.values() for l in v} | \
               {l for v in CLOSE.values() for l in v}
    absent = sorted(declared - labels)
    if absent:
        raise SystemExit(f"declared labels not in the model: {', '.join(absent)}")
    lid_out = {}
    for lang, rid, _g, _k, text in rows:
        lab, prob = lid_model.predict(text, k=1)
        lid_out[rid] = (lab[0].replace("__label__", ""), float(prob[0]))

    # ---- LaBSE similarity ----
    torch.manual_seed(0)
    enc = SentenceTransformer(str(labse), device="cpu")
    texts = [r[4] for r in rows]
    emb = enc.encode(texts, batch_size=64, normalize_embeddings=True,
                     convert_to_numpy=True, show_progress_bar=False)
    idx = {r[1]: i for i, r in enumerate(rows)}
    seeds = [(r[2], r[3], idx[r[1]]) for r in rows if r[0] == "en"]   # group, key, row
    seed_mat = np.stack([emb[i] for _, _, i in seeds])
    seed_groups = [g for g, _, _ in seeds]
    seed_keys = [k for _, k, _ in seeds]

    per_string = {}
    all_wrong, all_correct = [], []
    for i, (lang, rid, group, key, _t) in enumerate(rows):
        if lang == "en":
            continue
        sims = seed_mat @ emb[i]
        correct = float(sims[seed_keys.index(key)])
        wrong = [float(s) for s, g in zip(sims, seed_groups) if g != group]
        best = int(np.argmax(sims))
        per_string[rid] = {"correct": correct, "wrong": wrong,
                           "retrieved": seed_groups[best] == group}
        all_wrong.extend(wrong)
        all_correct.append(correct)
    sim_T = _percentile(all_wrong, SIM_PERCENTILE)

    # ---- per language ----
    langs = {}
    for code in codes:
        meta = bank["languages"][code]
        mine = [r for r in rows if r[0] == code]
        ok = set(GLOTLID_LABELS[code])
        close = ok | set(CLOSE.get(code, ()))
        got = [lid_out[r[1]] for r in mine]
        share = sum(l in ok for l, _ in got) / len(got)
        share_close = sum(l in close for l, _ in got) / len(got)
        misses = [{"id": r[1], "label": lid_out[r[1]][0], "p": round(lid_out[r[1]][1], 3)}
                  for r in mine if lid_out[r[1]][0] not in ok]
        entry = {"name": meta["name"], "provenance": meta.get("provenance", "author"),
                 "tier": tier_of(code), "n_strings": len(mine),
                 "text_sha256": text_sha256(bank, code),
                 "lid": {"share": round(share, 4), "share_close": round(share_close, 4),
                         "mean_p_top": round(sum(p for _, p in got) / len(got), 4),
                         "misses": misses},
                 "sim": None, "flags": [], "notes": []}
        if code != "en":
            ps = [per_string[r[1]] for r in mine]
            corr = [p["correct"] for p in ps]
            wrong = [w for p in ps for w in p["wrong"]]
            below = [{"id": r[1], "sim": round(per_string[r[1]]["correct"], 4)}
                     for r in mine if per_string[r[1]]["correct"] <= sim_T]
            m, mw = sum(corr) / len(corr), sum(wrong) / len(wrong)
            entry["sim"] = {"mean": round(m, 4), "min": round(min(corr), 4),
                            "mean_wrong": round(mw, 4), "margin": round(m - mw, 4),
                            "retrieval": round(sum(p["retrieved"] for p in ps) / len(ps), 4),
                            "n_at_or_below_T": len(below), "at_or_below_T": below}
        if share_close < LID_MIN:
            entry["flags"].append("lid")
        elif share < LID_MIN:
            entry["notes"].append("lid_near_neighbour")
        s = entry["sim"]
        if s and (s["n_at_or_below_T"] > SIM_MAX_AT_OR_BELOW or s["retrieval"] < RETRIEVAL_MIN):
            entry["flags"].append("sim")
        langs[code] = entry

    def pkg(name):
        from importlib.metadata import version
        try:
            return version(name)
        except Exception:
            return None

    lab_files = [Path(labse) / "model.safetensors", Path(labse) / "2_Dense" / "model.safetensors"]
    data = {
        "schema": SCHEMA,
        "what": ("Automated translation quality proxy per bank language. Two offline "
                 "signals that catch gross failures (wrong language, meaning drift). "
                 "Not a validation: neither tool measures fluency, register, or whether "
                 "a native speaker would read an attack as an instruction."),
        "generated_on": date.today().isoformat(),
        "bank_sha256": engine.bank_sha256(),
        "n_languages": len(codes), "n_machine": len(machine_codes(bank)),
        "preparation": ("linguistics.strip_fixed_tokens with the canary and control "
                        "token (removes both, Base64 blobs and SYSTEM OVERRIDE), then "
                        "whitespace collapsed. Applied to translations and English seeds."),
        "models": {
            "glotlid": {"repo": "cis-lmu/glotlid",
                        "revision": "85cd6716494360367b75f642b5bc78667605d0b4",
                        "file": Path(glotlid).name, "version": "v3",
                        "bytes": Path(glotlid).stat().st_size,
                        "sha256": _sha256_file(Path(glotlid)),
                        "license": "Apache-2.0 plus notices (model card: license other, "
                                   "apache-2.0-plus-notices; LICENSE file read)",
                        "n_labels": len(labels)},
            "labse": {"repo": "sentence-transformers/LaBSE",
                      "revision": "836121a0533e5664b21c7aacc5d22951f2b8b25b",
                      "files": {str(p.relative_to(labse)).replace("\\", "/"):
                                {"bytes": p.stat().st_size, "sha256": _sha256_file(p)}
                                for p in lab_files},
                      "license": "Apache-2.0 (model card)"},
        },
        "software": {"python": platform.python_version(), "fasttext": pkg("fasttext-numpy2-wheel"),
                     "torch": torch.__version__, "transformers": transformers.__version__,
                     "sentence_transformers": sentence_transformers.__version__,
                     "numpy": np.__version__, "device": "cpu"},
        "rules": {"lid_min_share_close": LID_MIN, "sim_threshold_percentile": SIM_PERCENTILE,
                  "sim_flag_if_more_than_n_at_or_below_T": SIM_MAX_AT_OR_BELOW,
                  "sim_retrieval_min": RETRIEVAL_MIN,
                  "groups": bank["categories"] + ["control"],
                  "wrong_pairs": "same translated string against every English seed of a "
                                 "different group",
                  "declared_before_scoring": "docs/progress/translation-quality.md"},
        "threshold": {"sim_T": round(sim_T, 4), "wrong_pairs_n": len(all_wrong),
                      "wrong_pairs_max": round(max(all_wrong), 4),
                      "wrong_pairs_p50": round(_percentile(all_wrong, 50), 4),
                      "correct_pairs_n": len(all_correct),
                      "correct_pairs_p01": round(_percentile(all_correct, 1), 4),
                      "correct_pairs_p50": round(_percentile(all_correct, 50), 4)},
        "lid_labels": {c: list(GLOTLID_LABELS[c]) for c in codes},
        "lid_close": {c: list(CLOSE[c]) for c in codes if c in CLOSE},
        "languages": langs,
    }
    flagged = sorted(c for c, e in langs.items() if e["flags"])
    data["summary"] = {
        "flagged": flagged,
        "flagged_machine": [c for c in flagged if langs[c]["provenance"] == "machine"],
        "near_neighbour_notes": sorted(c for c, e in langs.items()
                                       if "lid_near_neighbour" in e["notes"]),
    }
    out_path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any bank language is missing or stale")
    ap.add_argument("--flagged", action="store_true", help="show flagged languages only")
    ap.add_argument("--build", action="store_true", help="regenerate the JSON (heavy)")
    ap.add_argument("--glotlid", type=Path, help="path to GlotLID model_v3.bin")
    ap.add_argument("--labse", type=Path, help="path to the LaBSE model directory")
    a = ap.parse_args(argv)
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    if a.build:
        if not (a.glotlid and a.labse):
            ap.error("--build needs --glotlid and --labse")
        build(a.glotlid, a.labse)
    data = load()
    if data is None:
        print("translation_quality.json is missing or unreadable")
        return 1
    if a.check:
        cov = coverage(data, bank)
        bad = cov["missing"] or cov["stale"]
        print(f"{len(data['languages'])} languages scored; missing: "
              f"{', '.join(cov['missing']) or 'none'}; stale: {', '.join(cov['stale']) or 'none'}")
        return 1 if bad else 0
    print_report(data, bank, flagged_only=a.flagged)
    return 0


if __name__ == "__main__":
    sys.exit(main())
