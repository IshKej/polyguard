import BANK_COUNTS from '../bank-counts.json'
import LOCAL from '../local-example.json'
import LocalEvidence, { REPORT_URL } from './LocalEvidence'
import { useEffect, useMemo, useRef, useState } from 'react'
import { MotionSwitch } from './Chrome'
import HeroBubbles from './HeroBubbles'
import Chapter from './Chapter'
import Mechanism from './Mechanism'
import ScrollStory from './ScrollStory'
import SpotTheAttack from './SpotTheAttack'
import { useMotionOff } from '../lib/motion'
import { outcomes } from '../lib/outcomes'
import { PEOPLE_DETAIL, PEOPLE_LINE, REVIEWERS } from '../lib/people'

const REPO = 'https://github.com/IshKej/polyguard'
const EVERY = 2800 // ms on each language in the hero

// The hero walks through the scan's languages: the twenty written for the project
// and every language that let an attack through, breaks spread among the holds.
// The strip below shows all of them, so the walk never hides how rare a break was.
const WALK = ['cy', 'hi', 'es', 'zh', 'tr', 'ja', 'ar', 'fa', 'ko', 'fr', 'ceb', 'ru', 'pt', 'kk', 'de', 'vi', 'lt', 'it',
  'gu', 'sr', 'pl', 'tl', 'az', 'uk', 'el', 'id'].filter((c) => LOCAL.languages[c])

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

// Draws its highlighter stroke once on screen, and again whenever `again` changes.
function Marked({ children, again, className = '', ...rest }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    el.classList.remove('drawn')
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { requestAnimationFrame(() => el.classList.add('drawn')); io.disconnect() }
    }, { threshold: 0.5 })
    io.observe(el)
    return () => io.disconnect()
  }, [again])
  return <span ref={ref} className={`hl ${className}`} {...rest}>{children}</span>
}

