import { useEffect, useRef, useState } from 'react'
import { NO } from '../lib/languages'
import { isMotionOff, setMotionOff, useMotionOff } from '../lib/motion'

const REPO = 'https://github.com/IshKej/polyguard'

// Turns the page's motion off and on: the 3D bubble, the smooth scroll, the
// scroll story, the hero cycle. Remembered on this device.
export function MotionSwitch({ className = '' }) {
  const off = useMotionOff()
  return (
    <button
      type="button" onClick={() => setMotionOff(!off)} aria-pressed={!off}
      title={off ? 'Turn the animations back on' : 'Stop the animations'}
      className={`hl-hover caption ${className}`}
    >
      <span className="hl">Motion {off ? 'off' : 'on'}</span>
    </button>
  )
}

// The wordmark: "Poly" in the serif voice over "GUARD" in the heavy one.
export function Wordmark() {
  return (
    <span className="flex flex-col leading-[.82]">
      <span className="font-serif text-[1.45rem] tracking-[-.01em]">Poly</span>
      <span className="display display-caps text-[1.45rem] tracking-[-.01em]">Guard</span>
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
    // A page can render its first ground after the nav mounts (the method page
    // waits for its data), so look again whenever the page's size changes.
    // Without this, /how opened directly kept paper colours on its ink hero.
    const ro = new ResizeObserver(pick)
    ro.observe(document.body)
    return () => { window.removeEventListener('scroll', pick); window.removeEventListener('resize', pick); ro.disconnect() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

export function Nav({ live, loaded, onHome, onScan, onMethod, showScan, view }) {
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
            // Always shown, phones included, so a cropped screenshot of a demo can
            // never pass for a real measurement.
            <span
              className="tag inline-block border border-current"
              title={live ? 'Scans attack a real model.' : 'No model is attacked. Outcomes are made up.'}
            >
              {live ? 'Live' : 'Simulated'}
            </span>
          )}
          {onMethod && view !== 'method' && (
            <button type="button" onClick={onMethod} className="hl-hover caption hidden text-[.8rem] md:inline">
              <span className="hl">How we know</span>
            </button>
          )}
          <MotionSwitch className="hidden text-[.8rem] md:inline" />
          <a href={REPO} target="_blank" rel="noopener" className="hl-hover caption hidden text-[.8rem] md:inline">
            <span className="hl">GitHub</span>
          </a>
          {showScan && (
            <button type="button" onClick={onScan} className={`btn btn-sm hidden md:inline-flex ${surface === 'on-hi' ? 'btn-solid' : 'nav-hi'}`}>
              Scan your own chatbot
            </button>
          )}
          <MobileMenu onMethod={view !== 'method' ? onMethod : null} onScan={showScan ? onScan : null} />
        </div>
      </div>
    </header>
  )
}

// Below tablet width the nav keeps only the badge and this button. The panel holds
// everything the wide nav shows, with touch sized targets, and the Motion switch is
// in it so pausing is one tap away rather than at the bottom of the page.
function MobileMenu({ onMethod, onScan }) {
  const [open, setOpen] = useState(false)
  const button = useRef(null)
  const panel = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    panel.current?.querySelector('a, button')?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') { setOpen(false); button.current?.focus() }
    }
    const onAway = (e) => {
      if (!panel.current?.contains(e.target) && !button.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onAway)
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('pointerdown', onAway) }
  }, [open])
  const go = (fn) => () => { setOpen(false); fn?.() }
  const item = 'flex min-h-11 w-full items-center px-4 text-left text-base'
  return (
    <div className="relative md:hidden">
      <button
        ref={button} type="button" aria-expanded={open} aria-controls="site-menu"
        onClick={() => setOpen((o) => !o)}
        className="btn btn-sm min-h-11 min-w-11 nav-hi"
      >
        {open ? 'Close' : 'Menu'}
      </button>
      {open && (
        <nav id="site-menu" ref={panel} aria-label="Site"
             className="paper absolute right-0 top-full mt-2 w-64 border-2 border-ink py-2 shadow-[4px_4px_0_var(--ink)]">
          {onMethod && <button type="button" onClick={go(onMethod)} className={item}>How we know</button>}
          {onScan && <button type="button" onClick={go(onScan)} className={item}>Scan your own chatbot</button>}
          <div className={item}><MotionSwitch className="text-base" /></div>
          <a href={REPO} target="_blank" rel="noopener" className={item}>GitHub</a>
        </nav>
      )}
    </div>
  )
}

const LOADER_KEY = 'polyguard.seen'
const CYCLE = ['en', 'hi', 'es', 'ar', 'zh', 'ru', 'ja', 'fr', 'ko', 'gu']

// First visit only: one second of highlighter, the word "no" turning over in
// language after language. Skipped with motion off and on later visits.
export function Loader() {
  const [show, setShow] = useState(() => {
    if (isMotionOff()) return false
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
