"""
Read-only smoke test of a deployed PolyGuard: production after a push, or a preview.

    python web/e2e/smoke_live.py https://polyguard-ten.vercel.app
    python web/e2e/smoke_live.py <preview URL> --review

It only reads. It loads pages and fetches /api/meta; it never presses a button that
runs a scan, saves a result or answers the game, so it leaves nothing behind in the
shared store. A protected preview needs Vercel's bypass secret: put it in the
environment as VERCEL_AUTOMATION_BYPASS_SECRET (it is sent as a header and never
printed). Exit code 0 when every check passes.

    --review       also check /review and /review/coverage
    --no-headers   skip the page security header checks (for a deploy older than them)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES: list[tuple[str, bool]] = []


def check(name: str, ok) -> None:
    CASES.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


def get(base: str, path: str, headers: dict) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(base + path, headers={"User-Agent": "polyguard-smoke", **headers})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, b""


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    base = args[0].rstrip("/")
    want_review, want_headers = "--review" in argv, "--no-headers" not in argv
    secret = os.environ.get("VERCEL_AUTOMATION_BYPASS_SECRET")
    extra = {"x-vercel-protection-bypass": secret} if secret else {}
    print(f"PolyGuard smoke test (read-only): {base}")

    status, hdr, body = get(base, "/", extra)
    check("the home page answers 200", status == 200)
    if want_headers:
        csp = hdr.get("content-security-policy", "")
        check("the home page carries the security headers (policy, no framing, nosniff)",
              "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
              and hdr.get("x-frame-options") == "DENY" and hdr.get("x-content-type-options") == "nosniff")
    status, hdr, body = get(base, "/api/meta", extra)
    meta = json.loads(body or b"{}") if status == 200 else {}
    counts = json.loads((ROOT / "web" / "src" / "bank-counts.json").read_text(encoding="utf-8"))
    check(f"/api/meta answers with {counts['languages']} languages, as this checkout's bank has",
          status == 200 and len(meta.get("languages", [])) == counts["languages"])
    if want_headers:
        check("the API is not sent the page policy", "content-security-policy" not in hdr)
    pages = ["/how", "/examples/real-scan-2026-10-11.html"] + (["/review", "/review/coverage"] if want_review else [])
    for path in pages:
        check(f"{path} answers 200", get(base, path, extra)[0] == 200)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1280, 390):
            ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844},
                                      reduced_motion="reduce", extra_http_headers=extra)
            page = ctx.new_page()
            errors, blocked = [], []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: blocked.append(m.text) if "Content Security Policy" in m.text else None)
            for path in ["/", "/how"] + (["/review", "/review/coverage"] if want_review else []):
                page.goto(base + path, wait_until="networkidle")
                page.wait_for_timeout(800)
                h1 = page.locator("main h1").first
                check(f"{width}px {path}: the page renders its heading", h1.count() == 1 and h1.inner_text().strip() != "")
                badge = page.locator("header").get_by_text("Simulated", exact=True)
                if not meta.get("live"):
                    check(f"{width}px {path}: the header says Simulated", badge.is_visible())
                check(f"{width}px {path}: nothing scrolls sideways",
                      not page.evaluate("document.documentElement.scrollWidth > innerWidth"))
            check(f"{width}px: no page errors{': ' + errors[0][:120] if errors else ''}", not errors)
            check(f"{width}px: nothing blocked by the policy{': ' + blocked[0][:120] if blocked else ''}", not blocked)
            ctx.close()
        browser.close()

    passed = sum(ok for _, ok in CASES)
    print(f"{passed}/{len(CASES)} smoke checks passed")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
