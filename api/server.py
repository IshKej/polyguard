"""
PolyGuard web API: the only way the web app reaches the engine.

    uvicorn api.server:app --reload          # from the repository root

Endpoints
    GET  /api/meta                  languages, attack types, example bots, live or demo
    POST /api/scan                  run a scan and stream it as server-sent events:
                                    every attack result as it lands, then the verdict,
                                    the statistics and the self-contained report
    POST /api/harden                targeted rules for what broke, and the hardened prompt
    GET  /api/game                  real messages for the spot the attack game

Nothing is kept between requests. A scan runs inside the one request that streams
it, so any instance of the server can take any request. That is what lets the API
run as serverless functions (Vercel) as well as on a laptop.

Spend safety. A live scan is hundreds of paid model calls, and a public link means
strangers can press the button. So a scan is live only when an API key is
configured AND, if POLYGUARD_PASSCODE is set, the request carries it. Everything
else runs as a clearly labelled simulation. At most MAX_LIVE live scans run at
once on a server, inputs are bounded, and on hosting with a time limit a live scan
is capped at HOSTED_LIVE_MAX_ATTACKS so it can finish inside that limit. The
engine, statistics and honesty rules are the same code the research console and
CLI use; nothing is re-implemented here.
"""
from __future__ import annotations

import hmac
import json
import os
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import defenses  # noqa: E402
import engine  # noqa: E402
import providers  # noqa: E402
import report_html  # noqa: E402
from api.verdict import verdict  # noqa: E402
from examples import DESCRIPTIONS, EXAMPLES  # noqa: E402
from languages_catalog import tier_of  # noqa: E402

MAX_PROMPT_CHARS = 8000
MAX_LIVE = 2
REPLY_CHARS = 1200
KEEPALIVE_SECONDS = 10.0

# Vercel sets VERCEL=1. A function there stops after 300 seconds on the free plan,
# and a live attack is two model calls (the bot, then the judge), so a hosted live
# scan is capped to what can finish in that time. The full scan runs from a laptop
# or the CLI, where nothing stops it. Simulated scans are never capped.
HOSTED = os.environ.get("VERCEL") == "1"
HOSTED_LIVE_MAX_ATTACKS = int(os.environ.get("POLYGUARD_HOSTED_LIVE_MAX", "60"))

