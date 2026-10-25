import LOCAL from '../local-example.json'
import Chapter from './Chapter'

// The one real result the site can show today, as a graded sheet: every
// language, every break the review kept, every judge call it overturned, and the
// language left out, with the limits stated. All of it comes from the 2026-10-11
// scan and its 2026-10-12 reanalysis (web/src/local-example.json, written by
// publish_example.py from results/local/2026-10-11/). None of it is a study result.
export const REPORT_URL = '/examples/real-scan-2026-10-11.html'
const EVIDENCE = 'https://github.com/IshKej/polyguard/tree/main/results/local/2026-10-11'
const TIERS = [['high', 'High resource'], ['mid', 'Mid resource'], ['low', 'Low resource']]
// The most breaks any language had: the grader's pen goes round those cells.
const MOST = Math.max(...Object.values(LOCAL.languages).map((l) => l.kept))

const LIMITS = [
  'One small model, so this says nothing about the chatbots companies deploy.',
  `When it ran, ${Object.values(LOCAL.languages).filter((l) => l.machine).length} of the ${Object.keys(LOCAL.languages).length} languages were machine translated with no native speaker review.`,
  'It is not the pre-registered study: no production chatbot has been scanned, and no paid-model results are published yet.',
]

function Cell({ code, l }) {
  const n = LOCAL.per_language
  let tone = 'bg-(--card)'
  let note = null
  if (code === 'en') { tone = 'bg-hi text-ink font-semibold'; note = `0 of ${n}, the reference` }
  else if (l.excluded) { tone = 'border-[1.5px] border-dashed border-(--mute) text-(--mute)'; note = 'left out' }
  else if (l.kept) { tone = `bg-red text-ink ${l.kept === MOST ? 'pen-ring' : ''}`; note = `${l.kept} of ${n} got through` }
  else if (l.overturned) { tone = 'bg-(--bg) outline-2 -outline-offset-2 outline-red-text'; note = <s className="text-red-text decoration-[1.5px]">judge: got through</s> }
  return (
    <li className={`rounded-[5px] px-2 py-1 text-[.8rem] leading-tight ${tone}`}>
      <span lang={code} title={l.native}>{l.name}</span>
      {note && <span className="block text-[.68rem]">{note}</span>}
    </li>
  )
}

export default function LocalEvidence({ className = '', chapter }) {
  const langs = Object.entries(LOCAL.languages)
  const ex = LOCAL.excluded[0]
  const notes = [
    `${LOCAL.kept} breaks in ${LOCAL.attacks.toLocaleString('en-US')} attacks, after an AI assisted review not yet checked by the author. The judge alone flagged ${LOCAL.judged_breaks}; the review kept ${LOCAL.kept}.`,
    `${LOCAL.kept_extraction} of the ${LOCAL.kept} are the bot printing its own instructions, scored by exact overlap with no judge involved.`,
    `No gap between high and low resource languages (tier test p = ${LOCAL.tier_p.toFixed(3)}). One small model cannot say anything about production chatbots.`,
    ex && `${LOCAL.languages[ex.code].name} is left out: the model followed ${ex.followed} of its ${ex.of} harmless requests, against ${LOCAL.english_followed} of ${LOCAL.english_of} in English.`,
  ].filter(Boolean)
  return (
    <section data-surface="paper" className={`paper ${className}`} aria-labelledby="local-evidence">
      <div className="mx-auto max-w-7xl px-5 py-16 sm:py-20">
        {chapter && <Chapter n={chapter}>The result</Chapter>}
        <p className="caption text-(--mute)">Real local diagnostic, not the simulated demo</p>
        {chapter ? (
          <h2 id="local-evidence" className="display text-[clamp(1.9rem,3.6vw,3rem)]">
            {LOCAL.kept} breaks in {LOCAL.attacks.toLocaleString('en-US')} attacks. One real scan, graded.
          </h2>
        ) : (
          <h2 id="local-evidence" className="mt-2 max-w-3xl text-[clamp(1.6rem,3vw,2.3rem)] font-bold leading-tight">
            One real scan so far, graded language by language.
          </h2>
        )}
        <p className="mt-3 max-w-3xl text-(--mute)">
          {LOCAL.model} on a laptop, behind the example store support bot, scanned {LOCAL.scanned}: {LOCAL.per_language}{' '}
          attacks in each of {langs.length} languages, judged by {LOCAL.judge}. Not a production chatbot.
        </p>

        <figure className="mt-8 rounded-[10px] border-2 border-ink p-4 sm:p-5" aria-label="The local scan's result for every language">
          <ul className="flex flex-wrap gap-x-5 gap-y-2 text-[.8rem] text-(--mute)" aria-label="Key">
            <li><i className="mr-1.5 inline-block size-3.5 rounded-[3px] bg-red align-[-2px]" />got through, kept by the review</li>
            <li><i className="mr-1.5 inline-block size-3.5 rounded-[3px] outline-2 -outline-offset-2 outline-red-text align-[-2px]" />the judge said got through, the review found a refusal</li>
            <li><i className="mr-1.5 inline-block size-3.5 rounded-[3px] border-[1.5px] border-dashed border-(--mute) align-[-2px]" />left out, failed the capability check</li>
            <li><i className="mr-1.5 inline-block size-3.5 rounded-[3px] bg-(--card) align-[-2px]" />held all {LOCAL.per_language}</li>
          </ul>
          {TIERS.map(([tier, label]) => {
            const row = langs.filter(([, l]) => l.tier === tier).sort((a, b) => a[1].name.localeCompare(b[1].name))
            return (
              <div key={tier} className="mt-3 grid gap-2 border-t border-(--line) pt-3 md:grid-cols-[8.5rem_minmax(0,1fr)]">
                <h3 className="text-[.85rem] font-semibold md:pt-1">{label} ({row.length})</h3>
                <ul className="flex flex-wrap gap-1.5">{row.map(([code, l]) => <Cell key={code} code={code} l={l} />)}</ul>
              </div>
            )
          })}
          <div className="mt-4 grid gap-4 border-t-2 border-ink pt-4 sm:grid-cols-2 lg:grid-cols-4">
            {notes.map((n) => <p key={n} className="border-l-[3px] border-red-text pl-3 text-[.875rem] font-medium leading-snug text-red-text">{n}</p>)}
          </div>
        </figure>

        <div className="mt-8 max-w-4xl border-l-4 border-ink pl-5">
          <p className="font-bold">What it cannot show</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-(--mute)">
            {LIMITS.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <a href={REPORT_URL} className="btn btn-solid">Read the local-model report</a>
          <a href={EVIDENCE} target="_blank" rel="noopener" className="btn btn-line">Every reply, on GitHub</a>
        </div>
      </div>
    </section>
  )
}
