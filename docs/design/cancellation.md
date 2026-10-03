# Design brief: stop paying when the visitor leaves

**Status: open. Owner: Ishaan.** Acceptance tests: `api/test_cancellation.py`
(4 of 6 fail today, by design). This brief states the problem and the
constraints. The design and the code are the owner's, and so is the design note
at the end.

## The problem, measured

A live scan is up to two paid model calls per attack and per capability control.
Today, when the browser tab closes in the middle of a scan, nothing tells the
work to stop. The acceptance test measures it: a visitor leaves after 24 calls,
and the server goes on to start **228 more**, for a result nobody will see. The
scan's slot in the site-wide running cap (`api/guard.py`) stays taken until the
whole scan would have finished, so leaving also blocks the next visitor.

## Where the work happens

Read these before designing anything:

- `api/server.py`, `run_scan`: admits the scan through the guard, starts a
  worker thread, and returns a `StreamingResponse` whose generator reads results
  from a queue and writes them as server-sent events.
- `engine.py`, `scan`: submits every attack to a `ThreadPoolExecutor` with
  `MAX_WORKERS` threads at once, then the capability controls.
- `api/guard.py`, `admit_live`: returns the `release` function that hands the
  running slot back. It must run exactly once.

## Constraints

1. A call already sent to the model cannot be taken back. "Stopped" means no
   NEW call starts after the visitor leaves; at most the calls already in flight
   finish (the test allows `MAX_WORKERS`).
2. The slot is handed back exactly once, whether the scan finishes, crashes, or
   is abandoned, and promptly when abandoned.
3. A scan nobody leaves behaves exactly as it does now.
4. It has to work on Vercel, not just on a laptop. Read what Vercel does to a
   Python function when the client disconnects (its `supportsCancellation`
   setting) and decide whether you need it, rely on it, or work without it.
5. A cancelled scan is logged as `scan_cancelled`, with no prompt or reply in
   the log (only fields `guard.log` allows).
6. Simulated scans may share the mechanism; they must not break.

## Things to find out, not guess

- How a server-sent events response notices that the other end has gone: what
  Starlette does with a sync generator versus an async one, and when a
  generator's `finally` actually runs.
- What `ThreadPoolExecutor` does with work that has been submitted but not
  started, and how `cancel_futures` and `Future.cancel` behave.
- Whether a `threading.Event` checked by each attack before its call is enough,
  or whether something has to cancel the queued futures as well.

## Done means

- `python api/test_cancellation.py` passes 6 of 6.
- `python api/test_api.py`, `python test_engine.py` and `python verify_all.py`
  still pass.
- The test file is added to `.github/workflows/ci.yml`.
- `docs/design/cancellation-note.md` exists, written by the owner, answering:
  1. What was the bug, in one paragraph, with the measured cost.
  2. What options were considered, and why the chosen one won.
  3. How the stop travels from a closed socket to the thread about to make the
     next call, step by step.
  4. What still costs money after a cancel, and why that bound is acceptable.
  5. What the tests prove, and what they do not.
