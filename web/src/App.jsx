import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getMeta, getResult, startScan, streamScan } from './api'
import Landing from './components/Landing'
import LiveScan from './components/LiveScan'
import Results from './components/Results'
import Setup from './components/Setup'

const REPO = 'https://github.com/IshKej/polyguard'
const THEMES = [
  ['cobalt', 'Cobalt', '#1f3fff'],
  ['midnight', 'Midnight', '#000000'],
  ['tomato', 'Tomato', '#ff4b2b'],
  ['pink', 'Pink', '#ff4f9a'],
]
const THEME_KEY = 'polyguard.theme'

function readTheme() {
  try { return localStorage.getItem(THEME_KEY) || 'cobalt' } catch { return 'cobalt' }
}

// The mark: one flap from the board, with the seam a real flap has.
function Mark({ className = '' }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <rect width="64" height="64" rx="11" fill="var(--color-tile)" />
      <path fill="var(--color-on-tile)" fillRule="evenodd" d="M19 13h18a14 14 0 0 1 0 28h-8v10H19zm10 9v10h7.500a5 5 0 0 0 0-10z" />
      <rect y="30.500" width="64" height="3" fill="var(--color-tile)" />
    </svg>
  )
}

function Nav({ live, loaded, onHome, onScan, showScan }) {
  return (
    <header className="on-brand sticky top-0 z-30 bg-brand text-on-brand">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
        <button type="button" onClick={onHome} className="flex items-center gap-2.5" aria-label="PolyGuard home">
          <Mark className="size-8" />
          <span className="display text-[1.75rem]">PolyGuard</span>
        </button>
        <div className="flex items-center gap-4">
          {loaded && (
            <span
              className="tag hidden border-2 border-on-brand sm:inline-block"
              title={live ? 'Scans attack a real model.' : 'No model is attacked. Outcomes are made up.'}
            >
              {live ? 'Live' : 'Simulated'}
            </span>
          )}
          <a href={REPO} target="_blank" rel="noopener" className="hidden font-semibold underline-offset-4 hover:underline sm:inline">GitHub</a>
          {showScan && <button type="button" onClick={onScan} className="btn btn-solid btn-sm">Scan a chatbot</button>}
        </div>
      </div>
    </header>
  )
}

// Temporary: lets the look be chosen by trying it. Remove once one is picked.
function ThemeSwitcher({ theme, onPick }) {
  return (
    <div className="fixed left-3 top-1/2 z-50 flex -translate-y-1/2 flex-col items-stretch gap-1 rounded-[6px] border-2 border-black bg-white p-2 text-black shadow-[4px_4px_0_#000]" role="group" aria-label="Choose a look">
      <span className="display px-1 text-lg">Look</span>
      {THEMES.map(([key, name, swatch]) => (
        <button
          key={key} type="button" onClick={() => onPick(key)} aria-pressed={theme === key}
          className={`flex items-center gap-1.5 rounded-[4px] border-2 px-2 py-1 text-sm font-semibold ${theme === key ? 'border-black bg-black text-white' : 'border-transparent hover:border-black'}`}
        >
          <span className="size-3.5 rounded-full border border-black/40" style={{ background: swatch }} />
          {name}
        </button>
      ))}
    </div>
  )
}

