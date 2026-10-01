import { useEffect, useState } from 'react'
import { NO } from '../lib/languages'

const REPO = 'https://github.com/IshKej/polyguard'

// The wordmark: "Poly" in the serif voice over "GUARD" in the heavy one.
export function Wordmark() {
  return (
    <span className="flex flex-col leading-[.82]">
      <span className="font-serif text-[1.45rem] tracking-[-.01em]">Poly</span>
      <span className="display text-[1.45rem] tracking-[-.01em]">Guard</span>
    </span>
  )
}

// Which ground is under the nav right now, whether the page has scrolled, and
// whether the nav should step out of the way (scrolling down) or come back (up).
function useNavState(offset = 36, deps = []) {
  const [state, setState] = useState({ surface: 'paper', scrolled: false, hidden: false })
  useEffect(() => {
    let lastY = window.scrollY
    const pick = () => {
      const y = window.scrollY
      const hit = [...document.querySelectorAll('[data-surface]')].find((el) => {
        if (el.closest('header')) return false
        const r = el.getBoundingClientRect()
        return r.top <= offset && r.bottom > offset
      })
      const goingDown = y > lastY + 4
      const goingUp = y < lastY - 4
      lastY = y
      setState((prev) => ({
        surface: hit?.dataset.surface || 'paper',
        scrolled: y > 8,
        hidden: y < 120 ? false : goingDown ? true : goingUp ? false : prev.hidden,
      }))
    }
    pick()
    window.addEventListener('scroll', pick, { passive: true })
    window.addEventListener('resize', pick)
    return () => { window.removeEventListener('scroll', pick); window.removeEventListener('resize', pick) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

export function Nav({ live, loaded, onHome, onScan, showScan, view }) {
  const { surface, scrolled, hidden } = useNavState(36, [view])
  return (
    <header
      className={`${surface} fixed inset-x-0 top-0 z-30 transition-[transform,background-color] duration-300 ${scrolled ? 'border-b border-(--line)' : ''} ${hidden ? '-translate-y-full' : ''}`}
      style={scrolled ? undefined : { background: 'transparent' }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4">
        <button type="button" onClick={onHome} aria-label="PolyGuard home" className="text-left">
          <Wordmark />
        </button>
        <div className="flex items-center gap-3 sm:gap-5">
          {loaded && (
            <span
              className="tag hidden border border-current sm:inline-block"
              title={live ? 'Scans attack a real model.' : 'No model is attacked. Outcomes are made up.'}
            >
              {live ? 'Live' : 'Simulated'}
            </span>
          )}
          <a href={REPO} target="_blank" rel="noopener" className="hl-hover caption hidden text-[.8rem] sm:inline">
            <span className="hl">GitHub</span>
          </a>
          {showScan && (
            <button type="button" onClick={onScan} className={`btn btn-sm ${surface === 'on-hi' ? 'btn-solid' : 'nav-hi'}`}>
              Scan a chatbot
            </button>
          )}
        </div>
      </div>
    </header>
  )
}

const LOADER_KEY = 'polyguard.seen'
const CYCLE = ['en', 'hi', 'es', 'ar', 'zh', 'ru', 'ja', 'fr', 'ko', 'gu']

// First visit only: one second of highlighter, the word "no" turning over in
// language after language. Skipped for reduced motion and on later visits.
export function Loader() {
  const [show, setShow] = useState(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false
    try { return !sessionStorage.getItem(LOADER_KEY) } catch { return false }
  })
  const [n, setN] = useState(0)
  const [leaving, setLeaving] = useState(false)

  useEffect(() => {
    if (!show) return undefined
    try { sessionStorage.setItem(LOADER_KEY, '1') } catch { /* private mode */ }
    const tick = setInterval(() => setN((x) => x + 1), 90)
    const out = setTimeout(() => setLeaving(true), 1050)
    const done = setTimeout(() => setShow(false), 1550)
    return () => { clearInterval(tick); clearTimeout(out); clearTimeout(done) }
  }, [show])

  if (!show) return null
  const code = CYCLE[n % CYCLE.length]
  return (
    <div
      className={`on-hi fixed inset-0 z-[60] grid place-items-center transition-transform duration-500 ease-[cubic-bezier(.7,0,.2,1)] ${leaving ? '-translate-y-full' : ''}`}
      aria-hidden="true"
    >
      <div dir="auto" lang={code} className="display text-[clamp(4rem,14vw,10rem)] normal-case">{NO[code]}</div>
      <div className="caption absolute bottom-8 left-1/2 -translate-x-1/2">Learning to say no</div>
    </div>
  )
}
