# PolyGuard web app

The front end: a landing page, a scan setup screen, a live departure board that
fills in as attacks land, and a results screen. React, Vite, Tailwind and GSAP.
It talks to the Python API in `../api`, which wraps the same engine the research
console and CLI use.

## Run it

Two terminals, from the repository root:

```bash
python -m uvicorn api.server:app --port 8000     # the API
cd web && npm install && npm run dev             # the app, on http://localhost:5173
```

Without an API key the app runs as a labelled simulation: no model is attacked
and the outcomes are made up. With `ANTHROPIC_API_KEY` set for the API, scans are
live.

## Build it

```bash
cd web && npm run build
```

The API serves `web/dist` from its own origin when that folder exists, so one
deployment covers both.

## How it is put together

| File | What it is |
|---|---|
| `src/App.jsx` | The four screens and the scan's state |
| `src/api.js` | Every call to the server, and the result stream |
| `src/components/Board.jsx` | The departure board, used on every screen |
| `src/components/Landing.jsx` | The landing page |
| `src/components/Setup.jsx` | Choosing a bot, languages and attacks |
| `src/components/LiveScan.jsx` | The scan as it happens |
| `src/components/Results.jsx` | Verdict, languages, fixes, and the detail for researchers |
| `src/components/Drawer.jsx` | Every attack in one language, with its English original |
| `src/index.css` | The colour roles and the themes that fill them |

Colours are roles (`brand`, `page`, `accent`, and so on), never values. A theme
is one block in `src/index.css`.
