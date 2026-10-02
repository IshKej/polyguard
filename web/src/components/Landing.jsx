import { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react'
import { firstSentence } from '../api'
import { NO } from '../lib/languages'
import { useReducedMotion } from '../lib/motion'
import HighlighterField from './HighlighterField'
import ScrollStory from './ScrollStory'
import SpotTheAttack from './SpotTheAttack'

// Three.js is heavy, so the bubble loads after the page is already readable.
const Bubble3D = lazy(() => import('./Bubble3D'))
const REPO = 'https://github.com/IshKej/polyguard'
const EVERY = 2600 // ms on each language in the hero

// Draws its highlighter stroke once it is on screen, and again whenever `again`
// changes, so a word that swaps gets marked fresh.
function Marked({ children, again, className = '', ...rest }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    el.classList.remove('drawn')
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { requestAnimationFrame(() => el.classList.add('drawn')); io.disconnect() }
    }, { threshold: 0.6 })
    io.observe(el)
    return () => io.disconnect()
  }, [again])
  return <span ref={ref} className={`hl ${className}`} {...rest}>{children}</span>
}

// The cursor over the hero: a highlighter pen, tip at the lower left.
const PEN = `url("data:image/svg+xml,${encodeURIComponent(
  "<svg xmlns='http://www.w3.org/2000/svg' width='34' height='34' viewBox='0 0 34 34'><g transform='rotate(45 17 17)'><rect x='13' y='0' width='8' height='21' rx='2' fill='#1a1c15' stroke='#eeede5' stroke-width='1.5'/><path d='M13 21h8l-1.6 7h-4.8z' fill='#e6ff2e' stroke='#1a1c15' stroke-width='1.3' stroke-linejoin='round'/></g></svg>",
)}") 6 27, crosshair`

// A torn edge, so a paper section reads as a sheet torn from a pad. It is a strip
// of the same paper, grain and all, cut along a fixed but irregular line.
const TEAR = (() => {
  let seed = 7
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 }
  const pts = []
  for (let x = 0; x < 100; x += 0.5 + rand() * 1.2) pts.push([x, 2 + rand() * 9])
  pts.push([100, 6])
  return pts
})()
const at = ([x, y]) => `${x.toFixed(2)}% ${y.toFixed(1)}px`
const TORN = {
  bottom: `polygon(0 0, 100% 0, ${[...TEAR].reverse().map(at).join(', ')})`,
  top: `polygon(${TEAR.map(([x, y]) => at([x, 14 - y])).join(', ')}, 100% 14px, 0 14px)`,
}

function Torn({ side }) {
  return (
    <div
      aria-hidden="true"
      className={`paper pointer-events-none absolute inset-x-0 z-10 h-3.5 ${side === 'top' ? '-top-3.5' : '-bottom-3.5'}`}
      style={{ clipPath: TORN[side] }}
    />
  )
}

// How far an element has come up into view: 0 as its top reaches the bottom of
// the screen, 1 once its top is a quarter of the way down. Wide screens only, and
// never with reduced motion: on a phone the stretch would reflow the lines.
function useRiseProgress(ref) {
  const [v, setV] = useState(null)
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px) and (prefers-reduced-motion: no-preference)')
    let raf = 0
    const read = () => {
      raf = 0
      const el = ref.current
      if (!el || !mq.matches) { setV(null); return }
      const top = el.getBoundingClientRect().top
      setV(Math.min(1, Math.max(0, (window.innerHeight - top) / (window.innerHeight * 0.75))))
    }
    const on = () => { if (!raf) raf = requestAnimationFrame(read) }
    read()
    window.addEventListener('scroll', on, { passive: true })
    window.addEventListener('resize', on)
    mq.addEventListener('change', on)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('scroll', on)
      window.removeEventListener('resize', on)
      mq.removeEventListener('change', on)
    }
  }, [ref])
  return v
}

