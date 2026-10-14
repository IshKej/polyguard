Drafted with AI, reviewed by Ishaan.

# Design note: stopping a live scan when the visitor leaves

The brief is `docs/design/cancellation.md`; the acceptance tests are
`api/test_cancellation.py` (9 of 9, run in CI). This note answers the brief's
five questions from the code as it is. Where it says what the code does, the
lines are `engine.scan` in `engine.py` and `run_scan` in `api/server.py`.

## 1. The bug, and what it cost

A live scan sends every attack to the model, and for most of them a second call
to the judge. Before the fix, closing the tab in the middle of a scan told the
server nothing. The acceptance test measured it with a fake model: the visitor
left after 24 calls and the server went on to start 228 more, for a result
nobody would see. The scan's place in the site-wide running cap
(`guard.MAX_LIVE`) stayed taken until the scan would have ended, so leaving also
blocked the next visitor. Now no new call starts after the visitor leaves, the
place is handed back at once, and the server logs `scan_cancelled`.

## 2. Options considered

- **Rely only on Vercel ending the function** (`supportsCancellation`). It stops
  spending, but abruptly: no log line, and the place in the running cap is only
  freed when the guard's 15 minute expiry (`SLOT_TTL_SECONDS`) passes. Kept as a
  second stop, not the main one.
- **Check `request.is_disconnected()` inside the old generator.** The old
  generator was synchronous, so Starlette ran it in a thread pool and could not
  interrupt it; it would only have noticed the disconnect the next time it tried
  to send something, which can be seconds later.
- **Shut the thread pool down with `cancel_futures=True`.** This cancels work that
  has not started, but an attack that a worker has already picked up would still
  make its call.
- **Chosen:** a `threading.Event` that every attack checks immediately before its
  paid call, futures that have not started cancelled when the event is seen, the
  capability controls skipped, and an async event stream whose `finally` sets the
  event and frees the place exactly once. It needs nothing beyond the standard
  library and the existing stream.

## 3. How the stop travels, step by step

1. The tab closes and the browser drops the connection.
2. The server (uvicorn) receives the disconnect and Starlette's
   `StreamingResponse`, which listens for it, cancels the task that is reading
   the event stream.
3. The stream is an `async def` generator, so the cancellation is raised at the
   point it is waiting (`await asyncio.to_thread(inbox.get, ...)` or the pacing
   `await asyncio.sleep(...)`), and its `finally` runs right away. As a fallback,
   whenever the queue is idle for half a second the generator also asks
   `request.is_disconnected()` and returns if the visitor is gone.
4. In the `finally`, a scan that did not finish sets the cancel event and calls
   `release_once()`, which hands the place in the running cap back. A lock makes
   sure this happens exactly once, whether the scan ends, fails or is abandoned.
5. In the worker thread, `engine.scan` checks the event as each finished attack
   comes back. Once it is set, every future that has not started is cancelled,
   so it never starts.
6. An attack a worker had already picked up checks the event again inside
   `attack_unless_stopped`, right before calling the model, and returns without
   calling it.
7. With the event set, `engine.scan` skips the capability controls, marks the
   result `cancelled`, and its completeness says it is not complete.
8. The server's worker sees `cancelled`, logs `scan_cancelled` (scan id, mode,
   attacks scored, planned calls, duration; no prompt, no reply), builds no
   report and sends nothing, and its own `finally` calls `release_once()`, which
   does nothing the second time.

## 4. What still costs money after a cancel

A call that has already been sent cannot be taken back. At most `MAX_WORKERS`
attacks (12) can be inside a call when the stop arrives, and each of those can
still make its judge call after the model replies. So the worst case after a
cancel is about 12 model calls and 12 judge calls, against hundreds before. There
is also a short race: an attack that passed its check a moment before the event
was set still makes its call. Both are bounded by the number of workers, which is
why the acceptance test allows `MAX_WORKERS` more calls after the visitor leaves
(it measured 0).

## 5. What the tests prove, and what they do not

They prove, against a fake model on a real local server: the scan was running
when the visitor left; no more than the calls in flight finished; the place in
the running cap came back promptly; the cancellation was logged; `engine.scan`
accepts and honours the event, returns what it had, skips the controls and says
it is incomplete; and a scan nobody leaves still finishes normally.

They do not prove the behaviour on Vercel. No live paid scan has been
disconnected on the hosted site, because live scans need the API key. How Vercel
delivers a disconnect to a Python function, and what `supportsCancellation` does
there, is taken from Vercel's documentation, not measured. Proxies between the
visitor and the server can also delay the disconnect. If Vercel ends the function
before the `finally` runs, the place in the running cap is freed by the guard's
expiry instead of at once.

Owner's reasoning and corrections:

(Ishaan: add your own explanation and anything this draft gets wrong.)