export default function App() {
  const [theme, setTheme] = useState(readTheme)
  const [meta, setMeta] = useState(null)
  const [metaError, setMetaError] = useState('')
  const [view, setView] = useState('landing')
  const [config, setConfig] = useState(null)
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [scanLive, setScanLive] = useState(false)
  const [scanError, setScanError] = useState('')
  const [result, setResult] = useState(null)
  const [baseline, setBaseline] = useState(null)
  const stop = useRef(null)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem(THEME_KEY, theme) } catch { /* private mode */ }
  }, [theme])

  const loadMeta = useCallback(
    () => getMeta().then((m) => { setMeta(m); setMetaError(''); return m }).catch((e) => { setMetaError(e.message); return null }),
    [],
  )
  useEffect(() => {
    let alive = true
    getMeta().then((m) => alive && setMeta(m)).catch((e) => alive && setMetaError(e.message))
    return () => { alive = false; stop.current?.() }
  }, [])

  const go = (v) => { setView(v); window.scrollTo({ top: 0 }) }

  const launch = useCallback(async (cfg, { hardened, keepBaseline } = {}) => {
    stop.current?.()
    setConfig(cfg); setRows([]); setTotal(cfg.langs.length * cfg.categories.length * cfg.phrasings)
    setScanError(''); setResult(null)
    if (!keepBaseline) setBaseline(null)
    go('live')
    try {
      const { id, live } = await startScan({
        prompt: hardened ?? cfg.prompt, langs: cfg.langs, categories: cfg.categories,
        phrasings: cfg.phrasings, model: cfg.model,
        ...(hardened ? { extraction_reference: cfg.prompt } : {}),
      })
      setScanLive(live)
      stop.current = streamScan(id, {
        onResult: ({ row, total: t }) => { setRows((r) => [...r, row]); if (t) setTotal(t) },
        onDone: async () => {
          try {
            const res = await getResult(id)
            setResult(res); go('results')
          } catch (e) { setScanError(e.message) }
        },
        onError: (e) => setScanError(e.message),
      })
    } catch (e) { setScanError(e.message) }
  }, [])

  // The live board's state, derived from the rows that have arrived so far.
  const scanLanguages = useMemo(
    () => (meta && config ? meta.languages.filter((l) => config.langs.includes(l.code)) : []),
    [meta, config],
  )
  const outcomes = useMemo(() => {
    const m = {}
    for (const r of rows) (m[r.lang] ||= []).push(r.error ? 'error' : r.broke ? 'broke' : 'held')
    return m
  }, [rows])

  const switcher = <ThemeSwitcher theme={theme} onPick={setTheme} />

  if (metaError && !meta) {
    return (
      <>
        <Nav loaded={false} onHome={() => {}} showScan={false} />
        <main className="on-page mx-auto max-w-2xl px-5 py-24">
          <h1 className="display text-5xl">PolyGuard can’t reach its server.</h1>
          <p className="mt-4 text-dim">{metaError}</p>
          <button type="button" onClick={loadMeta} className="btn btn-solid mt-8">Try again</button>
        </main>
        {switcher}
      </>
    )
  }

  return (
    <>
      <Nav
        live={meta?.live} loaded={!!meta}
        onHome={() => { stop.current?.(); go('landing') }}
        onScan={() => go('setup')}
        showScan={view === 'landing' && !!meta}
      />
      {view === 'landing' && <Landing meta={meta} onStart={() => meta && go('setup')} />}
      {view === 'setup' && meta && (
        <Setup
          meta={meta} initial={config}
          onBack={() => go('landing')}
          onLaunch={(cfg) => launch(cfg)}
          onUnlock={async () => { const m = await loadMeta(); return !!m?.live }}
        />
      )}
      {view === 'live' && config && (
        <LiveScan
          languages={scanLanguages} outcomes={outcomes}
          expected={config.categories.length * config.phrasings}
          done={rows.length} total={total} broke={rows.filter((r) => r.broke).length}
          latest={rows[rows.length - 1]} live={scanLive}
          title={config.exampleName ? `the ${config.exampleName.toLowerCase()}` : 'your chatbot'}
          error={scanError} onCancel={() => { stop.current?.(); go('setup') }}
        />
      )}
      {view === 'results' && result && (
        <Results
          result={result} baseline={baseline} config={config}
          onAgain={() => go('setup')}
          onRescan={(hardened) => { setBaseline(result); launch(config, { hardened, keepBaseline: true }) }}
        />
      )}
      {switcher}
    </>
  )
}
