"""
PolyGuard web API: the only way the web app reaches the engine.

    uvicorn api.server:app --reload          # from the repository root

Endpoints
    GET  /api/meta                  languages, attack types, example bots, live or demo
    POST /api/scans                 start a scan, returns its id
    GET  /api/scans/{id}/stream     server-sent events: every attack result as it lands
    GET  /api/scans/{id}            the finished scan, with verdict and statistics
    GET  /api/scans/{id}/report     the self-contained HTML report
    POST /api/harden                targeted rules for what broke, and the hardened prompt

Spend safety. A live scan is hundreds of paid model calls, and a public link means
strangers can press the button. So a scan is live only when an API key is
configured AND, if POLYGUARD_PASSCODE is set, the request carries it. Everything
else runs as a clearly labelled simulation. At most MAX_LIVE live scans run at
once, inputs are bounded, and finished scans are kept in memory only up to
MAX_JOBS. The engine, statistics and honesty rules are the same code the research
console and CLI use; nothing is re-implemented here.
"""
from __future__ import annotations

import hmac
import json
import os
import sys
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
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
MAX_JOBS = 40
MAX_LIVE = 2
REPLY_CHARS = 1200

app = FastAPI(title="PolyGuard API", docs_url="/api/docs", openapi_url="/api/openapi.json")
_origins = [o.strip() for o in os.environ.get(
    "POLYGUARD_WEB_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origins, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "X-PolyGuard-Passcode"])

BANK = engine.load_bank()
EN_TEXT = {(a["category"], a.get("variant", 0)): a["text"]
           for a in BANK["attacks"] if a["lang"] == "en"}
_live_slots = threading.Semaphore(MAX_LIVE)
_jobs: "OrderedDict[str, Job]" = OrderedDict()
_jobs_lock = threading.Lock()


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


class Job:
    def __init__(self, req: ScanRequest, live: bool, model: str | None):
        self.id = uuid.uuid4().hex[:12]
        self.req, self.live, self.model = req, live, model
        self.rows: list[dict] = []
        self.total = 0
        self.out: dict | None = None
        self.error: str | None = None
        self.finished = False
        self.lock = threading.Lock()
        self.created = time.time()


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


def web_result(job: Job) -> dict:
    out = job.out
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
        "id": job.id,
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
                  "phrasings": job.req.phrasings},
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


def _run(job: Job) -> None:
    def on_result(row, done, total):
        with job.lock:
            job.rows.append(web_row(row))
            job.total = total

    try:
        victim = providers.build_victim(job.model) if job.live else None
        out = engine.scan(job.req.prompt, langs=job.req.langs, categories=job.req.categories,
                          mock=not job.live, victim=victim, max_variants=job.req.phrasings,
                          extraction_reference=job.req.extraction_reference,
                          on_result=on_result)
        with job.lock:
            job.out = out
    except Exception as e:  # never a stack trace to the browser
        with job.lock:
            job.error = f"The scan could not finish: {type(e).__name__}."
    finally:
        with job.lock:
            job.finished = True
        if job.live:
            _live_slots.release()


def _store(job: Job) -> None:
    with _jobs_lock:
        _jobs[job.id] = job
        while len(_jobs) > MAX_JOBS:
            _jobs.popitem(last=False)


def _get(job_id: str) -> Job:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "No scan with that id. It may have expired.")
    return job


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


@app.post("/api/scans")
def start_scan(req: ScanRequest, x_polyguard_passcode: str | None = Header(default=None)):
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
        if not _live_slots.acquire(blocking=False):
            raise HTTPException(429, "Two live scans are already running. Try again in a minute.")

    job = Job(req, live, model)
    _store(job)
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return {"id": job.id, "live": live}


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/api/scans/{job_id}/stream")
def stream(job_id: str):
    job = _get(job_id)

    def events():
        sent = 0
        yield _sse("start", {"id": job.id, "live": job.live})
        while True:
            with job.lock:
                fresh = job.rows[sent:]
                total, finished, error = job.total, job.finished, job.error
            for row in fresh:
                yield _sse("result", {"row": row, "done": sent + 1, "total": total})
                sent += 1
                if not job.live:
                    # A simulation finishes instantly. Pace the replay so the
                    # grid can be watched; the pacing is labelled as simulated.
                    time.sleep(min(0.05, 7.0 / max(total, 1)))
            if finished and sent >= len(job.rows):
                yield _sse("done", {"id": job.id, "error": error})
                return
            time.sleep(0.15)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/scans/{job_id}")
def result(job_id: str):
    job = _get(job_id)
    with job.lock:
        finished, error = job.finished, job.error
    if error:
        raise HTTPException(500, error)
    if not finished or job.out is None:
        raise HTTPException(409, "This scan is still running.")
    return web_result(job)


@app.get("/api/scans/{job_id}/report", response_class=HTMLResponse)
def report(job_id: str):
    job = _get(job_id)
    if not job.finished or job.out is None:
        raise HTTPException(409, "This scan is still running.")
    payload = cli.scan_payload(job.out, job.req.prompt, None)
    return HTMLResponse(report_html.build_report(payload),
                        headers={"Content-Disposition": 'attachment; filename="polyguard-report.html"'})


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
