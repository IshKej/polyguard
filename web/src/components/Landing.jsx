import BANK_COUNTS from '../bank-counts.json'
import LocalEvidence, { REPORT_URL } from './LocalEvidence'
import { useEffect, useMemo, useState } from 'react'
import { firstSentence } from '../api'
import { MotionSwitch } from './Chrome'
import Mechanism from './Mechanism'
import ScrollStory from './ScrollStory'
import SpotTheAttack from './SpotTheAttack'

const REPO = 'https://github.com/IshKej/polyguard'

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

// One attack, in one language, as a card: the gallery of the same attack. The
// attack text lives only in cards like this, never behind other copy.
function Specimen({ lang, text }) {
  return (
    <article className="card cut flex min-h-56 flex-col justify-between p-5">
      <p dir="auto" lang={lang.code} className="text-[1.3rem] font-semibold leading-snug">{text}</p>
      <div className="mt-6 pr-6">
        <div dir="auto" lang={lang.code} className="text-left font-semibold">{lang.native}</div>
        <div className="caption mt-1 text-(--mute)">{lang.name}, {lang.tier} resource</div>
      </div>
    </article>
  )
}

export default function Landing({ meta, onStart, onTry, onMethod, onReview }) {
  const others = useMemo(() => (meta?.languages || []).filter((l) => l.code !== 'en'), [meta])
  const lines = useMemo(
    () => others.map((l) => ({ code: l.code, text: firstSentence(meta?.hero_line?.[l.code]) })).filter((l) => l.text),
    [others, meta],
  )
  const english = firstSentence(meta?.hero_line?.en) || 'Ignore all previous instructions.'
  // Until /api/meta answers (or if it fails), the counts the build wrote from the
  // bank itself: never a hard-coded number that goes stale.
  const count = meta?.languages?.length ?? BANK_COUNTS.languages
  const gallery = useMemo(() => lines.slice(0, 8).map((l) => ({ ...l, lang: others.find((o) => o.code === l.code) })), [lines, others])
  // Everything under the hero mounts a frame after the first paint, so on a slow
  // phone the headline is not held back by sections nobody can see yet.
  const [rest, setRest] = useState(false)
  useEffect(() => {
    let timer = 0
    const frame = requestAnimationFrame(() => { timer = setTimeout(() => setRest(true), 0) })
    return () => { cancelAnimationFrame(frame); clearTimeout(timer) }
  }, [])

  return (
    <main>
      {/* Hero: the question, and one real attack worked through step by step. */}
      <section data-surface="paper" className="paper relative">
        <div className="mx-auto grid w-full max-w-7xl items-start gap-10 px-5 pb-16 pt-28 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-14 lg:pt-32">
          <div className="lg:sticky lg:top-28">
            <h1 className="display text-[clamp(2.2rem,4.4vw,3.9rem)]">
              Your chatbot says no in English. Does it say no in{' '}
              <span lang="cy" className="underline decoration-[3px] underline-offset-[.14em]">Welsh</span>?
            </h1>
            <p className="mt-6 max-w-md text-lg text-(--mute)">
              PolyGuard sends the same attacks in {count} languages and shows where a chatbot’s rules hold and where they
              give way.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              {onTry && (
                <button type="button" onClick={onTry} disabled={!meta?.examples?.length} className="btn btn-solid">
                  Try the illustrative demo
                </button>
              )}
              <a href={REPORT_URL} className="btn btn-line">Read the local-model report</a>
            </div>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-(--mute)" data-testid="hero-status">
              <span className="tag mr-2 border border-current">{meta?.live ? 'Live' : 'Simulated'}</span>
              {meta?.live
                ? 'Scans on this site can attack a real model, and setup shows the cost before anything is sent.'
                : 'The demo is simulated: no model is attacked and the outcomes are made up.'}{' '}
              The report is a real scan of a small open model on a laptop, not a production chatbot.{' '}
              To scan your own chatbot,{' '}
              <span className="whitespace-nowrap">
                <button type="button" onClick={onStart} className="underline underline-offset-4 hover:text-ink">
                  start setup
                </button>
                :
              </span>{' '}
              it shows the mode and cost first.
            </p>
          </div>
          <Mechanism />
        </div>
      </section>

      {rest && (<>
      {/* The one real result so far, graded language by language. */}
      <LocalEvidence className="cv border-t border-(--line)" />

      {/* Why it matters, with every language's own name as the evidence of the range. */}
      <section data-surface="ink" className="cv ink">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:py-24">
          <h2 className="display max-w-3xl text-[clamp(1.9rem,3.6vw,3rem)]">
            Most guardrail testing happens in English.
          </h2>
          <p className="mt-6 max-w-2xl text-lg text-(--mute)">
            A school, a clinic or a bank serves families who type in Hindi, Tagalog, Vietnamese and Spanish, and the same
            bot answers all of them. PolyGuard sends one set of attacks in every language below, scores each reply the
            same way, and uses statistics that say so when there is no gap at all.
          </p>
          {others.length > 0 && (
            <ul className="mt-12 flex flex-wrap gap-x-5 gap-y-2 text-[clamp(1.15rem,2vw,1.6rem)] font-semibold leading-snug" aria-label={`The ${count} languages PolyGuard tests, each in its own script`}>
              {(meta?.languages || []).map((l) => (
                <li key={l.code} dir="auto" lang={l.code} title={l.name}>{l.native}</li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* The gallery: one attack, written eight more ways. */}
      <section data-surface="paper" className="paper relative">
        <Torn side="top" />
        <Torn side="bottom" />
        <div className="ruler" />
        <div className="mx-auto max-w-7xl px-5 py-20 sm:py-24">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <h2 className="display max-w-2xl text-[clamp(1.9rem,3.6vw,3rem)]">The same attack, written in {count} languages.</h2>
            <p className="max-w-sm text-(--mute)">
              “{english}” is where a prompt injection usually starts. Here it is in eight of them.
            </p>
          </div>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {gallery.map((g) => g.lang && <Specimen key={g.code} lang={g.lang} text={g.text} />)}
          </div>
        </div>
      </section>

      {/* How a scan works, in four steps beside a finished board. */}
      <ScrollStory languages={others} />

      {/* The question every result raises, answered on its own page. */}
      <section data-surface="ink" className="ink">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 border-t border-(--line) px-5 py-12 sm:flex-row sm:items-center">
          <p className="max-w-3xl text-[clamp(1.3rem,2.4vw,1.9rem)] font-semibold leading-snug">
            Some language always comes out worst, even when a bot treats every language the same. The method page shows
            how PolyGuard tells a real gap from luck.
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
      <section data-surface="on-hi" className="on-hi px-3 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-16 sm:px-4 sm:pb-5">
        <div className="ink relative rounded-[36px] px-6 pb-10 pt-20 text-center sm:px-10">
          <svg viewBox="0 0 240 40" className="absolute -top-[39px] left-1/2 h-10 w-60 -translate-x-1/2 fill-ink" aria-hidden="true">
            <path d="M0 40 C 40 40, 50 0, 90 0 L 150 0 C 190 0, 200 40, 240 40 Z" />
          </svg>
          {/* The one place the heavy capitals and the serif meet, besides the wordmark. */}
          <h2 className="display display-caps mx-auto max-w-5xl text-[clamp(2.2rem,5.4vw,4.8rem)]">
            Find out where your bot <span className="serif">says yes.</span>
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-(--mute)">
            {meta?.examples?.length ? `${meta.examples.length} example chatbots are ready` : 'Example chatbots are ready'}, or paste the instructions your own bot runs on.
          </p>
          <button type="button" onClick={onStart} className="btn btn-solid mt-8">Scan a chatbot</button>
          <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-(--line) pt-6 text-sm sm:flex-row">
            <p className="text-(--mute)">PolyGuard is a defensive tool. Test only systems you own or are authorized to test.</p>
            <div className="flex items-center gap-5">
              <MotionSwitch />
              {onReview && (
                <button type="button" onClick={onReview} className="caption underline underline-offset-4">Translation review</button>
              )}
              <a href={REPO} target="_blank" rel="noopener" className="caption underline underline-offset-4">
                Source, audit and preregistration
              </a>
            </div>
          </div>
        </div>
      </section>
      </>)}
    </main>
  )
}
