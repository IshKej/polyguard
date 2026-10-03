"""
Shared state for the web API: the spend guard's counters, saved scans and game
answers.

On Vercel the API is many short-lived serverless copies, and none of them can see
another's memory, so anything that must hold across all of them (a daily budget of
paid calls, how many live scans are running, a share link) lives in Supabase
(`supabase/migrations/`). The API talks to it over plain HTTPS with the project's
secret key, which never leaves the server. Locally, and in tests, an in-memory
store with the same behaviour stands in.

    get_store()      SupabaseStore when SUPABASE_URL and SUPABASE_SECRET_KEY are set,
                     MemoryStore when running locally, and None on hosting without
                     Supabase. None means the shared guard is missing, and the
                     server then refuses live scans rather than run them unguarded.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


class StoreError(RuntimeError):
    """The shared store could not be reached or refused the request."""


class MemoryStore:
    """Process-local stand-in with the same semantics as the Supabase functions."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[str, tuple[int, float]] = {}   # key -> (value, expires_at)
        self._scans: dict[str, dict] = {}
        self._answers: list[dict] = []

    # -- guard ------------------------------------------------------------- #
    def take(self, key: str, amount: int, max_value: int, ttl_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            value, exp = self._counters.get(key, (0, now + ttl_seconds))
            if exp < now:
                value, exp = 0, now + ttl_seconds
            if value + amount > max_value:
                self._counters[key] = (value, exp)
                return False
            self._counters[key] = (value + amount, exp)
            return True

    def give(self, key: str, amount: int) -> None:
        with self._lock:
            if key in self._counters:
                value, exp = self._counters[key]
                self._counters[key] = (max(value - amount, 0), exp)

    def claim(self, key: str, ttl_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            if key in self._counters and self._counters[key][1] >= now:
                return False
            self._counters[key] = (1, now + ttl_seconds)
            return True

    # -- saved scans ------------------------------------------------------- #
    def save_scan(self, row: dict) -> None:
        with self._lock:
            self._scans[row["id"]] = {**row, "created_at": _iso(datetime.now(timezone.utc))}

    def get_scan(self, scan_id: str) -> dict | None:
        with self._lock:
            row = self._scans.get(scan_id)
        if not row or row["expires_at"] < _iso(datetime.now(timezone.utc)):
            return None
        return row

    def delete_scan(self, scan_id: str, token_sha256: str) -> bool:
        with self._lock:
            row = self._scans.get(scan_id)
            if row and row["delete_token_sha256"] == token_sha256:
                del self._scans[scan_id]
                return True
        return False

    def sweep(self) -> None:
        now = _iso(datetime.now(timezone.utc))
        with self._lock:
            for k in [k for k, r in self._scans.items() if r["expires_at"] < now]:
                del self._scans[k]

    # -- game -------------------------------------------------------------- #
    def add_answer(self, row: dict) -> None:
        with self._lock:
            self._answers.append(row)

    def game_stats(self) -> list[dict]:
        out: dict[str, dict] = {}
        with self._lock:
            for a in self._answers:
                d = out.setdefault(a["lang"], {"lang": a["lang"], "answers": 0, "correct": 0,
                                               "attacks_seen": 0, "attacks_caught": 0})
                d["answers"] += 1
                d["correct"] += a["is_attack"] == a["answered_attack"]
                d["attacks_seen"] += a["is_attack"]
                d["attacks_caught"] += a["is_attack"] and a["answered_attack"]
        return list(out.values())


class SupabaseStore:
    """The same operations against Supabase's Data API (PostgREST)."""

    def __init__(self, url: str, secret_key: str, timeout: float = 8.0):
        self._base = url.rstrip("/") + "/rest/v1/"
        self._key = secret_key
        self._timeout = timeout

    def _call(self, method: str, path: str, body=None, prefer: str | None = None):
        # Secret keys go in the apikey header, not Authorization: Bearer.
        headers = {"apikey": self._key, "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self._base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            # The body can name tables and columns; it stays in the server log, never the client.
            raise StoreError(f"store HTTP {e.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise StoreError(f"store unreachable: {type(e).__name__}") from None
        return json.loads(raw) if raw else None

    def take(self, key: str, amount: int, max_value: int, ttl_seconds: int) -> bool:
        rows = self._call("POST", "rpc/guard_take", {"p_key": key, "p_amount": amount,
                                                     "p_max": max_value, "p_ttl_seconds": ttl_seconds})
        return bool(rows and rows[0].get("allowed"))

    def give(self, key: str, amount: int) -> None:
        self._call("POST", "rpc/guard_give", {"p_key": key, "p_amount": amount})

    def claim(self, key: str, ttl_seconds: int) -> bool:
        return bool(self._call("POST", "rpc/guard_claim", {"p_key": key, "p_ttl_seconds": ttl_seconds}))

    def save_scan(self, row: dict) -> None:
        self._call("POST", "scans", row, prefer="return=minimal")

    def get_scan(self, scan_id: str) -> dict | None:
        now = urllib.parse.quote(_iso(datetime.now(timezone.utc)))
        rows = self._call("GET", f"scans?id=eq.{urllib.parse.quote(scan_id)}&expires_at=gt.{now}"
                                 "&select=id,created_at,expires_at,mode,redacted,result")
        return rows[0] if rows else None

    def delete_scan(self, scan_id: str, token_sha256: str) -> bool:
        rows = self._call("DELETE", f"scans?id=eq.{urllib.parse.quote(scan_id)}"
                                    f"&delete_token_sha256=eq.{token_sha256}&select=id",
                          prefer="return=representation")
        return bool(rows)

    def sweep(self) -> None:
        self._call("POST", "rpc/sweep_expired", {})

    def add_answer(self, row: dict) -> None:
        self._call("POST", "game_answers", row, prefer="return=minimal")

    def game_stats(self) -> list[dict]:
        return self._call("POST", "rpc/game_stats", {}) or []


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def expires_in(days: int) -> str:
    return _iso(datetime.now(timezone.utc) + timedelta(days=days))


_STORE = None
_STORE_READY = False


def get_store():
    global _STORE, _STORE_READY
    if not _STORE_READY:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")
        if url and key:
            _STORE = SupabaseStore(url, key)
        elif os.environ.get("VERCEL") == "1":
            _STORE = None          # hosted without a shared store: the guard is missing
        else:
            _STORE = MemoryStore()  # one process on a laptop: memory is shared enough
        _STORE_READY = True
    return _STORE


def set_store(store) -> None:
    """For tests: put a specific store in place."""
    global _STORE, _STORE_READY
    _STORE, _STORE_READY = store, True