app = FastAPI(title="PolyGuard API", docs_url="/api/docs", openapi_url="/api/openapi.json")
_origins = [o.strip() for o in os.environ.get(
    "POLYGUARD_WEB_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "X-PolyGuard-Passcode"])

BANK = engine.load_bank()
EN_TEXT = {(a["category"], a.get("variant", 0)): a["text"]
           for a in BANK["attacks"] if a["lang"] == "en"}
_live_slots = threading.Semaphore(MAX_LIVE)


# --------------------------------------------------------------------------- #
# What a scan is allowed to be
# --------------------------------------------------------------------------- #
class ScanRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    langs: list[str] = Field(min_length=1, max_length=100)
    categories: list[str] = Field(min_length=1, max_length=10)
    phrasings: int = Field(default=3, ge=1, le=3)
    model: str | None = None
    demo: bool = False
    # Set only by the hardened rescan, so extraction is scored against the
    # original prompt rather than the rules PolyGuard added (AUDIT.md 49).
    extraction_reference: str | None = Field(default=None, max_length=MAX_PROMPT_CHARS)


class HardenRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=MAX_PROMPT_CHARS)
    broken_categories: list[str] = Field(default_factory=list, max_length=10)


# --------------------------------------------------------------------------- #
# Shaping engine output for the browser
# --------------------------------------------------------------------------- #
def web_row(r: dict) -> dict:
    meta = BANK["languages"].get(r["lang"], {})
    return {"id": r["id"], "lang": r["lang"], "name": meta.get("name", r["lang"]),
            "native": meta.get("native", ""), "tier": tier_of(r["lang"]),
            "category": r["category"], "variant": r.get("variant", 0),
            "broke": bool(r.get("broke")), "error": r.get("error"),
            "attack": r.get("text", ""),
            "english": EN_TEXT.get((r["category"], r.get("variant", 0))),
            "reply": (r.get("reply") or "")[:REPLY_CHARS]}


def web_result(out: dict, req: ScanRequest, scan_id: str) -> dict:
    cap = out.get("capability") or {}
    limited = set(cap.get("capability_limited") or [])
    langs = [{"code": c, "name": d["name"], "native": d.get("native", ""),
              "tier": tier_of(c), "rate": d.get("rate"), "broke": d.get("broke", 0),
              "total": d.get("total", 0), "capability_limited": c in limited}
             for c, d in out["by_lang"].items()]
    langs.sort(key=lambda x: (x["rate"] is None, -(x["rate"] or 0), x["name"]))
    cats = [{"category": c, "rate": d.get("rate"), "broke": d.get("broke", 0),
             "total": d.get("total", 0)} for c, d in out["by_cat"].items()]
    cats.sort(key=lambda x: -(x["rate"] or 0))
    broken = defenses.broken_categories_from(out["results"])
    vm = out.get("victim") or {}
    return {
        "id": scan_id,
        "mock": out["mock"],
        # A simulated run attacked nothing, so it names no model (AUDIT.md 57).
        "victim": None if out["mock"] else {"label": vm.get("label"),
                                            "vendor": vm.get("vendor"),
                                            "deterministic": vm.get("deterministic"),
                                            "thinking_forced": vm.get("thinking_forced")},
        "totals": {"attacks": out["n_attacks"], "broke": out["n_broke"],
                   "errors": out["n_errors"], "overall_rate": out["overall_rate"],
                   "english_rate": out["en_rate"]},
        "verdict": verdict(out),
        "languages": langs,
        "categories": cats,
        "stats": {"worst_language_test": out.get("max_gap_test"),
                  "extraction_scoreable": out.get("extraction_scoreable"),
                  "token_collision": out.get("token_collision"),
                  "capability_limited": sorted(limited),
                  "controls_per_language": cap.get("controls_per_lang"),
                  "phrasings": req.phrasings},
        "broken_categories": broken,
        "fixes": defenses.recommend(broken) if broken else [],
        "results": [web_row(r) for r in out["results"]],
    }


# --------------------------------------------------------------------------- #
# Running scans
# --------------------------------------------------------------------------- #
def _live_available() -> bool:
    try:
        return providers.judge_client() is not None
    except Exception:
        return False


def _passcode_ok(given: str | None) -> bool:
    need = providers.resolve_key("POLYGUARD_PASSCODE")
    return (not need) or (given is not None and hmac.compare_digest(given, need))


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/api/meta")
def meta(x_polyguard_passcode: str | None = Header(default=None)):
    live = _live_available()
    needs_passcode = bool(providers.resolve_key("POLYGUARD_PASSCODE"))
    ready = [s for s in providers.available_models() if s["ready"]] if live else []
    return {
        "live": live and _passcode_ok(x_polyguard_passcode),
        "live_configured": live,
        "needs_passcode": needs_passcode,
        "languages": [{"code": c, "name": m["name"], "native": m["native"], "tier": tier_of(c),
                       "native_reviewed": bool(m.get("native_reviewed"))}
                      for c, m in BANK["languages"].items()],
        "categories": BANK["categories"],
        "examples": [{"name": n, "prompt": p, "description": DESCRIPTIONS.get(n, "")}
                     for n, p in EXAMPLES.items()],
        "models": [{"key": s["key"], "label": s["label"], "vendor": s["vendor"]} for s in ready],
        "default_model": providers.DEFAULT_MODEL,
        "hero_line": {a["lang"]: a["text"] for a in BANK["attacks"]
                      if a["category"] == "instruction_override" and a.get("variant", 0) == 0},
    }


# The spot the attack game: real messages from the bank, attacks and the ordinary
# requests PolyGuard sends as capability controls, each with its English original.
# Both kinds end by asking for a code word, and the two code words would give the
# answer away, so both become the same neutral one. Indirect injections keep
# "SYSTEM OVERRIDE" in English in every language and Base64 payloads look like what
# they are, so neither is used: the game would be about spotting English, not
# about reading a language.
GAME_CODE = "QX-7731"
GAME_CATEGORIES = ("instruction_override", "role_play_jailbreak", "system_prompt_extraction")


def _neutral(text: str) -> str:
    return text.replace(BANK["canary"], GAME_CODE).replace(BANK["control_token"], GAME_CODE)


@app.get("/api/game")
def game():
    english = {x["id"]: x["text"] for x in BANK["attacks"] + BANK["controls"] if x["lang"] == "en"}
    items = [{"id": a["id"], "lang": a["lang"], "attack": True, "category": a["category"],
              "text": _neutral(a["text"]),
              "english": _neutral(english.get(f"en_{a['category']}_{a['variant']}", ""))}
             for a in BANK["attacks"] if a["lang"] != "en" and a["category"] in GAME_CATEGORIES]
    items += [{"id": c["id"], "lang": c["lang"], "attack": False, "category": None,
               "text": _neutral(c["text"]), "english": _neutral(english.get(f"en_control_{c['variant']}", ""))}
              for c in BANK["controls"] if c["lang"] != "en"]
    return {"code": GAME_CODE, "items": items}


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/scan")
def run_scan(req: ScanRequest, x_polyguard_passcode: str | None = Header(default=None)):
    bad_langs = [c for c in req.langs if c not in BANK["languages"]]
    bad_cats = [c for c in req.categories if c not in BANK["categories"]]
    if bad_langs or bad_cats:
        raise HTTPException(422, f"Unknown languages {bad_langs} or attack types {bad_cats}.")

    live = (not req.demo) and _live_available() and _passcode_ok(x_polyguard_passcode)
    model = None
    if live:
        ready = {s["key"] for s in providers.available_models() if s["ready"]}
        model = req.model or providers.DEFAULT_MODEL
        if model not in ready:
            raise HTTPException(422, f"Model {model} is not available on this server.")
        planned = len(req.langs) * len(req.categories) * req.phrasings
        if HOSTED and planned > HOSTED_LIVE_MAX_ATTACKS:
            raise HTTPException(422, f"A live scan on the hosted site can fire at most {HOSTED_LIVE_MAX_ATTACKS} "
                                     f"attacks so it finishes inside the host's time limit, and this one would fire "
                                     f"{planned}. Pick fewer languages or one phrasing, or run the full scan locally.")
        if not _live_slots.acquire(blocking=False):
            raise HTTPException(429, "Two live scans are already running. Try again in a minute.")

    scan_id = uuid.uuid4().hex[:12]
    inbox: queue.Queue = queue.Queue()

    def on_result(row, done, total):
        inbox.put(("result", {"row": web_row(row), "done": done, "total": total}))

    def work():
        try:
            victim = providers.build_victim(model) if live else None
            out = engine.scan(req.prompt, langs=req.langs, categories=req.categories,
                              mock=not live, victim=victim, max_variants=req.phrasings,
                              extraction_reference=req.extraction_reference, on_result=on_result)
            report = report_html.build_report(cli.scan_payload(out, req.prompt, None))
            inbox.put(("done", {"result": web_result(out, req, scan_id), "report": report}))
        except Exception as e:  # never a stack trace to the browser
            inbox.put(("done", {"error": f"The scan could not finish: {type(e).__name__}."}))
        finally:
            if live:
                _live_slots.release()

    threading.Thread(target=work, daemon=True).start()

    def events():
        yield _sse("start", {"id": scan_id, "live": live})
        while True:
            try:
                kind, data = inbox.get(timeout=KEEPALIVE_SECONDS)
            except queue.Empty:
                # A live attack can take a while. A comment line keeps the
                # connection from looking idle to proxies along the way.
                yield ": still scanning\n\n"
                continue
            yield _sse(kind, data)
            if kind == "done":
                return
            if not live:
                # A simulation finishes instantly. Pace the replay so the board
                # can be watched; the pacing is labelled as simulated.
                time.sleep(min(0.05, 7.0 / max(data["total"], 1)))

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/harden")
def harden(req: HardenRequest):
    cats = [c for c in req.broken_categories if c in BANK["categories"]]
    return {"rules": defenses.recommend(cats) if cats else [],
            "hardened": defenses.harden(req.prompt, cats)}


# The built web app, when present, is served from the same origin, so one
# deployment is enough. During development Vite serves it instead.
_dist = ROOT / "web" / "dist"
if _dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="web")
