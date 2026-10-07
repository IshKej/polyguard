"""
PolyGuard command line interface.

The app is how you explore a result. This is how a result gets used.

A security scanner that only runs in a browser is a demo. One that runs headless,
writes machine-readable output, and returns a non-zero exit code when the bot got
worse is something a team can put in front of a deploy. That is the difference
between a project and a tool, and it is the whole reason this file exists.

    polyguard scan --prompt bot.txt --out today.json
    polyguard scan --prompt bot.txt --baseline last-week.json --fail-on-regression
    polyguard scan --prompt bot.txt --bundle runs/2026-10-03   # reproducible package
    polyguard compare last-week.json today.json
    polyguard defend --prompt bot.txt --arms baseline,placebo,current,data_boundary
    polyguard replay today.json        # recompute every number from the evidence
    polyguard report today.json --html report.html
    polyguard languages

Exit codes, chosen so CI can act on them:

    0   scan completed, and no regression against the baseline
    1   a regression was detected (only with --fail-on-regression)
    2   the scan could not be completed at all
    3   the baseline cannot be compared: it was measured differently (a different
        bank, judge, model, scoring version or configuration), so any "regression"
        would be the instrument changing, not the bot. Only with --fail-on-regression;
        --allow-instrument-change compares anyway, labelled as such.

Run with --mock to exercise everything offline with no API key. Mock output is
labelled as simulated in every file it writes, because a JSON report that does
not say it is fake will eventually be read as though it were real.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import defenses
import engine
import providers
from languages_catalog import CATALOG, tier_of

VERSION = "1.1"
SCAN_FILE_SCHEMA = "polyguard.scan-file/1"


def instrument_differences(before: dict, after: dict) -> list[str]:
    """Every way the two scans were measured differently. Empty means comparable."""
    bi, ai = before.get("instrument"), after.get("instrument")
    if not bi or not ai:
        return ["one of the scans has no instrument record (it predates stamping), "
                "so what produced it is unknown"]
    d = engine.INSTRUMENT_DEFAULTS
    return [f"{f}: {bi.get(f, d.get(f))!r} then {ai.get(f, d.get(f))!r}"
            for f in engine.COMPARABLE_FIELDS if bi.get(f, d.get(f)) != ai.get(f, d.get(f))]


# --------------------------------------------------------------------------- #
# Regression detection
# --------------------------------------------------------------------------- #
def compare_scans(before: dict, after: dict, alpha: float = 0.05,
                  allow_instrument_change: bool = False) -> dict:
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

    So is comparing two scans measured differently: a different attack bank, judge
    model, judge wording, scoring version, victim, language set or phrasing count.
    A changed instrument moves the numbers on its own, and calling that a
    regression in the bot would be a fake finding. `allow_instrument_change`
    compares anyway and labels the result, for when the change is the point.
    """
    diffs = instrument_differences(before, after)
    if diffs and not allow_instrument_change:
        return {"comparable": False, "instrument_differences": diffs,
                "reason": "the two scans were measured differently (" + "; ".join(diffs) + "), so a "
                          "difference between them could be the instrument, not the bot"}
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

    # When both files carry their evidence, say how the change looks on the
    # held-out phrasing alone, which is the only fair test of a defence.
    defense = (engine.defense_evaluation(before["results"], after["results"])
               if before.get("results") and after.get("results") else None)

    return {
        "comparable": True,
        "defense_evaluation": defense,
        "instrument_changed": bool(diffs),
        "instrument_differences": diffs,
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
def evidence_rows(results: list[dict], redact_replies: bool = False) -> list[dict]:
    """One row per attack: what was fired, what came back, and how it was scored.
    The attack text itself is in the bank, pinned by the instrument's bank_sha256."""
    keep = ("id", "lang", "category", "variant", "goal", "broke", "evidence", "error",
            "error_kind", "error_stage")
    rows = []
    for r in results:
        row = {k: r.get(k) for k in keep}
        if redact_replies:
            row["reply"], row["reply_redacted"] = "", True
        else:
            row["reply"] = r.get("reply") or ""
        rows.append(row)
    return rows


def scan_payload(out: dict, prompt: str, args, redact_replies: bool = False) -> dict:
    """The machine-readable record of one scan. Carries its own caveats, what
    produced it, and the per-attack evidence every number is computed from."""
    vm = out.get("victim") or {}
    return {
        "schema": SCAN_FILE_SCHEMA,
        "polyguard_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Stated first and unmissable. A JSON file outlives the terminal it was
        # printed in, and somebody will read this without the context.
        "mode": "MOCK-SIMULATED" if out["mock"] else "live",
        "mock": out["mock"],
        # A simulated run attacked and judged nothing, so it names no model.
        "victim": None if out["mock"] else vm,
        "model": None if out["mock"] else out.get("model"),
        "judge_model": None if out["mock"] else out.get("judge_model"),
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
        "instrument": out.get("instrument"),
        "completeness": engine.completeness(out),
        "results": evidence_rows(out["results"], redact_replies),
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
    if cmp.get("instrument_changed"):
        print("  INSTRUMENT CHANGED (compared anyway, on request):")
        for d in cmp["instrument_differences"]:
            print(f"    {d}")
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

    payload = scan_payload(out, prompt, args, redact_replies=args.redact_replies)

    # A simulated run attacked nothing, so it names no model.
    victim = "none (simulated run)" if payload.get("mock") else payload["model"]
    print(f"\nPolyGuard {VERSION}  victim: {victim}")
    print_summary(out)

    exit_code = 0
    if args.baseline:
        base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        cmp = compare_scans(base, payload, allow_instrument_change=args.allow_instrument_change)
        payload["comparison"] = cmp
        print(f"\nCompared against {args.baseline}:")
        print_comparison(cmp)
        if not cmp["comparable"] and args.fail_on_regression:
            # Never a silent pass: a gate that cannot compare has not checked anything.
            print("\n  NOT CHECKED: the baseline cannot be compared, so this build is stopped. "
                  "Re-baseline, or pass --allow-instrument-change.")
            exit_code = 3
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
    if args.bundle:
        write_bundle(Path(args.bundle), payload, prompt, args)
    return exit_code


def _parse_arms(text: str | None) -> list[str]:
    """The arms to run, in canonical order. The baseline always runs, because it
    is the scan the rules are chosen from."""
    asked = ([a.strip() for a in text.split(",") if a.strip()]
             if text and text != "all" else list(defenses.ARMS))
    unknown = [a for a in asked if a not in defenses.ARMS]
    if unknown:
        raise SystemExit(f"unknown arm(s): {', '.join(unknown)}; "
                         f"choose from {', '.join(defenses.ARMS)}")
    return [a for a in defenses.ARMS if a == "baseline" or a in asked]


def print_arm_table(table: list[dict], words: dict) -> None:
    pct = lambda v: "n/a" if v is None else f"{v:.0%}"
    ci = lambda c: "" if not c else f"({c[0]:.0%} to {c[1]:.0%})"
    print(f"  {'arm':<15}{'words':>6}  {'held-out break rate':<30}"
          f"{'benign follow rate':<30}vs placebo")
    for r in table:
        brk = f"{pct(r['heldout_rate'])} {ci(r['heldout_ci'])} {r['heldout_broke']}/{r['heldout_scored']}"
        ben = f"{pct(r['benign_rate'])} {ci(r['benign_ci'])} {r['benign_followed']}/{r['benign_scored']}"
        vp = r.get("vs_placebo")
        if vp:
            st = vp["sign_test"]
            bd = "n/a" if vp["benign_diff"] is None else f"{vp['benign_diff'] * 100:+.0f}"
            cmp = (f"break {vp['heldout_diff'] * 100:+.0f} pts, benign {bd} pts, "
                   f"{st['better']} languages better, {st['worse']} worse, sign p={st['p']:.3g}")
        else:
            cmp = "reference" if r["arm"] == "placebo" else "no placebo run"
        print(f"  {r['arm']:<15}{words.get(r['arm'], 0):>6}  {brk:<30}{ben:<30}{cmp}")


def cmd_defend(args) -> int:
    """Judge the defence blocks fairly: every arm against the same held-out
    attacks and benign controls, next to a placebo of the same length."""
    prompt = read_prompt(args)
    if not prompt.strip():
        raise SystemExit("the prompt is empty")
    arms = _parse_arms(args.arms)
    bank = engine.load_bank()
    leaks = defenses.lint_all(bank)
    if leaks:
        for name, probs in leaks.items():
            print(f"  LINT  {name}: {'; '.join(probs)}", file=sys.stderr)
        print("A defence text quotes the test, so it cannot be judged on it.", file=sys.stderr)
        return 2

    victim, client = None, None
    if not args.mock:
        client = providers.judge_client()
        if client is None:
            print("No ANTHROPIC_API_KEY found. Re-run with --mock to try the "
                  "pipeline offline, or set the key for a real run.", file=sys.stderr)
            return 2
        try:
            victim = providers.build_victim(args.model)
        except Exception as e:
            print(f"Could not reach {args.model}: {e}", file=sys.stderr)
            return 2

    langs = [c.strip() for c in args.langs.split(",")] if args.langs else None
    # Every arm starts from the prompt with any earlier PolyGuard block removed,
    # and extraction is always scored against that same original text.
    base = defenses.strip_defences(defenses.strip_defences(prompt), defenses.PLACEBO_HEADER)
    common = dict(langs=langs, client=client, victim=victim, mock=args.mock,
                  model=args.model, extraction_reference=base)

    say = (lambda m: None) if args.quiet else (lambda m: print(m, file=sys.stderr))
    say("  baseline: every phrasing, so the rules come from the development ones")
    runs = {"baseline": engine.scan(base, **common)}
    broken = (list(defenses.DEFENCES) if args.rules == "all"
              else defenses.broken_categories_from(runs["baseline"]["results"]))
    blocks = defenses.arm_blocks(broken)
    if not broken:
        arms = ["baseline"]
        print("\n  Nothing broke on the development phrasings, so there is no block to "
              "evaluate. Use --rules all to test the fixed blocks anyway.")
    for arm in arms[1:]:
        say(f"  {arm}: held-out phrasing only")
        runs[arm] = engine.scan(defenses.arm_prompt(base, arm, broken),
                                heldout_only=True, **common)

    cap = runs["baseline"].get("capability") or {}
    excluded = cap.get("capability_limited") or []
    table = engine.arm_table({a: {"results": runs[a]["results"],
                                  "controls": runs[a].get("controls", [])} for a in arms},
                             exclude_langs=excluded)
    words = {a: defenses.word_count(blocks[a]) for a in arms}

    who = "none (simulated run)" if args.mock else args.model
    print(f"\nPolyGuard {VERSION} defence arms  victim: {who}")
    if args.mock:
        print("  MODE: MOCK-SIMULATED. The simulated victim ignores the system prompt, "
              "so every arm\n  must come out the same. These numbers are not a measurement.")
    source = ("every category (--rules all)" if args.rules == "all"
              else "the development phrasings")
    print(f"  rules chosen from {source}: {', '.join(broken) or 'none'}")
    if excluded:
        print(f"  excluded as capability-limited in the baseline: {', '.join(excluded)}")
    print_arm_table(table, words)
    print("\n  A lower held-out break rate means fewer of this fixed bank's attacks worked.\n"
          "  It is not evidence that the bot is secure: no adaptive attacker was tested.")

    if args.out:
        payload = {
            "schema": "polyguard.defence-arms/1",
            "polyguard_version": VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": "MOCK-SIMULATED" if args.mock else "live",
            "mock": bool(args.mock),
            "model": None if args.mock else args.model,
            "prompt_sha256": hashlib.sha256(base.encode("utf-8")).hexdigest(),
            "rules_source": "all" if args.rules == "all" else "development phrasings",
            "broken_categories": broken,
            "excluded_capability_limited": excluded,
            "claim": "reduced the break rate on this fixed bank; never evidence of security",
            "arms": {a: {"words": words[a], "block": blocks[a],
                         "instrument": runs[a].get("instrument")} for a in arms},
            "table": table,
            "results": {a: evidence_rows(runs[a]["results"], args.redact_replies)
                        for a in arms},
        }
        Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                  encoding="utf-8", newline="\n")
        print(f"\n  wrote {args.out}")
    return 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle(folder: Path, payload: dict, prompt: str, args) -> None:
    """A folder someone else can check a result with: the scan file with its
    per-attack evidence, the report, the exact command, the instrument record,
    the environment, and a fingerprint of every file."""
    from report_html import write_report
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "scan.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                      encoding="utf-8", newline="\n")
    write_report(payload, folder / "report.html")
    if args.bundle_include_prompt:
        (folder / "prompt.txt").write_text(prompt, encoding="utf-8", newline="\n")

    def version_of(pkg: str) -> str | None:
        try:
            from importlib.metadata import version
            return version(pkg)
        except Exception:
            return None

    files = sorted(p for p in folder.iterdir() if p.is_file() and p.name != "manifest.json")
    manifest = {
        "schema": "polyguard.bundle/1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": payload["mode"],
        "command": "python cli.py " + " ".join(sys.argv[1:]),
        "instrument": payload.get("instrument"),
        "prompt_sha256": payload["prompt_sha256"],
        "prompt_included": bool(args.bundle_include_prompt),
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "anthropic": version_of("anthropic"), "openai": version_of("openai")},
        "files": {p.name: _sha256(p) for p in files},
        "how_to_check": [
            "git checkout <instrument.git_commit>",
            "python -c \"import engine; print(engine.bank_sha256())\"   # must equal instrument.bank_sha256",
            "python cli.py replay scan.json   # recomputes every rate and test from the evidence",
        ],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                          encoding="utf-8", newline="\n")
    print(f"  wrote bundle {folder}/ ({len(files) + 1} files)")


