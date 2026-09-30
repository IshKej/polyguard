import { firstSentence } from '../api'
import Board from './Board'

// The scan as it happens. Every result arrives over the wire and flips one cell,
// so what is on screen is the scan itself, not a progress bar standing in for it.
export default function LiveScan({ languages, outcomes, expected, done, total, broke, latest, live, title, error, onCancel }) {
  const share = total ? done / total : 0
  return (
    <main className="on-page mx-auto max-w-6xl px-5 pb-24 pt-10">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <span className="tag border-2 border-ink">{live ? 'Live scan' : 'Simulated scan'}</span>
          <h1 className="display mt-3 text-[clamp(2.4rem,6vw,4.5rem)]">Attacking {title}</h1>
          <p className="mt-1 text-dim">
            {languages.length} language{languages.length === 1 ? '' : 's'}, {expected} attack{expected === 1 ? '' : 's'} each
          </p>
        </div>
        <div className="flex gap-10">
          <div>
            <div className="display text-6xl tabular-nums">{done}</div>
            <div className="text-dim">of {total || '…'} fired</div>
          </div>
          <div>
            <div className={`display text-6xl tabular-nums ${broke ? 'text-red' : 'text-green'}`}>{broke}</div>
            <div className="text-dim">got through</div>
          </div>
        </div>
      </div>

      <div
        className="mt-6 h-2 overflow-hidden rounded-full bg-rule"
        role="progressbar" aria-label="Scan progress" aria-valuemin={0} aria-valuemax={total || 1} aria-valuenow={done}
      >
        <div className="h-full bg-accent transition-[width] duration-200" style={{ width: `${share * 100}%` }} />
      </div>

      <div className="mt-4 flex min-h-8 items-center gap-3 text-dim" aria-hidden="true">
        {latest && (
          <>
            <span className={`tag shrink-0 ${latest.error ? 'bg-ink text-page' : latest.broke ? 'bg-red text-on-signal' : 'bg-green text-on-signal'}`}>
              {latest.error ? 'No answer' : latest.broke ? 'Got through' : 'Held'}
            </span>
            <span className="shrink-0 font-semibold text-ink">{latest.name}</span>
            <span dir="auto" lang={latest.lang} className="truncate">{firstSentence(latest.attack)}</span>
          </>
        )}
      </div>

      {error ? (
        <div role="alert" className="panel mt-8 p-6">
          <p className="display text-3xl text-red">The scan stopped.</p>
          <p className="mt-2">{error}</p>
          <button type="button" onClick={onCancel} className="btn btn-line btn-sm mt-5">Back to setup</button>
        </div>
      ) : (
        <div className="mt-5">
          <Board languages={languages} outcomes={outcomes} expected={expected} columns={2} />
        </div>
      )}

      {!live && !error && (
        <p className="mt-5 max-w-3xl text-dim">
          This is a simulation. No model is being attacked, and the stand-in bot behaves the same in every
          language, so the pattern on the board is chance.
        </p>
      )}
    </main>
  )
}
