# Performance, measured

Measured, not estimated, with `python perf_probe.py` from a home connection in
Sammamish, Washington, against https://polyguard-ten.vercel.app (Vercel region
iad1, Washington DC) on **2026-10-02 at 21:53 Pacific**, commit `09d57f8`. The
network between here and the host is part of every number, so these describe one
place at one time. Rerun the probe to measure from somewhere else.

## The API

| Request | p50 | p95 | max | n |
|---|---|---|---|---|
| First request of the run (may land on a cold function) | 1643 ms | | | 1 |
| `GET /api/meta` (what the site loads first) | 208 ms | 390 ms | 446 ms | 20 |
| `GET /api/game` | 283 ms | 336 ms | 336 ms | 10 |
| Simulated scan, time to its first event | 287 ms | 862 ms | 862 ms | 10 |
| Simulated scan of 3 attacks, finished | 433 ms | 1013 ms | 1013 ms | 10 |
| `GET /` (the page itself) | 165 ms | 311 ms | 311 ms | 10 |

A live scan is not measured here: no API key exists yet. Its time is dominated by
the model calls, at most `MAX_WORKERS` (12) at once, and a hosted live scan is
capped at 60 attacks so it ends inside the 300 second function limit.

## What a visitor downloads

| File | Raw | Gzipped |
|---|---|---|
| The app (`index-*.js`) | 404.8 kB | 128.3 kB |
| The 3D bubble (`Bubble3D-*.js`, Three.js), loaded after the page is readable | 511.3 kB | 127.8 kB |
| Styles (`index-*.css`) | 44.1 kB | 9.5 kB |

## The API function

Installed from `uv.lock` with only `anthropic` and `fastapi` and what they need.
Before the slim dependencies (commit `8adb658`) the function carried the research
console's Streamlit, pandas and Altair, its bundle was 345.64 MB, and Vercel
installed packages at every cold start. The current build completes in about ten
seconds with no bundle size warning.

## Is a job queue needed?

Not by these numbers. A simulated scan finishes inside a second; a live one fits
the function's time limit by construction (the hosted cap) and streams its
progress, so nothing waits on a background worker. A durable queue would add a
service, a failure mode and state to keep consistent. Revisit if live scans
measured after the pilot run close to the 300 second limit, or if the hosted cap
turns out too small to be useful.
