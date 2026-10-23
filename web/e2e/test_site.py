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
off. The site follows it by default (a still page) and the Motion switch is the
explicit way to turn motion on, remembered across reloads.
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
        print(f"::error title=browser test::{name}".replace(chr(10), " ")[:900], flush=True)


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
    log = open(Path(tempfile.gettempdir()) / "polyguard-e2e-server.log", "w+", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.server:app", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60          # a cold CI machine imports slowly
    while time.time() < deadline and proc.poll() is None:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return base, proc
        except OSError:
            time.sleep(0.25)
    proc.kill()
    log.seek(0)
    tail = log.read()[-1500:]
    print(tail)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::error title=browser test::the local server did not start: " + tail.replace(chr(10), " | ")[-800:])
    raise SystemExit("the local server did not start")


def axe(page, where: str) -> None:
    # Measure the page at rest: no hover, no colour change half finished.
    page.mouse.move(1, 1)
    page.wait_for_timeout(500)
    # Loaded through the devtools protocol, not as a <script> tag: the site's policy
    # blocks inline scripts, and the test must not need it relaxed.
    if not page.evaluate("typeof window.axe !== 'undefined'"):
        page.evaluate(AXE.read_text(encoding="utf-8") + "\n;window.axe = axe; true")
    found = page.evaluate("""async () => {
        const r = await axe.run(document, { resultTypes: ['violations'], preload: false });
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
            # The page headers (vercel.json) are served locally too: anything they block shows here.
            csp = []
            page.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)

            # --- landing --------------------------------------------------------------
            page.goto(base + "/", wait_until="networkidle")
            page.wait_for_timeout(1800)
            check("with reduced motion reported, the landing page is still by default",
                  page.evaluate("document.documentElement.dataset.motion") == "off")
            check("and nothing on it animates on its own: no running animations, the hero's four steps all shown at once",
                  page.evaluate("document.getAnimations().filter(a => a.playState === 'running').length") == 0
                  and page.locator("figure[data-played]").get_attribute("data-played") == "4")
            check("with motion off, How a scan works is still steps, not a pinned scroll story",
                  page.locator("#how").get_attribute("style") is None)
            axe(page, "the landing page")

            # --- the Motion switch ----------------------------------------------------
            page.get_by_role("button", name="Motion off").first.click()
            page.wait_for_timeout(300)
            check("the Motion switch turns motion on even though the system asks for less",
                  page.evaluate("document.documentElement.dataset.motion") == "on")
            page.evaluate("window.scrollTo(0, 0)")
            early = page.locator("figure[data-played]").get_attribute("data-played")
            # The worked attack is chapter 01, below the hero: it plays when it comes into view.
            page.locator("figure[data-played]").scroll_into_view_if_needed()
            page.wait_for_timeout(3200)
            check("with motion turned on, the hero's four steps play in order once (input, boundary, reply, verdict)",
                  early != "4" and page.locator("figure[data-played]").get_attribute("data-played") == "4")
            check("with motion on, How a scan works is the pinned scroll story (a tall section that plays as you scroll)",
                  "height" in (page.locator("#how").get_attribute("style") or ""))
            page.reload(wait_until="networkidle")
            check("that choice is remembered across a reload",
                  page.evaluate("document.documentElement.dataset.motion") == "on")
            page.get_by_role("button", name="Motion on").first.click()
            page.reload(wait_until="networkidle")
            check("switching motion off again is remembered too",
                  page.evaluate("document.documentElement.dataset.motion") == "off")
            page.get_by_role("button", name="Motion off").first.click()

            # --- setup and the preflight ------------------------------------------------
            page.get_by_role("button", name="Scan your own chatbot").first.click()
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
            nav_ink = page.evaluate("""() => { const h = document.querySelector('header'); const w = h.querySelector('[aria-label="PolyGuard home"]');
                return h.classList.contains('ink') && getComputedStyle(w).color }""")
            check("opened directly, the How we know nav takes the dark hero's colours (light text on ink)",
                  nav_ink == "rgb(238, 237, 229)")
            rates = page.locator("#rates-list > li")
            n_langs = json.loads((ROOT / "web" / "src" / "bank-counts.json").read_text(encoding="utf-8"))["languages"]
            first_rows = rates.count()
            toggle = page.get_by_role("button", name=f"Show all {n_langs} languages")
            check("the rates chart starts at English plus the ten highest, with a control that says it is collapsed",
                  first_rows == 11 and toggle.get_attribute("aria-expanded") == "false")
            toggle.click()
            check("one press shows every language, and the control says it is expanded",
                  rates.count() == n_langs
                  and page.get_by_role("button", name="Show the top 10 only").get_attribute("aria-expanded") == "true")
            lao = page.locator('#rates-list [lang="lo"]').first
            check("Lao in the chart has a font that covers it (Noto Sans Lao is in the stack and loaded)",
                  lao.count() == 1 and "Noto Sans Lao" in lao.evaluate("e => getComputedStyle(e).fontFamily")
                  and page.evaluate("document.fonts.check('16px \"Noto Sans Lao\"', 'ລາວ')"))
            page.get_by_role("button", name="Show the top 10 only").click()
            axe(page, "the How we know page")
            page.go_back()
            page.wait_for_timeout(1200)
            check("the back button returns to the previous screen", page.url.rstrip("/") == base)

            # --- one press from the home page -------------------------------------------
            page.goto(base + "/", wait_until="networkidle")
            status = page.get_by_test_id("hero-status").inner_text()
            check("the hero says, next to its buttons, that the demo is simulated and the report is local",
                  "simulated" in status.lower() and "no model is attacked" in status
                  and "not a production chatbot" in status)
            ev = page.locator("#local-evidence").locator("xpath=ancestor::section").inner_text()
            check("the home page shows the local scan's evidence with judged and reviewed breaks kept apart",
                  "flagged 14" in ev and "kept 10" in ev and "not yet checked by the author" in ev
                  and "no production chatbot has been scanned, and no paid-model results are published yet" in ev)
            sheet = page.locator("#local-evidence").locator("xpath=ancestor::section").locator("figure li[class*='rounded']")
            check("the graded sheet has a cell for every language in the scan",
                  sheet.count() == len(json.loads((ROOT / "web" / "src" / "local-example.json").read_text(encoding="utf-8"))["languages"]))
            fig = page.locator("figure[aria-labelledby='mechanism-caption']")
            check("the hero works one real attack through four steps, with the real Welsh reply and its outcome",
                  fig.locator("ol > li").count() == 4 and "PWNED_7F3A" in fig.inner_text()
                  and fig.get_by_text("Got through", exact=True).count() == 1 and fig.get_by_text("Held", exact=True).count() == 1
                  and "not a production chatbot" in fig.inner_text())
            check("no attack text sits behind the hero heading, copy or buttons",
                  page.locator("h1").first.evaluate("e => !e.closest('section').querySelector('[aria-hidden=true] [lang]')"))
            page.get_by_role("button", name="Watch a scan").click()
            page.wait_for_url("**/scan/results", timeout=60000)
            page.wait_for_timeout(800)
            check("one press on the home page runs a simulated scan of an example bot to its results",
                  page.get_by_text("Simulated scan").count() >= 1)

            # --- the published real scan ------------------------------------------------
            page.goto(base + "/", wait_until="networkidle")
            page.get_by_role("link", name="Read the local-model report").first.click()
            page.wait_for_load_state("networkidle")
            check("the home page links to a real scan that says what it is and is not",
                  page.get_by_text("A real local diagnostic, published as an example").count() == 1
                  and page.get_by_text("not a production chatbot").count() >= 1)
            check("the report has a way back to the site and says what kind of evidence it is",
                  page.get_by_role("link", name="Back to PolyGuard").count() == 1
                  and page.get_by_text("Real local diagnostic", exact=True).count() == 1)

            # --- the language count before, without and after /api/meta -------------------
            want = json.loads((ROOT / "web" / "src" / "bank-counts.json").read_text(encoding="utf-8"))["languages"]

            def hero_counts(p2):
                text = p2.locator("main").inner_text()
                return re.findall(r"(\d+) languages", text)

            for label in ("delayed", "failed"):
                c2 = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
                p2 = c2.new_page()
                p2_errors, held = [], []
                p2.on("pageerror", lambda e: p2_errors.append(str(e)))
                # Hold the request without blocking the browser connection; release it
                # (delayed) or fail it (failed) only after the cold page is checked.
                p2.route("**/api/meta", lambda route: held.append(route))
                p2.goto(base + "/", wait_until="domcontentloaded")
                p2.wait_for_timeout(600)
                early = hero_counts(p2)
                check(f"{label} metadata: every language count on the page is {want} before it arrives",
                      bool(held) and early and all(n == str(want) for n in early))
                for r in held:
                    r.continue_() if label == "delayed" else r.abort()
                p2.wait_for_timeout(1500)
                late = hero_counts(p2)
                if label == "delayed":
                    check(f"{label} metadata: still {want} afterwards, with no page error",
                          late and all(n == str(want) for n in late) and not p2_errors)
                else:
                    notice = p2.get_by_role("status").filter(has_text="reach its server")
                    check("failed metadata: the home page stays up with a small notice and a retry, "
                          f"every count still {want}, no page error",
                          notice.count() == 1 and notice.get_by_role("button", name="Try again").count() == 1
                          and p2.get_by_role("heading", level=1).count() == 1
                          and late and all(n == str(want) for n in late) and not p2_errors)
                    p2.unroute("**/api/meta")
                    notice.get_by_role("button", name="Try again").click()
                    p2.wait_for_timeout(1200)
                    check("failed metadata: Try again loads it and the notice goes away",
                          p2.get_by_role("status").filter(has_text="reach its server").count() == 0
                          and p2.get_by_role("button", name="Watch a scan").is_enabled())
                c2.close()
            page.goto(base + "/", wait_until="networkidle")
            settled = hero_counts(page)
            check(f"settled metadata: every language count on the page is {want}",
                  settled and all(n == str(want) for n in settled))

            # --- a phone: badge, menu, pause ------------------------------------------------
            c3 = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            m = c3.new_page()
            m.goto(base + "/", wait_until="networkidle")
            check("on a phone the Simulated badge is in the header",
                  m.locator("header").get_by_text("Simulated", exact=True).is_visible())
            menu = m.get_by_role("button", name="Menu")
            box = menu.bounding_box()
            check("the phone menu button is a 44 pixel touch target", box and box["height"] >= 43.5)
            menu.focus()
            m.keyboard.press("Enter")
            check("the menu opens with the keyboard and says so",
                  m.locator('[aria-controls="site-menu"]').get_attribute("aria-expanded") == "true"
                  and m.locator("#site-menu").is_visible())
            check("the menu holds How we know, own bot setup, translation review, the Motion switch and GitHub",
                  all(m.locator("#site-menu").get_by_text(x).count() for x in
                      ("How we know", "Scan your own chatbot", "Translation review", "Motion", "GitHub")))
            m.locator("#site-menu").get_by_role("button", name="Motion off").click()
            check("pausing is one tap away: the Motion switch in the menu works",
                  m.evaluate("document.documentElement.dataset.motion") == "on")
            m.locator("#site-menu").get_by_role("button", name="Motion on").click()
            m.keyboard.press("Escape")
            check("Escape closes the menu and focus goes back to its button",
                  not m.locator("#site-menu").count()
                  and m.evaluate("document.activeElement.textContent") == "Menu")
            axe(m, "the phone home page with its menu")
            ar = m.locator('[data-code="ar"] [lang="ar"]')
            check("in the hero's language strip, Arabic is its own chip and reads right to left",
                  ar.count() == 1 and ar.evaluate("e => getComputedStyle(e).direction") == "rtl")
            m.goto(base + "/scan", wait_until="networkidle")
            m.wait_for_timeout(800)
            bar = m.locator("main > div.fixed").bounding_box()
            check(f"the phone /scan bar takes at most an eighth of the screen ({bar and round(bar['height'])} of 844 px)",
                  bar and bar["height"] <= 844 / 8)
            check("and its Launch scan button is still a 40 pixel target",
                  m.get_by_role("button", name="Launch scan").bounding_box()["height"] >= 40)
            c3.close()

            # --- choosing languages on a touch phone, by keyboard and by tap ---------------
            c4 = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce",
                                     has_touch=True, is_mobile=True)
            t4 = c4.new_page()
            t4.on("pageerror", lambda e: errors.append(str(e)))
            t4.goto(base + "/scan", wait_until="networkidle")
            t4.wait_for_timeout(800)
            lao = t4.locator('button[aria-pressed]:has(> [lang="lo"])').first
            langs_in_bar = lambda: t4.locator("main > div.fixed").inner_text()  # noqa: E731
            start = lao.get_attribute("aria-pressed")
            lao.evaluate("e => e.previousElementSibling.focus()")
            t4.keyboard.press("Tab")
            ring = lao.evaluate("e => document.activeElement === e && getComputedStyle(e).outlineStyle !== 'none'"
                                " && parseFloat(getComputedStyle(e).outlineWidth) >= 2")
            check("Tab reaches a language button and shows a visible focus ring", ring)
            t4.keyboard.press("Space")
            after_space = lao.get_attribute("aria-pressed")
            bar_after = langs_in_bar()
            t4.keyboard.press("Enter")
            check("Space and Enter each toggle a language, and the sticky bar's count follows",
                  after_space != start and lao.get_attribute("aria-pressed") == start
                  and f"{want - 1} languages" in " ".join(bar_after.split()))
            lao.tap()
            check("a tap toggles a language on a touch screen", lao.get_attribute("aria-pressed") != start)
            lao.tap()
            check("Lao on the setup page has its fallback font (Noto Sans Lao in the stack)",
                  "Noto Sans Lao" in t4.locator('button [lang="lo"]').last.evaluate("e => getComputedStyle(e).fontFamily"))
            c4.close()

            # --- the review pages: why native review matters, and coverage ----------------
            rd = json.loads((ROOT / "web" / "src" / "review-data.json").read_text(encoding="utf-8"))
            accepted = {"Iliyana Dimitrova", "Finnur Friðriksson", "Marko P. Milovanović",
                        "UW PORT 202, Intermediate Portuguese (University of Washington), led by Teaching "
                        "Professor Eduardo Viana da Silva, credited with his permission"}
            for width in (1280, 390, 320):
                c5 = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844},
                                         reduced_motion="reduce", has_touch=width < 500, is_mobile=width < 500)
                r5 = c5.new_page()
                r5.on("pageerror", lambda e: errors.append(str(e)))
                r5.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
                r5.goto(base + "/review", wait_until="networkidle")
                r5.wait_for_timeout(800)
                h1 = r5.get_by_role("heading", level=1).inner_text()
                dumbbells = r5.locator('figure[aria-labelledby="dumbbell-caption"] [role="img"]')
                labels = [dumbbells.nth(i).get_attribute("aria-label") for i in range(dumbbells.count())]
                want_lt = f"Lithuanian, lowest row: {rd['moved'][[m['code'] for m in rd['moved']].index('lt')]['lowest'][0]:.3f} before review"
                check(f"{width}px /review opens directly: headline, a before and after for every language whose text "
                      "the review changed, the numbers from the data",
                      "score went down" in h1 and dumbbells.count() == 2 * len(rd["moved"])
                      and any(want_lt in (lab or "") for lab in labels))
                check(f"{width}px /review shows the Lithuanian line whose score fell most, with its English",
                      r5.get_by_text("The line whose score fell most").count() == 1
                      and "CTRL_4B8E" in r5.locator("dl").first.inner_text())
                check(f"{width}px /review: the header still says Simulated, and nothing scrolls sideways",
                      r5.locator("header").get_by_text("Simulated", exact=True).is_visible()
                      and not r5.evaluate("document.documentElement.scrollWidth > innerWidth"))
                if width in (1280, 390):
                    axe(r5, f"the /review page at {width}px")
                r5.goto(base + "/review/coverage", wait_until="networkidle")
                r5.wait_for_timeout(800)
                cells = r5.locator("li[data-status]")
                from collections import Counter
                shown = Counter(cells.nth(i).get_attribute("data-status") for i in range(cells.count()))
                wanted = Counter(l["status"] for l in rd["languages"])
                check(f"{width}px /review/coverage maps every language with its status from the data ({cells.count()})",
                      cells.count() == len(rd["languages"]) == 73 and shown == wanted)
                credits = {x.strip() for x in r5.locator("[data-credit]:visible").all_inner_texts()}
                html = r5.content()
                check(f"{width}px coverage credits: the withheld string or a credit the reviewer accepted, and no email address",
                      credits and credits <= accepted | {rd["withheld"]} and "Iliyana Dimitrova" in credits
                      and not re.search(r"[\w.+-]+@[\w-]+\.(edu|com|org|net|ac|zw|uk|si|is|es)", html))
                check(f"{width}px coverage: Shona is shown as arranged, not as reviewed",
                      r5.locator('li[data-status]:has([lang="sn"])').get_attribute("data-status") == "under_way")
                check(f"{width}px coverage: nothing scrolls sideways, and the right layout for the width is shown",
                      not r5.evaluate("document.documentElement.scrollWidth > innerWidth")
                      and (r5.locator("table").is_visible() if width > 500 else r5.locator("ul[aria-label^='Languages with']").is_visible()))
                if width in (1280, 390):
                    axe(r5, f"the /review/coverage page at {width}px")
                if width == 1280:
                    r5.get_by_role("button", name="Why native review matters").click()
                    r5.wait_for_timeout(500)
                    check("coverage links to the why page in the app", r5.url.rstrip("/").endswith("/review"))
                    check("after the change of screen the tab is named for it and focus is on its heading",
                          r5.title() == "Why native review matters | PolyGuard"
                          and r5.evaluate("document.activeElement && document.activeElement.tagName") == "H1")
                    r5.goto(base + "/", wait_until="networkidle")
                    check("on a wide screen the nav links to translation review too",
                          r5.locator("header").get_by_role("button", name="Translation review").is_visible())
                    r5.locator("main").get_by_role("button", name="Translation review").click()
                    r5.wait_for_timeout(500)
                    check("the home page footer links to review coverage", r5.url.rstrip("/").endswith("/review/coverage"))
                    r5.go_back()
                    r5.wait_for_timeout(500)
                    check("and the back button returns home", r5.url.rstrip("/") == base)
                    r5.route("**/api/meta", lambda route: route.abort())
                    r5.goto(base + "/review", wait_until="domcontentloaded")
                    r5.wait_for_timeout(1500)
                    check("with the server unreachable, the review page still shows (it needs nothing from the server)",
                          "score went down" in r5.get_by_role("heading", level=1).inner_text())
                    r5.unroute("**/api/meta")
                c5.close()

            hdr = page.request.get(base + "/").headers
            rep = page.request.get(base + "/examples/real-scan-2026-10-11.html").headers
            check("the site and the published report are sent with the security headers (policy, nosniff, no framing)",
                  all("frame-ancestors 'none'" in h.get("content-security-policy", "")
                      and h.get("x-content-type-options") == "nosniff" and h.get("x-frame-options") == "DENY"
                      for h in (hdr, rep))
                  and "content-security-policy" not in page.request.get(base + "/api/meta").headers)
            check(f"nothing on the pages the main run visited was blocked by the policy{': ' + csp[0][:160] if csp else ''}",
                  not csp)
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
