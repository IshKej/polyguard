"""
Intake for the stage 1 live pilot: one paid scan, Claude Haiku 4.5 as victim and judge.

The pilot is run outside this repository. Its bundle comes back as the scan file
the engine writes (scan.json) plus a small pilot.json with what a scan file cannot
know: the run date, what was spent and the cap it ran under.

    python pilot_intake.py path/to/scan.json path/to/pilot.json            # check only
    python pilot_intake.py path/to/scan.json path/to/pilot.json --write    # write it in

pilot.json:
    {"run_date": "2026-10-22", "victim": "claude-haiku-4-5", "judge": "claude-haiku-4-5",
     "spend_usd": 7.41, "cap_usd": 10, "smoke_test": "passed", "notes": "..."}

Checking refuses a simulated scan, a scan whose models differ from pilot.json, a
missing or over-cap spend, and a scan with no completeness record. Writing puts the
bundle in results/live/<run_date>-stage1/ and builds
web/public/examples/live-pilot-<run_date>.html, labelled as one diagnostic run: not
the preregistered study and not a production chatbot. Nothing links to that page
and no other surface changes; the site stays labelled simulated until the author
decides otherwise. No API key is needed to check, write or test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import publish_example
import report_html

ROOT = Path(__file__).resolve().parent
LABEL = "Live pilot, diagnostic"
BANNER = ("One paid diagnostic run: Claude Haiku 4.5 as the victim and as the judge, one scan. "
          "Not the preregistered study (several models, the full analysis) and not a production chatbot.")


class Refused(ValueError):
    pass


def _model_of(scan: dict) -> str:
    return str((scan.get("victim") or {}).get("model_id") or scan.get("model") or "")


def check(scan: dict, pilot: dict) -> dict:
    """The facts the evidence page states, or Refused with the reason."""
    if scan.get("mock") or scan.get("mode") != "live":
        raise Refused("this is a simulated scan, not a live one")
    for key in ("run_date", "victim", "judge", "spend_usd", "cap_usd"):
        if pilot.get(key) in (None, ""):
            raise Refused(f"pilot.json has no {key}")
    if not str(_model_of(scan)).endswith(pilot["victim"]):
        raise Refused(f"the scan's victim is {_model_of(scan)!r}, pilot.json says {pilot['victim']!r}")
    if not str(scan.get("judge_model") or "").endswith(pilot["judge"]):
        raise Refused(f"the scan's judge is {scan.get('judge_model')!r}, pilot.json says {pilot['judge']!r}")
    spend, cap = float(pilot["spend_usd"]), float(pilot["cap_usd"])
    if spend < 0 or spend > cap:
        raise Refused(f"spend {spend} is outside 0 to the cap of {cap}")
    comp = scan.get("completeness")
    if not isinstance(comp, dict) or "planned" not in comp:
        raise Refused("the scan has no completeness record")
    inst = scan.get("instrument") or {}
    return {
        "label": LABEL, "run_date": pilot["run_date"], "victim": pilot["victim"], "judge": pilot["judge"],
        "spend_usd": round(spend, 2), "cap_usd": round(cap, 2), "smoke_test": pilot.get("smoke_test"),
        "attacks_planned": comp.get("planned"), "attacks_scored": comp.get("scored"),
        "errors": comp.get("errors"), "errors_by_kind": comp.get("errors_by_kind") or {},
        "controls_scored": comp.get("controls_scored"), "controls_planned": comp.get("controls_planned"),
        "complete": bool(comp.get("complete")), "languages": len(scan.get("by_lang") or {}),
        "bank_sha256": inst.get("bank_sha256"), "scoring_version": inst.get("scoring_version"),
        "generated_at": scan.get("generated_at"), "notes": pilot.get("notes"),
    }


def page(scan: dict, facts: dict) -> str:
    html = report_html.build_report(scan)
    head, body = "<title>PolyGuard report</title>", "<body><main class=wrap>"
    assert html.count(head) == 1 and html.count(body) == 1
    title = f"<title>PolyGuard: live pilot, {facts['run_date']}</title>"
    html = html.replace(head, publish_example.FONT + title + publish_example.EXTRA_CSS)
    e = report_html._e
    items = [
        f"<b>What:</b> {e(BANNER)}",
        f"<b>When:</b> run {e(facts['run_date'])}; scan file written {e(facts['generated_at'] or 'not recorded')}.",
        f"<b>Models:</b> victim {e(facts['victim'])}, judge {e(facts['judge'])}.",
        f"<b>Completeness:</b> {e(facts['attacks_scored'])} of {e(facts['attacks_planned'])} attacks scored, "
        f"{e(facts['controls_scored'])} of {e(facts['controls_planned'])} capability controls, "
        f"{e(facts['errors'])} errors{' (' + e(json.dumps(facts['errors_by_kind'])) + ')' if facts['errors_by_kind'] else ''}.",
        f"<b>Spend:</b> ${facts['spend_usd']:.2f} of a ${facts['cap_usd']:.2f} cap.",
        f"<b>Instrument:</b> bank {e(str(facts['bank_sha256'])[:12])}, scoring {e(facts['scoring_version'])}.",
    ]
    if facts["victim"] == facts["judge"]:
        # Recorded in PREREGISTRATION.md (2026-10-21) before any result was seen.
        items.append("<b>Caveat:</b> the judge is the same model as the victim, so its verdicts on its own "
                     "replies may be lenient. Extraction breaks are scored by verbatim overlap, with no judge.")
    status = ('<nav class="back" aria-label="Site"><a href="/">Back to PolyGuard</a>'
              f'<span class="status">{e(LABEL)}</span></nav>')
    summary = ('<div class="note n-info summary"><b>One diagnostic run, published as it came back.</b><ul>'
               + "".join(f"<li>{i}</li>" for i in items) + "</ul></div>")
    return html.replace(body, body + status + summary)


def write(scan_path: Path, pilot_path: Path, scan: dict, pilot: dict, facts: dict, root: Path = ROOT) -> list[Path]:
    folder = root / "results" / "live" / f"{facts['run_date']}-stage1"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(scan_path, folder / "scan.json")
    shutil.copyfile(pilot_path, folder / "pilot.json")
    (folder / "summary.json").write_text(json.dumps(facts, indent=1) + "\n", encoding="utf-8", newline="\n")
    out = root / "web" / "public" / "examples" / f"live-pilot-{facts['run_date']}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(scan, facts), encoding="utf-8", newline="\n")
    return [folder / "scan.json", folder / "pilot.json", folder / "summary.json", out]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("scan", type=Path)
    ap.add_argument("pilot", type=Path)
    ap.add_argument("--write", action="store_true", help="write the bundle and the page (default: check only)")
    a = ap.parse_args(argv)
    scan = json.loads(a.scan.read_text(encoding="utf-8"))
    pilot = json.loads(a.pilot.read_text(encoding="utf-8"))
    try:
        facts = check(scan, pilot)
    except Refused as err:
        print(f"REFUSED: {err}")
        return 1
    print(json.dumps(facts, indent=1))
    print("scan sha256:", hashlib.sha256(a.scan.read_bytes()).hexdigest())
    if a.write:
        for p in write(a.scan, a.pilot, scan, pilot, facts):
            print("wrote", p.relative_to(ROOT))
    else:
        print("checked only; add --write to bring it in")
    return 0


if __name__ == "__main__":
    sys.exit(main())
