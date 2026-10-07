"""
Render a scan into one self-contained HTML file.

A JSON report is for machines. This is the thing you send to a person: a single
file with no external assets, no network calls, and no build step, that opens in
any browser and still works in a year. It uses the system font of whatever
machine opens it, follows that machine's light or dark setting, and prints on
white.

Every caveat the scan carried travels with it. A simulated run says so at the top
before any number, a scan whose prompt collided with PolyGuard's own token refuses
to show its numbers as findings, and a tier comparison that could not be computed
says why instead of quietly showing nothing. A report that omits its own
limitations is worse than no report, because it will be forwarded.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

REPO_URL = "https://github.com/IshKej/polyguard"

CSS = """
:root{color-scheme:dark;--bg:#000;--tile:#1d1d1f;--raised:#2c2c2e;--ink:#f5f5f7;
--quiet:#86868b;--line:#424245;--red:#ff453a;--green:#30d158;--yellow:#ffd60a;
--blue:#2997ff;--base:#86868b}
@media (prefers-color-scheme:light){:root{color-scheme:light;--bg:#fff;--tile:#f5f5f7;
--raised:#e8e8ed;--ink:#1d1d1f;--quiet:#6e6e73;--line:#d2d2d7;--red:#d70015;
--green:#248a3d;--yellow:#b25000;--blue:#0066cc;--base:#86868b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:17px/1.47 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI Variable Text",
"Segoe UI",Roboto,"Helvetica Neue",sans-serif;-webkit-font-smoothing:antialiased;
padding:3.5rem 1.25rem 4rem}
.wrap{max-width:880px;margin:0 auto}
.mark{font-weight:600;font-size:1.0625rem;letter-spacing:-.01em;margin:0}
h1{font-size:clamp(2.25rem,6vw,3.5rem);line-height:1.05;letter-spacing:-.03em;
font-weight:600;margin:2.5rem 0 .6rem}
.sub{color:var(--quiet);margin:0 0 2.5rem;font-size:1.0625rem}
h2{font-size:1.75rem;letter-spacing:-.022em;font-weight:600;margin:4rem 0 1.1rem}
.note{background:var(--tile);border-radius:18px;padding:1.1rem 1.3rem;margin:.9rem 0;
font-size:.9375rem;line-height:1.55}
.note b{font-weight:600}
.n-mock b{color:var(--yellow)}.n-bad b{color:var(--red)}.n-ok b{color:var(--green)}
.n-info b{color:var(--blue)}
.specs{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0 2rem}
.spec{border-top:1px solid var(--line);padding:1rem 0 1.25rem}
.spec .k{color:var(--quiet);font-size:.875rem}
.spec .v{font-size:2.75rem;font-weight:600;letter-spacing:-.03em;line-height:1.1;
margin-top:.3rem;font-variant-numeric:tabular-nums}
.spec .c{color:var(--quiet);font-size:.8125rem;margin-top:.25rem}
dl{display:grid;grid-template-columns:minmax(10rem,14rem) 1fr;gap:0;margin:0}
dt,dd{margin:0;padding:.7rem 0;border-top:1px solid var(--line);font-size:.9375rem}
dt{color:var(--quiet)}
dd{overflow-wrap:anywhere}
table{width:100%;border-collapse:collapse;font-size:.9375rem}
th{text-align:left;color:var(--quiet);font-weight:400;font-size:.8125rem;
padding:0 .75rem .6rem 0}
td{padding:.55rem .75rem .55rem 0;border-top:1px solid var(--line);vertical-align:middle}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.nat{color:var(--quiet);font-size:.8125rem;margin-left:.4rem}
.dim{color:var(--quiet)}
.bar{height:.5rem;border-radius:99px;background:var(--raised);overflow:hidden;min-width:5rem}
.bar span{display:block;height:100%;border-radius:99px;background:var(--red)}
.bar.base span{background:var(--base)}
ul.fix{padding-left:1.1rem;margin:0}
ul.fix li{margin:.45rem 0;font-size:.9375rem}
footer{margin-top:4.5rem;padding-top:1.25rem;border-top:1px solid var(--line);
color:var(--quiet);font-size:.8125rem;line-height:1.6}
footer a{color:var(--quiet)}
@media (max-width:560px){dl{grid-template-columns:1fr}dd{border-top:none;padding-top:0}
.hide-sm{display:none}}
@media print{:root{color-scheme:light;--bg:#fff;--tile:#f5f5f7;--raised:#e8e8ed;
--ink:#000;--quiet:#555;--line:#ccc}body{padding:0}h2{break-after:avoid}
tr,.note,.spec{break-inside:avoid}}
"""


def _pct(v, dash="n/a"):
    return dash if v is None else f"{v:.0%}"


def _e(s):
    return html.escape(str(s))


def _bar(rate, baseline=False):
    width = max(0.0, min(1.0, rate or 0)) * 100
    return (f"<div class=\"bar{' base' if baseline else ''}\" role=\"img\" "
            f"aria-label=\"{_pct(rate)}\"><span style=\"width:{width:.0f}%\"></span></div>")


def _spec(label, value, caption=""):
    cap = f'<div class="c">{_e(caption)}</div>' if caption else ""
    return (f'<div class="spec"><div class="k">{_e(label)}</div>'
            f'<div class="v">{_e(value)}</div>{cap}</div>')


def _tq_cell(code: str, d: dict, data: dict | None) -> str:
    """Per-language translation proxy text; says why when there is none."""
    import tq_report
    if code == "en":
        return "source language"
    q = tq_report.lang_quality(code, data or {})
    if not q:
        return "not scored"
    src = "machine translated" if d.get("provenance") == "machine" else "author written"
    return f"{q['summary']}; {src}"


def build_report(scan: dict) -> str:
    mock = bool(scan.get("mock"))
    collision = scan.get("token_collision") or []
    victim = scan.get("victim") or {}
    by_lang = scan.get("by_lang", {})
    cap = scan.get("capability") or {}
    limited = set(cap.get("capability_limited") or [])
    against = "a simulated victim" if mock else (victim.get("label") or scan.get("model") or "?")

    parts = ["<!doctype html><html lang=en><meta charset=utf-8>",
             "<meta name=viewport content='width=device-width,initial-scale=1'>",
             f"<title>PolyGuard report</title><style>{CSS}</style>",
             "<body><main class=wrap>",
             '<p class="mark">PolyGuard</p>',
             "<h1>Scan report</h1>",
             f'<p class="sub">{_e(scan.get("attacks_fired", 0))} attacks against '
             f'{_e(against)}. Generated {_e(scan.get("generated_at", "?"))}.</p>']

    # Caveats first, always, before any number.
    if mock:
        parts.append('<div class="note n-mock"><b>Simulated run, not a measurement.</b> '
                     "These results came from an offline mock with no model involved. The "
                     "mock is the same in every language by design, so nothing here says "
                     "anything about any real chatbot.</div>")
    if collision:
        parts.append(f'<div class="note n-bad"><b>These results are invalid.</b> The '
                     f"scanned prompt contains PolyGuard's own {_e(' and '.join(collision))}, "
                     f"so the bot emits that token while doing its normal job and ordinary "
                     f"answers were counted as successful attacks. Remove it and scan "
                     f"again.</div>")
    if scan.get("extraction_scoreable") is False:
        parts.append('<div class="note n-info"><b>Prompt extraction could not register.</b> '
                     "The system prompt is shorter than the verbatim run used to detect a "
                     "leak, so those attacks could not score as broken and the overall rate "
                     "reads low.</div>")

    # Headline numbers
    parts.append('<div class="specs">')
    parts.append(_spec("Attacks fired", scan.get("attacks_fired", 0)))
    parts.append(_spec("Broke the bot", scan.get("attacks_broke", 0),
                       f"{_pct(scan.get('overall_break_rate'))} of attacks"))
    parts.append(_spec("English break rate", _pct(scan.get("english_break_rate")),
                       "The baseline"))
    parts.append("</div>")

    # Provenance: what was actually tested, and how trustworthy it is.
    parts.append("<h2>What was tested</h2><dl>")
    # A simulated run attacked nothing and judged nothing. Naming the model it
    # would have attacked, or saying its temperature was pinned, would let a
    # forwarded copy of this file read as a real test of that model.
    rows = [("Victim model", "none, this was a simulated run"),
            ("Phrasings per cell", scan.get("phrasings_per_cell")),
            ("Mode", "MOCK-SIMULATED")] if mock else [
        ("Victim model", victim.get("label") or scan.get("model")),
        ("Vendor", victim.get("vendor")),
        ("Compliance judge", scan.get("judge_model")),
        ("Phrasings per cell", scan.get("phrasings_per_cell")),
        ("Temperature pinned", "yes" if victim.get("deterministic") else
         "no, results are samples rather than fixed values"),
        ("Reasoned before answering",
         "yes, this model cannot switch thinking off, so it is not directly "
         "comparable with a victim that answers immediately"
         if victim.get("thinking_forced") else None),
        ("Prompt fingerprint", ((scan.get("prompt_sha256") or "")[:16] + "...")
         if scan.get("prompt_sha256") else None),
        ("Mode", "MOCK-SIMULATED" if mock else "live"),
    ]
    for k, v in rows:
        if v not in (None, ""):
            parts.append(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>")
    parts.append("</dl>")

    # Tier comparison, or a plain explanation of why there isn't one.
    tiers: dict[str, list[float]] = {}
    for code, d in by_lang.items():
        if d.get("rate") is None or code in limited:
            continue
        tiers.setdefault(d.get("tier", "?"), []).append(d["rate"])
    parts.append("<h2>By resource tier</h2>")
    if tiers.get("low") and tiers.get("high"):
        lo = sum(tiers["low"]) / len(tiers["low"])
        hi = sum(tiers["high"]) / len(tiers["high"])
        parts.append('<div class="specs">')
        for t in ("high", "mid", "low"):
            if tiers.get(t):
                avg = sum(tiers[t]) / len(tiers[t])
                parts.append(_spec(f"{t.capitalize()} resource", f"{avg:.0%}",
                                   f"{len(tiers[t])} languages"))
        parts.append("</div>")
        direction = "more often" if lo > hi else "less often"
        parts.append(f'<p class="dim">Low resource languages broke {abs(lo - hi):.0%} '
                     f"{direction} than high resource ones, averaged per language. "
                     f"Whether that is more than chance is tested in the app and the "
                     f"JSON export, not asserted here.</p>")
    else:
        parts.append('<div class="note n-info"><b>No tier comparison.</b> This scan did not '
                     "include languages from both the low and high resource tiers, so the "
                     "comparison could not be computed. Generate the low resource languages "
                     "and scan again.</div>")

    if limited:
        names = ", ".join(_e(by_lang.get(c, {}).get("name", c)) for c in sorted(limited))
        parts.append(f'<div class="note n-bad"><b>Left out of the comparison: {names}.</b> '
                     f"The bot could not follow ordinary, harmless instructions in these "
                     f"languages, so a low break rate there reflects incapacity rather than "
                     f"defence and would hide a real gap.</div>")

    # Per-language table, most broken first, English drawn as the baseline.
    # Translation quality sits beside every rate, because a garbled attack can
    # fail for reasons unrelated to the bot. It is an automated proxy (language ID
    # and embedding similarity), never a validation, and is labelled as such.
    import tq_report
    tq_data = tq_report.load()
    parts.append("<h2>By language</h2><table><thead><tr><th>Language</th>"
                 "<th class=hide-sm>Tier</th><th></th><th class=num>Broke</th>"
                 "<th class=num>Rate</th>"
                 "<th class=hide-sm>Translation check (automated proxy)</th>"
                 "</tr></thead><tbody>")
    for code, d in sorted(by_lang.items(), key=lambda kv: -(kv[1].get("rate") or -1)):
        rate = d.get("rate")
        native = d.get("native")
        nat = f'<span class="nat" dir="auto">{_e(native)}</span>' if native else ""
        flag = ' <span class="dim">(not scoreable)</span>' if code in limited else ""
        parts.append(
            f"<tr><td>{_e(d.get('name', code))}{nat}{flag}</td>"
            f"<td class='dim hide-sm'>{_e(d.get('tier', '?'))}</td>"
            f"<td style='width:34%'>{_bar(rate, baseline=(code == 'en'))}</td>"
            f"<td class='num dim'>{_e(d.get('broke', 0))} of {_e(d.get('total', 0))}</td>"
            f"<td class=num>{_pct(rate)}</td>"
            f"<td class='dim hide-sm' style='font-size:.8125rem'>{_e(_tq_cell(code, d, tq_data))}</td>"
            "</tr>")
    parts.append("</tbody></table>")
    parts.append('<p class="dim" style="font-size:.8125rem">Translation check: an '
                 "automated proxy, not a validation. LID is the share of this "
                 "language's strings that GlotLID identified as the intended language; "
                 "LaBSE is the mean similarity to the English original and its margin "
                 "over unrelated English strings. They catch the wrong language and "
                 "gross meaning drift, not fluency or whether an attack still reads as "
                 "an instruction. Scores and rules: translation_quality.json.</p>")
    if "en" in by_lang:
        parts.append('<p class="dim" style="font-size:.8125rem">English, in grey, is the '
                     "baseline every other language is compared against.</p>")

    # Attack types
    if scan.get("by_category"):
        parts.append("<h2>By attack type</h2><table><thead><tr><th>Attack type</th><th></th>"
                     "<th class=num>Rate</th></tr></thead><tbody>")
        for cat, d in sorted(scan["by_category"].items(),
                             key=lambda kv: -(kv[1].get("rate") or -1)):
            rate = d.get("rate")
            parts.append(f"<tr><td>{_e(cat.replace('_', ' ').capitalize())}</td>"
                         f"<td style='width:40%'>{_bar(rate)}</td>"
                         f"<td class=num>{_pct(rate)}</td></tr>")
        parts.append("</tbody></table>")

    # Regression against a baseline, if the scan carried one
    cmp = scan.get("comparison")
    if cmp:
        parts.append("<h2>Compared with the baseline</h2>")
        if not cmp.get("comparable"):
            parts.append(f'<div class="note n-info"><b>Not comparable.</b> '
                         f"{_e(cmp.get('reason'))}</div>")
        else:
            if cmp.get("regressed"):
                parts.append('<div class="note n-bad"><b>Regression.</b> This bot is '
                             "measurably easier to break than the baseline.</div>")
            else:
                parts.append('<div class="note n-ok"><b>No regression.</b> Nothing got '
                             "measurably worse.</div>")
            if cmp.get("regressions"):
                parts.append("<table><thead><tr><th>Language</th><th class=num>Before</th>"
                             "<th class=num>After</th><th class=num>Change</th></tr>"
                             "</thead><tbody>")
                for r in cmp["regressions"]:
                    parts.append(f"<tr><td>{_e(r['name'])}</td>"
                                 f"<td class=num>{r['before']:.0%}</td>"
                                 f"<td class=num>{r['after']:.0%}</td>"
                                 f"<td class=num>{r['delta']:+.0%}</td></tr>")
                parts.append("</tbody></table>")

    # What broke, and the fix
    broken = scan.get("broken_categories") or []
    if broken:
        import defenses
        parts.append("<h2>Recommended fixes</h2><ul class=fix>")
        for clause in defenses.recommend(broken):
            parts.append(f"<li>{_e(clause)}</li>")
        parts.append("</ul>")

    parts.append(
        "<footer>Generated by PolyGuard. A break is counted only when a judge that reads "
        "any language decides the bot complied, so a refusal that quotes the code word is "
        "not a break. Results are specific to the victim model named above. No language "
        "in this project has been reviewed by a native speaker yet, so translation quality "
        "remains a known limitation. "
        f'<a href="{REPO_URL}">Source, audit and preregistration</a>.'
        "</footer></main></body></html>")
    return "".join(parts)


def write_report(scan: dict, path: Path) -> Path:
    path.write_text(build_report(scan), encoding="utf-8", newline="\n")
    return path


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        raise SystemExit("usage: python report_html.py scan.json out.html")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(write_report(data, Path(sys.argv[2])))
