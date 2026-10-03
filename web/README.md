# PolyGuard web app

The front end: a landing page, a scan setup screen, a live board that
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
server can run both locally. On Vercel the two deploy as Services of one project
(`../vercel.json`): the site at `/`, the API at `/api/*`.

## How it is put together

| File | What it is |
|---|---|
| `src/App.jsx` | The four screens and the scan's state |
| `src/api.js` | Every call to the server, and the result stream |
| `src/components/Chrome.jsx` | The nav (it takes the colour of the section under it) and the first visit loader |
| `src/components/Landing.jsx` | The landing page |
| `src/components/HighlighterField.jsx` | The hero's paper: the cursor is a highlighter that reveals the attack in other languages |
| `src/components/Bubble3D.jsx` | The 3D speech bubble (Three.js, loaded after the page) that says no in each language |
| `src/components/ScrollStory.jsx` | How it works, pinned and played by scrolling: prompt, attacks, board, red pen and fix |
| `src/components/Board.jsx` | The scan board, used on every screen; it can circle a row in red pen |
| `src/components/Setup.jsx` | Choosing a bot, languages and attacks |
| `src/components/SpotTheAttack.jsx` | The game: six real messages from the bank, attack or safe, with the English revealed |
| `src/components/LiveScan.jsx` | The scan as it happens, with a feed of the latest attacks |
| `src/components/Results.jsx` | Verdict, languages, fixes, and the detail for researchers |
| `src/components/Drawer.jsx` | Every attack in one language, with its English original |
| `src/lib/smooth.js` | Weighted smooth scrolling (Lenis), off when the visitor turns Motion off |
| `src/lib/motion.js` | The Motion switch: motion plays for everyone unless switched off; the system setting is not read |
| `src/index.css` | The grounds, the type, the highlighter stroke and the buttons |

The look is the test sheet: paper and ink grounds, one highlighter colour for
"held" and the way forward, red only for "got through". A section declares its
ground with the `paper`, `ink` or `on-hi` class. Why it looks this way, and the
research behind it, is in `../docs/design-research.md`.
