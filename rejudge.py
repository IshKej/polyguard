"""
Second judge pass over a saved scan.

Every attack reply that contains the canary was scored by one LLM judge. This
asks a second, independently configured judge the same question about the same
replies and reports how often the two agree (Cohen's kappa) and every reply
where they do not. It changes nothing in the scan file: the scan's own numbers
stay the ones its judge produced, and this is evidence about that judge.

Why it exists: a local judge is a small model, and published work finds LLM
judges weakest in exactly the languages PolyGuard studies. One judge's verdicts
are a measurement only once a second judge has been compared against them.

    POLYGUARD_JUDGE_BACKEND=local POLYGUARD_JUDGE_URL=http://127.0.0.1:8080 \\
        python rejudge.py results/local/<date>/<run>/scan.json

Writes second_judge.json next to the scan. Exit 0 when every reply was judged,
2 when the second judge is not configured or a verdict failed.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import engine
import providers


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    path = Path(argv[0])
    scan = json.loads(path.read_text(encoding="utf-8"))
    client = providers.judge_client()
    if client is None:
        print("No second judge configured (see the docstring).", file=sys.stderr)
        return 2
    second = engine.judge_name(client)
    first = scan.get("judge_model")
    canary = engine.load_bank()["canary"]
    rows = [r for r in scan["results"]
            if r.get("goal") != "extract" and not r.get("error")
            and engine._norm(canary) in engine._norm(r.get("reply") or "")]
    a, b, disagree, failed = [], [], [], 0
    for r in rows:
        try:
            v = engine.llm_judge_compliance(client, r["reply"], canary)
        except Exception as e:          # a failed verdict is reported, never guessed
            failed += 1
            print(f"  could not judge {r['id']}: {e}", file=sys.stderr)
            continue
        a.append(bool(r["broke"]))
        b.append(v)
        if v != bool(r["broke"]):
            disagree.append({"id": r["id"], "lang": r["lang"], "category": r["category"],
                             "first_judge": bool(r["broke"]), "second_judge": v,
                             "reply": r["reply"]})
    kappa = engine.cohens_kappa(a, b) if a else None
    out = {
        "schema": "polyguard.second-judge/1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scan": path.name,
        "first_judge": first,
        "second_judge": second,
        "second_judge_weights": getattr(client, "provenance", None),
        "judge_prompt_sha256": engine.judge_prompt_sha256(),
        "replies_with_canary": len(rows),
        "judged_by_both": len(a),
        "failed": failed,
        "first_says_broke": sum(a),
        "second_says_broke": sum(b),
        "agreement": (sum(x == y for x, y in zip(a, b)) / len(a)) if a else None,
        "kappa": kappa,
        "disagreements": disagree,
    }
    dest = path.with_name("second_judge.json")
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8",
                    newline="\n")
    k = kappa or {}
    print(f"{path}: {len(rows)} replies contain the canary; {len(a)} judged by both")
    print(f"  {first}: {sum(a)} broke   {second}: {sum(b)} broke")
    if a:
        print(f"  agreement {out['agreement']:.0%}, kappa "
              f"{'n/a' if k.get('kappa') is None else format(k['kappa'], '.2f')}, "
              f"{len(disagree)} disagreement(s)")
    print(f"  wrote {dest}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
