"""
Rebuild the published example report, web/public/examples/real-scan-2026-10-11.html.

The page is the 2026-10-11 local scan as reanalysed on 2026-10-12, rendered by the
same report_html.build_report every scan uses, so no number on it is typed by
hand. Around it this adds only what a page on the site needs: the site's font, a
way back to the site, a status tag that says what kind of evidence this is, and a
short summary of what it is and is not. Run it after the report's look changes or
after another reanalysis; the evidence itself lives in results/local/2026-10-11/.

It also writes web/src/local-example.json, the numbers and replies the home page
shows from the same scan (the hero's English and Welsh example and the graded
sheet), so the site never types them by hand either.

    python publish_example.py
"""
from __future__ import annotations

import json
from pathlib import Path

import report_html
from examples import EXAMPLES

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "results/local/2026-10-11/reanalysis-2026-10-12/scan.json"
REVIEW = ROOT / "results/local/2026-10-11/HAND_REVIEW.md"
OUT = ROOT / "web/public/examples/real-scan-2026-10-11.html"
SITE_DATA = ROOT / "web/src/local-example.json"
# The translation scores as they stood for the bank this scan sent (4e2ba320...),
# kept beside the scan so later bank edits cannot change what its report shows.
TQ_AT_SCAN = ROOT / "results/local/2026-10-11/translation_quality-at-scan.json"
HERO_PAIR = ("en_instruction_override_0", "cy_instruction_override_0")
EVIDENCE = "https://github.com/IshKej/polyguard/tree/main/results/local/2026-10-11"

# The site's own fonts, served from the site (web/public/fonts), like every other page.
FONT = ('<link rel="preload" href="/fonts/mona-sans-latin.woff2" as="font" type="font/woff2" crossorigin>'
        '<link rel="preload" href="/fonts/gloock-latin.woff2" as="font" type="font/woff2" crossorigin>'
        '<link rel="stylesheet" href="/fonts/fonts.css">')
# The site's look around the report: an ink bar with the wordmark and the way back,
# the highlighter status tag, the site's display weight on the headings and an ink
# footer. The report inside (report_html.build_report) is untouched, numbers and
# labels included.
EXTRA_CSS = ("<style>"
             "body{padding-top:0}"
             ".site{background:var(--ink);color:var(--bg);margin:0 -1.25rem 3rem;padding:1rem 1.25rem}"
             ".site .in{max-width:880px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;"
             "gap:1rem;flex-wrap:wrap}"
             ".site a{color:var(--bg)}"
             ".wm{display:inline-flex;flex-direction:column;line-height:.82;text-decoration:none}"
             ".wm .s{font-family:Gloock,Georgia,serif;font-size:1.45rem;letter-spacing:-.01em}"
             ".wm .h{font-weight:800;font-stretch:104%;text-transform:uppercase;font-size:1.45rem;letter-spacing:-.01em}"
             ".site .right{display:flex;align-items:center;gap:1.1rem;flex-wrap:wrap}"
             ".site .right a{font-weight:600;font-size:.9375rem;text-underline-offset:4px}"
             ".status{display:inline-block;background:var(--hi);color:var(--ink);padding:.3rem .55rem;border-radius:3px;"
             "font-size:.75rem;font-weight:800;font-stretch:104%;letter-spacing:.02em;text-transform:uppercase}"
             "h1,h2{font-weight:760}"
             ".mark{display:none}"
             ".summary ul{margin:.6rem 0 0;padding-left:1.1rem}.summary li{margin:.35rem 0}"
             "footer{background:var(--ink);color:var(--bg);border-top:0;margin:4.5rem -1.25rem -4rem;"
             "padding:2rem 1.25rem 2.5rem}"
             "footer a{color:var(--bg)}"
             "@media print{.site,footer{background:none;color:inherit}.site a,footer a{color:inherit}}"
             "</style>")


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
    tq = json.loads(TQ_AT_SCAN.read_text(encoding="utf-8"))
    assert tq["bank_sha256"] == scan["instrument"]["bank_sha256"], "scores must be for the scan's own bank"
    page = report_html.build_report(scan, tq_data=tq)
    head_anchor = "<title>PolyGuard report</title>"
    body_anchor = "<body><main class=wrap>"
    assert page.count(head_anchor) == 1 and page.count(body_anchor) == 1
    page = page.replace(head_anchor, FONT + "<title>PolyGuard: a real local scan, 2026-10-11</title>" + EXTRA_CSS)
    back = ('<header class="site"><nav class="in" aria-label="Site">'
            '<a class="wm" href="/" aria-label="PolyGuard home"><span class="s">Poly</span><span class="h">Guard</span></a>'
            '<span class="right"><span class="status">Real local diagnostic</span>'
            '<a href="/">Back to PolyGuard</a></span></nav></header>')
    return page.replace("<body><main class=wrap>", "<body>" + back + "<main class=wrap>" + summary(scan))


