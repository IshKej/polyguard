import { useEffect, useRef, useState } from 'react'
import { firstSentence, label } from '../api'
import Board from './Board'

const VERDICT = (r) => (r.error ? ['No answer', 'bg-amber text-ink'] : r.broke ? ['Got through', 'bg-red text-ink'] : ['Held', 'bg-hi text-ink'])

// The last few attacks, the way a chat fills in: newest at the bottom, each one
// arriving as it lands, with what came of it.
function Feed({ recent }) {
  // A simulated scan lands about 40 results a second, faster than anyone can read,
  // so the feed catches up twice a second instead of on every result. New
  // messages slide in without fading, so the feed never looks washed out.
  const [shown, setShown] = useState(recent)
  const latest = useRef(recent)
  useEffect(() => { latest.current = recent }, [recent])
  useEffect(() => {
    const id = setInterval(() => setShown((prev) => (prev === latest.current ? prev : latest.current)), 500)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="flex h-[17rem] flex-col justify-end gap-3 overflow-hidden rounded-[18px] bg-ink-2 p-4 ring-1 ring-ink-3 [mask-image:linear-gradient(to_bottom,transparent,#000_28%)]">
      {shown.length === 0 && <p className="caption text-(--mute)">The first attacks are on their way.</p>}
      {shown.map((r) => {
        const [text, tone] = VERDICT(r)
        return (
          <div key={r.id} className="animate-[rise_.28s_cubic-bezier(.3,.7,.3,1)_both]">
            <div className="caption mb-1 flex items-center justify-between gap-2 text-(--mute)">
              <span className="truncate">{r.name}, {label(r.category).toLowerCase()}</span>
              <span className={`tag shrink-0 ${tone}`}>{text}</span>
            </div>
            <p dir="auto" lang={r.lang} className="line-clamp-2 rounded-[12px] rounded-br-[3px] bg-hi px-3 py-2 text-[.95rem] font-semibold leading-snug text-ink">
              {firstSentence(r.attack)}
            </p>
          </div>
        )
      })}
    </div>
  )
}

// The scan as it happens. Every result arrives over the wire and flips one cell,
// so what is on screen is the scan itself, not a progress bar standing in for it.
export default function LiveScan({ languages, outcomes, expected, done, total, broke, recent, live, title, error, onCancel }) {
  const share = total ? done / total : 0
  const latest = recent[recent.length - 1]
  return (
    <main data-surface="ink" className="ink min-h-screen">
      <div className="mx-auto max-w-7xl px-5 pb-24 pt-28">
        <div className="grid items-end gap-8 lg:grid-cols-[minmax(0,1fr)_24rem]">
          <div>
            <span className="tag border border-current text-(--mute)">{live ? 'Live scan' : 'Simulated scan'}</span>
            <h1 className="display mt-4 text-[clamp(2.4rem,5vw,4.4rem)]">
              Attacking <span className="serif">{title}.</span>
            </h1>
            <p className="caption mt-3 text-(--mute)">
              {languages.length} language{languages.length === 1 ? '' : 's'}, {expected} attack{expected === 1 ? '' : 's'} each
            </p>
            <div className="mt-8 flex gap-10">
              <div>
                <div className="display text-[4.5rem] tabular-nums">{done}</div>
                <div className="caption text-(--mute)">of {total || '…'} fired</div>
              </div>
              <div>
                <div className={`display text-[4.5rem] tabular-nums ${broke ? 'text-red' : 'text-hi'}`}>{broke}</div>
                <div className="caption text-(--mute)">got through</div>
              </div>
            </div>
          </div>
          <div className="hidden lg:block" aria-hidden="true">
            <Feed recent={recent} />
          </div>
        </div>

        <div
          className="mt-8 h-2.5 overflow-hidden rounded-full bg-ink-3"
          role="progressbar" aria-label="Scan progress" aria-valuemin={0} aria-valuemax={total || 1} aria-valuenow={done}
        >
          <div className="h-full bg-hi transition-[width] duration-200" style={{ width: `${share * 100}%` }} />
        </div>

        {/* On a phone the feed would push the board away, so only the latest attack is shown. */}
        <div className="mt-4 flex min-h-8 items-center gap-3 text-(--mute) lg:hidden" aria-hidden="true">
          {latest && (
            <>
              <span className={`tag shrink-0 ${VERDICT(latest)[1]}`}>{VERDICT(latest)[0]}</span>
              <span className="shrink-0 font-semibold text-paper">{latest.name}</span>
              <span dir="auto" lang={latest.lang} className="truncate">{firstSentence(latest.attack)}</span>
            </>
          )}
        </div>

        {error ? (
          <div role="alert" className="card mt-8 p-6">
            <p className="display text-3xl text-red">The scan stopped.</p>
            <p className="mt-2">{error}</p>
            <button type="button" onClick={onCancel} className="btn btn-line btn-sm mt-5">Back to setup</button>
          </div>
        ) : (
          <div className="mt-6">
            <Board languages={languages} outcomes={outcomes} expected={expected} columns={2} />
          </div>
        )}

        {!live && !error && (
          <p className="mt-6 max-w-3xl text-(--mute)">
            This is a simulation. No model is being attacked, and the stand-in bot behaves the same in every
            language, so the pattern on the board is chance.
          </p>
        )}
      </div>
    </main>
  )
}
