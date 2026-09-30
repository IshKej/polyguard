import { useEffect, useMemo, useRef, useState } from 'react'
import gsap from 'gsap'
import { firstSentence } from '../api'
import { useReducedMotion } from '../lib/motion'
import Board from './Board'

const REPO = 'https://github.com/IshKej/polyguard'

// The language that finishes the headline, on a flap that turns over to the next
// one. The names are the bank's own, each in its own script.
function FlapWord({ names }) {
  const [i, setI] = useState(0)
  const ref = useRef(null)
  const reduce = useReducedMotion()

  useEffect(() => {
    if (reduce || names.length < 2) return
    const id = setInterval(() => {
      gsap.to(ref.current, {
        rotateX: 90, duration: 0.2, ease: 'power1.in',
        onComplete: () => {
          setI((n) => (n + 1) % names.length)
          gsap.fromTo(ref.current, { rotateX: -90 }, { rotateX: 0, duration: 0.26, ease: 'power2.out' })
        },
      })
    }, 1900)
    return () => clearInterval(id)
  }, [names.length, reduce])

  const current = names[i] || { native: 'every language', code: 'en' }
  return (
    <span ref={ref} dir="auto" lang={current.code} className="flap whitespace-nowrap align-baseline">
      {current.native}
    </span>
  )
}

