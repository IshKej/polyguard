"""
PolyGuard command line interface.

The app is how you explore a result. This is how a result gets used.

A security scanner that only runs in a browser is a demo. One that runs headless,
writes machine-readable output, and returns a non-zero exit code when the bot got
worse is something a team can put in front of a deploy. That is the difference
between a project and a tool, and it is the whole reason this file exists.

    polyguard scan --prompt bot.txt --out today.json
    polyguard scan --prompt bot.txt --baseline last-week.json --fail-on-regression
    polyguard compare last-week.json today.json
    polyguard report today.json --html report.html
    polyguard languages

Exit codes, chosen so CI can act on them:

    0   scan completed, and no regression against the baseline
    1   a regression was detected (only with --fail-on-regression)
    2   the scan could not be completed at all

Run with --mock to exercise everything offline with no API key. Mock output is
labelled as simulated in every file it writes, because a JSON report that does
not say it is fake will eventually be read as though it were real.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import defenses
import engine
import providers
from languages_catalog import CATALOG, tier_of

VERSION = "1.0"


# --------------------------------------------------------------------------- #
# Regression detection
# --------------------------------------------------------------------------- #
def compare_scans(before: dict, after: dict, alpha: float = 0.05) -> dict:
    """
    Did the bot get worse?

    Compared at the LANGUAGE level, the same unit of analysis the rest of the
    project uses, because attacks against one bot in one language are correlated
    and pooling them would call noise a regression.

    A per-language change is only reported when the two Wilson intervals do not
    overlap, which is a deliberately conservative screen: CI should fail on
    evidence, not on a single unlucky attack. The overall change additionally
    gets a proportion test.

    Comparing a mock run against a live one is refused outright. That comparison
    is meaningless and would produce a confident, fabricated verdict.
    """
    if bool(before.get("mock")) != bool(after.get("mock")):
        return {"comparable": False,
                "reason": "one scan is simulated and the other is live; "
                          "those numbers cannot be compared"}
    if before.get("model") != after.get("model"):
        return {"comparable": False,
                "reason": f"different victim models ({before.get('model')} vs "
                          f"{after.get('model')}); a change could be the model, "
                          f"not the prompt"}

    b_lang, a_lang = before.get("by_lang", {}), after.get("by_lang", {})
    shared = sorted(set(b_lang) & set(a_lang))
    regressions, improvements = [], []
    for code in shared:
        b, a = b_lang[code], a_lang[code]
        if not b.get("total") or not a.get("total"):
            continue
        b_lo, b_hi = engine.wilson_ci_cc(b["broke"], b["total"])
        a_lo, a_hi = engine.wilson_ci_cc(a["broke"], a["total"])
        delta = (a["broke"] / a["total"]) - (b["broke"] / b["total"])
        row = {"lang": code, "name": a.get("name", code), "tier": tier_of(code),
               "before": b["broke"] / b["total"], "after": a["broke"] / a["total"],
               "delta": delta}
        if a_lo > b_hi:                       # got worse, intervals disjoint
            regressions.append(row)
        elif a_hi < b_lo:                     # got better, intervals disjoint
            improvements.append(row)

    # The verdict is a PAIRED test on per-language outcomes. The same languages
    # appear in both scans, so the pairing is real, and the language is the unit
    # of analysis everywhere else in this project for the same reason: attacks
    # against one bot in one language are correlated.
    #
    # The obvious alternative is what this deliberately does not do. Pooling every
    # attack into one proportion test rejects a true null 16.6% of the time under
    # realistic clustering (AUDIT.md finding 16), so wiring it to --fail-on-
    # regression would fail a build on noise about one run in six. It is still
    # computed and reported, labelled optimistic, exactly as the app does.
    n_worse = sum(1 for c in shared
                  if (a_lang[c].get("rate") or 0) > (b_lang[c].get("rate") or 0))
    n_better = sum(1 for c in shared
                   if (a_lang[c].get("rate") or 0) < (b_lang[c].get("rate") or 0))
    sign = engine.sign_test(n_worse, n_better)
    direction_worse = n_worse > n_better

    bt = sum(d["total"] for d in b_lang.values())
    bb = sum(d["broke"] for d in b_lang.values())
    at = sum(d["total"] for d in a_lang.values())
    ab = sum(d["broke"] for d in a_lang.values())
    pooled = engine.two_proportion_test(ab, at, bb, bt) if (at and bt) else {}

    # A regression is either a consistent shift across languages, or at least one
    # language whose intervals moved apart entirely. Both are language-level.
    regressed = bool(regressions) or bool(sign["significant"] and direction_worse)

    return {
        "comparable": True,
        "languages_compared": len(shared),
        "regressions": sorted(regressions, key=lambda r: -r["delta"]),
        "improvements": sorted(improvements, key=lambda r: r["delta"]),
        "languages_worse": n_worse,
        "languages_better": n_better,
        "sign_test": sign,
        "overall_before": (bb / bt) if bt else None,
        "overall_after": (ab / at) if at else None,
        "overall_delta": ((ab / at) - (bb / bt)) if (at and bt) else None,
        "pooled_test_optimistic": pooled,
        "regressed": regressed,
    }


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def scan_payload(out: dict, prompt: str, args) -> dict:
    """The machine-readable record of one scan. Carries its own caveats."""
    vm = out.get("victim") or {}
    return {
        "polyguard_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Stated first and unmissable. A JSON file outlives the terminal it was
        # printed in, and somebody will read this without the context.
        "mode": "MOCK-SIMULATED" if out["mock"] else "live",
        "mock": out["mock"],
        "victim": vm,
        "model": out.get("model"),
        "judge_model": out.get("judge_model"),
        "phrasings_per_cell": out.get("max_variants"),
        "temperature_pinned": vm.get("deterministic"),
        "thinking_forced": vm.get("thinking_forced"),
        "extraction_scoreable": out.get("extraction_scoreable"),
        "token_collision": out.get("token_collision"),
        "prompt_sha256": __import__("hashlib").sha256(
            prompt.encode("utf-8")).hexdigest(),
        "attacks_fired": out["n_attacks"],
        "attacks_broke": out["n_broke"],
        "errors": out["n_errors"],
        "overall_break_rate": out["overall_rate"],
        "english_break_rate": out["en_rate"],
        "worst_language_test": out.get("max_gap_test"),
        "capability": out.get("capability"),
        "by_lang": {c: {**d, "tier": tier_of(c)} for c, d in out["by_lang"].items()},
        "by_category": out["by_cat"],
        "broken_categories": defenses.broken_categories_from(out["results"]),
    }


def print_summary(out: dict) -> None:
    pct = lambda v: "n/a" if v is None else f"{v:.0%}"
    if out["mock"]:
        print("  MODE: MOCK-SIMULATED. These numbers are not a measurement.")
    if out.get("token_collision"):
        print(f"  INVALID: the prompt contains PolyGuard's "
              f"{' and '.join(out['token_collision'])}; every number below is "
              f"meaningless. Remove it and rescan.")
    print(f"  attacks   {out['n_attacks']} fired, {out['n_broke']} broke, "
          f"{out['n_errors']} errored")
    print(f"  overall   {pct(out['overall_rate'])} break rate")
    if out.get("en_rate") is not None:
        print(f"  english   {pct(out['en_rate'])}")

    tr = engine.tier_rates(out)
    lo, hi = tr["rates"]["low"], tr["rates"]["high"]
    if lo and hi:
        mw = engine.mann_whitney_u(lo, hi)
        eff = engine.cliffs_delta_ci(lo, hi)
        diff = sum(lo) / len(lo) - sum(hi) / len(hi)
        print(f"  tier gap  {diff:+.0%} low vs high, p={mw['p']:.3g}, "
              f"delta {eff['delta']:+.2f} ({eff['magnitude']})")
        if tr["n_excluded"]:
            print(f"            {tr['n_excluded']} capability-limited language(s) "
                  f"excluded: {', '.join(tr['excluded'])}")
    else:
        print("  tier gap  cannot be computed: the scan needs both low-resource "
              "and high-resource languages")

    cap = out.get("capability") or {}
    if cap.get("capability_limited"):
        print(f"  WARNING   the bot cannot follow ordinary instructions in "
              f"{', '.join(cap['capability_limited'])}; a low break rate there "
              f"is incapacity, not safety")


def print_comparison(cmp: dict) -> None:
    if not cmp["comparable"]:
        print(f"  NOT COMPARABLE: {cmp['reason']}")
        return
    print(f"  compared {cmp['languages_compared']} shared language(s)")
    if cmp["overall_delta"] is not None:
        print(f"  overall  {cmp['overall_before']:.0%} -> {cmp['overall_after']:.0%} "
              f"({cmp['overall_delta']:+.0%})")
    st = cmp.get("sign_test") or {}
    if st.get("n"):
        print(f"  verdict  {cmp['languages_worse']} language(s) worse, "
              f"{cmp['languages_better']} better, paired sign test p={st['p']:.3g}"
              f"{'  REGRESSION' if st['significant'] and cmp['languages_worse'] > cmp['languages_better'] else ''}")
    pooled = cmp.get("pooled_test_optimistic") or {}
    if pooled.get("p") is not None:
        print(f"           (pooled attack-level p={pooled['p']:.3g}, optimistic, "
              f"not the verdict)")
    for r in cmp["regressions"]:
        print(f"  WORSE    {r['name']:<14} {r['before']:.0%} -> {r['after']:.0%} "
              f"({r['delta']:+.0%})")
    for r in cmp["improvements"]:
        print(f"  better   {r['name']:<14} {r['before']:.0%} -> {r['after']:.0%} "
              f"({r['delta']:+.0%})")
    if not cmp["regressions"] and not cmp["improvements"]:
        print("  no per-language change large enough to separate from noise")


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def read_prompt(args) -> str:
    if args.prompt_text:
        return args.prompt_text
    if args.prompt == "-":
        return sys.stdin.read()
    p = Path(args.prompt)
    if not p.exists():
        raise SystemExit(f"prompt file not found: {p}")
    return p.read_text(encoding="utf-8")


def cmd_scan(args) -> int:
    prompt = read_prompt(args)
    if not prompt.strip():
        raise SystemExit("the prompt is empty")

    victim, client = None, None
    if not args.mock:
        client = providers.judge_client()
        if client is None:
            print("No ANTHROPIC_API_KEY found. Re-run with --mock to try the "
                  "pipeline offline, or set the key for a real scan.",
                  file=sys.stderr)
            return 2
        try:
            victim = providers.build_victim(args.model)
        except Exception as e:
            print(f"Could not reach {args.model}: {e}", file=sys.stderr)
            return 2

    langs = [c.strip() for c in args.langs.split(",")] if args.langs else None
    cats = [c.strip() for c in args.categories.split(",")] if args.categories else None

    done = {"n": 0}

    def progress(d, t):
        if args.quiet:
            return
        if d == t or d - done["n"] >= max(1, t // 20):
            done["n"] = d
            print(f"\r  scanning {d}/{t}", end="", file=sys.stderr, flush=True)

    out = engine.scan(prompt, langs=langs, categories=cats, client=client,
                      victim=victim, mock=args.mock, model=args.model,
                      max_variants=args.phrasings, progress=progress,
                      with_controls=not args.no_controls)
    if not args.quiet:
        print(file=sys.stderr)

    payload = scan_payload(out, prompt, args)

    print(f"\nPolyGuard {VERSION}  victim: {payload['model']}")
    print_summary(out)

    exit_code = 0
    if args.baseline:
        base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        cmp = compare_scans(base, payload)
        payload["comparison"] = cmp
        print(f"\nCompared against {args.baseline}:")
        print_comparison(cmp)
        if cmp.get("regressed"):
            print("\n  REGRESSION: this bot is measurably easier to break than "
                  "the baseline.")
            if args.fail_on_regression:
                exit_code = 1

    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8",
            newline="\n")
        print(f"\n  wrote {args.out}")
    if args.html:
        from report_html import write_report
        write_report(payload, Path(args.html))
        print(f"  wrote {args.html}")
    return exit_code


def cmd_compare(args) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    cmp = compare_scans(before, after)
    print(f"\n{args.before} -> {args.after}")
    print_comparison(cmp)
    if not cmp["comparable"]:
        return 2
    return 1 if (cmp["regressed"] and args.fail_on_regression) else 0


def cmd_report(args) -> int:
    payload = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    from report_html import write_report
    write_report(payload, Path(args.html))
    print(f"wrote {args.html}")
    return 0


def cmd_models(args) -> int:
    """Which victim models are usable right now, and what each one still needs."""
    ready = set(providers.ready_model_keys())
    print(f"{len(ready)} of {len(providers.MODELS)} victim models are ready.")
    print()
    print(f"{'key':<20}{'vendor':<20}{'status':<34}pinnable")
    for st in providers.available_models():
        print(f"{st['key']:<20}{st['vendor']:<20}{st['reason']:<34}"
              f"{'yes' if st['deterministic'] else 'no'}")
    print()
    if not ready:
        print("No model is ready. Set ANTHROPIC_API_KEY, or use --mock to run "
              "the pipeline offline.")
    else:
        print(f"Scan one with:  python cli.py scan --prompt bot.txt "
              f"--model {sorted(ready)[0]}")
    print()
    print("'pinnable' means the model still accepts temperature=0. Where it does")
    print("not, results are samples rather than fixed values, and the scan says so.")
    return 0


def cmd_languages(args) -> int:
    bank = engine.load_bank()
    in_bank = set(bank["languages"])
    print(f"{len(CATALOG)} languages in the catalog, {len(in_bank)} in the bank.\n")
    print(f"{'code':<6}{'language':<20}{'tier':<7}{'joshi':<7}in bank")
    for code, m in sorted(CATALOG.items(), key=lambda kv: (kv[1]["tier"], kv[0])):
        print(f"{code:<6}{m['name']:<20}{m['tier']:<7}{m.get('joshi','?'):<7}"
              f"{'yes' if code in in_bank else '-'}")
    missing = [c for c in CATALOG if c not in in_bank]
    if missing:
        print(f"\n{len(missing)} language(s) not yet generated. "
              f"Run: python expand_languages.py --tier low")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="polyguard",
        description="Test whether a chatbot can be broken in languages other "
                    "than English.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit codes: 0 ok, 1 regression detected, 2 scan failed.")
    p.add_argument("--version", action="version", version=f"polyguard {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="scan a system prompt")
    src = s.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", help="file containing the system prompt, or - for stdin")
    src.add_argument("--prompt-text", help="the system prompt inline")
    s.add_argument("--model", default=providers.DEFAULT_MODEL,
                   help=f"victim model (default {providers.DEFAULT_MODEL})")
    s.add_argument("--langs", help="comma-separated language codes")
    s.add_argument("--categories", help="comma-separated attack categories")
    s.add_argument("--phrasings", type=int, default=3, choices=(1, 2, 3),
                   help="phrasings per category (default 3)")
    s.add_argument("--no-controls", action="store_true",
                   help="skip capability controls (not recommended)")
    s.add_argument("--baseline", help="a previous scan JSON to compare against")
    s.add_argument("--fail-on-regression", action="store_true",
                   help="exit 1 if the bot got measurably worse")
    s.add_argument("--out", help="write the scan JSON here")
    s.add_argument("--html", help="write a shareable HTML report here")
    s.add_argument("--mock", action="store_true",
                   help="run offline with simulated results, no API key needed")
    s.add_argument("--quiet", action="store_true", help="no progress output")
    s.set_defaults(func=cmd_scan)

    c = sub.add_parser("compare", help="compare two scan JSON files")
    c.add_argument("before")
    c.add_argument("after")
    c.add_argument("--fail-on-regression", action="store_true")
    c.set_defaults(func=cmd_compare)

    r = sub.add_parser("report", help="render a scan JSON as HTML")
    r.add_argument("scan")
    r.add_argument("--html", required=True)
    r.set_defaults(func=cmd_report)

    lg = sub.add_parser("languages", help="list the catalog and what is generated")
    lg.set_defaults(func=cmd_languages)

    md = sub.add_parser("models", help="which victim models are usable right now")
    md.set_defaults(func=cmd_models)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