// One attack, in one language, as a card: the gallery of the same attack.
function Specimen({ lang, text }) {
  const ref = useRef(null)
  const reduce = useReducedMotion()
  const onMove = (e) => {
    if (reduce) return
    const r = ref.current.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width - 0.5
    const y = (e.clientY - r.top) / r.height - 0.5
    ref.current.style.transform = `perspective(900px) rotateX(${-y * 6}deg) rotateY(${x * 8}deg) translateY(-4px)`
  }
  const onLeave = () => { ref.current.style.transform = '' }
  return (
    <article
      ref={ref} onPointerMove={onMove} onPointerLeave={onLeave}
      className="hl-hover card cut flex min-h-64 flex-col justify-between p-5 transition-transform duration-200 ease-out will-change-transform"
    >
      <p dir="auto" lang={lang.code} className="text-[1.45rem] font-semibold leading-snug">
        <span className="hl">{text}</span>
      </p>
      <div className="mt-6 flex items-end justify-between gap-3 pr-6">
        <div>
          <div dir="auto" lang={lang.code} className="font-semibold">{lang.native}</div>
          <div className="caption mt-1 text-(--mute)">{lang.name}, {lang.tier} resource</div>
        </div>
      </div>
    </article>
  )
}

const REASONS = [
  ['Safety gets tested', 'in English first.', 'Most testing of AI guardrails happens in English, so English is where they are strongest.'],
  ['Real people write', 'in every language.', 'A school, a clinic or a bank serves families who type in Hindi, Tagalog, Vietnamese and Spanish. The same bot answers all of them.'],
  ['PolyGuard measures', 'the difference.', 'The same attack in every language, scored the same way, with statistics honest enough to say when there is no gap at all.'],
]

