import { useMemo } from 'react'
import Board from './Board'

// How a scan works: four steps beside a finished board. It used to pin the page
// and play by scrolling; the page no longer captures the scroll, so this is the
// same still version everyone gets, whatever the motion setting.
const STEPS = [
  ['Pick a chatbot', 'Paste the instructions it runs on, or start from an example.'],
  ['Attack it', 'Five kinds of prompt injection, in every language, several phrasings each.'],
  ['Watch the board', 'A judge model scores whether the bot held or gave in, in each language of the bank. How reliable it is in each language is not established yet.'],
  ['Close the gap', 'See which languages broke, whether it is more than chance, and rules that make those attacks less likely to work.'],
]

const EXPECTED = 10
const outcomeFor = (li, ai) => ((li * 7 + ai * 13 + li * ai) % 10 < 3 ? 'broke' : 'held')

export default function ScrollStory({ languages }) {
  const board = useMemo(() => languages.slice(0, 7), [languages])
  const outcomes = useMemo(() => {
    const m = {}
    board.forEach((l, li) => { m[l.code] = Array.from({ length: EXPECTED }, (_, ai) => outcomeFor(li, ai)) })
    return m
  }, [board])

  return (
    <section id="how" data-surface="ink" className="ink scroll-mt-16">
      <div className="mx-auto grid max-w-7xl items-start gap-14 px-5 py-20 sm:py-28 lg:grid-cols-[minmax(0,.85fr)_minmax(0,1.15fr)]">
        <div>
          <h2 className="display text-[clamp(1.9rem,3.6vw,3rem)]">How a scan works</h2>
          <ol className="mt-10 space-y-5">
            {STEPS.map(([title, body], n) => (
              <li key={title} className="grid grid-cols-[3rem_1fr] gap-x-4">
                <span aria-hidden="true" className="display grid size-12 place-items-center rounded-md bg-hi text-2xl text-ink">{n + 1}</span>
                <span>
                  <span className="display block text-[1.55rem]">{title}</span>
                  <span className="mt-1 block max-w-sm text-(--mute)">{body}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
        <Board languages={board} outcomes={outcomes} expected={EXPECTED} compact caption="An illustration with made up outcomes. Highlighter held. Red got through." />
      </div>
    </section>
  )
}
