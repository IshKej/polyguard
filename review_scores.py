"""
The data behind the two review pages of the site: what native review changed in the
automated translation score, and where review stands for every language.

Two outputs, both reproducible:

  review_row_scores.json   per row LaBSE similarity to the English source, before and
                           after native review, for every language whose text changed
                           because of a review. Heavy: needs the local LaBSE model.
                               python review_scores.py --build --labse C:/dev/llm/models/labse
  web/src/review-data.json what the site shows, from native_review.json, the bank,
                           translation_quality.json, the scan-time scores and the file
                           above. Light, no models.
                               python review_scores.py

"Before" is the bank the 2026-10-11 local scan sent (SHA-256 4e2ba320...), recovered
from git; for every reviewed language whose text changed since, that is its text
before the review (checked by text hash against the scan-time scores). The per row
numbers must reproduce the published per language mean and lowest score exactly;
verify_all.py checks that.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BANK = ROOT / "attack_bank.json"
STATUS = ROOT / "native_review.json"
TQ_NOW = ROOT / "translation_quality.json"
TQ_BEFORE = ROOT / "results/local/2026-10-11/translation_quality-at-scan.json"
ROWS_OUT = ROOT / "review_row_scores.json"
SITE_OUT = ROOT / "web/src/review-data.json"
BEFORE_BANK_SHA = "4e2ba320c932823e046d2113af44ee2ca5e4042cf3d75f1ea8abd15117cdf1f8"
BEFORE_BANK_COMMIT = "75e5fe6"
REVIEWED = ("integrated", "integrated_in_part")


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _bank_rows(bank: dict, code: str) -> list[tuple[str, tuple, str]]:
    rows = [(a["id"], (a["category"], a["variant"]), a["text"]) for a in bank["attacks"] if a["lang"] == code]
    rows += [(c["id"], ("control", c["variant"]), c["text"]) for c in bank["controls"] if c["lang"] == code]
    return rows


def changed_languages(status: dict, tq_before: dict, tq_now: dict) -> list[str]:
    """Reviewed languages whose text differs between the scan-time scores and now."""
    return [c for c, s in status["languages"].items() if s["status"] in REVIEWED
            and tq_before["languages"][c]["text_sha256"] != tq_now["languages"][c]["text_sha256"]]


def build_rows(labse: Path) -> dict:
    import tq_report
    from sentence_transformers import SentenceTransformer
    import torch

    before_raw = subprocess.run(["git", "show", f"{BEFORE_BANK_COMMIT}:attack_bank.json"], cwd=ROOT,
                                capture_output=True, check=True).stdout
    assert hashlib.sha256(before_raw).hexdigest() == BEFORE_BANK_SHA, "wrong before bank"
    before, now = json.loads(before_raw.decode("utf-8")), _load(BANK)
    status, tq_b, tq_n = _load(STATUS), _load(TQ_BEFORE), _load(TQ_NOW)
    assert tq_b["bank_sha256"] == BEFORE_BANK_SHA and tq_n["bank_sha256"] == hashlib.sha256(BANK.read_bytes()).hexdigest()
    langs = changed_languages(status, tq_b, tq_n)
    for c in langs:  # the before text is the text the scan-time scores describe
        assert tq_report.text_sha256(before, c) == tq_b["languages"][c]["text_sha256"], c

    torch.manual_seed(0)
    enc = SentenceTransformer(str(labse), device="cpu")

    def sims(bank: dict, code: str) -> dict:
        en = {k: tq_report._prepare(t, bank) for _, k, t in _bank_rows(bank, "en")}
        mine = _bank_rows(bank, code)
        texts = [tq_report._prepare(t, bank) for _, _, t in mine] + [en[k] for _, k, _ in mine]
        e = enc.encode(texts, batch_size=64, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        n = len(mine)
        return {rid: round(float(e[i] @ e[n + i]), 6) for i, (rid, _, _) in enumerate(mine)}

    out = {"schema": "polyguard.review-row-scores/1",
           "what": "LaBSE cosine similarity of each row to its English source, before and after native review. "
                   "An automated proxy, not a validation.",
           "before_bank_sha256": BEFORE_BANK_SHA, "after_bank_sha256": tq_n["bank_sha256"],
           "model": tq_n["models"]["labse"], "preparation": tq_n["preparation"], "languages": {}}
    text_of = lambda bank: {r["id"]: r["text"] for r in bank["attacks"] + bank["controls"]}  # noqa: E731
    tb, tn = text_of(before), text_of(now)
    out["featured"] = {}
    for c in langs:
        b, a = sims(before, c), sims(now, c)
        out["languages"][c] = {rid: {"before": b[rid], "after": a[rid]} for rid in a}
        # The row whose score fell most, with its wording before and after and the
        # English it is compared with, so the page can show what the reviewer did.
        rid = min(a, key=lambda r: a[r] - b[r])
        en = rid.replace(f"{c}_", "en_", 1)
        out["featured"][c] = {"id": rid, "english": tn[en], "before": tb[rid], "after": tn[rid]}
    ROWS_OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return out


def site_data() -> dict:
    from languages_catalog import tier_of
    bank, status, tq_b, tq_n = _load(BANK), _load(STATUS), _load(TQ_BEFORE), _load(TQ_NOW)
    rows = _load(ROWS_OUT)
    langs = []
    for code, meta in bank["languages"].items():
        s = status["languages"].get(code, {})
        langs.append({
            "code": code, "name": meta["name"], "native": meta["native"], "tier": tier_of(code),
            "provenance": meta["provenance"],
            "status": "source" if code == "en" else s.get("status", "none"),
            "credit": s.get("credit"), "returned": s.get("returned"), "integrated": s.get("integrated"),
            "rows_changed": s.get("rows_changed"), "rows_held": s.get("rows_held"), "note": s.get("note"),
        })
    moved = []
    for code in changed_languages(status, tq_b, tq_n):
        b, n = tq_b["languages"][code]["sim"], tq_n["languages"][code]["sim"]
        per = rows["languages"][code]
        biggest = min(per.items(), key=lambda kv: kv[1]["after"] - kv[1]["before"])
        moved.append({
            "code": code, "name": bank["languages"][code]["name"],
            "mean": [b["mean"], n["mean"]], "lowest": [b["min"], n["min"]],
            "rows_changed": status["languages"][code]["rows_changed"],
            "rows_held": status["languages"][code]["rows_held"],
            "biggest_drop": {"id": biggest[0], "before": biggest[1]["before"], "after": biggest[1]["after"],
                             "text": rows["featured"][code]},
            "rows": [{"id": k, **v} for k, v in sorted(per.items())],
        })
    no_before = [c for c, s in status["languages"].items() if s["status"] in REVIEWED
                 and c not in {m["code"] for m in moved}]
    mach = [c for c, e in tq_n["languages"].items() if e["provenance"] == "machine"]
    means = sorted(tq_n["languages"][c]["sim"]["mean"] for c in mach)
    return {
        "statuses": status["statuses"], "withheld": status["withheld"], "languages": langs, "moved": moved,
        "reviewed_before_scores": [{"code": c, "name": bank["languages"][c]["name"],
                                    "integrated": status["languages"][c]["integrated"]} for c in no_before],
        "scores_first_built": tq_b["generated_on"], "scores_rebuilt": tq_n["generated_on"],
        "machine": {"n": len(mach), "lowest_mean": means[0], "median_mean": means[len(means) // 2],
                    "flagged": [bank["languages"][c]["name"] for c in mach if tq_n["languages"][c]["flags"]],
                    "flag_threshold": tq_n["threshold"]["sim_T"]},
        "before_bank": BEFORE_BANK_SHA, "after_bank": tq_n["bank_sha256"],
    }


def site_json() -> str:
    return json.dumps(site_data(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--build", action="store_true", help="recompute per row scores (needs the local LaBSE model)")
    ap.add_argument("--labse", type=Path, help="path to the LaBSE model directory")
    a = ap.parse_args()
    if a.build:
        if not a.labse:
            raise SystemExit("--build needs --labse")
        build_rows(a.labse)
        print(f"wrote {ROWS_OUT.relative_to(ROOT)}")
    SITE_OUT.write_text(site_json(), encoding="utf-8", newline="\n")
    print(f"wrote {SITE_OUT.relative_to(ROOT)}")