export default function Landing({ meta, onStart, onMethod }) {
  const others = useMemo(() => (meta?.languages || []).filter((l) => l.code !== 'en'), [meta])
  const headline = useMemo(() => others.filter((l) => l.native.length <= 10), [others])
  const lines = useMemo(
    () => others.map((l) => ({ code: l.code, text: firstSentence(meta?.hero_line?.[l.code]) })).filter((l) => l.text),
    [others, meta],
  )
  const english = firstSentence(meta?.hero_line?.en) || 'Ignore all previous instructions.'
  const count = meta?.languages?.length ?? 20
  const reduce = useReducedMotion()
  const close = useRef(null)
  const rise = useRiseProgress(close)
  // The closing words widen into place as the panel arrives (Mona Sans has a width axis).
  const stretch = rise == null ? undefined : { fontStretch: `${80 + 32 * rise}%` }

  // The language the hero is on. Every fourth one gets through, as an illustration.
  const [i, setI] = useState(0)
  const [picked, setPicked] = useState(null)
  useEffect(() => {
    if (reduce || picked || headline.length < 2) return undefined
    const id = setInterval(() => setI((n) => (n + 1) % headline.length), EVERY)
    return () => clearInterval(id)
  }, [headline.length, reduce, picked])
  const lang = (picked && others.find((l) => l.code === picked)) || headline[i] || { native: 'Hindi', name: 'Hindi', code: 'hi', tier: 'high' }
  const broke = !picked && i % 4 === 2

  // Keep the strip's chosen language in view as the hero cycles.
  const strip = useRef(null)
  useEffect(() => {
    const box = strip.current
    const chip = box?.querySelector(`[data-code="${lang.code}"]`)
    if (!box || !chip) return
    box.scrollTo({ left: chip.offsetLeft - box.clientWidth / 2 + chip.clientWidth / 2, behavior: reduce ? 'auto' : 'smooth' })
  }, [lang.code, reduce])
  const nudge = (dir) => strip.current?.scrollBy({ left: dir * 320, behavior: reduce ? 'auto' : 'smooth' })
  const gallery = useMemo(() => lines.slice(0, 8).map((l) => ({ ...l, lang: others.find((o) => o.code === l.code) })), [lines, others])

  return (
    <main>
      {/* Hero: paper, the highlighter, the bubble. */}
      <section data-surface="paper" className="paper relative flex min-h-[max(100svh,700px)] flex-col overflow-hidden" style={{ cursor: PEN }}>
        <HighlighterField english={english} lines={lines} />
        <div className="relative mx-auto grid w-full max-w-7xl flex-1 items-center gap-6 px-5 pb-8 pt-32 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,.7fr)] lg:pt-24">
          <div>
            <h1 className="display text-[clamp(2.2rem,4.15vw,4.1rem)]">
              Your chatbot
              <br />
              says <span className="serif text-[1.1em]">no</span> in English.
              <br />
              Does it say <span className="serif text-[1.1em]">no</span>
              <br />
              in{' '}
              <Marked again={lang.code} dir="auto" lang={lang.code} className={`serif text-[1.1em] ${lang.native.length <= 10 ? 'whitespace-nowrap' : ''}`}>{lang.native}</Marked>?
            </h1>
            <p className="mt-7 max-w-md text-lg text-(--mute)">
              PolyGuard sends the same attacks in {count} languages and shows where a chatbot’s guardrails hold, and
              where they give way.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button type="button" onClick={onStart} className="btn btn-solid">Scan a chatbot</button>
              <a href="#how" className="btn btn-line">How it works</a>
            </div>
          </div>
          <div className="relative -mx-5 lg:mx-0">
            <Suspense fallback={null}>
              <Bubble3D word={broke ? 'PWNED' : NO[lang.code] || 'No.'} broke={broke} className="h-[clamp(260px,42vw,560px)] w-full" />
            </Suspense>
            {/* The card that says what the bubble is showing, like a race card. */}
            <div className="relative mx-5 -mt-4 w-60 rounded-md lg:absolute lg:bottom-2 lg:left-0 lg:mx-0 lg:mt-0 border border-(--fg) bg-(--bg)/85 p-3 backdrop-blur-[2px] lg:left-0">
              <div className="caption text-(--mute)">Now testing</div>
              <div dir="auto" lang={lang.code} className="mt-1 text-2xl font-bold leading-tight">{lang.native}</div>
              <div className="caption mt-0.5">{lang.name}</div>
              <div className="mt-3 flex items-center justify-between border-t border-(--line) pt-2">
                <span className={`tag ${broke ? 'bg-red text-ink' : 'bg-hi text-ink'}`}>{broke ? 'Got through' : 'Held'}</span>
                <span className="caption text-(--mute)">Illustration</span>
              </div>
            </div>
          </div>
        </div>
        {/* Every language in the bank, Duolingo style: find yours, and the page answers in it. */}
        <div className="relative border-t border-(--line) bg-(--bg)/90">
          <div className="mx-auto flex max-w-7xl items-center gap-3 px-5 py-3">
            <span className="caption hidden shrink-0 sm:block">Pick your language</span>
            <button type="button" onClick={() => nudge(-1)} aria-label="Earlier languages" className="hidden size-8 shrink-0 place-items-center rounded-md border border-(--line) hover:border-ink sm:grid">
              <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
            </button>
            <div ref={strip} className="flex min-w-0 flex-1 gap-1 overflow-x-auto [scrollbar-width:none]" role="group" aria-label="Pick your language">
              {others.map((l) => {
                const on = l.code === lang.code
                return (
                  <button
                    key={l.code} data-code={l.code} type="button" aria-pressed={on}
                    onClick={() => setPicked(l.code)} title={l.name}
                    className={`hl-hover shrink-0 rounded-md px-3 py-1.5 font-semibold transition-colors ${on ? 'bg-ink text-paper' : 'hover:text-ink'}`}
                  >
                    <span dir="auto" lang={l.code} className={on ? '' : 'hl'}>{l.native}</span>
                  </button>
                )
              })}
            </div>
            <button type="button" onClick={() => nudge(1)} aria-label="More languages" className="hidden size-8 shrink-0 place-items-center rounded-md border border-(--line) hover:border-ink sm:grid">
              <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden="true"><path d="m6 3 5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" /></svg>
            </button>
            {picked && (
              <button type="button" onClick={() => setPicked(null)} className="hl-hover caption hidden shrink-0 md:block"><span className="hl">Cycle again</span></button>
            )}
            <span className="caption hidden shrink-0 text-(--mute) xl:block">Move the cursor. It is a highlighter.</span>
          </div>
        </div>
      </section>

      {/* The same attack, scrolling past in every script. */}
      <section data-surface="on-hi" className="on-hi overflow-hidden border-y-2 border-ink py-4" aria-label="The same attack in every language">
        <div className="flex">
          <div className="flex shrink-0 animate-marquee items-center gap-8 pr-8">
            {[...lines, ...lines].map((l, n) => (
              <span key={n} className="flex items-center gap-8 whitespace-nowrap">
                <span dir="auto" lang={l.code} className="display text-[1.6rem] normal-case">{l.text}</span>
                <svg viewBox="0 0 24 24" className="size-5 shrink-0" aria-hidden="true">
                  <path fill="currentColor" d="M5 3h14a4 4 0 0 1 4 4v7a4 4 0 0 1-4 4h-7l-6 5v-5H5a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4z" />
                </svg>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Why: three statements, in the mixed voice. */}
      <section data-surface="ink" className="ink">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:py-28">
          <h2 className="display max-w-5xl text-[clamp(2.4rem,5.6vw,5rem)]">
            The people using your chatbot <span className="serif">don’t all write in English.</span>
          </h2>
          <div className="mt-14 border-b border-(--line)">
            {REASONS.map(([a, b, body]) => (
              <div key={a} className="hl-hover group grid gap-x-10 gap-y-3 border-t border-(--line) py-8 md:grid-cols-[minmax(0,6fr)_minmax(0,5fr)]">
                <h3 className="display text-[clamp(1.6rem,2.8vw,2.4rem)]">
                  <span className="hl">{a}</span> <span className="serif">{b}</span>
                </h3>
                <p className="max-w-[48ch] self-end text-(--mute)">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* The gallery: one attack, written eight more ways. */}
      <section data-surface="paper" className="paper relative">
        <Torn side="top" />
        <Torn side="bottom" />
        <div className="ruler" />
        <div className="mx-auto max-w-7xl px-5 py-20 sm:py-24">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <h2 className="display text-[clamp(2.4rem,5.6vw,5rem)]">
              Same attack.
              <br />
              <span className="serif">{count} languages.</span>
            </h2>
            <p className="max-w-sm text-(--mute)">
              “{english}” is where a prompt injection usually starts. Hover a card to see the line PolyGuard marks.
            </p>
          </div>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {gallery.map((g) => g.lang && <Specimen key={g.code} lang={g.lang} text={g.text} />)}
          </div>
        </div>
      </section>

      {/* How it works: pinned, and played by scrolling. */}
      <ScrollStory languages={others} lines={lines} prompt={meta?.examples?.[0]?.prompt || ''} />

      {/* The question every result raises, answered on its own page. */}
      <section data-surface="ink" className="ink">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 border-t border-(--line) px-5 py-12 sm:flex-row sm:items-center">
          <p className="display max-w-3xl text-[clamp(1.6rem,3vw,2.4rem)]">
            Some language always comes out worst. <span className="serif">So how do you know a gap is real?</span>
          </p>
          <button type="button" onClick={onMethod} className="btn btn-line shrink-0">See how we know</button>
        </div>
      </section>

      {/* The game, on a fresh sheet. */}
      <div className="relative">
        <Torn side="top" />
        <SpotTheAttack languages={others} onStart={onStart} />
      </div>

      {/* The close: highlighter ground, an ink panel with a bump, like a speech bubble's top. */}
      <section data-surface="on-hi" className="on-hi px-3 pb-3 pt-16 sm:px-4">
        <div ref={close} className="ink relative rounded-[36px] px-6 pb-10 pt-20 text-center sm:px-10">
          <svg viewBox="0 0 240 40" className="absolute -top-[39px] left-1/2 h-10 w-60 -translate-x-1/2 fill-ink" aria-hidden="true">
            <path d="M0 40 C 40 40, 50 0, 90 0 L 150 0 C 190 0, 200 40, 240 40 Z" />
          </svg>
          <h2 className="display mx-auto max-w-6xl text-[clamp(2.4rem,6vw,5.6rem)]">
            <span className="lg:whitespace-nowrap" style={stretch}>Find out where</span>
            <br className="hidden lg:block" />{' '}
            <span className="lg:whitespace-nowrap"><span style={stretch}>your bot</span> <span className="serif">says yes.</span></span>
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-(--mute)">
            {meta?.examples?.length ?? 4} example chatbots are ready, or paste the instructions your own bot runs on.
          </p>
          <button type="button" onClick={onStart} className="btn btn-solid mt-8">Scan a chatbot</button>
          <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-(--line) pt-6 text-sm sm:flex-row">
            <p className="text-(--mute)">PolyGuard is a defensive tool. Test only systems you own or are authorized to test.</p>
            <a href={REPO} target="_blank" rel="noopener" className="hl-hover caption">
              <span className="hl">Source, audit and preregistration</span>
            </a>
          </div>
        </div>
      </section>
    </main>
  )
}