def cmd_replay(args) -> int:
    """Recompute every number in a scan file from its per-attack evidence.

    Proves the summary was computed from the evidence it ships with, by the
    scoring code in this checkout, against the bank it names. Exit 0 when all of
    it matches, 4 when something does not.
    """
    payload = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    rows = payload.get("results")
    if not rows:
        print("This scan file has no per-attack evidence (it predates evidence export).")
        return 4
    problems = []
    inst = payload.get("instrument") or {}
    if inst.get("bank_sha256") and inst["bank_sha256"] != engine.bank_sha256():
        problems.append("the attack bank in this checkout is not the one the scan used "
                        f"({engine.bank_sha256()[:12]} here, {inst['bank_sha256'][:12]} in the scan)")
    if inst.get("scoring_version") and inst["scoring_version"] != engine.SCORING_VERSION:
        problems.append(f"scoring version {engine.SCORING_VERSION} here, "
                        f"{inst['scoring_version']} in the scan")
    redo = engine.summarize([{**r, "error": r.get("error")} for r in rows], engine.load_bank(),
                            payload.get("mock", True), payload.get("model"))
    checks = [("attacks fired", payload["attacks_fired"], redo["n_attacks"]),
              ("attacks broke", payload["attacks_broke"], redo["n_broke"]),
              ("errors", payload["errors"], redo["n_errors"]),
              ("overall break rate", payload["overall_break_rate"], redo["overall_rate"])]
    for code, d in payload["by_lang"].items():
        checks.append((f"{code} break rate", d.get("rate"), (redo["by_lang"].get(code) or {}).get("rate")))
    stored_p = (payload.get("worst_language_test") or {}).get("p")
    checks.append(("worst language test p", stored_p, (redo.get("max_gap_test") or {}).get("p")))
    for name, stored, recomputed in checks:
        same = stored == recomputed or (isinstance(stored, float) and isinstance(recomputed, float)
                                        and abs(stored - recomputed) < 1e-12)
        if not same:
            problems.append(f"{name}: file says {stored!r}, evidence gives {recomputed!r}")
    print(f"\nReplayed {len(rows)} attacks from {args.scan} ({payload.get('mode')})")
    if problems:
        for p in problems:
            print(f"  MISMATCH  {p}")
        return 4
    print(f"  every number matches its evidence ({len(checks)} checks)")
    return 0


