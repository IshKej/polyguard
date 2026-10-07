import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getGame, getGameStats, label, postGameAnswer } from '../api'

const ROUNDS = 6

// Six real messages from the bank, each in a different language, roughly half of
// them attacks. Chosen fresh for every game.
function deal(items) {
  const byLang = {}
  for (const it of items) (byLang[it.lang] ||= []).push(it)
  const langs = Object.keys(byLang).sort(() => Math.random() - 0.5).slice(0, ROUNDS)
  return langs.map((lang) => {
    const want = Math.random() < 0.5
    const pool = byLang[lang].filter((it) => it.attack === want)
    const from = pool.length ? pool : byLang[lang]
    return from[Math.floor(Math.random() * from.length)]
  })
}

const VERDICT = [
  [6, 'Six for six. Now do that for every message, in every language, all day. That is your chatbot’s job.'],
  [4, 'Most of these were in languages you don’t read, so some of that was a guess. Your chatbot can’t guess.'],
  [0, 'Hard, isn’t it? In a language you can’t read, an attack looks like any other message. That is the gap PolyGuard measures.'],
]

// The game, the honest version of "break the bot yourself": no model is involved,
// so it needs no key. It asks the question every multilingual chatbot has to
// answer, about real messages PolyGuard sends.
export default function SpotTheAttack({ languages, onStart }) {
  const section = useRef(null)
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [deck, setDeck] = useState([])
  const [answers, setAnswers] = useState([])
  const [revealed, setRevealed] = useState(false)
  const [finished, setFinished] = useState(false)
  const [crowd, setCrowd] = useState(null)

  // Load the messages only when the game is close to the screen.
  useEffect(() => {
    const el = section.current
    if (!el || items) return undefined
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return
      io.disconnect()
      getGame().then((g) => { setItems(g.items); setDeck(deal(g.items)) }).catch((x) => setError(x.message))
    }, { rootMargin: '600px' })
    io.observe(el)
    return () => io.disconnect()
  }, [items])

  const round = answers.length - (revealed ? 1 : 0)
  const item = deck[round]
  const last = answers[answers.length - 1]
  const done = finished
  const score = answers.filter((a) => a.correct).length
  const lang = item && languages.find((l) => l.code === item.lang)

  const guess = useCallback((attack) => {
    if (!item || revealed) return
    setAnswers((a) => [...a, { id: item.id, lang: item.lang, correct: attack === item.attack }])
    setRevealed(true)
    postGameAnswer(item.id, attack)       // anonymous: which message, and the guess
  }, [item, revealed])
  const next = () => setRevealed(false)
  const again = () => { setDeck(deal(items)); setAnswers([]); setRevealed(false); setFinished(false); setCrowd(null) }

  // A and S answer from the keyboard, Enter moves on, once the game has focus.
  const onKey = (e) => {
    if (e.target.closest('textarea, input')) return
    if (!revealed && (e.key === 'a' || e.key === 'A')) guess(true)
    else if (!revealed && (e.key === 's' || e.key === 'S')) guess(false)
    else if (revealed && !done && e.key === 'Enter') { e.preventDefault(); if (round + 1 < deck.length) next(); else setFinished(true) }
  }

  const dots = useMemo(() => Array.from({ length: ROUNDS }, (_, n) => answers[n]), [answers])

  // At the end, how everyone else did in the same languages, once a language has
  // enough answers for the number to mean something.
  useEffect(() => {
    if (!finished) return undefined
    let alive = true
    getGameStats().then((g) => alive && setCrowd(g)).catch(() => alive && setCrowd({ languages: [], min_answers: 10 }))
    return () => { alive = false }
  }, [finished])
  const crowdHere = useMemo(() => {
    if (!crowd) return []
    const mine = new Set(answers.map((a) => a.lang))
    return crowd.languages.filter((l) => mine.has(l.lang))
  }, [crowd, answers])

  return (
    <section ref={section} data-surface="paper" className="paper relative" onKeyDown={onKey}>
      <div className="mx-auto grid max-w-7xl items-start gap-12 px-5 py-20 sm:py-28 lg:grid-cols-[minmax(0,.8fr)_minmax(0,1.2fr)]">
        <div>
          <h2 className="display text-[clamp(2.4rem,5.6vw,5rem)]">
            Your turn.
            <br />
            <span className="serif">Spot the attack.</span>
          </h2>
          <p className="mt-6 max-w-md text-(--mute)">
            Six messages, each in a different language. Some are attacks, some are ordinary requests. A chatbot has to
            tell them apart every time, in every language.
          </p>
          <div className="mt-8 flex gap-2" role="img" aria-label={`${score} right of ${answers.length} answered`}>
            {dots.map((a, n) => (
              <span
                key={n}
                className={`size-4 rounded-full border-2 border-ink transition-colors duration-300 ${a ? (a.correct ? 'bg-hi' : 'bg-red') : ''}`}
              />
            ))}
          </div>
          <p className="caption mt-6 max-w-sm text-(--mute)">
            Real messages from PolyGuard’s attack bank. The code word each one asks for is the same in every message,
            so it can’t give the answer away.
          </p>
        </div>

        <div className="ink relative min-h-[26rem] rounded-[22px] p-6 sm:p-8" aria-live="polite">
          {error && <p className="text-(--mute)">The game couldn’t load its messages. {error}</p>}
          {!error && !item && !done && <p className="caption text-(--mute)">Dealing the messages…</p>}

          {done ? (
            <div className="flex min-h-[22rem] flex-col justify-between">
              <div>
                <div className="caption text-(--mute)">Your score</div>
                <div className="display mt-2 text-[clamp(4rem,10vw,7rem)] tabular-nums">
                  {score}<span className="serif text-[.6em] text-(--mute)"> of {deck.length}</span>
                </div>
                <p className="mt-4 max-w-md text-lg">{VERDICT.find(([min]) => score >= min)[1]}</p>
                {crowd && (
                  <div className="mt-6 max-w-md">
                    <div className="caption text-(--mute)">Everyone else, in the same languages</div>
                    {crowdHere.length ? (
                      <ul className="mt-2 space-y-1">
                        {crowdHere.map((l) => (
                          <li key={l.lang}>
                            {l.name}: <span className="font-semibold">{Math.round(l.accuracy * 100)}%</span> right
                            <span className="text-(--mute)">, from {l.answers} answers</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-(--mute)">Not enough answers yet. A language shows here once it has {crowd.min_answers}.</p>
                    )}
                  </div>
                )}
              </div>
              <div className="mt-8 flex flex-wrap gap-3">
                <button type="button" onClick={onStart} className="btn btn-solid">Scan a chatbot</button>
                <button type="button" onClick={again} className="btn btn-line">Play again</button>
              </div>
            </div>
          ) : item && (
            <div key={item.id} className="flex min-h-[22rem] animate-[pop_.35s_cubic-bezier(.3,.7,.3,1)_both] flex-col">
              <div className="flex items-center justify-between gap-3">
                <span className="caption text-(--mute)">Message {round + 1} of {deck.length}</span>
                <span className="tag border border-current">{lang ? `${lang.native}, ${lang.name}` : item.lang}</span>
              </div>
              <p dir="auto" lang={item.lang} className="mt-6 text-[clamp(1.25rem,2.2vw,1.65rem)] font-semibold leading-snug">
                <span className={`hl ${revealed && item.attack ? 'drawn' : ''}`}>{item.text}</span>
              </p>

              {revealed ? (
                <div className="mt-auto pt-8">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`tag ${last?.correct ? 'bg-hi text-ink' : 'bg-red text-ink'}`}>{last?.correct ? 'Right' : 'Not quite'}</span>
                    <span className="font-semibold">
                      {item.attack ? `An attack: ${label(item.category).toLowerCase()}.` : 'An ordinary request. PolyGuard sends these too, to check the bot works in this language at all.'}
                    </span>
                  </div>
                  <p className="caption mt-5 text-(--mute)">In English</p>
                  <p className="mt-1 text-(--mute)">{item.english}</p>
                  {round + 1 < deck.length ? (
                    <button type="button" onClick={next} className="btn btn-solid btn-sm mt-6">Next message</button>
                  ) : (
                    <button type="button" onClick={() => setFinished(true)} className="btn btn-solid btn-sm mt-6">See your score</button>
                  )}
                </div>
              ) : (
                <div className="mt-auto flex flex-wrap gap-3 pt-8">
                  <button type="button" onClick={() => guess(true)} className="btn bg-red text-ink [--btn:var(--color-red)] hover:bg-transparent hover:text-red">
                    It’s an attack <kbd className="caption hidden opacity-60 sm:inline">A</kbd>
                  </button>
                  <button type="button" onClick={() => guess(false)} className="btn btn-solid">
                    It’s safe <kbd className="caption hidden opacity-60 sm:inline">S</kbd>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
