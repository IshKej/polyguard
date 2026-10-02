import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getMeta, getResult, startScan, streamScan } from './api'
import { Loader, Nav } from './components/Chrome'
import { jumpToTop, startSmoothScroll, stopSmoothScroll } from './lib/smooth'
import Landing from './components/Landing'
import LiveScan from './components/LiveScan'
import Results from './components/Results'
import Setup from './components/Setup'

export default function App() {
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

  const loadMeta = useCallback(
    () => getMeta().then((m) => { setMeta(m); setMetaError(''); return m }).catch((e) => { setMetaError(e.message); return null }),
    [],
  )
  useEffect(() => {
    let alive = true
    getMeta().then((m) => alive && setMeta(m)).catch((e) => alive && setMetaError(e.message))
    return () => { alive = false; stop.current?.() }
  }, [])

  // Moving between screens: a highlighter panel wipes up over the page, the
  // screen changes underneath it, and it carries on up and away.
  const [wipe, setWipe] = useState('idle')
  const wipeTimers = useRef([])
  const go = useCallback((v) => {
    const instant = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    wipeTimers.current.forEach(clearTimeout)
    if (instant) { setView(v); jumpToTop(); return }
    setWipe('in')
    wipeTimers.current = [
      setTimeout(() => { setView(v); jumpToTop(); setWipe('out') }, 380),
      setTimeout(() => setWipe('idle'), 820),
    ]
  }, [])
  useEffect(() => () => wipeTimers.current.forEach(clearTimeout), [])
  useEffect(() => { startSmoothScroll(); return stopSmoothScroll }, [])

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
  }, [go])

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

  if (metaError && !meta) {
    return (
      <>
        <Nav loaded={false} onHome={() => {}} showScan={false} view="error" />
        <main data-surface="paper" className="paper mx-auto min-h-screen max-w-2xl px-5 pb-24 pt-36">
          <h1 className="display text-5xl">PolyGuard can’t reach <span className="serif">its server.</span></h1>
          <p className="mt-4 max-w-lg text-(--mute)">
            The scan server isn’t answering. If you are running PolyGuard yourself, start it with{' '}
            <code className="rounded bg-paper-2 px-1.5 py-0.5 text-ink">python -m uvicorn api.server:app --port 8000</code>{' '}
            and try again.
          </p>
          <button type="button" onClick={loadMeta} className="btn btn-solid mt-8">Try again</button>
        </main>
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
        view={view}
      />
      <Loader />
      <div
        aria-hidden="true"
        className={`on-hi pointer-events-none fixed inset-0 z-50 grid place-items-center ${
          wipe === 'idle' ? 'translate-y-full' : wipe === 'in' ? 'translate-y-0 transition-transform duration-[380ms] ease-[cubic-bezier(.7,0,.3,1)]' : '-translate-y-full transition-transform duration-[440ms] ease-[cubic-bezier(.7,0,.3,1)]'
        }`}
      >
        <span className="font-serif text-[clamp(3rem,8vw,6rem)] leading-none">Poly<span className="display">Guard</span></span>
      </div>
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
          recent={rows.slice(-4)} live={scanLive}
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
    </>
  )
}