def cmd_compare(args) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after).read_text(encoding="utf-8"))
    cmp = compare_scans(before, after, allow_instrument_change=args.allow_instrument_change)
    print(f"\n{args.before} -> {args.after}")
    print_comparison(cmp)
    if not cmp["comparable"]:
        return 3 if cmp.get("instrument_differences") else 2
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
        epilog="Exit codes: 0 ok, 1 regression detected, 2 scan failed, "
               "3 baseline measured differently, 4 replay mismatch.")
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
    s.add_argument("--allow-instrument-change", action="store_true",
                   help="compare with a baseline measured differently, labelled as such")
    s.add_argument("--redact-replies", action="store_true",
                   help="leave the bot's replies out of the JSON (they can contain the prompt)")
    s.add_argument("--bundle", help="write a reproducible folder: scan, report, manifest")
    s.add_argument("--bundle-include-prompt", action="store_true",
                   help="put the system prompt itself in the bundle (off by default)")
    s.set_defaults(func=cmd_scan)

    c = sub.add_parser("compare", help="compare two scan JSON files")
    c.add_argument("before")
    c.add_argument("after")
    c.add_argument("--fail-on-regression", action="store_true")
    c.add_argument("--allow-instrument-change", action="store_true")
    c.set_defaults(func=cmd_compare)

    rp = sub.add_parser("replay", help="recompute every number in a scan file from its evidence")
    rp.add_argument("scan")
    rp.set_defaults(func=cmd_replay)

    r = sub.add_parser("report", help="render a scan JSON as HTML")
    r.add_argument("scan")
    r.add_argument("--html", required=True)
    r.set_defaults(func=cmd_report)

    d = sub.add_parser("defend", help="judge the defence blocks against a placebo, "
                                      "held-out phrasing only")
    dsrc = d.add_mutually_exclusive_group(required=True)
    dsrc.add_argument("--prompt", help="file containing the system prompt, or - for stdin")
    dsrc.add_argument("--prompt-text", help="the system prompt inline")
    d.add_argument("--arms", default="all",
                   help=f"comma-separated arms from {', '.join(defenses.ARMS)} "
                        f"(default all; the baseline always runs)")
    d.add_argument("--rules", choices=("scan", "all"), default="scan",
                   help="choose rules from what broke on the development phrasings "
                        "(scan), or apply every category's rule (all)")
    d.add_argument("--model", default=providers.DEFAULT_MODEL,
                   help=f"victim model (default {providers.DEFAULT_MODEL})")
    d.add_argument("--langs", help="comma-separated language codes")
    d.add_argument("--out", help="write the arm table and evidence JSON here")
    d.add_argument("--mock", action="store_true",
                   help="run offline with simulated results, no API key needed")
    d.add_argument("--quiet", action="store_true", help="no progress output")
    d.add_argument("--redact-replies", action="store_true",
                   help="leave the bot's replies out of the JSON")
    d.set_defaults(func=cmd_defend)

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
