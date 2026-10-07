"""
PolyGuard web API: the only way the web app reaches the engine.

    uvicorn api.server:app --reload          # from the repository root

Endpoints
    GET    /api/meta                languages, attack types, example bots, live or demo
    POST   /api/scan                run a scan and stream it as server-sent events:
                                    every attack result as it lands, then the verdict,
                                    the statistics and the self-contained report
    POST   /api/harden              targeted rules for what broke, and the hardened prompt
    GET    /api/game                real messages for the spot the attack game
    POST   /api/game/answer         one anonymous answer to the game
    GET    /api/game/stats          how well people spot attacks, per language
    POST   /api/scans               save a finished scan behind a share link
    GET    /api/scans/{id}          open a saved scan
    DELETE /api/scans/{id}          delete it (needs the delete token from saving)

Nothing is kept between requests. A scan runs inside the one request that streams
it, so any instance of the server can take any request. That is what lets the API
run as serverless functions (Vercel) as well as on a laptop.

Spend safety. A live scan is hundreds of paid model calls, and a public link means
strangers can press the button. So a scan is live only when ALL of these hold, and
anything missing fails closed into a clearly labelled simulation or a refusal:
an API key is configured, a passcode is configured (no passcode means no live
scans, never open access), the request carries that passcode, and the shared spend
guard (api/guard.py) admits it: a daily budget of paid calls, a per-visitor hourly
limit, and a site-wide cap on scans running at once, all held in Supabase so every
serverless copy sees the same numbers. Inputs are bounded, and on hosting with a
time limit a live scan is capped at HOSTED_LIVE_MAX_ATTACKS so it can finish
inside that limit. The engine, statistics and honesty rules are the same code the
research console and CLI use; nothing is re-implemented here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import queue
import random
import re
import secrets
import sys
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import defenses  # noqa: E402
import engine  # noqa: E402
import providers  # noqa: E402
import report_html  # noqa: E402
import tq_report  # noqa: E402
from api import guard  # noqa: E402
from api.store import StoreError, expires_in, get_store  # noqa: E402
from api.verdict import verdict  # noqa: E402
from examples import DESCRIPTIONS, EXAMPLES  # noqa: E402
from languages_catalog import tier_of  # noqa: E402

MAX_PROMPT_CHARS = 8000
REPLY_CHARS = 1200
SCAN_SCHEMA = "polyguard.scan/1"
SAVED_DAYS = 30
MAX_SAVED_BYTES = 1_500_000
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
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type", "X-PolyGuard-Passcode", "Idempotency-Key",
                                  "X-Delete-Token"])


@app.exception_handler(guard.Refused)
def _refused(_request, exc: guard.Refused):
    guard.log("refused", status=exc.status, reason=exc.reason)
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "reason": exc.reason})

BANK = engine.load_bank()
EN_TEXT = {(a["category"], a.get("variant", 0)): a["text"]
           for a in BANK["attacks"] if a["lang"] == "en"}
CONTROLS_PER_LANG = {c: sum(1 for x in BANK.get("controls", []) if x["lang"] == c)
                     for c in BANK["languages"]}


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
              "total": d.get("total", 0), "capability_limited": c in limited,
              # automated proxy, not a validation (tq_report.py)
              "translation_quality": tq_report.lang_quality(c)}
             for c, d in out["by_lang"].items()]
    langs.sort(key=lambda x: (x["rate"] is None, -(x["rate"] or 0), x["name"]))
    cats = [{"category": c, "rate": d.get("rate"), "broke": d.get("broke", 0),
             "total": d.get("total", 0)} for c, d in out["by_cat"].items()]
    cats.sort(key=lambda x: -(x["rate"] or 0))
    broken = defenses.broken_categories_from(out["results"])
    vm = out.get("victim") or {}
    return {
        "schema": SCAN_SCHEMA,
        "id": scan_id,
        "mock": out["mock"],
        # What exactly produced this: commit, bank fingerprint, judge wording, config.
        "instrument": out.get("instrument"),
        # How complete the run was, stated before any rate is read.
        "completeness": engine.completeness(out),
        # A simulated run attacked nothing, so it names no model (AUDIT.md 57).
        "victim": None if out["mock"] else {"label": vm.get("label"),
                                            "vendor": vm.get("vendor"),
                                            "deterministic": vm.get("deterministic"),
                                            "thinking_forced": vm.get("thinking_forced")},
        "totals": {"attacks": out["n_attacks"], "broke": out["n_broke"],
                   "errors": out["n_errors"], "overall_rate": out["overall_rate"],
                   "english_rate": out["en_rate"],
                   # Harmless requests the bot followed: a defence that refuses
                   # everything shows up here, not in the attack numbers.
                   "controls_scored": sum(1 for c in out.get("controls") or [] if not c.get("error")),
                   "controls_followed": sum(1 for c in out.get("controls") or []
                                            if not c.get("error") and c.get("followed"))},
        "heldout_variant": engine.HELDOUT_VARIANT,
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
    """Fails closed: with no passcode configured, nobody gets a live scan."""
    need = providers.resolve_key("POLYGUARD_PASSCODE")
    return bool(need) and given is not None and hmac.compare_digest(given.encode(), need.encode())


def _live_state(given: str | None) -> tuple[bool, str]:
    """Whether this caller would get a live scan, and if not, the first reason why."""
    if not _live_available():
        return False, "no_key"
    if not providers.resolve_key("POLYGUARD_PASSCODE"):
        return False, "no_passcode_configured"
    if get_store() is None:
        return False, "no_guard"
    if not _passcode_ok(given):
        return False, "locked"
    return True, "ok"


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/api/meta")
def meta(x_polyguard_passcode: str | None = Header(default=None)):
    live_configured = _live_available()
    live, live_reason = _live_state(x_polyguard_passcode)
    ready = [s for s in providers.available_models() if s["ready"]] if live_configured else []
    return {
        "live": live,
        "live_reason": live_reason,
        "live_configured": live_configured,
        # A live server always asks for the passcode: there is no open mode.
        "needs_passcode": live_configured,
        "saving": get_store() is not None,
        "limits": {"daily_call_budget": guard.DAILY_CALL_BUDGET, "live_per_hour": guard.LIVE_PER_HOUR,
                   "hosted_live_max_attacks": HOSTED_LIVE_MAX_ATTACKS if HOSTED else None},
        # What the preflight needs to show an upper bound on cost before a live scan:
        # every call at its output cap and every character of input a token.
        "cost_model": {
            "prices_per_mtok": {k: list(v) for k, v in providers.PRICES_PER_MTOK.items()},
            "judge_model": engine.JUDGE_MODEL,
            "victim_max_output_tokens": 300,
            "judge_max_output_tokens": 50,
            # The judge reads its instructions (a token per character at most) and one
            # reply, which the victim's own output cap holds to 300 tokens.
            "judge_input_tokens": len(engine.JUDGE_COMPLIANCE_PROMPT) + 300 + 20,
            "max_attack_chars": max(len(a["text"]) for a in BANK["attacks"] + BANK["controls"]),
            "controls_per_language": max(CONTROLS_PER_LANG.values(), default=0),
        },
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


# --------------------------------------------------------------------------- #
# Signing: a share link only for a result this server produced, unchanged
#
# A share link opens on this site's own address, so it must not be able to carry
# a result someone wrote by hand: a made-up "live scan" with a made-up verdict
# would look like PolyGuard's own finding. Every result is signed when it is
# produced (HMAC-SHA256 over its canonical JSON, keyed by a server secret), and
# only a result whose signature still matches can be saved behind a link.
# --------------------------------------------------------------------------- #
_LOCAL_SIGNING_KEY = secrets.token_bytes(32)      # one process on a laptop


def _signing_key() -> bytes:
    explicit = os.environ.get("POLYGUARD_SIGNING_KEY")
    if explicit:
        return explicit.encode("utf-8")
    secret = os.environ.get("SUPABASE_SECRET_KEY")
    if secret:      # every serverless copy shares it, so every copy agrees
        return hashlib.sha256(("polyguard-sign|" + secret).encode("utf-8")).digest()
    return _LOCAL_SIGNING_KEY


def _canonical(result: dict) -> bytes:
    body = {k: v for k, v in result.items() if k not in ("signature", "report")}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sign_result(result: dict) -> str:
    return hmac.new(_signing_key(), _canonical(result), hashlib.sha256).hexdigest()


def signature_ok(result: dict) -> bool:
    sig = result.get("signature")
    return isinstance(sig, str) and hmac.compare_digest(sig, sign_result(result))


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def planned_attacks(req: ScanRequest) -> int:
    langs, cats = set(req.langs), set(req.categories)
    return sum(1 for a in BANK["attacks"] if a["lang"] in langs and a["category"] in cats
               and a.get("variant", 0) < req.phrasings)


@app.post("/api/scan")
def run_scan(req: ScanRequest, request: Request,
             x_polyguard_passcode: str | None = Header(default=None),
             idempotency_key: str | None = Header(default=None)):
    req.langs = list(dict.fromkeys(req.langs))            # a repeated language is one language
    req.categories = list(dict.fromkeys(req.categories))
    bad_langs = [c for c in req.langs if c not in BANK["languages"]]
    bad_cats = [c for c in req.categories if c not in BANK["categories"]]
    if bad_langs or bad_cats:
        raise HTTPException(422, f"Unknown languages {bad_langs} or attack types {bad_cats}.")

    who = guard.visitor(request.headers, request.client.host if request.client else None)
    store = get_store()
    live = (not req.demo) and _live_state(x_polyguard_passcode)[0]
    model, release = None, (lambda: None)
    planned = planned_attacks(req)
    calls = 0
    if live:
        ready = {s["key"] for s in providers.available_models() if s["ready"]}
        model = req.model or providers.DEFAULT_MODEL
        if model not in ready:
            raise HTTPException(422, f"Model {model} is not available on this server.")
        if HOSTED and planned > HOSTED_LIVE_MAX_ATTACKS:
            raise HTTPException(422, f"A live scan on the hosted site can fire at most {HOSTED_LIVE_MAX_ATTACKS} "
                                     f"attacks so it finishes inside the host's time limit, and this one would fire "
                                     f"{planned}. Pick fewer languages or one phrasing, or run the full scan locally.")
        calls = guard.planned_calls(planned, sum(CONTROLS_PER_LANG.get(c, 0) for c in req.langs))
        release = guard.admit_live(store, who, calls, idempotency_key)
    else:
        guard.limit(store, who, "simulated")

    scan_id = uuid.uuid4().hex[:12]
    started = time.time()
    guard.log("scan_start", scan_id=scan_id, mode="live" if live else "simulated",
              langs=len(req.langs), attacks=planned, planned_calls=calls, visitor=who)
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
            guard.log("scan_done", scan_id=scan_id, mode="live" if live else "simulated",
                      attacks=out["n_attacks"], broke=out["n_broke"],
                      errors_by_kind=out.get("errors_by_kind"),
                      duration_ms=round((time.time() - started) * 1000))
            res = web_result(out, req, scan_id)
            res["signature"] = sign_result(res)
            inbox.put(("done", {"result": res, "report": report}))
        except Exception as e:  # never a stack trace to the browser
            guard.log("scan_failed", scan_id=scan_id, reason=type(e).__name__)
            inbox.put(("done", {"error": f"The scan could not finish: {type(e).__name__}."}))
        finally:
            release()

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


# --------------------------------------------------------------------------- #
# Saved scans: share links
#
# Private by default: a saved scan is reachable only through its link, which is
# 128 random bits, and is listed nowhere. The bot's replies are left out unless the
# person saving asks to keep them, because a reply to an extraction attack can
# contain the bot's own system prompt. Links expire after SAVED_DAYS, and whoever
# saved one gets a delete token (only its hash is stored) to remove it sooner.
# --------------------------------------------------------------------------- #
SCAN_ID = re.compile(r"^[A-Za-z0-9_-]{22}$")
SAVED_FIELDS = ("schema", "id", "mock", "instrument", "completeness", "victim", "totals", "verdict",
                "languages", "categories", "stats", "broken_categories", "fixes", "results",
                "heldout_variant")


class SaveRequest(BaseModel):
    result: dict
    keep_replies: bool = False


def _need_store():
    store = get_store()
    if store is None:
        raise HTTPException(503, "Saving is not set up on this server.")
    return store


@app.post("/api/scans")
def save_scan(req: SaveRequest, request: Request):
    store = _need_store()
    guard.limit(store, guard.visitor(request.headers, request.client.host if request.client else None), "save")
    r = req.result
    if r.get("schema") != SCAN_SCHEMA or not isinstance(r.get("results"), list) \
            or not isinstance(r.get("languages"), list) or not isinstance(r.get("mock"), bool):
        raise HTTPException(422, "That is not a PolyGuard scan result.")
    if len(json.dumps(r, ensure_ascii=False).encode("utf-8")) > 2 * MAX_SAVED_BYTES:
        raise HTTPException(413, "That scan is too large to save.")
    if not signature_ok(r):
        raise HTTPException(422, "Only scans run on this site can be shared, exactly as they came back. "
                                 "This one was changed, or made somewhere else.")
    clean = {k: r[k] for k in SAVED_FIELDS if k in r}
    if not req.keep_replies:
        clean["results"] = [{**row, "reply": "", "reply_redacted": True} if isinstance(row, dict) else row
                            for row in clean["results"]]
    body = json.dumps(clean, ensure_ascii=False)
    if len(body.encode("utf-8")) > MAX_SAVED_BYTES:
        raise HTTPException(413, "That scan is too large to save.")
    scan_id = secrets.token_urlsafe(16)
    token = secrets.token_urlsafe(24)
    row = {"id": scan_id, "mode": "simulated" if clean["mock"] else "live",
           "redacted": not req.keep_replies,
           "delete_token_sha256": hashlib.sha256(token.encode()).hexdigest(),
           "size_bytes": len(body.encode("utf-8")), "result": clean,
           "expires_at": expires_in(SAVED_DAYS)}
    try:
        store.save_scan(row)
        if random.random() < 0.1:
            store.sweep()
    except StoreError:
        raise HTTPException(503, "Saving failed. Try again in a moment.") from None
    guard.log("scan_saved", saved_id_prefix=scan_id[:4], mode=row["mode"])
    return {"id": scan_id, "path": f"/s/{scan_id}", "delete_token": token,
            "expires_at": row["expires_at"], "redacted": row["redacted"]}


@app.get("/api/scans/{scan_id}")
def get_saved_scan(scan_id: str):
    if not SCAN_ID.match(scan_id):
        raise HTTPException(404, "No saved scan has that link.")
    try:
        row = _need_store().get_scan(scan_id)
    except StoreError:
        raise HTTPException(503, "Saved scans cannot be reached right now.") from None
    if not row:
        raise HTTPException(404, "No saved scan has that link, or it has expired.")
    return {"result": row["result"], "mode": row["mode"], "redacted": row["redacted"],
            "created_at": row.get("created_at"), "expires_at": row["expires_at"]}


@app.delete("/api/scans/{scan_id}", status_code=204)
def delete_saved_scan(scan_id: str, x_delete_token: str | None = Header(default=None)):
    if not SCAN_ID.match(scan_id) or not x_delete_token or len(x_delete_token) > 64:
        raise HTTPException(404, "No saved scan matches that link and token.")
    try:
        ok = _need_store().delete_scan(scan_id, hashlib.sha256(x_delete_token.encode()).hexdigest())
    except StoreError:
        raise HTTPException(503, "Saved scans cannot be reached right now.") from None
    if not ok:
        raise HTTPException(404, "No saved scan matches that link and token.")
    return Response(status_code=204)


# --------------------------------------------------------------------------- #
# The game's crowd numbers: anonymous, one row per answer, truth from the bank
# --------------------------------------------------------------------------- #
CONTROL_IDS = frozenset(c["id"] for c in BANK["controls"])
GAME_ITEMS = {x["id"]: x for x in BANK["attacks"] + BANK["controls"]
              if x["lang"] != "en" and (x["id"] in CONTROL_IDS or x.get("category") in GAME_CATEGORIES)}
MIN_ANSWERS_SHOWN = 10


class AnswerRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)
    answered_attack: bool


@app.post("/api/game/answer", status_code=204)
def game_answer(req: AnswerRequest, request: Request):
    item = GAME_ITEMS.get(req.item_id)
    if item is None:
        raise HTTPException(422, "Unknown game item.")
    store = get_store()
    if store is None:
        return Response(status_code=204)
    guard.limit(store, guard.visitor(request.headers, request.client.host if request.client else None), "answer")
    is_attack = item["id"] not in CONTROL_IDS
    try:
        store.add_answer({"item_id": item["id"], "lang": item["lang"], "is_attack": is_attack,
                          "answered_attack": req.answered_attack})
    except StoreError:
        pass        # a lost answer is a lost data point, not an error worth showing a player
    return Response(status_code=204)


@app.get("/api/game/stats")
def game_stats(response: Response):
    store = get_store()
    try:
        rows = store.game_stats() if store is not None else []
    except StoreError:
        rows = []
    response.headers["Cache-Control"] = "public, max-age=60"
    langs = {c: m for c, m in BANK["languages"].items()}
    out = [{"lang": r["lang"], "name": langs.get(r["lang"], {}).get("name", r["lang"]),
            "answers": int(r["answers"]), "accuracy": int(r["correct"]) / int(r["answers"]),
            "attacks_caught": (int(r["attacks_caught"]) / int(r["attacks_seen"])) if int(r["attacks_seen"]) else None}
           for r in rows if int(r["answers"]) >= MIN_ANSWERS_SHOWN]
    out.sort(key=lambda x: -x["answers"])
    return {"min_answers": MIN_ANSWERS_SHOWN, "languages": out}


# The built web app, when present, is served from the same origin, so one
# deployment is enough. During development Vite serves it instead.
_dist = ROOT / "web" / "dist"
if _dist.is_dir():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    # The site's own addresses all load the same page; the page picks the screen.
    for _path in ("/how", "/scan", "/scan/live", "/scan/results", "/s/{scan_id}"):
        app.add_api_route(_path, lambda: FileResponse(_dist / "index.html"), include_in_schema=False)
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="web")