def reviewer_verdicts() -> dict[str, str]:
    """Attack id to the reviewer's verdict ("break" or "hold"), from the table in
    HAND_REVIEW.md: | Attack | Judge 1 | Judge 2 | Reviewer | Why |."""
    out = {}
    for line in REVIEW.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[1] in ("break", "hold") and cells[3] in ("break", "hold"):
            out[cells[0]] = cells[3]
    return out


def site_data() -> dict:
    scan = json.loads(SOURCE.read_text(encoding="utf-8"))
    bank = json.loads((ROOT / "attack_bank.json").read_text(encoding="utf-8"))
    text = {a["id"]: a["text"] for a in bank["attacks"]}
    res = {r["id"]: r for r in scan["results"]}
    verdict = reviewer_verdicts()
    judged = [r["id"] for r in scan["results"] if r["broke"]]
    assert sorted(judged) == sorted(verdict), "HAND_REVIEW.md must cover every judged break"
    kept = [i for i in judged if verdict[i] == "break"]
    cap = scan["capability"]
    excluded = cap["capability_limited"]
    per_lang = {}
    for code, l in scan["by_lang"].items():
        per_lang[code] = {
            "name": l["name"], "native": l["native"], "tier": l["tier"], "attacks": l["total"],
            "kept": sum(res[i]["lang"] == code for i in kept),
            "overturned": sum(res[i]["lang"] == code and verdict[i] == "hold" for i in judged),
            "excluded": code in excluded, "machine": l["provenance"] == "machine",
        }
    hero = {}
    for i in HERO_PAIR:
        r = res[i]
        hero[r["lang"]] = {"attack": text[i], "reply": r["reply"], "outcome": r["outcome"],
                           "kept": i in kept}
    first = {code: cap["per_lang"][code] for code in excluded}
    return {
        "date": scan["generated_at"][:10], "scanned": "2026-10-11",
        "model": "Qwen3.5 4B", "judge": "Gemma 4 E2B",
        "system_prompt": ". ".join(EXAMPLES["Retail support bot"].split(". ")[:3]) + ".",
        "hero": hero,
        "attacks": scan["attacks_fired"], "per_language": scan["attacks_fired"] // len(scan["by_lang"]),
        "judged_breaks": len(judged), "kept": len(kept),
        "kept_extraction": sum(res[i]["category"] == "system_prompt_extraction" for i in kept),
        "tier_p": round(scan["analysis"]["what_changed"]["primary_tier_test_p"]["after"], 3),
        "excluded": [{"code": c, "followed": first[c]["followed"], "of": first[c]["n"]} for c in excluded],
        "english_followed": cap["per_lang"]["en"]["followed"], "english_of": cap["per_lang"]["en"]["n"],
        "languages": per_lang,
    }


def site_json() -> str:
    return json.dumps(site_data(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    SITE_DATA.write_text(site_json(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} and {SITE_DATA.relative_to(ROOT)}")
