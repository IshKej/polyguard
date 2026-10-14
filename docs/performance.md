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

Since 2026-10-13 the hero no longer has the 3D bubble, so Three.js is gone from the
site. A local build of that change measures the app at 354.2 kB raw and 107.2 kB
gzipped, the styles at 43.9 kB and 9.5 kB, and there is no second chunk. The API
numbers above are from before that change and were not rerun.

## A slow phone, measured locally

2026-10-13, local builds served by uvicorn (uncompressed), a 390 pixel phone in
Chromium with the CPU slowed six times, 150 ms latency and 1.6 Mbps down, cache off,
median of three runs. Before is the build before 2026-10-13's redesign; after is the
current one.

| | Before | After |
|---|---|---|
| JavaScript, raw | 919 kB | 339 kB |
| Main thread long tasks, motion off | 5.5 s | 2.1 s |
| Main thread long tasks, motion on | 5.6 s | 1.3 s |
| Largest contentful paint (the headline), motion off | 3.52 s | 3.50 s |
| Largest contentful paint, motion on | 3.02 s | 2.63 s |

The largest paint is about the same with motion off: the new page renders more at
load (the graded sheet, every language's name), and `content-visibility: auto` on the
long sections under the hero is what keeps it level. Between runs the before build's
largest paint moved by 0.3 s, so differences smaller than that are noise.

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
