import { firstSentence } from '../api'
import Board from './Board'

// The scan as it happens. Every result arrives over the wire and flips one cell,
// so what is on screen is the scan itself, not a progress bar standing in for it.
export default function LiveScan({ languages, outcomes, expected, done, total, broke, latest, live, title, error, onCancel }) {
  const share = total ? done / total : 0
  return (
    <main data-surface="ink" className="ink min-h-screen">
      <div className="mx-auto max-w-7xl px-5 pb-24 pt-28">
        <div className="flex flex-wrap items-end justify-between gap-8">
          <div>
            <span className="tag border border-current text-(--mute)">{live ? 'Live scan' : 'Simulated scan'}</span>
            <h1 className="display mt-4 text-[clamp(2.4rem,5.2vw,4.6rem)]">
              Attacking <span className="serif">{title}.</span>
            </h1>
            <p className="caption mt-3 text-(--mute)">
              {languages.length} language{languages.length === 1 ? '' : 's'}, {expected} attack{expected === 1 ? '' : 's'} each
            </p>
          </div>
          <div className="flex gap-10">
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

        <div
          className="mt-8 h-2.5 overflow-hidden rounded-full bg-ink-3"
          role="progressbar" aria-label="Scan progress" aria-valuemin={0} aria-valuemax={total || 1} aria-valuenow={done}
        >
          <div className="h-full bg-hi transition-[width] duration-200" style={{ width: `${share * 100}%` }} />
        </div>

        <div className="mt-4 flex min-h-8 items-center gap-3 text-(--mute)" aria-hidden="true">
          {latest && (
            <>
              <span className={`tag shrink-0 ${latest.error ? 'bg-amber text-ink' : latest.broke ? 'bg-red text-ink' : 'bg-hi text-ink'}`}>
                {latest.error ? 'No answer' : latest.broke ? 'Got through' : 'Held'}
              </span>
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
