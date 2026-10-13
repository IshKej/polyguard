"""
How well a judge agrees with the assisted review of a set of local scans.

`results/local/2026-10-06/HAND_REVIEW.md` read every reply either judge called a
break and every unscored attack, and records a reviewer verdict for each; every
other reply containing the canary was also read and none looked like
compliance, so it is labelled a hold. This compares, over the replies that
contain the canary (the only ones a judge ever sees; extraction is scored by
overlap, not by a judge):

  before   the scan's own judge (scoring 1.1 wording) and the second judge pass
           saved beside each scan (second_judge.json, same wording)
  after    any number of rejudge.py outputs made with the current wording

The reviewer labels are one reader's judgement from an AI assisted session, not
yet checked by Ishaan and not a validated gold set. Agreement with them is
evidence about the judge wording, not proof of accuracy.

    python review_agreement.py results/local/2026-10-06 \\
        --after gemma=results/local/<date>/rejudge/gemma \\
        --out results/local/<date>/rejudge/agreement.json

Each --after directory holds <run>.json files written by rejudge.py --out.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import engine


def review_labels(md: str) -> dict[str, dict[str, bool]]:
    """{run: {attack id: reviewer says break}} from the HAND_REVIEW.md tables."""
    out: dict[str, dict[str, bool]] = {}
    run = None
    for line in md.splitlines():
        m = re.match(r"^## (\S+)", line)
        if m:
            run = m.group(1)
            out[run] = {}
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if run and len(cells) == 5 and re.match(r"^[a-z]{2,3}_\w+_\d$", cells[0]):
            out[run][cells[0]] = cells[3] == "break"
    return out


def score(truth: list[bool], pred: list[bool]) -> dict:
    n = len(truth)
    agree = sum(t == p for t, p in zip(truth, pred))
    return {"n": n, "agreement": agree / n if n else None,
            "kappa": engine.cohens_kappa(truth, pred)["kappa"] if n else None,
            "judge_breaks": sum(pred), "reviewer_breaks": sum(truth),
            "false_breaks": sum(1 for t, p in zip(truth, pred) if p and not t),
            "missed_breaks": sum(1 for t, p in zip(truth, pred) if t and not p)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("results", help="folder with HAND_REVIEW.md and one folder per run")
    ap.add_argument("--after", action="append", default=[],
                    help="name=folder of rejudge.py outputs, one <run>.json per run")
    ap.add_argument("--out", help="write the comparison as JSON here")
    args = ap.parse_args(argv)

    root = Path(args.results)
    labels = review_labels((root / "HAND_REVIEW.md").read_text(encoding="utf-8"))
    after = dict(a.split("=", 1) for a in args.after)
    canary = engine.load_bank()["canary"]
    report: dict = {"schema": "polyguard.review-agreement/1", "results": str(root),
                    "label_source": "HAND_REVIEW.md, assisted review, not yet checked by Ishaan",
                    "runs": {}, "pooled_full_scans": {}}
    pooled: dict[str, tuple[list, list]] = {}
    for run, lab in labels.items():
        scan = json.loads((root / run / "scan.json").read_text(encoding="utf-8"))
        rows = [r for r in scan["results"] if r.get("goal") != "extract"
                and engine._norm(canary) in engine._norm(r.get("reply") or "")]
        truth = {r["id"]: lab.get(r["id"], False) for r in rows}
        judges: dict[str, dict[str, bool]] = {}
        # Before: the scan's own judge, on the rows it scored.
        judges["before: scan judge"] = {r["id"]: bool(r["broke"]) for r in rows
                                        if not r.get("error")}
        sj = root / run / "second_judge.json"
        if sj.exists():
            second = json.loads(sj.read_text(encoding="utf-8"))
            flipped = {d["id"]: d["second_judge"] for d in second.get("disagreements", [])}
            judges["before: second judge"] = {i: flipped.get(i, v) for i, v
                                              in judges["before: scan judge"].items()}
        for name, folder in after.items():
            f = Path(folder) / f"{run}.json"
            if f.exists():
                got = json.loads(f.read_text(encoding="utf-8"))
                judges[f"after: {name}"] = {v["id"]: v["second_outcome"] == "complied"
                                            for v in got["verdicts"]}
                judges[f"after: {name}"]["_echoed"] = sum(
                    1 for v in got["verdicts"] if v["second_outcome"] == "echoed")
        report["runs"][run] = {"replies_with_canary": len(rows),
                               "reviewer_breaks": sum(truth.values()), "judges": {}}
        for name, pred in judges.items():
            echoed = pred.pop("_echoed", None)
            ids = sorted(i for i in pred if i in truth)
            s = score([truth[i] for i in ids], [pred[i] for i in ids])
            if echoed is not None:
                s["echoed"] = echoed
            report["runs"][run]["judges"][name] = s
            if run.startswith("full-"):
                t, p = pooled.setdefault(name, ([], []))
                t.extend(truth[i] for i in ids)
                p.extend(pred[i] for i in ids)
    for name, (t, p) in pooled.items():
        report["pooled_full_scans"][name] = score(t, p)

    print(f"Agreement with the assisted review in {root / 'HAND_REVIEW.md'}")
    print("(replies containing the canary; reviewer labels not yet checked by Ishaan)\n")
    for run, d in report["runs"].items():
        print(f"{run}: {d['replies_with_canary']} replies, reviewer breaks {d['reviewer_breaks']}")
        for name, s in d["judges"].items():
            extra = f", echoed {s['echoed']}" if "echoed" in s else ""
            print(f"  {name:<24} n={s['n']:<3} agree {s['agreement']:.0%}  "
                  f"breaks {s['judge_breaks']} (false {s['false_breaks']}, "
                  f"missed {s['missed_breaks']}){extra}")
    print("\nPooled over the four full scans:")
    for name, s in report["pooled_full_scans"].items():
        k = "n/a" if s["kappa"] is None else f"{s['kappa']:.2f}"
        print(f"  {name:<24} n={s['n']:<3} agree {s['agreement']:.1%}  kappa {k}  "
              f"breaks {s['judge_breaks']} (false {s['false_breaks']}, "
              f"missed {s['missed_breaks']})")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                  encoding="utf-8", newline="\n")
        print(f"\n  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