// A self-playing preview of the board. The outcomes are generated here in the
// browser, from a fixed pattern, and the caption says so.
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
    if (reduce || !shown.length) return
    let step = 0
    let holdUntil = 0
    const order = []
    for (let ai = 0; ai < expected; ai++) shown.forEach((l) => order.push(l.code))
    const id = setInterval(() => {
      if (Date.now() < holdUntil) return
      if (step >= order.length) {
        // Filled: hold the finished board for a moment, then start over.
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
      caption="A preview with made up outcomes. Green held. Red got through."
    />
  )
}

// The real attack, in every language, moving like a ticker.
function LanguageWall({ lines }) {
  if (!lines.length) return null
  const row = (items, reverse, tone) => (
    <div className="flex overflow-hidden">
      <div className="flex shrink-0 animate-wall gap-12 pr-12" style={reverse ? { animationDirection: 'reverse' } : undefined}>
        {[...items, ...items].map((l, i) => (
          <span key={i} dir="auto" lang={l.code} className={`whitespace-nowrap text-2xl font-semibold sm:text-[1.75rem] ${tone}`}>
            {l.text}
          </span>
        ))}
      </div>
    </div>
  )
  const half = Math.ceil(lines.length / 2)
  return (
    <div className="space-y-4" aria-hidden="true">
      {row(lines.slice(0, half), false, 'text-on-band')}
      {row(lines.slice(half), true, 'text-on-band-alt')}
    </div>
  )
}

const REASONS = [
  ['Safety gets tested in English first.', 'Most testing of AI guardrails happens in English, so English is where they are strongest.'],
  ['Real people write in every language.', 'A school, a clinic or a bank serves families who type in Hindi, Tagalog, Vietnamese and Spanish. The same bot answers all of them.'],
  ['So PolyGuard measures the difference.', 'The same attack in every language, scored the same way, with statistics honest enough to say when there is no gap at all.'],
]

const STOPS = [
  ['Pick a chatbot', 'Paste the instructions it runs on, or start from an example.'],
  ['Attack it', 'Five kinds of prompt injection, in every language, several phrasings each.'],
  ['Watch the board', 'A judge that reads any language decides whether the bot held or gave in.'],
  ['Close the gap', 'See which languages broke, whether it is more than chance, and the rules that fix it.'],
]

export default function Landing({ meta, onStart }) {
  const others = useMemo(() => (meta?.languages || []).filter((l) => l.code !== 'en'), [meta])
  // Only names short enough to keep the headline on two lines.
  const headlineNames = useMemo(() => others.filter((l) => l.native.length <= 10), [others])
  const lines = useMemo(
    () => others.map((l) => ({ code: l.code, text: firstSentence(meta?.hero_line?.[l.code]) })).filter((l) => l.text),
    [others, meta],
  )
  const count = meta?.languages?.length ?? 20

  return (
    <main>
      <section className="on-brand bg-brand text-on-brand">
        <div className="mx-auto max-w-6xl px-5 pb-16 pt-10 sm:pt-14">
          <h1 className="display text-[clamp(2.7rem,7.4vw,6rem)]">
            Your chatbot says no in English.
            <br />
            Does it say no in <FlapWord names={headlineNames} />?
          </h1>
          <div className="mt-9 grid items-start gap-10 lg:grid-cols-[minmax(0,.8fr)_minmax(0,1.2fr)]">
            <div>
              <p className="max-w-md text-xl text-on-brand-dim">
                PolyGuard sends the same attacks in {count} languages and shows where the guardrails hold,
                and where they give way.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <button type="button" onClick={onStart} className="btn btn-solid">Scan a chatbot</button>
                <a href="#how" className="btn btn-line">How it works</a>
              </div>
            </div>
            <PreviewBoard languages={others} />
          </div>
        </div>
      </section>

      <section className="bg-band py-12 text-on-band">
        <p className="mx-auto mb-7 max-w-6xl px-5 text-xl">
          <span className="font-semibold">“Ignore all previous instructions.”</span>{' '}
          <span className="text-on-band-alt">One attack, written {lines.length} more ways.</span>
        </p>
        <LanguageWall lines={lines} />
      </section>

      <section className="on-page mx-auto max-w-6xl px-5 py-20 sm:py-24">
        <h2 className="display max-w-4xl text-[clamp(2.4rem,5.4vw,4.25rem)]">
          The people using your chatbot don’t all write in English.
        </h2>
        <div className="mt-10 border-b-2 border-ink">
          {REASONS.map(([lead, body]) => (
            <div key={lead} className="grid gap-x-10 gap-y-2 border-t-2 border-ink py-6 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
              <h3 className="display text-[1.9rem] leading-none">{lead}</h3>
              <p className="max-w-[60ch] text-dim">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="how" className="on-deep scroll-mt-20 bg-deep text-on-deep">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <h2 className="display text-[clamp(2.4rem,5.4vw,4.25rem)] text-deep-accent">How it works</h2>
          {/* A route with four stops, the way a transit map draws one. */}
          <ol className="relative mt-12 grid gap-y-10 sm:grid-cols-2 sm:gap-x-8 lg:grid-cols-4">
            <span aria-hidden="true" className="absolute left-[11px] top-3 h-[calc(100%-1.5rem)] w-[2px] bg-deep-accent sm:hidden lg:left-0 lg:top-[11px] lg:block lg:h-[2px] lg:w-[calc(75%+1rem)]" />
            {STOPS.map(([title, body], i) => (
              <li key={title} className="relative pl-10 sm:pl-0 sm:pt-10">
                <span aria-hidden="true" className="absolute left-0 top-0 size-6 rounded-full border-2 border-deep-accent bg-deep" />
                <h3 className="display text-[1.75rem] leading-none">
                  <span className="text-deep-accent">{i + 1}</span> {title}
                </h3>
                <p className="mt-2 max-w-xs text-on-deep-dim">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="on-brand bg-brand text-on-brand">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-5 py-14 sm:flex-row sm:items-center">
          <h2 className="display text-[clamp(2rem,4.6vw,3.5rem)]">
            {meta?.examples?.length ?? 4} example chatbots are ready to scan.
          </h2>
          <button type="button" onClick={onStart} className="btn btn-solid shrink-0">Scan a chatbot</button>
        </div>
      </section>

      <footer className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-7 text-base text-dim sm:flex-row sm:items-center sm:justify-between">
        <p>PolyGuard is a defensive tool. Test only systems you own or are authorized to test.</p>
        <a href={REPO} target="_blank" rel="noopener" className="font-semibold text-link underline underline-offset-4">
          Source, audit and preregistration
        </a>
      </footer>
    </main>
  )
}