export default function Landing({ meta, onStart, onTry, onMethod, onReview }) {
  const others = useMemo(() => (meta?.languages || []).filter((l) => l.code !== 'en'), [meta])
  // Until /api/meta answers (or if it fails), the counts the build wrote from the
  // bank itself: never a hard-coded number that goes stale.
  const count = meta?.languages?.length ?? BANK_COUNTS.languages
  const attacks = BANK_COUNTS.attacks
  const all = useMemo(() => outcomes().filter((o) => o.code !== 'en'), [])
  const broke = all.filter((o) => o.kept > 0).length
  const reduce = useMotionOff()
  // Reviewers credited by name, from the review data the review pages load anyway;
  // fetched after the page is up so the home page's first load stays small.
  const [named, setNamed] = useState([])
  useEffect(() => {
    let live = true
    import('../review-data.json').then(({ default: R }) => {
      if (live) setNamed(R.languages.filter((l) => l.credit && l.credit !== R.withheld))
    }).catch(() => {})
    return () => { live = false }
  }, [])

  // The language the hero is on: walks on its own with motion on, stays on Welsh
  // with motion off, and stays wherever the visitor picks.
  const [i, setI] = useState(0)
  const [picked, setPicked] = useState(null)
  useEffect(() => {
    if (reduce || picked) return undefined
    const id = setInterval(() => setI((n) => (n + 1) % WALK.length), EVERY)
    return () => clearInterval(id)
  }, [reduce, picked])
  const code = picked || (reduce ? 'cy' : WALK[i])
  const lang = LOCAL.languages[code]

  // Keep the strip's language in view as the hero walks.
  const strip = useRef(null)
  useEffect(() => {
    const box = strip.current
    const chip = box?.querySelector(`[data-code="${code}"]`)
    if (!box || !chip) return
    box.scrollTo({ left: chip.offsetLeft - box.clientWidth / 2 + chip.clientWidth / 2, behavior: reduce ? 'auto' : 'smooth' })
  }, [code, reduce])

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
      {/* Hero: the question in three voices, and the answer from the real scan. */}
      <section data-surface="paper" className="paper relative flex min-h-[min(100svh,980px)] flex-col">
        <div className="mx-auto grid w-full max-w-7xl flex-1 content-center gap-x-12 gap-y-9 px-5 pb-10 pt-28 lg:grid-cols-[minmax(0,1.12fr)_minmax(0,.88fr)] lg:pt-28">
          <div className="self-end">
            <h1 className="display display-caps text-[clamp(2.3rem,5vw,4.6rem)]">
              Your chatbot says <span className="serif text-[1.08em]">no</span> in English.
              <br className="hidden sm:block" />{' '}
              Does it say <span className="serif text-[1.08em]">no</span> in{' '}
              <span className="whitespace-nowrap">
                <Marked again={code} dir="auto" lang={code} className="serif inline-block text-[1.08em] normal-case leading-[1.3]">{lang.native}</Marked>?
              </span>
            </h1>
            <p className="mt-7 max-w-lg text-lg text-(--mute)">
              PolyGuard sends the same attacks in {count} languages and marks the exact place where a chatbot’s rules
              give way.
            </p>
          </div>
          <div className="lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:self-center">
            <HeroBubbles code={code} name={lang.name} native={lang.native} animate={!reduce && !picked} />
          </div>
          <div className="self-start">
            <div className="flex flex-wrap gap-3">
              {onTry && (
                <button type="button" onClick={onTry} disabled={!meta?.examples?.length} className="btn btn-solid">
                  Watch a scan <span className="tag bg-(--btn-text) text-(--btn)">Simulated</span>
                </button>
              )}
              <button type="button" onClick={onStart} className="btn btn-line">Scan your own bot</button>
            </div>
            <p className="mt-5 max-w-lg text-sm leading-relaxed text-(--mute)" data-testid="hero-status">
              {meta?.live
                ? 'Scans on this site can attack a real model, and setup shows the cost before anything is sent.'
                : 'The demo is simulated: no model is attacked and its outcomes are made up.'}{' '}
              The bubbles are not: they are real replies from a small open model on a laptop, not a production chatbot.{' '}
              <a href={REPORT_URL} className="whitespace-nowrap underline underline-offset-4 hover:text-ink">Read the local-model report</a>
            </p>
          </div>
        </div>

        {/* Every language in the scan, marked by what it did. Pick one and the hero answers in it. */}
        <div className="relative border-t border-(--line)">
          <div className="mx-auto flex max-w-7xl items-center gap-4 px-5 py-3">
            <p className="caption hidden shrink-0 sm:block">
              <span className="tabular-nums">{broke}</span> of {all.length + 1} languages let an attack through
            </p>
            <div
              ref={strip} role="group" aria-label="Every language in the real scan; pick one to see its result"
              className="flex min-w-0 flex-1 gap-1 overflow-x-auto py-1 [scrollbar-width:none]"
            >
              {all.map((o) => {
                const on = o.code === code
                const red = o.kept > 0
                return (
                  <button
                    key={o.code} data-code={o.code} type="button" aria-pressed={on}
                    onClick={() => setPicked(o.code)}
                    title={`${o.name}: ${red ? `got through ${o.kept} of ${LOCAL.per_language}` : o.excluded ? 'left out, failed the capability check' : `held all ${LOCAL.per_language}`}`}
                    className={`hl-hover relative shrink-0 rounded-md px-3 py-1.5 font-semibold transition-colors ${on ? 'bg-ink text-paper' : 'hover:text-ink'} ${o.excluded ? 'text-(--mute) line-through' : ''}`}
                  >
                    <span dir="auto" lang={o.code} className={on ? '' : 'hl'}>{o.native}</span>
                    {red && <span aria-hidden="true" className="absolute right-1 top-1 size-1.5 rounded-full bg-red-text" />}
                  </button>
                )
              })}
            </div>
            {picked && (
              <button type="button" onClick={() => setPicked(null)} className="hl-hover caption shrink-0"><span className="hl">Walk again</span></button>
            )}
          </div>
        </div>
      </section>

      {rest && (<>
      {/* The numbers, set as objects. */}
      <section data-surface="ink" className="ink" aria-label="PolyGuard in numbers">
        <dl className="mx-auto grid max-w-7xl grid-cols-2 gap-x-6 gap-y-10 px-5 py-14 sm:py-16 lg:grid-cols-4">
          {[
            [count, 'languages, each in its own script'],
            [attacks.toLocaleString('en-US'), 'attacks in a full scan, scored the same way'],
            [meta?.categories?.length ?? 5, 'kinds of attack, from override to hidden instructions'],
            [REVIEWERS, 'language professors and native speakers who shaped the bank'],
          ].map(([n, label]) => (
            <div key={label} className="border-t border-(--line) pt-4">
              <dt className="sr-only">{label}</dt>
              <dd>
                <span className="display block text-[clamp(3rem,7vw,6rem)] leading-none tabular-nums">{n}</span>
                <span className="mt-3 block max-w-[16rem] text-(--mute)">{label}</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {/* 01: one real attack, worked through. */}
      <section data-surface="paper" className="paper cv relative">
        <div className="ruler" />
        <div className="mx-auto grid max-w-7xl items-start gap-12 px-5 py-20 sm:py-24 lg:grid-cols-[minmax(0,.8fr)_minmax(0,1.2fr)]">
          <div className="lg:sticky lg:top-28">
            <Chapter n="01">One attack</Chapter>
            <h2 className="display display-caps text-[clamp(2.2rem,4.6vw,4.2rem)]">
              Same question. <span className="serif">Two answers.</span>
            </h2>
            <p className="mt-6 max-w-md text-lg text-(--mute)">
              The attack is a customer message telling the bot to drop its rules and print a code word. In English the bot
              refuses. In Welsh it prints the code word. Four steps, every word from the real scan.
            </p>
          </div>
          <Mechanism />
        </div>
      </section>

      {/* 02: why it matters, with every language's own name as the evidence of the range. */}
      <section data-surface="ink" className="cv ink">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:py-28">
          <Chapter n="02">The gap</Chapter>
          <h2 className="display display-caps max-w-5xl text-[clamp(2.2rem,5.2vw,4.8rem)]">
            Most guardrail testing <span className="serif">happens in English.</span>
          </h2>
          <p className="mt-6 max-w-2xl text-lg text-(--mute)">
            A school, a clinic or a bank serves families who type in Hindi, Tagalog, Vietnamese and Spanish, and the same
            bot answers all of them. PolyGuard sends one set of attacks in every language below and scores each reply the
            same way.
          </p>
          {others.length > 0 && (
            <ul className="mt-12 flex flex-wrap gap-x-6 gap-y-3 text-[clamp(1.2rem,2.3vw,1.9rem)] font-semibold leading-[1.5]" aria-label={`The ${count} languages PolyGuard tests, each in its own script`}>
              {(meta?.languages || []).map((l) => (
                <li key={l.code} dir="auto" lang={l.code} title={l.name}>{l.native}</li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* 03: how a scan works, in four steps beside a finished board. */}
      <ScrollStory languages={others} chapter="03" />

      {/* 04: the question every result raises, on the highlighter. */}
      <section data-surface="on-hi" className="on-hi cv">
        <div className="mx-auto grid max-w-7xl items-end gap-10 px-5 py-20 sm:py-24 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,.7fr)]">
          <div>
            <Chapter n="04">The proof</Chapter>
            <h2 className="display display-caps text-[clamp(2.2rem,5.2vw,4.8rem)]">
              Some language always comes out worst. <span className="serif">Is the gap real?</span>
            </h2>
          </div>
          <div>
            <p className="text-lg">
              Scan a bot that treats every language exactly the same, and one of them will still look worse by luck.
              PolyGuard shuffles the results a thousand times and only calls a gap real when luck rarely makes one that big.
            </p>
            <button type="button" onClick={onMethod} className="btn btn-solid mt-7">See how we know</button>
          </div>
        </div>
      </section>

      {/* 05: the one real result so far, graded language by language. */}
      <LocalEvidence chapter="05" className="border-t border-(--line)" />

      {/* 06: the people who shaped the bank. */}
      <section data-surface="ink" className="cv ink">
        <div className="mx-auto max-w-7xl px-5 py-20 sm:py-28">
          <Chapter n="06">The people</Chapter>
          <h2 className="display display-caps max-w-5xl text-[clamp(2.2rem,5.2vw,4.8rem)]">
            {REVIEWERS} professors and native speakers. <span className="serif">One attack bank.</span>
          </h2>
          <p className="mt-6 max-w-2xl text-lg text-(--mute)">{PEOPLE_LINE} {PEOPLE_DETAIL}</p>
          <ul className="mt-12 grid gap-px overflow-hidden rounded-[10px] border border-(--line) bg-(--line) sm:grid-cols-2 lg:grid-cols-3" aria-label="Reviewers credited by name, with their agreement">
            {named.map((l) => (
              <li key={l.code} className="bg-(--bg) p-6">
                <div dir="auto" lang={l.code} className="display text-[1.6rem] leading-tight">{l.native}</div>
                <div className="caption mt-1 text-(--mute)">{l.name}</div>
                <p className="mt-5 leading-snug">{l.credit}</p>
              </li>
            ))}
            <li className="bg-(--bg) p-6">
              <div className="display text-[1.6rem] leading-tight">And more</div>
              <div className="caption mt-1 text-(--mute)">Names withheld</div>
              <p className="mt-5 leading-snug text-(--mute)">Reviewers who asked not to be named are credited as a native speaker, nothing else.</p>
            </li>
          </ul>
          {onReview && (
            <button type="button" onClick={onReview} className="btn btn-line mt-10">Review coverage, language by language</button>
          )}
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
