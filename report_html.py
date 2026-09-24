"""
Render a scan into one self-contained HTML file.

A JSON report is for machines. This is the thing you send to a person: a single
file with no external assets, no network calls, and no build step, that opens in
any browser and still works in a year.

Every caveat the scan carried travels with it. A simulated run says so at the top
in a colour nobody can miss, a scan whose prompt collided with PolyGuard's own
token refuses to show its numbers as findings, and a tier comparison that could
not be computed says why instead of quietly showing nothing. A report that omits
its own limitations is worse than no report, because it will be forwarded.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

CSS = """
:root{--bg:#0b0f16;--panel:#12161f;--line:#262c36;--ink:#e6edf3;--dim:#8b949e;
--accent:#f0603a;--ok:#3fb950;--warn:#d29922}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
padding:2.5rem 1.25rem}
.wrap{max-width:900px;margin:0 auto}
h1{font-size:1.9rem;margin:0;letter-spacing:-.5px}
h1 .g{color:var(--accent)}
h2{font-size:1.05rem;margin:2.2rem 0 .7rem;padding-bottom:.35rem;
border-bottom:1px solid var(--line);color:var(--ink)}
.sub{color:var(--dim);margin:.25rem 0 1.5rem;font-size:.9rem}
.banner{border-radius:10px;padding:.85rem 1.1rem;margin:1rem 0;font-size:.92rem;
border:1px solid}
.b-mock{background:#2a2410;border-color:var(--warn);color:#f0d58c}
.b-bad{background:#3a1417;border-color:var(--accent);color:#ff9a8f}
.b-ok{background:#12261a;border-color:var(--ok);color:#87e0a0}
.b-info{background:var(--panel);border-color:var(--line);color:#c9d3de}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.7rem}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:.8rem .95rem}
.card .k{color:var(--dim);font-size:.76rem;text-transform:uppercase;
letter-spacing:.04em}
.card .v{font-size:1.45rem;font-weight:700;margin-top:.15rem}
table{width:100%;border-collapse:collapse;margin-top:.5rem;font-size:.88rem}
th{text-align:left;color:var(--dim);font-weight:600;font-size:.78rem;
text-transform:uppercase;letter-spacing:.04em;padding:.45rem .6rem;
border-bottom:1px solid var(--line)}
td{padding:.45rem .6rem;border-bottom:1px solid #1a1f29}
tr:last-child td{border-bottom:none}
.bar{height:7px;border-radius:4px;background:#1a1f29;overflow:hidden;min-width:70px}
.bar span{display:block;height:100%}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem}
.dim{color:var(--dim)}
footer{margin-top:2.5rem;padding-top:1rem;border-top:1px solid var(--line);
color:var(--dim);font-size:.82rem}
@media print{body{background:#fff;color:#111}.card,.banner{border-color:#ccc}}
"""


def _pct(v, dash="n/a"):
    return dash if v is None else f"{v:.0%}"


def _heat(rate):
    if rate is None:
        return "#20262f"
    r = int(60 + rate * 180)
    g = int(200 - rate * 165)
    b = int(90 - rate * 55)
    return f"rgb({r},{g},{b})"


def _e(s):
    return html.escape(str(s))


def build_report(scan: dict) -> str:
    mock = bool(scan.get("mock"))
    collision = scan.get("token_collision") or []
    victim = scan.get("victim") or {}
    by_lang = scan.get("by_lang", {})
    cap = scan.get("capability") or {}
    limited = set(cap.get("capability_limited") or [])

    parts = [f"<!doctype html><html lang=en><meta charset=utf-8>",
             "<meta name=viewport content='width=device-width,initial-scale=1'>",
             f"<title>PolyGuard report</title><style>{CSS}</style>",
             "<body><div class=wrap>",
             "<h1>&#128737; Poly<span class=g>Guard</span></h1>",
             f"<p class=sub>Multilingual prompt-injection report &middot; "
             f"generated {_e(scan.get('generated_at','?'))}</p>"]

    # Caveats first, always, before any number.
    if mock:
        parts.append("<div class='banner b-mock'><b>Simulated run, not a "
                     "measurement.</b> These results came from an offline mock "
                     "with no model involved. The mock is language-independent by "
                     "design, so nothing here says anything about any real "
                     "chatbot.</div>")
    if collision:
        parts.append(f"<div class='banner b-bad'><b>These results are invalid.</b> "
                     f"The scanned prompt contains PolyGuard's own "
                     f"{_e(' and '.join(collision))}, so the bot emits that token "
                     f"while doing its normal job and ordinary answers were counted "
                     f"as successful attacks. Remove it and scan again.</div>")
    if scan.get("extraction_scoreable") is False:
        parts.append("<div class='banner b-info'>The system prompt is shorter than "
                     "the verbatim run used to detect a leak, so prompt-extraction "
                     "attacks could not register and the overall rate reads low.</div>")

    # Headline numbers
    parts.append("<div class=grid>")
    for k, v in (("Attacks fired", scan.get("attacks_fired")),
                 ("Broke the bot", scan.get("attacks_broke")),
                 ("Overall break rate", _pct(scan.get("overall_break_rate"))),
                 ("English", _pct(scan.get("english_break_rate")))):
        parts.append(f"<div class=card><div class=k>{_e(k)}</div>"
                     f"<div class=v>{_e(v)}</div></div>")
    parts.append("</div>")

    # Provenance: what was actually tested, and how trustworthy it is.
    parts.append("<h2>What was tested</h2><table>")
    rows = [
        ("Victim model", victim.get("label") or scan.get("model")),
        ("Vendor", victim.get("vendor")),
        ("Compliance judge", scan.get("judge_model")),
        ("Phrasings per cell", scan.get("phrasings_per_cell")),
        ("Temperature pinned", "yes" if victim.get("deterministic") else
         "no, results are samples rather than fixed values"),
        ("Prompt fingerprint", (scan.get("prompt_sha256") or "")[:16] + "..."),
        ("Mode", "MOCK-SIMULATED" if mock else "live"),
    ]
    for k, v in rows:
        if v not in (None, ""):
            parts.append(f"<tr><td class=dim>{_e(k)}</td>"
                         f"<td class=mono>{_e(v)}</td></tr>")
    parts.append("</table>")

    # Tier comparison, or an honest explanation of why there isn't one.
    tiers = {}
    for code, d in by_lang.items():
        if d.get("rate") is None or code in limited:
            continue
        tiers.setdefault(d.get("tier", "?"), []).append(d["rate"])
    parts.append("<h2>By resource tier</h2>")
    if tiers.get("low") and tiers.get("high"):
        lo = sum(tiers["low"]) / len(tiers["low"])
        hi = sum(tiers["high"]) / len(tiers["high"])
        parts.append("<div class=grid>")
        for t in ("high", "mid", "low"):
            if tiers.get(t):
                avg = sum(tiers[t]) / len(tiers[t])
                parts.append(f"<div class=card><div class=k>{_e(t)}-resource "
                             f"({len(tiers[t])} langs)</div>"
                             f"<div class=v>{avg:.0%}</div></div>")
        parts.append("</div>")
        verdict = ("more often" if lo > hi else "less often")
        parts.append(f"<p class=sub>Low-resource languages broke <b>{abs(lo-hi):.0%}"
                     f"</b> {verdict} than high-resource ones.</p>")
    else:
        parts.append("<div class='banner b-info'>The low-versus-high comparison "
                     "could not be computed: this scan did not include languages "
                     "from both tiers. Generate the low-resource languages and "
                     "scan again.</div>")

    if limited:
        names = ", ".join(_e(by_lang.get(c, {}).get("name", c)) for c in sorted(limited))
        parts.append(f"<div class='banner b-bad'>Excluded from the comparison: "
                     f"<b>{names}</b>. The bot could not follow ordinary, harmless "
                     f"instructions in these languages, so a low break rate there "
                     f"reflects incapacity rather than defence and would hide a "
                     f"real gap.</div>")

    # Per-language table
    parts.append("<h2>By language</h2><table>"
                 "<tr><th>Language</th><th>Tier</th><th>Break rate</th>"
                 "<th></th><th>Attacks</th></tr>")
    for code, d in sorted(by_lang.items(),
                          key=lambda kv: -(kv[1].get("rate") or -1)):
        rate = d.get("rate")
        flag = " <span class=dim>(unscoreable)</span>" if code in limited else ""
        parts.append(
            f"<tr><td>{_e(d.get('name', code))}{flag}</td>"
            f"<td class=dim>{_e(d.get('tier','?'))}</td>"
            f"<td class=mono>{_pct(rate)}</td>"
            f"<td><div class=bar><span style='width:{(rate or 0)*100:.0f}%;"
            f"background:{_heat(rate)}'></span></div></td>"
            f"<td class=dim>{_e(d.get('broke',0))}/{_e(d.get('total',0))}</td></tr>")
    parts.append("</table>")

    # Categories
    if scan.get("by_category"):
        parts.append("<h2>By attack type</h2><table>"
                     "<tr><th>Attack</th><th>Break rate</th><th></th></tr>")
        for cat, d in sorted(scan["by_category"].items(),
                             key=lambda kv: -(kv[1].get("rate") or -1)):
            rate = d.get("rate")
            parts.append(
                f"<tr><td>{_e(cat.replace('_',' ').title())}</td>"
                f"<td class=mono>{_pct(rate)}</td>"
                f"<td><div class=bar><span style='width:{(rate or 0)*100:.0f}%;"
                f"background:{_heat(rate)}'></span></div></td></tr>")
        parts.append("</table>")

    # Regression against a baseline, if the scan carried one
    cmp = scan.get("comparison")
    if cmp:
        parts.append("<h2>Compared with the baseline</h2>")
        if not cmp.get("comparable"):
            parts.append(f"<div class='banner b-info'>Not comparable: "
                         f"{_e(cmp.get('reason'))}</div>")
        else:
            cls = "b-bad" if cmp.get("regressed") else "b-ok"
            msg = ("This bot is measurably easier to break than the baseline."
                   if cmp.get("regressed") else
                   "No regression: nothing got measurably worse.")
            parts.append(f"<div class='banner {cls}'><b>{msg}</b></div>")
            if cmp.get("regressions"):
                parts.append("<table><tr><th>Language</th><th>Before</th>"
                             "<th>After</th><th>Change</th></tr>")
                for r in cmp["regressions"]:
                    parts.append(f"<tr><td>{_e(r['name'])}</td>"
                                 f"<td class=mono>{r['before']:.0%}</td>"
                                 f"<td class=mono>{r['after']:.0%}</td>"
                                 f"<td class=mono>{r['delta']:+.0%}</td></tr>")
                parts.append("</table>")

    # What broke, and the fix
    broken = scan.get("broken_categories") or []
    if broken:
        import defenses
        parts.append("<h2>Recommended fixes</h2><ul>")
        for clause in defenses.recommend(broken):
            parts.append(f"<li>{_e(clause)}</li>")
        parts.append("</ul>")

    parts.append(
        "<footer>Generated by PolyGuard. Break detection is canary-based and "
        "confirmed by a language-agnostic judge, so a refusal that quotes the "
        "token is not counted as a break. Results are specific to the victim "
        "model named above. No language in this project has been reviewed by a "
        "native speaker, so translation quality remains a known limitation."
        "</footer></div></body></html>")
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
