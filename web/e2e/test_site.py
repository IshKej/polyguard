"""
End-to-end tests for the web app, in a real browser.

    cd web && npm run build && cd ..
    python web/e2e/test_site.py                          # starts its own server on a free port
    python web/e2e/test_site.py https://polyguard-ten.vercel.app   # or test a deployment

Drives the site the way a person does: the landing page, the Motion switch, the
setup screen and its preflight, a simulated scan from launch to results, the
evidence download, a share link opened and deleted, a saved file opened again,
the game, the How we know page and the back button. Every screen is also checked
with axe-core, and any serious or critical accessibility violation fails the run.

The browser reports reduced motion, the way Windows does with Animation effects
off, because that is the setting that once froze the whole site.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
AXE = ROOT / "web" / "node_modules" / "axe-core" / "axe.min.js"
CASES: list[tuple[str, bool]] = []


def check(name, cond):
    CASES.append((name, bool(cond)))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}", flush=True)
    if not cond and os.environ.get("GITHUB_ACTIONS"):
        # An annotation, so a failure can be read from the run page and the API.
        print(f"::error title=browser test::{name}".replace("
", " ")[:900], flush=True)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server() -> tuple[str, subprocess.Popen]:
    """The API serving the built site, as one origin, with an in-memory store."""
    if not (ROOT / "web" / "dist" / "index.html").exists():
        raise SystemExit("Build the site first: cd web && npm run build")
    port = free_port()
    env = {k: v for k, v in os.environ.items()
           if k not in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "ANTHROPIC_API_KEY", "VERCEL")}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.server:app", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return base, proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise SystemExit("the local server did not start")


def axe(page, where: str) -> None:
    page.add_script_tag(path=str(AXE))
    found = page.evaluate("""async () => {
        const r = await axe.run(document, { resultTypes: ['violations'] });
        return r.violations.filter(v => v.impact === 'serious' || v.impact === 'critical')
                           .map(v => `${v.id} (${v.nodes.length}): ${v.help} e.g. ` +
                                v.nodes.slice(0, 2).map(n => n.html.slice(0, 90) + ' ' +
                                  ((n.any[0] || n.all[0] || {}).message || '').slice(0, 140)).join(' | '));
    }""")
    check(f"no serious accessibility problems on {where}" + (f": {found}" if found else ""), not found)


def main() -> int:
    base, proc = (sys.argv[1].rstrip("/"), None) if len(sys.argv) > 1 else start_server()
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce",
                                      accept_downloads=True)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))

            # --- landing --------------------------------------------------------------
            page.goto(base + "/", wait_until="networkidle")
            page.wait_for_timeout(1800)
            check("the landing page plays its motion even with reduced motion reported",
                  page.evaluate("document.documentElement.dataset.motion") == "on")
            first = page.locator("text=Now testing").locator("xpath=..").inner_text()
            page.wait_for_timeout(2900)
            check("the hero changes language on its own",
                  page.locator("text=Now testing").locator("xpath=..").inner_text() != first)
            axe(page, "the landing page")

            # --- the Motion switch ----------------------------------------------------
            page.get_by_role("button", name="Motion on").first.click()
            page.reload(wait_until="networkidle")
            check("switching motion off is remembered across a reload",
                  page.evaluate("document.documentElement.dataset.motion") == "off")
            page.get_by_role("button", name="Motion off").first.click()

            # --- setup and the preflight ------------------------------------------------
            page.get_by_role("button", name="Scan a chatbot").first.click()
            page.wait_for_url("**/scan")
            page.wait_for_timeout(1300)          # the highlighter wipe between screens takes 820 ms
            check("the preflight says nothing leaves the server on a simulated scan",
                  page.get_by_text("Nothing leaves this server").count() == 1)
            page.get_by_role("button", name="Quick").click()
            page.wait_for_timeout(500)           # let the buttons finish their colour change
            counts = page.get_by_text("harmless capability checks").inner_text()
            check("the preflight counts the attacks and checks for the chosen languages",
                  "capability checks" in counts and "languages" in counts)
            axe(page, "the setup screen")

            # --- a simulated scan, start to finish -------------------------------------
            page.get_by_role("button", name="Launch scan").click()
            page.wait_for_url("**/scan/results", timeout=60000)
            page.wait_for_timeout(800)
            check("a simulated scan reaches its results", page.get_by_text("Simulated scan").count() >= 1)
            check("the results say how complete the run was before any rate",
                  page.get_by_text("planned attacks ran and were scored").count() == 1)
            check("every chart is labelled simulated", page.locator(".tag", has_text="Simulated").count() >= 2)
            with page.expect_download() as dl:
                page.get_by_role("button", name="Download the evidence").click()
            path = Path(tempfile.mkdtemp()) / "evidence.json"
            dl.value.save_as(path)
            ev = json.loads(path.read_text(encoding="utf-8"))
            check("the evidence download is the full result with what produced it",
                  ev["schema"] == "polyguard.scan/1" and ev["instrument"]["bank_sha256"]
                  and len(ev["results"]) == ev["totals"]["attacks"] and "report" not in ev)
            axe(page, "the results screen")

            # --- a share link ---------------------------------------------------------
            page.get_by_role("button", name="Make a link").click()
            link = page.get_by_label("Share link")
            link.wait_for(timeout=10000)
            url = link.input_value()
            check("a share link is made", "/s/" in url)
            other = ctx.new_page()
            other.goto(url, wait_until="networkidle")
            other.wait_for_timeout(600)
            check("the link opens the same scan, read only, with the replies left out",
                  other.get_by_text("opened from a share link").count() == 1
                  and other.get_by_role("button", name="Scan the hardened prompt").count() == 0)
            page.get_by_role("button", name="Delete the link").click()
            page.get_by_text("The link is deleted.").wait_for(timeout=10000)
            other.reload(wait_until="networkidle")
            other.wait_for_timeout(600)
            check("a deleted link has nothing behind it", other.get_by_text("has nothing behind it").count() == 1)
            other.close()

            # --- opening the saved file again --------------------------------------------
            page.get_by_role("button", name="Scan another chatbot").click()
            page.wait_for_url("**/scan")
            page.locator("input[type=file]").set_input_files(str(path))
            page.wait_for_url("**/scan/results")
            page.get_by_text("Opened from a file on this computer").wait_for(timeout=5000)
            check("a downloaded scan opens again from the file, with no server involved",
                  page.get_by_text("Opened from a file on this computer").count() == 1)

            # --- the game -----------------------------------------------------------------
            page.goto(base + "/", wait_until="networkidle")
            page.locator("text=Spot the attack").scroll_into_view_if_needed()
            page.get_by_role("button", name=re.compile("an attack")).first.wait_for(timeout=15000)
            for n in range(6):
                page.get_by_role("button", name=re.compile("an attack")).first.click()
                page.wait_for_timeout(200)
                nxt = page.get_by_role("button", name="Next message")
                if nxt.count():
                    nxt.click()
                else:
                    page.get_by_role("button", name="See your score").click()
            page.get_by_text("Everyone else, in the same languages").wait_for(timeout=10000)
            check("the game ends with a score and the crowd's numbers",
                  page.get_by_text("Your score").count() == 1)

            # --- How we know, and the back button ----------------------------------------
            page.goto(base + "/how", wait_until="networkidle")
            page.wait_for_timeout(1200)
            check("the How we know page renders", page.get_by_text("What is not proven yet").count() == 1)
            axe(page, "the How we know page")
            page.go_back()
            page.wait_for_timeout(1200)
            check("the back button returns to the previous screen", page.url.rstrip("/") == base)

            check(f"no page errors anywhere{': ' + '; '.join(errors[:3]) if errors else ''}", not errors)
            browser.close()
    except Exception as e:
        check(f"the run itself did not crash: {type(e).__name__}: {str(e)[:300]}", False)
    finally:
        if proc:
            proc.terminate()
    passed = sum(1 for _, ok in CASES if ok)
    print(f"\n{passed}/{len(CASES)} browser tests passed")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
