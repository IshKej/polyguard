import { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react'
import { firstSentence } from '../api'
import { NO } from '../lib/languages'
import { useReducedMotion } from '../lib/motion'
import Board from './Board'
import HighlighterField from './HighlighterField'

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

// A self-playing preview of the scan board. The outcomes are generated here in
// the browser, from a fixed pattern, and the caption says so.
function PreviewBoard({ languages }) {
  const expected = 10
  const reduce = useReducedMotion()
  const shown = useMemo(() => languages.slice(0, 7), [languages])
  const full = useMemo(() => {
    const pattern = (li, ai) => ((li * 7 + ai * 13 + li * ai) % 10 < 3 ? 'broke' : 'held')
    return Object.fromEntries(shown.map((l, li) => [l.code, Array.from({ length: expected }, (_, ai) => pattern(li, ai))]))
  }, [shown])
  const [outcomes, setOutcomes] = useState({})

  useEffect(() => {
    if (reduce || !shown.length) return undefined
    let step = 0
    let holdUntil = 0
    const order = []
    for (let ai = 0; ai < expected; ai++) shown.forEach((l) => order.push(l.code))
    const id = setInterval(() => {
      if (Date.now() < holdUntil) return
      if (step >= order.length) {
        if (holdUntil === 0) { holdUntil = Date.now() + 2800; return }
        holdUntil = 0
        step = 0
        setOutcomes({})
        return
      }
      const code = order[step]
      setOutcomes((prev) => {
        const have = prev[code] || []
        return { ...prev, [code]: [...have, full[code][have.length]] }
      })
      step += 1
    }, 110)
    return () => clearInterval(id)
  }, [shown, full, reduce])

  return (
    <Board
      languages={shown} outcomes={reduce ? full : outcomes} expected={expected} compact
      caption="A preview with made up outcomes. Highlighter held. Red got through."
    />
  )
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

const STEPS = [
  ['Pick a chatbot', 'Paste the instructions it runs on, or start from an example.'],
  ['Attack it', 'Five kinds of prompt injection, in every language, several phrasings each.'],
  ['Watch the board', 'A judge that reads any language decides whether the bot held or gave in.'],
  ['Close the gap', 'See which languages broke, whether it is more than chance, and the rules that fix it.'],
]

export default function Landing({ meta, onStart }) {
  const others = useMemo(() => (meta?.languages || []).filter((l) => l.code !== 'en'), [meta])
  const headline = useMemo(() => others.filter((l) => l.native.length <= 10), [others])
  const lines = useMemo(
    () => others.map((l) => ({ code: l.code, text: firstSentence(meta?.hero_line?.[l.code]) })).filter((l) => l.text),
    [others, meta],
  )
  const english = firstSentence(meta?.hero_line?.en) || 'Ignore all previous instructions.'
  const count = meta?.languages?.length ?? 20
  const reduce = useReducedMotion()

  // The language the hero is on. Every fourth one gets through, as an illustration.
  const [i, setI] = useState(0)
  useEffect(() => {
    if (reduce || headline.length < 2) return undefined
    const id = setInterval(() => setI((n) => (n + 1) % headline.length), EVERY)
    return () => clearInterval(id)
  }, [headline.length, reduce])
  const lang = headline[i] || { native: 'Hindi', name: 'Hindi', code: 'hi', tier: 'high' }
  const broke = i % 4 === 2
  const gallery = useMemo(() => lines.slice(0, 8).map((l) => ({ ...l, lang: others.find((o) => o.code === l.code) })), [lines, others])

  return (
    <main>
      {/* Hero: paper, the highlighter, the bubble. */}
      <section data-surface="paper" className="paper relative min-h-[max(100svh,680px)] overflow-hidden">
        <HighlighterField english={english} lines={lines} />
        <div className="relative mx-auto grid max-w-7xl items-center gap-6 px-5 pb-10 pt-32 lg:min-h-[max(100svh,680px)] lg:grid-cols-[minmax(0,1.3fr)_minmax(0,.7fr)] lg:pt-24">
          <div>
            <h1 className="display text-[clamp(2.2rem,4.15vw,4.1rem)]">
              Your chatbot
              <br />
              says <span className="serif text-[1.1em]">no</span> in English.
              <br />
              Does it say <span className="serif text-[1.1em]">no</span>
              <br />
              in{' '}
              <Marked again={lang.code} dir="auto" lang={lang.code} className="serif whitespace-nowrap text-[1.1em]">{lang.native}</Marked>?
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
        <p className="caption absolute bottom-4 right-5 hidden text-(--mute) lg:block">Move the cursor. It is a highlighter.</p>
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
      <section data-surface="paper" className="paper">
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

      {/* How it works, with the board running beside it. */}
      <section id="how" data-surface="ink" className="ink scroll-mt-16">
        <div className="mx-auto grid max-w-7xl items-start gap-14 px-5 py-20 sm:py-28 lg:grid-cols-[minmax(0,.9fr)_minmax(0,1.1fr)]">
          <div>
            <h2 className="display text-[clamp(2.4rem,5.6vw,5rem)]">
              How it <span className="serif">works.</span>
            </h2>
            <ol className="mt-10 space-y-7">
              {STEPS.map(([title, body], n) => (
                <li key={title} className="hl-hover grid grid-cols-[3.25rem_1fr] gap-x-4">
                  <span aria-hidden="true" className="display grid size-12 place-items-center rounded-md bg-hi text-2xl text-ink">{n + 1}</span>
                  <div>
                    <h3 className="display text-[1.7rem]"><span className="hl">{title}</span></h3>
                    <p className="mt-1.5 max-w-sm text-(--mute)">{body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <div className="lg:pt-6">
            <PreviewBoard languages={others} />
          </div>
        </div>
      </section>

      {/* The close: highlighter ground, an ink panel with a bump, like a speech bubble's top. */}
      <section data-surface="on-hi" className="on-hi px-3 pb-3 pt-16 sm:px-4">
        <div className="ink relative rounded-[36px] px-6 pb-10 pt-20 text-center sm:px-10">
          <svg viewBox="0 0 240 40" className="absolute -top-[39px] left-1/2 h-10 w-60 -translate-x-1/2 fill-ink" aria-hidden="true">
            <path d="M0 40 C 40 40, 50 0, 90 0 L 150 0 C 190 0, 200 40, 240 40 Z" />
          </svg>
          <h2 className="display mx-auto max-w-5xl text-[clamp(2.4rem,6vw,5.6rem)]">
            Find out where your bot <span className="serif">says yes.</span>
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
