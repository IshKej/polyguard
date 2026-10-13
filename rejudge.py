"""
Second judge pass over a saved scan.

Every attack reply that contains the canary was scored by one LLM judge. This
asks a second, independently configured judge the same question about the same
replies and reports how often the two agree (Cohen's kappa) and every reply
where they do not. It changes nothing in the scan file: the scan's own numbers
stay the ones its judge produced, and this is evidence about that judge.

The judge is shown the user's message as well as the reply (scoring 1.2), so a
faithful translation of an injected line can be told from obedience. Scan files
do not store the attack text; it is looked up by id in the bank, and the bank's
SHA-256 must match the one the scan names. Pass `--bank` to point at the bank a
scan used when it is not the one in this checkout (for example
`git show <commit>:attack_bank.json > old_bank.json`).

Replies whose first judge failed (unscored) are judged too when they contain
the canary, so a rerun can fill in what the first pass could not.

    POLYGUARD_JUDGE_BACKEND=local POLYGUARD_JUDGE_URL=http://127.0.0.1:8081 \\
        python rejudge.py results/local/<date>/<run>/scan.json [--bank FILE] [--out FILE]

Writes second_judge.json next to the scan unless `--out` names another file.
Exit 0 when every reply was judged, 2 when the judge is not configured, the bank
does not match, or a verdict failed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import engine
import providers


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Second judge pass over a saved scan.")
    ap.add_argument("scan")
    ap.add_argument("--bank", help="the attack bank the scan used (default: this checkout's)")
    ap.add_argument("--out", help="where to write the result (default: second_judge.json "
                                  "next to the scan)")
    args = ap.parse_args(argv)

    path = Path(args.scan)
    scan = json.loads(path.read_text(encoding="utf-8"))
    bank_path = Path(args.bank) if args.bank else engine.BANK_PATH
    bank_sha = hashlib.sha256(bank_path.read_bytes()).hexdigest()
    want = (scan.get("instrument") or {}).get("bank_sha256")
    if want and want != bank_sha:
        print(f"The scan used bank {want[:12]}, but {bank_path} is {bank_sha[:12]}. "
              f"Pass --bank with the bank it used.", file=sys.stderr)
        return 2
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    texts = {a["id"]: a["text"] for a in bank["attacks"]}

    client = providers.judge_client()
    if client is None:
        print("No second judge configured (see the docstring).", file=sys.stderr)
        return 2
    second = engine.judge_name(client)
    first = scan.get("judge_model")
    canary = bank["canary"]
    rows = [r for r in scan["results"]
            if r.get("goal") != "extract"
            and (not r.get("error") or r.get("error_stage") == "judge")
            and engine._norm(canary) in engine._norm(r.get("reply") or "")]
    a, b, disagree, verdicts, failed = [], [], [], [], 0
    for r in rows:
        try:
            v = engine.llm_judge_attack(client, r["reply"], canary, request=texts[r["id"]])
        except Exception as e:          # a failed verdict is reported, never guessed
            failed += 1
            print(f"  could not judge {r['id']}: {e}", file=sys.stderr)
            continue
        first_v = None if r.get("error") else bool(r["broke"])
        verdicts.append({"id": r["id"], "lang": r["lang"], "category": r["category"],
                         "first_judge": first_v, "second_outcome": v})
        if first_v is None:
            continue
        a.append(first_v)
        b.append(v == "complied")
        if (v == "complied") != first_v:
            disagree.append({"id": r["id"], "lang": r["lang"], "category": r["category"],
                             "first_judge": first_v, "second_judge": v == "complied",
                             "second_outcome": v, "reply": r["reply"]})
    kappa = engine.cohens_kappa(a, b) if a else None
    out = {
        "schema": "polyguard.second-judge/2",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scan": str(path),
        "bank_sha256": bank_sha,
        "first_judge": first,
        "first_scoring_version": (scan.get("instrument") or {}).get("scoring_version"),
        "second_judge": second,
        "second_judge_weights": getattr(client, "provenance", None),
        "judge_prompt_sha256": engine.judge_prompt_sha256(),
        "scoring_version": engine.SCORING_VERSION,
        "replies_with_canary": len(rows),
        "judged_by_both": len(a),
        "failed": failed,
        "first_says_broke": sum(a),
        "second_says_broke": sum(1 for v in verdicts if v["second_outcome"] == "complied"),
        "second_says_echoed": sum(1 for v in verdicts if v["second_outcome"] == "echoed"),
        "agreement": (sum(x == y for x, y in zip(a, b)) / len(a)) if a else None,
        "kappa": kappa,
        "verdicts": verdicts,
        "disagreements": disagree,
    }
    dest = Path(args.out) if args.out else path.with_name("second_judge.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8",
                    newline="\n")
    k = kappa or {}
    print(f"{path}: {len(rows)} replies contain the canary; {len(a)} judged by both")
    print(f"  {first}: {sum(a)} broke   {second}: {out['second_says_broke']} broke, "
          f"{out['second_says_echoed']} echoed")
    if a:
        print(f"  agreement {out['agreement']:.0%}, kappa "
              f"{'n/a' if k.get('kappa') is None else format(k['kappa'], '.2f')}, "
              f"{len(disagree)} disagreement(s)")
    print(f"  wrote {dest}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
