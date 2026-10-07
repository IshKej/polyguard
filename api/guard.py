"""
The spend guard: what has to be true before the server spends money, and the
limits on everything else.

A live scan is up to two paid model calls per attack and per capability control
(the bot, then the judge). On serverless hosting every request may land on a
different copy of the server, so an in-memory limit protects nothing. These
limits live in the shared store (api/store.py) instead, and they FAIL CLOSED: if
the store is missing or cannot be reached, a live scan is refused. Free actions
(a simulated scan, saving a link, a game answer) are rate limited the same way but
fail open, because refusing them protects no money.

Limits, all overridable by environment variable:

    POLYGUARD_DAILY_CALL_BUDGET   paid calls per UTC day, across every visitor (2000)
    POLYGUARD_LIVE_PER_HOUR       live scans per visitor per hour (4)
    POLYGUARD_MAX_LIVE            live scans running at once, site wide (2)

A visitor is a salted hash of their IP address. The IP itself is never stored or
logged.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time

from api.store import StoreError

DAILY_CALL_BUDGET = int(os.environ.get("POLYGUARD_DAILY_CALL_BUDGET", "2000"))
LIVE_PER_HOUR = int(os.environ.get("POLYGUARD_LIVE_PER_HOUR", "4"))
MAX_LIVE = int(os.environ.get("POLYGUARD_MAX_LIVE", "2"))
# A live scan that crashed without handing back its slot frees it after this long.
SLOT_TTL_SECONDS = 900
IDEMPOTENCY_TTL_SECONDS = 3600

# Free actions, per visitor per hour.
FREE_LIMITS = {"simulated": 40, "save": 20, "answer": 150}

IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class Refused(Exception):
    """The request is not allowed; status and message go to the client."""

    def __init__(self, status: int, message: str, reason: str):
        super().__init__(message)
        self.status, self.message, self.reason = status, message, reason


def _salt() -> str:
    explicit = os.environ.get("POLYGUARD_IP_SALT")
    if explicit:
        return explicit
    # Derived from the store's secret so it is secret too, without one more variable.
    return hashlib.sha256(("polyguard-ip|" + os.environ.get("SUPABASE_SECRET_KEY", "local")).encode()).hexdigest()


def visitor(headers, client_host: str | None) -> str:
    """A salted hash of the caller's IP: enough to rate limit, useless to identify."""
    ip = (headers.get("x-real-ip") or (headers.get("x-forwarded-for") or "").split(",")[0]
          or client_host or "unknown").strip()
    return hashlib.sha256((_salt() + ip).encode()).hexdigest()[:16]


def planned_calls(n_attacks: int, n_controls: int) -> int:
    """Upper bound on paid calls: the bot and the judge, for every attack and control."""
    return 2 * (n_attacks + n_controls)


def _hour() -> str:
    return time.strftime("%Y%m%d%H", time.gmtime())


def _day() -> str:
    return time.strftime("%Y%m%d", time.gmtime())


def admit_live(store, who: str, calls: int, idempotency_key: str | None):
    """Admit one live scan or raise Refused. Returns a release function that
    hands the running slot back; call it exactly when the scan's paid work ends."""
    if store is None:
        raise Refused(503, "Live scans are off on this server: the shared spend guard is not set up. "
                           "Simulated scans still work.", "no_guard")
    if idempotency_key is not None and not IDEMPOTENCY_KEY.match(idempotency_key):
        raise Refused(422, "Idempotency-Key must be 8 to 64 letters, digits, - or _.", "bad_idempotency_key")
    if calls > DAILY_CALL_BUDGET:
        raise Refused(422, f"This scan could make up to {calls} paid calls, more than the whole "
                           f"daily budget of {DAILY_CALL_BUDGET}. Pick fewer languages.", "over_budget")
    try:
        if idempotency_key and not store.claim(f"idem:{idempotency_key}", IDEMPOTENCY_TTL_SECONDS):
            raise Refused(409, "This scan was already started. Refresh to see it rather than "
                               "starting, and paying for, it twice.", "duplicate")
        if not store.take(f"rate:live:{who}:{_hour()}", 1, LIVE_PER_HOUR, 3700):
            raise Refused(429, f"Live scans are limited to {LIVE_PER_HOUR} an hour for each visitor. "
                               "Simulated scans are not limited this way.", "visitor_rate")
        if not store.take("live:running", 1, MAX_LIVE, SLOT_TTL_SECONDS):
            raise Refused(429, f"{MAX_LIVE} live scans are already running. Try again in a minute.", "busy")
        if not store.take(f"budget:calls:{_day()}", calls, DAILY_CALL_BUDGET, 2 * 86400):
            store.give("live:running", 1)
            raise Refused(429, "Today's budget for live scans is used up. It resets at midnight UTC. "
                               "Simulated scans still work.", "daily_budget")
    except StoreError:
        raise Refused(503, "The spend guard cannot be reached right now, so live scans are paused. "
                           "Simulated scans still work.", "guard_unreachable") from None

    done = threading.Event()

    def release():
        if done.is_set():
            return
        done.set()
        try:
            store.give("live:running", 1)
        except StoreError:
            pass          # the slot expires by itself after SLOT_TTL_SECONDS

    return release


def limit(store, who: str, action: str) -> None:
    """Rate limit a free action. Fails open: no money is at stake."""
    if store is None:
        return
    try:
        allowed = store.take(f"rate:{action}:{who}:{_hour()}", 1, FREE_LIMITS[action], 3700)
    except StoreError:
        return
    if not allowed:
        raise Refused(429, "Too many requests from here this hour. Try again later.", f"{action}_rate")


# --------------------------------------------------------------------------- #
# Structured logs
# --------------------------------------------------------------------------- #
# Only these fields can ever be logged. Prompts, replies, attack text, passcodes,
# keys and IP addresses are not on the list, so they cannot leak into the host's
# logs by accident.
_LOG_FIELDS = {"event", "scan_id", "mode", "langs", "attacks", "planned_calls", "duration_ms",
               "errors_by_kind", "status", "reason", "visitor", "broke", "saved_id_prefix"}


def log(event: str, **fields) -> None:
    rec = {"t": round(time.time(), 3), "event": event}
    rec.update({k: v for k, v in fields.items() if k in _LOG_FIELDS})
    print(json.dumps(rec, ensure_ascii=True, default=str), file=sys.stdout, flush=True)
