"""
Rebuild the published example report, web/public/examples/real-scan-2026-10-11.html.

The page is the 2026-10-11 local scan as reanalysed on 2026-10-12, rendered by the
same report_html.build_report every scan uses, so no number on it is typed by
hand. Around it this adds only what a page on the site needs: the site's font, a
way back to the site, a status tag that says what kind of evidence this is, and a
short summary of what it is and is not. Run it after the report's look changes or
after another reanalysis; the evidence itself lives in results/local/2026-10-11/.

    python publish_example.py
"""
from __future__ import annotations

import json
from pathlib import Path

import report_html

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "results/local/2026-10-11/reanalysis-2026-10-12/scan.json"
OUT = ROOT / "web/public/examples/real-scan-2026-10-11.html"
EVIDENCE = "https://github.com/IshKej/polyguard/tree/main/results/local/2026-10-11"

FONT = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Mona+Sans:wdth,wght@75..125,200..900'
        '&display=swap" rel="stylesheet">')
EXTRA_CSS = ("<style>.back{display:flex;align-items:center;justify-content:space-between;gap:1rem;"
             "flex-wrap:wrap;margin:0 0 1.5rem}.back a{font-weight:600}"
             ".status{display:inline-block;border:1.5px solid var(--ink);padding:.15rem .5rem;"
             "font-size:.75rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase}"
             ".summary ul{margin:.6rem 0 0;padding-left:1.1rem}.summary li{margin:.35rem 0}</style>")


def summary(scan: dict) -> str:
    what = scan["analysis"]["what_changed"]
    p_before = what["primary_tier_test_p"]["before"]
    p_after = what["primary_tier_test_p"]["after"]
    items = [
        "<b>What:</b> the example retail support bot, running on Qwen3.5 4B, a small open model on a "
        "laptop. Not a production chatbot, and not the simulated demo.",
        "<b>When:</b> scanned 2026-10-11, all 73 languages. Reanalysed 2026-10-12 from the same saved "
        "replies under the current capability rule, with no new model calls.",
        f"<b>Judging:</b> a second small open model (Gemma 4 E2B) called {scan['attacks_broke']} of "
        f"{scan['attacks_fired']:,} attacks breaks. An AI assisted review of each of those, not yet "
        "checked by the author, kept 10.",
        "<b>Reanalysis:</b> Yoruba is left out (it followed 1 of its 6 harmless requests, English 5 of 6). "
        f"The tier test moves from p = {p_before:.3f} to p = {p_after:.3f}: no gap between low and high "
        "resource languages either way.",
        f'<b>Evidence:</b> every reply and both analyses are in <a href="{EVIDENCE}">results/local/2026-10-11</a>.',
    ]
    return ('<div class="note n-info summary"><b>A real local diagnostic, published as an example.</b><ul>'
            + "".join(f"<li>{i}</li>" for i in items) + "</ul></div>")


def build() -> str:
    scan = json.loads(SOURCE.read_text(encoding="utf-8"))
    page = report_html.build_report(scan)
    head_anchor = "<title>PolyGuard report</title>"
    body_anchor = "<body><main class=wrap>"
    assert page.count(head_anchor) == 1 and page.count(body_anchor) == 1
    page = page.replace(head_anchor, FONT + "<title>PolyGuard: a real local scan, 2026-10-11</title>" + EXTRA_CSS)
    back = ('<nav class="back" aria-label="Site"><a href="/">Back to PolyGuard</a>'
            '<span class="status">Real local diagnostic</span></nav>')
    return page.replace(body_anchor, body_anchor + back + summary(scan))


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
